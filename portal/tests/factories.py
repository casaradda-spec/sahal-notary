import base64

from django.contrib.auth import get_user_model

from accounts.models import User as AccountsUser
from portal.models import ClientProfile, DocumentTemplate, NotaryProfile

User = get_user_model()

# A real, valid 1x1 transparent PNG — used wherever tests need actual image bytes.
TINY_PNG_BASE64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='


def tiny_png_bytes():
    return base64.b64decode(TINY_PNG_BASE64)


def tiny_png_data_url():
    return f'data:image/png;base64,{TINY_PNG_BASE64}'


def make_client_profile(username, first='Test', last='Client', password='123', city='Muqdisho',
                         phone='0610000000', national_id='SOM-TEST-001', address='Test Address',
                         with_signature=False):
    user = User.objects.create_user(
        username=username, password=password, first_name=first, last_name=last,
        role=AccountsUser.Role.CLIENT, must_change_password=False,
    )
    profile = ClientProfile.objects.create(
        user=user, city=city, phone=phone, national_id=national_id, address=address,
    )
    if with_signature:
        from django.core.files.base import ContentFile
        profile.signature.save('signature.png', ContentFile(tiny_png_bytes()), save=True)
    return profile


def make_notary_profile(username, first='Test', last='Notary', password='123',
                         license_number='NOT-TEST-001', region='Banaadir'):
    user = User.objects.create_user(
        username=username, password=password, first_name=first, last_name=last,
        role=AccountsUser.Role.NOTARY, must_change_password=False,
    )
    return NotaryProfile.objects.create(user=user, license_number=license_number, region=region)


def make_admin_user(username='testadmin', password='123'):
    return User.objects.create_user(
        username=username, password=password, first_name='Test', last_name='Admin',
        role=AccountsUser.Role.ADMIN, must_change_password=False, is_staff=True,
    )


def make_template(title='Test Lease', category='Heshiis Kirada', party_type=DocumentTemplate.PartyType.ONE,
                   requires_witnesses=False, body=None, created_by=None):
    body = body or (
        '{{client_name}} iyo {{client2_name}} taariikhda {{date}} magaalada {{city}}. '
        'Notaayo: {{notary_name}} ({{notary_license}}) Tixraac: {{ref}}'
    )
    return DocumentTemplate.objects.create(
        title=title, category=category, party_type=party_type,
        requires_witnesses=requires_witnesses, body=body, created_by=created_by,
    )
