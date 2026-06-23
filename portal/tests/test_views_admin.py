from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import User as AccountsUser
from portal.models import ClientProfile, Document, DocumentTemplate, NotaryProfile

from .base import TempMediaTestCase
from .factories import (
    make_admin_user, make_client_profile, make_notary_profile, make_template, tiny_png_data_url,
)

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

    def test_list_view_has_live_search_input(self):
        admin = make_admin_user()
        self.client.force_login(admin)
        response = self.client.get(reverse('admin_clients'))
        self.assertContains(response, 'id="clients-search-input"')


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


class ClientEditTests(TempMediaTestCase):
    def setUp(self):
        self.admin = make_admin_user()
        self.profile = make_client_profile(
            'editclienttarget', first='Amina', last='Yusuf', phone='0610000001',
            national_id='SOM-OLD', address='Old Address', city='Muqdisho',
        )
        self.client.force_login(self.admin)

    def valid_payload(self, **overrides):
        payload = {
            'full_name': 'Amina Yusuf Cusub',
            'phone': '0699999999',
            'email': 'amina@example.com',
            'national_id': 'SOM-NEW',
            'address': 'New Address',
            'city': 'Kismaayo',
        }
        payload.update(overrides)
        return payload

    def test_anonymous_redirected(self):
        self.client.logout()
        response = self.client.get(reverse('admin_client_edit', args=[self.profile.pk]))
        self.assertEqual(response.status_code, 302)

    def test_client_role_forbidden(self):
        self.client.force_login(self.profile.user)
        response = self.client.get(reverse('admin_client_edit', args=[self.profile.pk]))
        self.assertEqual(response.status_code, 403)

    def test_notary_can_access(self):
        notary = make_notary_profile('clienteditnotary')
        self.client.force_login(notary.user)
        response = self.client.get(reverse('admin_client_edit', args=[self.profile.pk]))
        self.assertEqual(response.status_code, 200)

    def test_get_prefills_current_values(self):
        response = self.client.get(reverse('admin_client_edit', args=[self.profile.pk]))
        initial = response.context['form'].initial
        self.assertEqual(initial['full_name'], 'Amina Yusuf')
        self.assertEqual(initial['phone'], '0610000001')
        self.assertEqual(initial['national_id'], 'SOM-OLD')
        self.assertEqual(initial['address'], 'Old Address')
        self.assertEqual(initial['city'], 'Muqdisho')

    def test_valid_submission_updates_profile_and_redirects(self):
        response = self.client.post(reverse('admin_client_edit', args=[self.profile.pk]), self.valid_payload())
        self.assertRedirects(response, reverse('admin_clients'))

        self.profile.refresh_from_db()
        self.profile.user.refresh_from_db()
        self.assertEqual(self.profile.user.get_full_name(), 'Amina Yusuf Cusub')
        self.assertEqual(self.profile.user.email, 'amina@example.com')
        self.assertEqual(self.profile.phone, '0699999999')
        self.assertEqual(self.profile.national_id, 'SOM-NEW')
        self.assertEqual(self.profile.address, 'New Address')
        self.assertEqual(self.profile.city, 'Kismaayo')

    def test_valid_submission_shows_success_message(self):
        response = self.client.post(reverse('admin_client_edit', args=[self.profile.pk]), self.valid_payload(), follow=True)
        self.assertContains(response, 'waa la cusbooneysiiyay')

    def test_missing_required_field_blocks_save_and_shows_specific_error(self):
        response = self.client.post(reverse('admin_client_edit', args=[self.profile.pk]), self.valid_payload(phone=''))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Telefoonka waa loo baahan yahay.')
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.phone, '0610000001')  # unchanged

    def test_blank_full_name_shows_specific_error(self):
        response = self.client.post(reverse('admin_client_edit', args=[self.profile.pk]), self.valid_payload(full_name=''))
        self.assertContains(response, 'Magaca waa loo baahan yahay.')

    def test_blank_national_id_shows_specific_error(self):
        response = self.client.post(reverse('admin_client_edit', args=[self.profile.pk]), self.valid_payload(national_id=''))
        self.assertContains(response, 'Aqoonsiga Qaranka waa loo baahan yahay.')

    def test_blank_address_shows_specific_error(self):
        response = self.client.post(reverse('admin_client_edit', args=[self.profile.pk]), self.valid_payload(address=''))
        self.assertContains(response, 'Cinwaanka waa loo baahan yahay.')

    def test_blank_city_shows_specific_error(self):
        response = self.client.post(reverse('admin_client_edit', args=[self.profile.pk]), self.valid_payload(city=''))
        self.assertContains(response, 'Magaalada waa loo baahan yahay.')

    def test_new_signature_replaces_old_one(self):
        from django.core.files.base import ContentFile
        from .factories import tiny_png_bytes
        self.profile.signature.save('original.png', ContentFile(tiny_png_bytes()), save=True)
        original_name = self.profile.signature.name

        self.client.post(
            reverse('admin_client_edit', args=[self.profile.pk]),
            self.valid_payload(signature_data=tiny_png_data_url()),
        )
        self.profile.refresh_from_db()
        self.assertNotEqual(self.profile.signature.name, original_name)

    def test_blank_signature_data_keeps_existing_signature(self):
        from django.core.files.base import ContentFile
        from .factories import tiny_png_bytes
        self.profile.signature.save('original.png', ContentFile(tiny_png_bytes()), save=True)
        original_name = self.profile.signature.name

        self.client.post(reverse('admin_client_edit', args=[self.profile.pk]), self.valid_payload())
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.signature.name, original_name)

    def test_edit_link_appears_on_clients_list(self):
        response = self.client.get(reverse('admin_clients'))
        self.assertContains(response, reverse('admin_client_edit', args=[self.profile.pk]))


