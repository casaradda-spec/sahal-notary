from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.models import User as AccountsUser
from portal.models import ClientProfile, DocumentTemplate, NotaryProfile

User = get_user_model()
TEMP_PASSWORD = '123'

LEASE_BODY = (
    "Bismillaahi Rahmaani Rahiim. Heshiiskaan rasmi ah ayaa lagu sameeyay magaalada {{city}}, "
    "taariikhdana waxay ahayd {{date}}, labada dhinac oo magacyadoodu yihiin {{client_name}} iyo {{client2_name}}.\n"
    "Dhinacu koowaad iyo dhinaca labaad waxay si wadajir ah u aqbaleen dhammaan shuruudaha ku qoran "
    "dukumeentigan, kaasoo ah mid sharci ah oo loo xaqiijiyay Sahal Notary System. Saxiixa dhinac kasta "
    "waxay muujinaysaa in aqbalidda ay tahay mid xor ah oo kamid ah.\n"
    "Heshiiskaan waxaa lagu dhaqangelin doonaa sida uu sharciga Soomaalida u tilmaamayo. Qofkasta oo "
    "ku xad-gudba shuruudahan waxaa lagu eedeysan doonaa xeer-dhaqanka Soomaalida.\n"
    "Saxiixa {{client_name}}: {{client1_signature}}\n"
    "Saxiixa {{client2_name}}: {{client2_signature}}\n"
    "Notaayo: {{notary_name}} ({{notary_license}}) · Tixraac: {{ref}}"
)

WILL_BODY = (
    "Bismillaahi Rahmaani Rahiim. Dardaarankan qoyska ayaa lagu sameeyay magaalada {{city}} "
    "taariikhda {{date}}, waxaana qoray {{client_name}}, isagoo caqli-gal ah oo si xor ah u doortay.\n"
    "Dardaarankan wuxuu sharci ahaan rumaysan yahay marka la xaqiijiyo saxiixa qofka iyo "
    "marqaatiyaasha ku xusan hoos, sida uu Sahal Notary System u xaqiijiyay.\n"
    "Saxiixa {{client_name}}: {{client_signature}}\n"
    "Notaayo: {{notary_name}} ({{notary_license}}) · Tixraac: {{ref}}"
)

POA_BODY = (
    "Bismillaahi Rahmaani Rahiim. Wakaaladdan sharciga ah ayaa lagu sameeyay magaalada {{city}} "
    "taariikhda {{date}}, waxaana siiyay {{client_name}} oggolaansho buuxda si loo wakiilo arrimo "
    "gaar ah oo sharci ah.\n"
    "Wakaaladdan waxay khasab tahay ilaa lagu noqdo qoraal kale oo cad.\n"
    "Saxiixa {{client_name}}: {{client_signature}}\n"
    "Notaayo: {{notary_name}} ({{notary_license}}) · Tixraac: {{ref}}"
)

LOAN_BODY = (
    "Bismillaahi Rahmaani Rahiim. Heshiiskan deynta ayaa ka dhexeeya {{client_name}} (deyn-bixiyaha) "
    "iyo {{client2_name}} (deyn-qaataha), lagu sameeyay {{city}} taariikhda {{date}}.\n"
    "Labada dhinac waxay ku heshiiyeen shuruudaha bixinta iyo wakhtiga la qabsiga, sida uu Sahal "
    "Notary System u diiwaangeliyay.\n"
    "Saxiixa {{client_name}}: {{client1_signature}}\n"
    "Saxiixa {{client2_name}}: {{client2_signature}}\n"
    "Notaayo: {{notary_name}} ({{notary_license}}) · Tixraac: {{ref}}"
)


class Command(BaseCommand):
    help = 'Seed demo data for the Sahal Notary System (admin, notaries, clients, templates).'

    def handle(self, *args, **options):
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults=dict(
                first_name='Admin', last_name='Sahal', role=AccountsUser.Role.ADMIN,
                is_staff=True, is_superuser=True, must_change_password=True,
            ),
        )
        if created:
            admin_user.set_password(TEMP_PASSWORD)
            admin_user.save()
            self.stdout.write('Created admin user "admin" / temp password "123"')

        notary_specs = [
            ('Maxamed', 'Daahir', 'NOT-2022-001', 'Banaadir'),
            ('Nasra', 'Warsame', 'NOT-2022-014', 'Banaadir'),
            ('Ibraahim', 'Jimale', 'NOT-2023-007', 'Hirshabelle'),
        ]
        notaries = []
        for first, last, license_number, region in notary_specs:
            username = f'{first.lower()}.{last.lower()}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults=dict(first_name=first, last_name=last, role=AccountsUser.Role.NOTARY),
            )
            if created:
                user.set_password(TEMP_PASSWORD)
                user.save()
            profile, _ = NotaryProfile.objects.get_or_create(
                user=user, defaults=dict(license_number=license_number, region=region)
            )
            notaries.append(profile)
        self.stdout.write(f'Notaries ready: {len(notaries)}')

        client_specs = [
            ('Amina', 'Yusuf', 'Muqdisho'),
            ('Hodan', 'Maxamed', 'Muqdisho'),
            ('Faadumo', 'Aadan', 'Kismaayo'),
            ('Cabdi', 'Xasan', 'Muqdisho'),
        ]
        clients = []
        for first, last, city in client_specs:
            username = f'{first.lower()}.{last.lower()}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults=dict(first_name=first, last_name=last, role=AccountsUser.Role.CLIENT),
            )
            if created:
                user.set_password(TEMP_PASSWORD)
                user.save()
            profile, _ = ClientProfile.objects.get_or_create(user=user, defaults=dict(city=city))
            clients.append(profile)
        self.stdout.write(f'Clients ready: {len(clients)}')

        template_specs = [
            ('Heshiiska Kirada Guriga', 'Heshiis Kirada', DocumentTemplate.PartyType.TWO, False, LEASE_BODY),
            ('Dardaaran Qoyseed', 'Dardaaran', DocumentTemplate.PartyType.ONE, True, WILL_BODY),
            ('Wakaalad Sharci', 'Wakaalad', DocumentTemplate.PartyType.ONE, False, POA_BODY),
            ('Heshiis Deyn', 'Heshiis Deyn', DocumentTemplate.PartyType.TWO, True, LOAN_BODY),
        ]
        for title, category, party_type, requires_witnesses, body in template_specs:
            DocumentTemplate.objects.get_or_create(
                title=title,
                defaults=dict(
                    category=category, party_type=party_type,
                    requires_witnesses=requires_witnesses, body=body, created_by=notaries[0],
                ),
            )
        self.stdout.write('Templates ready.')

        self.stdout.write(self.style.SUCCESS(
            'Seed complete. Login as admin/123, maxamed.daahir/123, or amina.yusuf/123 (forced password change on first login).'
        ))
