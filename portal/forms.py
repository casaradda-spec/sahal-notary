from django import forms
from django.utils.translation import gettext_lazy as _

from .models import ClientProfile, DocumentTemplate, NotaryProfile
from .utils import decode_signature_data_url


class UniqueClientFieldsMixin:
    """Validates phone/national_id uniqueness across ClientProfile.

    `instance_pk` (set by edit forms) excludes the profile being edited from the
    uniqueness check; create forms leave it None so every other client counts.
    """
    instance_pk = None

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            qs = ClientProfile.objects.filter(phone=phone)
            if self.instance_pk:
                qs = qs.exclude(pk=self.instance_pk)
            if qs.exists():
                raise forms.ValidationError('Lambarka telefoonka waa la isticmaalaa.')
        return phone

    def clean_national_id(self):
        national_id = self.cleaned_data.get('national_id')
        if national_id:
            qs = ClientProfile.objects.filter(national_id=national_id)
            if self.instance_pk:
                qs = qs.exclude(pk=self.instance_pk)
            if qs.exists():
                raise forms.ValidationError('Aqoonsiga waa la isticmaalaa.')
        return national_id


class UniqueNotaryFieldsMixin:
    """Validates phone/license_number uniqueness across NotaryProfile, the same way
    UniqueClientFieldsMixin does for clients."""
    instance_pk = None

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            qs = NotaryProfile.objects.filter(phone=phone)
            if self.instance_pk:
                qs = qs.exclude(pk=self.instance_pk)
            if qs.exists():
                raise forms.ValidationError('Lambarka telefoonka waa la isticmaalaa.')
        return phone

    def clean_license_number(self):
        license_number = self.cleaned_data.get('license_number')
        if license_number:
            qs = NotaryProfile.objects.filter(license_number=license_number)
            if self.instance_pk:
                qs = qs.exclude(pk=self.instance_pk)
            if qs.exists():
                raise forms.ValidationError('Lambarka ruqsadda waa la isticmaalaa.')
        return license_number


class ClientCreateForm(UniqueClientFieldsMixin, forms.Form):
    full_name = forms.CharField(label=_('Full Name'), max_length=150)
    phone = forms.CharField(label=_('Phone'), max_length=30, required=False)
    email = forms.EmailField(label=_('Email'), required=False)
    national_id = forms.CharField(label=_('National ID'), max_length=40, required=False)
    address = forms.CharField(label=_('Address'), max_length=200, required=False)
    city = forms.CharField(label=_('City'), max_length=80, required=False)


class NotaryCreateForm(UniqueNotaryFieldsMixin, forms.Form):
    full_name = forms.CharField(
        label=_('Full Name'), max_length=150,
        error_messages={'required': 'Magaca waa loo baahan yahay.'},
    )
    phone = forms.CharField(
        label=_('Phone'), max_length=30,
        error_messages={'required': 'Telefoonka waa loo baahan yahay.'},
    )
    license_number = forms.CharField(
        label=_('License Number'), max_length=40,
        error_messages={'required': 'Lambarka Ruqsadda waa loo baahan yahay.'},
    )
    region = forms.CharField(
        label=_('Region'), max_length=80,
        error_messages={'required': 'Gobolka waa loo baahan yahay.'},
    )
    signature_data = forms.CharField(
        label=_('Signature'), widget=forms.HiddenInput,
        error_messages={'required': 'Saxiixa waa loo baahan yahay.'},
    )
    seal_image = forms.ImageField(label=_('Stamp Image'), required=False)

    def clean_signature_data(self):
        data = self.cleaned_data.get('signature_data')
        signature_file = decode_signature_data_url(data)
        if signature_file is None:
            raise forms.ValidationError('Saxiixa waa loo baahan yahay.')
        return signature_file


class ClientEditForm(UniqueClientFieldsMixin, forms.Form):
    full_name = forms.CharField(
        label=_('Full Name'), max_length=150,
        error_messages={'required': 'Magaca waa loo baahan yahay.'},
    )
    phone = forms.CharField(
        label=_('Phone'), max_length=30,
        error_messages={'required': 'Telefoonka waa loo baahan yahay.'},
    )
    national_id = forms.CharField(
        label=_('National ID'), max_length=40,
        error_messages={'required': 'Aqoonsiga Qaranka waa loo baahan yahay.'},
    )
    address = forms.CharField(
        label=_('Address'), max_length=200,
        error_messages={'required': 'Cinwaanka waa loo baahan yahay.'},
    )
    city = forms.CharField(
        label=_('City'), max_length=80,
        error_messages={'required': 'Magaalada waa loo baahan yahay.'},
    )
    email = forms.EmailField(label=_('Email'), required=False)

    def __init__(self, *args, instance_pk=None, **kwargs):
        self.instance_pk = instance_pk
        super().__init__(*args, **kwargs)


