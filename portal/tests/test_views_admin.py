from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import User as AccountsUser
from portal.models import ClientProfile, Document, NotaryProfile

from .base import TempMediaTestCase
from .factories import make_admin_user, make_client_profile, make_notary_profile, make_template, tiny_png_data_url

User = get_user_model()


class ClientsViewAccessTests(TestCase):
    def test_anonymous_redirected(self):
        response = self.client.get(reverse('admin_clients'))
        self.assertEqual(response.status_code, 302)

    def test_wrong_role_forbidden(self):
        client_profile = make_client_profile('notaccessclient')
        self.client.force_login(client_profile.user)
        response = self.client.get(reverse('admin_clients'))
        self.assertEqual(response.status_code, 403)

    def test_notary_can_access(self):
        notary = make_notary_profile('clientsaccessnotary')
        self.client.force_login(notary.user)
        response = self.client.get(reverse('admin_clients'))
        self.assertEqual(response.status_code, 200)


class ClientCreationTests(TestCase):
    def setUp(self):
        self.admin = make_admin_user()
        self.client.force_login(self.admin)

    def test_creates_user_and_profile_with_temp_password(self):
        response = self.client.post(reverse('admin_clients'), {
            'full_name': 'Farhan Axmed',
            'phone': '+252610000000',
            'email': '',
            'national_id': 'SOM-1',
            'address': 'Hodan',
            'city': 'Muqdisho',
        })
        self.assertRedirects(response, reverse('admin_clients'))

        user = User.objects.get(username='farhan.axmed')
        self.assertEqual(user.role, AccountsUser.Role.CLIENT)
        self.assertTrue(user.must_change_password)
        self.assertTrue(user.check_password('123'))

        profile = ClientProfile.objects.get(user=user)
        self.assertEqual(profile.city, 'Muqdisho')
        self.assertEqual(profile.national_id, 'SOM-1')

    def test_duplicate_names_get_distinct_usernames(self):
        for _ in range(2):
            self.client.post(reverse('admin_clients'), {
                'full_name': 'Farhan Axmed', 'phone': '', 'email': '', 'national_id': '', 'address': '', 'city': '',
            })
        usernames = sorted(User.objects.filter(role=AccountsUser.Role.CLIENT).values_list('username', flat=True))
        self.assertEqual(usernames, ['farhan.axmed', 'farhan.axmed2'])

    def test_blank_full_name_is_rejected(self):
        response = self.client.post(reverse('admin_clients'), {
            'full_name': '', 'phone': '', 'email': '', 'national_id': '', 'address': '', 'city': '',
        })
        self.assertEqual(response.status_code, 200)  # re-renders the add form
        self.assertEqual(User.objects.filter(role=AccountsUser.Role.CLIENT).count(), 0)


class ClientSignatureCaptureTests(TempMediaTestCase):
    def setUp(self):
        self.admin = make_admin_user()
        self.client.force_login(self.admin)

    def test_signature_data_on_create_is_saved_to_profile(self):
        response = self.client.post(reverse('admin_clients'), {
            'full_name': 'Signed Client',
            'phone': '', 'email': '', 'national_id': '', 'address': '', 'city': 'Muqdisho',
            'signature_data': tiny_png_data_url(),
        })
        self.assertRedirects(response, reverse('admin_clients'))
        profile = ClientProfile.objects.get(user__username='signed.client')
        self.assertTrue(profile.signature)

    def test_blank_signature_data_on_create_leaves_signature_empty(self):
        self.client.post(reverse('admin_clients'), {
            'full_name': 'Unsigned Client',
            'phone': '', 'email': '', 'national_id': '', 'address': '', 'city': 'Muqdisho',
        })
        profile = ClientProfile.objects.get(user__username='unsigned.client')
        self.assertFalse(profile.signature)