class NotaryEditTests(TempMediaTestCase):
    def setUp(self):
        self.admin = make_admin_user()
        self.profile = make_notary_profile(
            'editnotarytarget', first='Maxamed', last='Daahir',
            license_number='NOT-OLD', region='Banaadir',
        )
        self.profile.phone = '0610000002'
        self.profile.save(update_fields=['phone'])
        self.client.force_login(self.admin)

    def valid_payload(self, **overrides):
        payload = {
            'full_name': 'Maxamed Daahir Cusub',
            'phone': '0688888888',
            'email': 'maxamed@example.com',
            'license_number': 'NOT-NEW',
            'region': 'Hirshabelle',
            'bio': 'Updated bio.',
        }
        payload.update(overrides)
        return payload

    def test_anonymous_redirected(self):
        self.client.logout()
        response = self.client.get(reverse('admin_notary_edit', args=[self.profile.pk]))
        self.assertEqual(response.status_code, 302)

    def test_notary_role_forbidden(self):
        self.client.force_login(self.profile.user)
        response = self.client.get(reverse('admin_notary_edit', args=[self.profile.pk]))
        self.assertEqual(response.status_code, 403)

    def test_get_prefills_current_values(self):
        response = self.client.get(reverse('admin_notary_edit', args=[self.profile.pk]))
        initial = response.context['form'].initial
        self.assertEqual(initial['full_name'], 'Maxamed Daahir')
        self.assertEqual(initial['phone'], '0610000002')
        self.assertEqual(initial['license_number'], 'NOT-OLD')
        self.assertEqual(initial['region'], 'Banaadir')

    def test_valid_submission_updates_profile_and_redirects(self):
        response = self.client.post(reverse('admin_notary_edit', args=[self.profile.pk]), self.valid_payload())
        self.assertRedirects(response, reverse('admin_notaries'))

        self.profile.refresh_from_db()
        self.profile.user.refresh_from_db()
        self.assertEqual(self.profile.user.get_full_name(), 'Maxamed Daahir Cusub')
        self.assertEqual(self.profile.user.email, 'maxamed@example.com')
        self.assertEqual(self.profile.phone, '0688888888')
        self.assertEqual(self.profile.license_number, 'NOT-NEW')
        self.assertEqual(self.profile.region, 'Hirshabelle')
        self.assertEqual(self.profile.bio, 'Updated bio.')

    def test_valid_submission_shows_success_message(self):
        response = self.client.post(reverse('admin_notary_edit', args=[self.profile.pk]), self.valid_payload(), follow=True)
        self.assertContains(response, 'waa la cusbooneysiiyay')

    def test_missing_phone_blocks_save_and_shows_specific_error(self):
        response = self.client.post(reverse('admin_notary_edit', args=[self.profile.pk]), self.valid_payload(phone=''))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Telefoonka waa loo baahan yahay.')
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.phone, '0610000002')  # unchanged

    def test_blank_license_number_shows_specific_error(self):
        response = self.client.post(reverse('admin_notary_edit', args=[self.profile.pk]), self.valid_payload(license_number=''))
        self.assertContains(response, 'Lambarka Ruqsadda waa loo baahan yahay.')

    def test_blank_region_shows_specific_error(self):
        response = self.client.post(reverse('admin_notary_edit', args=[self.profile.pk]), self.valid_payload(region=''))
        self.assertContains(response, 'Gobolka waa loo baahan yahay.')

    def test_new_seal_image_replaces_old_one(self):
        from django.core.files.base import ContentFile
        from .factories import tiny_png_bytes
        self.profile.seal_image.save('original.png', ContentFile(tiny_png_bytes()), save=True)
        original_name = self.profile.seal_image.name

        upload = SimpleUploadedFile('new_seal.png', tiny_png_bytes(), content_type='image/png')
        self.client.post(
            reverse('admin_notary_edit', args=[self.profile.pk]),
            self.valid_payload(seal_image=upload),
        )
        self.profile.refresh_from_db()
        self.assertNotEqual(self.profile.seal_image.name, original_name)

    def test_blank_seal_image_keeps_existing_seal(self):
        from django.core.files.base import ContentFile
        from .factories import tiny_png_bytes
        self.profile.seal_image.save('original.png', ContentFile(tiny_png_bytes()), save=True)
        original_name = self.profile.seal_image.name

        self.client.post(reverse('admin_notary_edit', args=[self.profile.pk]), self.valid_payload())
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.seal_image.name, original_name)

    def test_edit_link_appears_on_notaries_list(self):
        response = self.client.get(reverse('admin_notaries'))
        self.assertContains(response, reverse('admin_notary_edit', args=[self.profile.pk]))


