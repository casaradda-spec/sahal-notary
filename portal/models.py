import hashlib
import re
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe


class ClientProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='client_profile')
    national_id = models.CharField('Aqoonsiga Qaranka', max_length=40, blank=True)
    phone = models.CharField('Telefoonka', max_length=30, blank=True)
    city = models.CharField('Magaalada', max_length=80, blank=True)
    address = models.CharField('Cinwaanka', max_length=200, blank=True)
    signature = models.ImageField('Saxiixa', upload_to='signatures/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    @property
    def doc_count(self):
        return self.documents.count() + self.documents_as_party2.count()


class NotaryProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notary_profile')
    license_number = models.CharField('Lambarka Ruqsadda', max_length=40, blank=True)
    region = models.CharField('Gobolka', max_length=80, blank=True)
    seal_image = models.ImageField('Sawirka Shaambooyinka', upload_to='seals/', blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=5.0)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class DocumentTemplate(models.Model):
    class PartyType(models.TextChoices):
        ONE = 'ONE', 'Hal dhinac'
        TWO = 'TWO', 'Laba dhinac'

    title = models.CharField('Cinwaanka Qaabka', max_length=150)
    category = models.CharField('Nooca', max_length=80)
    party_type = models.CharField(max_length=4, choices=PartyType.choices, default=PartyType.ONE)
    requires_witnesses = models.BooleanField('U baahan yahay marqaatiyaal', default=False)
    body = models.TextField(
        'Qoraalka',
        help_text='Isticmaal {{client_name}}, {{client2_name}}, {{date}}, {{city}}, {{notary_name}}, '
        '{{notary_license}}, {{ref}} si loo buuxiyo si toos ah. Isticmaal {{client_signature}} '
        '(ama {{client1_signature}} / {{client2_signature}}) si loo geliyo saxiixa macmiilka.',
    )
    created_by = models.ForeignKey(
        NotaryProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='templates'
    )
    times_used = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def party_label(self):
        return 'Laba Dhinac' if self.party_type == self.PartyType.TWO else 'Hal Dhinac'

    def __str__(self):
        return self.title


PLACEHOLDER_RE = re.compile(r'\{\{\s*(\w+)\s*\}\}')


def _signature_html(client_profile):
    """Resolve a {{client_signature}}-style token into actual markup: the saved
    signature image, a "no signature on file" warning, or blank if there's no
    such party (e.g. {{client2_signature}} on a one-party document)."""
    if client_profile is None:
        return ''
    if not client_profile.signature:
        return format_html('<span class="sig-missing">Saxiix lama helin</span>')
    return format_html(
        '<img src="{}" alt="Saxiixa {}" style="max-height:60px; height:auto; width:auto;">',
        client_profile.signature.url,
        client_profile.user.get_full_name(),
    )


class Document(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Sugaya'
        SIGNED = 'SIGNED', 'La saxiixay'
        COMPLETED = 'COMPLETED', 'Dhammaystiran'

    ref = models.CharField(max_length=20, unique=True, editable=False)
    template = models.ForeignKey(DocumentTemplate, on_delete=models.PROTECT, related_name='documents')
    notary = models.ForeignKey(NotaryProfile, on_delete=models.PROTECT, related_name='documents')
    client = models.ForeignKey(ClientProfile, on_delete=models.PROTECT, related_name='documents')
    client2 = models.ForeignKey(
        ClientProfile, on_delete=models.PROTECT, related_name='documents_as_party2', null=True, blank=True
    )
    city = models.CharField(max_length=80, default='Muqdisho')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    rendered_body = models.TextField(editable=False)
    content_hash = models.CharField(max_length=64, editable=False)
    pdf_hash = models.CharField('SHA-256 PDF', max_length=64, editable=False, blank=True)
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    signed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.ref

    def missing_signature_labels(self):
        """Somali-language labels of signatures still needed before this document can be
        completed. The Witness model has no signature image of its own, so a required-witness
        check stands in for "witness signatures" here: at least one witness must be on record."""
        missing = []
        if not self.client.signature:
            missing.append(f'Saxiixa {self.client.user.get_full_name()}')
        if self.client2 and not self.client2.signature:
            missing.append(f'Saxiixa {self.client2.user.get_full_name()}')
        if self.template.requires_witnesses and not self.witnesses.exists():
            missing.append('Marqaatiyaal')
        return missing

    @property
    def body_paragraphs(self):
        # mark_safe() on a string doesn't survive str.split() — each fragment
        # comes back as a plain str, which Django's autoescape would re-escape
        # (mangling the <img>/<span> markup render_body() already produced).
        return [mark_safe(p) for p in self.rendered_body.split('\n') if p.strip()]

    @staticmethod
    def next_ref():
        last = Document.objects.order_by('-id').first()
        next_n = (last.id + 1) if last else 1
        return f'SNS-{4800 + next_n}'

    def render_body(self):
        text_context = {
            'client_name': self.client.user.get_full_name(),
            'client2_name': self.client2.user.get_full_name() if self.client2 else '',
            'date': timezone.now().strftime('%d %B %Y'),
            'city': self.city,
            'notary_name': self.notary.user.get_full_name(),
            'notary_license': self.notary.license_number,
            'ref': self.ref,
        }
        signature_context = {
            'client_signature': self.client,
            'client1_signature': self.client,
            'client2_signature': self.client2,
        }

        def replace(match):
            token = match.group(1)
            if token in signature_context:
                return _signature_html(signature_context[token])
            return escape(text_context.get(token, ''))

        # Escape the raw template body first — curly braces aren't in Django's
        # escape table, so {{token}} markers still match afterwards, while any
        # stray <, >, & typed into the template body is now safely escaped.
        # Each substitution is then escaped (text) or deliberately left as
        # trusted markup (signature image/warning), and the assembled result
        # is marked safe as a whole so templates render the <img> tags as-is.
        escaped_body = escape(self.template.body)
        return mark_safe(PLACEHOLDER_RE.sub(replace, escaped_body))

    def finalize(self):
        """Snapshot the rendered body and hash it. Call once, at creation."""
        if not self.ref:
            self.ref = self.next_ref()
        self.rendered_body = self.render_body()
        self.content_hash = hashlib.sha256(self.rendered_body.encode('utf-8')).hexdigest()


class Witness(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='witnesses')
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name


class AuditLog(models.Model):
    class Action(models.TextChoices):
        DOCUMENT_COMPLETED = 'DOCUMENT_COMPLETED', 'Dokumeenti la dhammeystiray'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=40, choices=Action.choices)
    document = models.ForeignKey(Document, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    details = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_action_display()} — {self.document.ref if self.document else "-"}'