class ClientSignatureViewTests(TempMediaTestCase):
    def setUp(self):
        self.admin = make_admin_user()
        self.client.force_login(self.admin)
        self.profile = make_client_profile('siguser')

    def test_wrong_role_forbidden(self):
        client_profile = make_client_profile('sigclientview')
        self.client.force_login(client_profile.user)
        response = self.client.get(reverse('admin_client_signature', args=[self.profile.pk]))
        self.assertEqual(response.status_code, 403)

    def test_notary_can_access(self):
        notary = make_notary_profile('signotaryview')
        self.client.force_login(notary.user)
        response = self.client.get(reverse('admin_client_signature', args=[self.profile.pk]))
        self.assertEqual(response.status_code, 200)

    def test_get_renders_capture_page(self):
        response = self.client.get(reverse('admin_client_signature', args=[self.profile.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['profile'], self.profile)

    def test_post_with_data_url_saves_signature(self):
        response = self.client.post(
            reverse('admin_client_signature', args=[self.profile.pk]),
            {'signature_data': tiny_png_data_url()},
        )
        self.assertRedirects(response, reverse('admin_clients'))
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.signature)

    def test_post_without_signature_data_does_not_clear_existing(self):
        from django.core.files.base import ContentFile
        from .factories import tiny_png_bytes
        self.profile.signature.save('original.png', ContentFile(tiny_png_bytes()), save=True)
        original_name = self.profile.signature.name

        self.client.post(reverse('admin_client_signature', args=[self.profile.pk]), {'signature_data': ''})
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.signature.name, original_name)


class NotaryCreationTests(TestCase):
    def setUp(self):
        self.admin = make_admin_user()
        self.client.force_login(self.admin)

    def test_notary_role_forbidden_from_registering_notaries(self):
        notary = make_notary_profile('notaryregisterattempt')
        self.client.force_login(notary.user)
        response = self.client.get(reverse('admin_notaries'))
        self.assertEqual(response.status_code, 403)

    def test_creates_user_and_profile(self):
        response = self.client.post(reverse('admin_notaries'), {
            'full_name': 'Nasra Warsame',
            'license_number': 'NOT-2024-099',
            'region': 'Banaadir',
        })
        self.assertRedirects(response, reverse('admin_notaries'))

        user = User.objects.get(username='nasra.warsame')
        self.assertEqual(user.role, AccountsUser.Role.NOTARY)
        self.assertTrue(user.check_password('123'))

        profile = NotaryProfile.objects.get(user=user)
        self.assertEqual(profile.license_number, 'NOT-2024-099')
        self.assertEqual(profile.region, 'Banaadir')

    def test_admins_auto_provisioned_notary_profile_excluded_from_listing(self):
        NotaryProfile.objects.create(user=self.admin)
        response = self.client.get(reverse('admin_notaries'))
        self.assertEqual(list(response.context['notaries']), [])


class ReportsTests(TestCase):
    def setUp(self):
        self.admin = make_admin_user()
        self.client.force_login(self.admin)

    def test_notary_role_forbidden_from_reports(self):
        notary = make_notary_profile('notaryreportsattempt')
        self.client.force_login(notary.user)
        response = self.client.get(reverse('admin_reports'))
        self.assertEqual(response.status_code, 403)

    def test_aggregates_reflect_real_data(self):
        notary_busy = make_notary_profile('busynotary', first='Busy', last='Notary')
        notary_quiet = make_notary_profile('quietnotary', first='Quiet', last='Notary')
        template = make_template(created_by=notary_busy)
        client_profile = make_client_profile('reportclient')

        for _ in range(4):
            doc = Document(template=template, notary=notary_busy, client=client_profile, city='Muqdisho')
            doc.finalize()
            doc.save()
        doc = Document(template=template, notary=notary_quiet, client=client_profile, city='Muqdisho')
        doc.finalize()
        doc.save()

        response = self.client.get(reverse('admin_reports'))
        self.assertEqual(response.context['total_docs'], 5)
        self.assertEqual(response.context['total_clients'], 1)
        self.assertEqual(response.context['total_notaries'], 2)

        bars = {b['name']: b for b in response.context['notary_bars']}
        self.assertEqual(bars[notary_busy.user.get_full_name()]['count'], 4)
        self.assertEqual(bars[notary_busy.user.get_full_name()]['pct'], 100)
        self.assertEqual(bars[notary_quiet.user.get_full_name()]['count'], 1)
        self.assertEqual(bars[notary_quiet.user.get_full_name()]['pct'], 25)

    def test_admins_auto_provisioned_notary_profile_excluded_from_notary_stats(self):
        # An Admin acting as a document signer lazily gets a NotaryProfile (see
        # get_or_create_notary_profile) — it shouldn't pollute the notary leaderboard.
        NotaryProfile.objects.create(user=self.admin)

        response = self.client.get(reverse('admin_reports'))
        self.assertEqual(response.context['total_notaries'], 0)
        self.assertEqual(list(response.context['notary_bars']), [])