class NotaryEditForm(UniqueNotaryFieldsMixin, forms.Form):
    full_name = forms.CharField(
        label=_('Full Name'), max_length=150,
        error_messages={'required': 'Magaca waa loo baahan yahay.'},
    )
    phone = forms.CharField(
        label=_('Phone'), max_length=30,
        error_messages={'required': 'Telefoonka waa loo baahan yahay.'},
    )
    license_number = forms.CharField(
        label=_('License Number'), max_length=40,
        error_messages={'required': 'Lambarka Ruqsadda waa loo baahan yahay.'},
    )
    region = forms.CharField(
        label=_('Region'), max_length=80,
        error_messages={'required': 'Gobolka waa loo baahan yahay.'},
    )
    email = forms.EmailField(label=_('Email'), required=False)
    bio = forms.CharField(label=_('Bio'), required=False, widget=forms.Textarea(attrs={'rows': 4}))
    seal_image = forms.ImageField(label=_('Stamp Image'), required=False)

    def __init__(self, *args, instance_pk=None, **kwargs):
        self.instance_pk = instance_pk
        super().__init__(*args, **kwargs)


class DocumentTemplateForm(forms.ModelForm):
    class Meta:
        model = DocumentTemplate
        fields = ['title', 'category', 'party_type', 'requires_witnesses', 'body']
        labels = {
            'title': _('Template Title'),
            'category': _('Category'),
            'party_type': _('Parties'),
            'requires_witnesses': _('Requires witnesses'),
            'body': _('Body Text'),
        }
        widgets = {
            'body': forms.Textarea(attrs={'rows': 12}),
        }


class NotaryProfileForm(forms.ModelForm):
    class Meta:
        model = NotaryProfile
        fields = ['phone', 'bio', 'seal_image']
        labels = {
            'phone': _('Phone'),
            'bio': _('Bio'),
            'seal_image': _('Stamp Image'),
        }
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }


def client_missing_fields_error(client):
    """Build a "Name: field missing, field missing" message for an incomplete client
    profile, or return None if nothing is missing."""
    missing = client.missing_required_fields()
    if not missing:
        return None
    parts = ', '.join(f'{field} missing' for field in missing)
    return f'{client.user.get_full_name()}: {parts}'


class ClientModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return (
            f'{obj.user.get_full_name()} — {obj.phone or "—"} · {obj.city or "—"} · '
            f'{_("%(count)s documents") % {"count": obj.doc_count}}'
        )


class TemplateModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f'{obj.title} — {obj.category} · {obj.party_label}'


class ClientSelectForm(forms.Form):
    client = ClientModelChoiceField(
        queryset=ClientProfile.objects.select_related('user'),
        widget=forms.RadioSelect,
        label='',
        empty_label=None,
    )

    def clean_client(self):
        client = self.cleaned_data['client']
        error = client_missing_fields_error(client)
        if error:
            raise forms.ValidationError(error)
        return client


class TemplateSelectForm(forms.Form):
    template = TemplateModelChoiceField(
        queryset=DocumentTemplate.objects.all(),
        widget=forms.RadioSelect,
        label='',
        empty_label=None,
    )


class Party2SelectForm(forms.Form):
    client2 = ClientModelChoiceField(
        queryset=ClientProfile.objects.none(),
        widget=forms.RadioSelect,
        label='',
        empty_label=None,
    )

    def __init__(self, *args, queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if queryset is not None:
            self.fields['client2'].queryset = queryset

    def clean_client2(self):
        client2 = self.cleaned_data['client2']
        error = client_missing_fields_error(client2)
        if error:
            raise forms.ValidationError(error)
        return client2


class WitnessForm(forms.Form):
    name = forms.CharField(label=_('Witness Name'), max_length=150, required=False)
    phone = forms.CharField(label=_('Phone'), max_length=30, required=False)


WitnessFormSet = forms.formset_factory(WitnessForm, extra=2, max_num=5)


class ConfirmForm(forms.Form):
    """Empty — the confirm step is a read-only review; submitting it creates the document."""


class DocumentEditForm(forms.Form):
    """Lets a notary/admin change a PENDING document's template and parties, then
    regenerate its rendered body. Uses dropdowns rather than the wizard's radio
    lists since it's a single-page edit, not a multi-step flow."""

    template = TemplateModelChoiceField(queryset=DocumentTemplate.objects.all(), label=_('Template'))
    client = ClientModelChoiceField(queryset=ClientProfile.objects.select_related('user'), label=_('Party 1'))
    client2 = ClientModelChoiceField(
        queryset=ClientProfile.objects.select_related('user'), label=_('Party 2'), required=False
    )

    def clean(self):
        cleaned = super().clean()
        template = cleaned.get('template')
        client = cleaned.get('client')
        client2 = cleaned.get('client2')
        if not template or not client:
            return cleaned

        if template.party_type == DocumentTemplate.PartyType.TWO:
            if not client2:
                self.add_error('client2', 'Qaabkani waa laba-dhinac — waa inaad dooratid macmiilka labaad.')
            elif client2.pk == client.pk:
                self.add_error('client2', 'Dhinaca labaad waa inuu ka duwanaadaa dhinaca koowaad.')
        else:
            cleaned['client2'] = None

        parties = [client]
        if template.party_type == DocumentTemplate.PartyType.TWO and client2 and client2.pk != client.pk:
            parties.append(client2)
        errors = [error for error in (client_missing_fields_error(c) for c in parties) if error]
        if errors:
            raise forms.ValidationError(errors)
        return cleaned