class NotaryCreationTests(TempMediaTestCase):
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
            'phone': '0677000099',
            'license_number': 'NOT-2024-099',
            'region': 'Banaadir',
            'signature_data': tiny_png_data_url(),
        })
        self.assertRedirects(response, reverse('admin_notaries'))

        user = User.objects.get(username='nasra.warsame')
        self.assertEqual(user.role, AccountsUser.Role.NOTARY)
        self.assertTrue(user.check_password('123'))

        profile = NotaryProfile.objects.get(user=user)
        self.assertEqual(profile.license_number, 'NOT-2024-099')
        self.assertEqual(profile.region, 'Banaadir')
        self.assertTrue(profile.signature)

    def test_blank_required_fields_are_rejected(self):
        for field in ('full_name', 'phone', 'license_number', 'region'):
            payload = {
                'full_name': 'Some Notary', 'phone': '0677000001',
                'license_number': 'NOT-REQ-1', 'region': 'Banaadir',
                'signature_data': tiny_png_data_url(),
            }
            payload[field] = ''
            response = self.client.post(reverse('admin_notaries'), payload)
            self.assertEqual(response.status_code, 200, f'{field} should be required')
            self.assertEqual(NotaryProfile.objects.filter(license_number='NOT-REQ-1').count(), 0)

    def test_blank_signature_is_rejected(self):
        response = self.client.post(reverse('admin_notaries'), {
            'full_name': 'No Signature', 'phone': '0677000002',
            'license_number': 'NOT-REQ-2', 'region': 'Banaadir', 'signature_data': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Saxiixa waa loo baahan yahay.')
        self.assertFalse(User.objects.filter(username='no.signature').exists())

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


class ClientUniqueFieldValidationTests(TestCase):
    def setUp(self):
        self.admin = make_admin_user()
        self.client.force_login(self.admin)
        self.existing = make_client_profile('uniqueexisting', phone='0611111111', national_id='SOM-UNIQUE-1')

    def test_create_with_duplicate_phone_is_blocked(self):
        response = self.client.post(reverse('admin_clients'), {
            'full_name': 'Duplicate Phone', 'phone': '0611111111', 'email': '',
            'national_id': '', 'address': '', 'city': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lambarka telefoonka waa la isticmaalaa.')
        self.assertFalse(User.objects.filter(username='duplicate.phone').exists())

    def test_create_with_duplicate_national_id_is_blocked(self):
        response = self.client.post(reverse('admin_clients'), {
            'full_name': 'Duplicate Nid', 'phone': '', 'email': '',
            'national_id': 'SOM-UNIQUE-1', 'address': '', 'city': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Aqoonsiga waa la isticmaalaa.')
        self.assertFalse(User.objects.filter(username='duplicate.nid').exists())

    def test_edit_with_duplicate_phone_is_blocked(self):
        other = make_client_profile('uniqueeditother', phone='0622222222', national_id='SOM-UNIQUE-2')
        response = self.client.post(reverse('admin_client_edit', args=[other.pk]), {
            'full_name': other.user.get_full_name(), 'phone': '0611111111',
            'national_id': other.national_id, 'address': 'X', 'city': 'X', 'email': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lambarka telefoonka waa la isticmaalaa.')
        other.refresh_from_db()
        self.assertEqual(other.phone, '0622222222')  # unchanged

    def test_edit_with_duplicate_national_id_is_blocked(self):
        other = make_client_profile('uniqueeditother2', phone='0633333333', national_id='SOM-UNIQUE-3')
        response = self.client.post(reverse('admin_client_edit', args=[other.pk]), {
            'full_name': other.user.get_full_name(), 'phone': other.phone,
            'national_id': 'SOM-UNIQUE-1', 'address': 'X', 'city': 'X', 'email': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Aqoonsiga waa la isticmaalaa.')

    def test_edit_keeping_own_phone_and_national_id_is_allowed(self):
        response = self.client.post(reverse('admin_client_edit', args=[self.existing.pk]), {
            'full_name': self.existing.user.get_full_name(), 'phone': self.existing.phone,
            'national_id': self.existing.national_id, 'address': 'X', 'city': 'X', 'email': '',
        })
        self.assertRedirects(response, reverse('admin_clients'))


class NotaryUniqueFieldValidationTests(TestCase):
    def setUp(self):
        self.admin = make_admin_user()
        self.client.force_login(self.admin)
        self.existing = make_notary_profile('uniquenotaryexisting', license_number='NOT-UNIQUE-1')
        self.existing.phone = '0644444444'
        self.existing.save(update_fields=['phone'])

    def test_create_with_duplicate_phone_is_blocked(self):
        response = self.client.post(reverse('admin_notaries'), {
            'full_name': 'Dup Notary', 'phone': '0644444444', 'license_number': 'NOT-DUP-1',
            'region': 'Banaadir', 'signature_data': tiny_png_data_url(),
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lambarka telefoonka waa la isticmaalaa.')
        self.assertFalse(User.objects.filter(username='dup.notary').exists())

    def test_create_with_duplicate_license_number_is_blocked(self):
        response = self.client.post(reverse('admin_notaries'), {
            'full_name': 'Dup License', 'phone': '0699999998', 'license_number': 'NOT-UNIQUE-1',
            'region': 'Banaadir', 'signature_data': tiny_png_data_url(),
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lambarka ruqsadda waa la isticmaalaa.')
        self.assertFalse(User.objects.filter(username='dup.license').exists())

    def test_edit_with_duplicate_phone_is_blocked(self):
        other = make_notary_profile('uniquenotaryother', license_number='NOT-UNIQUE-2')
        response = self.client.post(reverse('admin_notary_edit', args=[other.pk]), {
            'full_name': other.user.get_full_name(), 'phone': '0644444444',
            'license_number': other.license_number, 'region': 'X', 'email': '', 'bio': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lambarka telefoonka waa la isticmaalaa.')

    def test_edit_with_duplicate_license_number_is_blocked(self):
        other = make_notary_profile('uniquenotaryother2', license_number='NOT-UNIQUE-3')
        response = self.client.post(reverse('admin_notary_edit', args=[other.pk]), {
            'full_name': other.user.get_full_name(), 'phone': '0655555555',
            'license_number': 'NOT-UNIQUE-1', 'region': 'X', 'email': '', 'bio': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lambarka ruqsadda waa la isticmaalaa.')

    def test_edit_keeping_own_phone_and_license_number_is_allowed(self):
        response = self.client.post(reverse('admin_notary_edit', args=[self.existing.pk]), {
            'full_name': self.existing.user.get_full_name(), 'phone': self.existing.phone,
            'license_number': self.existing.license_number, 'region': 'X', 'email': '', 'bio': '',
        })
        self.assertRedirects(response, reverse('admin_notaries'))


class ClientDeleteTests(TestCase):
    def setUp(self):
        self.admin = make_admin_user()
        self.client.force_login(self.admin)

    def test_delete_button_appears_on_clients_list(self):
        profile = make_client_profile('deletelistclient')
        response = self.client.get(reverse('admin_clients'))
        self.assertContains(response, reverse('admin_client_delete', args=[profile.pk]))

    def test_deletes_client_with_no_documents(self):
        profile = make_client_profile('deletableclient')
        user_pk = profile.user.pk
        response = self.client.post(reverse('admin_client_delete', args=[profile.pk]))
        self.assertRedirects(response, reverse('admin_clients'))
        self.assertFalse(ClientProfile.objects.filter(pk=profile.pk).exists())
        self.assertFalse(User.objects.filter(pk=user_pk).exists())

    def test_blocks_deletion_when_client_is_party1(self):
        notary = make_notary_profile('deleteblocknotary')
        template = make_template(created_by=notary)
        profile = make_client_profile('undeletableclient')
        doc = Document(template=template, notary=notary, client=profile, city='Muqdisho')
        doc.finalize()
        doc.save()

        response = self.client.post(reverse('admin_client_delete', args=[profile.pk]), follow=True)
        self.assertContains(response, 'lama tirtiri karo')
        self.assertTrue(ClientProfile.objects.filter(pk=profile.pk).exists())

    def test_blocks_deletion_when_client_is_party2(self):
        notary = make_notary_profile('deleteblocknotary2')
        template = make_template(party_type=DocumentTemplate.PartyType.TWO, created_by=notary)
        client1 = make_client_profile('party1fordelete')
        profile = make_client_profile('party2fordelete')
        doc = Document(template=template, notary=notary, client=client1, client2=profile, city='Muqdisho')
        doc.finalize()
        doc.save()

        response = self.client.post(reverse('admin_client_delete', args=[profile.pk]), follow=True)
        self.assertContains(response, 'lama tirtiri karo')
        self.assertTrue(ClientProfile.objects.filter(pk=profile.pk).exists())

    def test_get_request_does_not_delete(self):
        profile = make_client_profile('getnodeleteclient')
        self.client.get(reverse('admin_client_delete', args=[profile.pk]))
        self.assertTrue(ClientProfile.objects.filter(pk=profile.pk).exists())

    def test_notary_can_delete_client(self):
        notary = make_notary_profile('deletenotaryrole')
        self.client.force_login(notary.user)
        profile = make_client_profile('notarydeletesclient')
        response = self.client.post(reverse('admin_client_delete', args=[profile.pk]))
        self.assertRedirects(response, reverse('admin_clients'))
        self.assertFalse(ClientProfile.objects.filter(pk=profile.pk).exists())

    def test_client_role_forbidden(self):
        profile = make_client_profile('deleteforbiddenclient')
        self.client.force_login(profile.user)
        response = self.client.post(reverse('admin_client_delete', args=[profile.pk]))
        self.assertEqual(response.status_code, 403)


class NotaryDeleteTests(TestCase):
    def setUp(self):
        self.admin = make_admin_user()
        self.client.force_login(self.admin)

    def test_delete_button_appears_on_notaries_list(self):
        profile = make_notary_profile('deletelistnotary')
        response = self.client.get(reverse('admin_notaries'))
        self.assertContains(response, reverse('admin_notary_delete', args=[profile.pk]))

    def test_deletes_notary_with_no_documents_or_templates(self):
        profile = make_notary_profile('deletablenotary')
        user_pk = profile.user.pk
        response = self.client.post(reverse('admin_notary_delete', args=[profile.pk]))
        self.assertRedirects(response, reverse('admin_notaries'))
        self.assertFalse(NotaryProfile.objects.filter(pk=profile.pk).exists())
        self.assertFalse(User.objects.filter(pk=user_pk).exists())

    def test_blocks_deletion_when_notary_has_documents(self):
        profile = make_notary_profile('undeletablenotarydocs')
        template = make_template(created_by=profile)
        client_profile = make_client_profile('docsfornotarydelete')
        doc = Document(template=template, notary=profile, client=client_profile, city='Muqdisho')
        doc.finalize()
        doc.save()

        response = self.client.post(reverse('admin_notary_delete', args=[profile.pk]), follow=True)
        self.assertContains(response, 'lama tirtiri karo')
        self.assertTrue(NotaryProfile.objects.filter(pk=profile.pk).exists())

    def test_blocks_deletion_when_notary_has_templates(self):
        profile = make_notary_profile('undeletablenotarytpl')
        make_template(created_by=profile)

        response = self.client.post(reverse('admin_notary_delete', args=[profile.pk]), follow=True)
        self.assertContains(response, 'lama tirtiri karo')
        self.assertTrue(NotaryProfile.objects.filter(pk=profile.pk).exists())

    def test_get_request_does_not_delete(self):
        profile = make_notary_profile('getnodeletenotary')
        self.client.get(reverse('admin_notary_delete', args=[profile.pk]))
        self.assertTrue(NotaryProfile.objects.filter(pk=profile.pk).exists())

    def test_notary_role_forbidden(self):
        profile = make_notary_profile('deleteforbiddennotary')
        self.client.force_login(profile.user)
        response = self.client.post(reverse('admin_notary_delete', args=[profile.pk]))
        self.assertEqual(response.status_code, 403)
