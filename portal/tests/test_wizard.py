from django.test import TestCase
from django.urls import reverse

from portal.models import Document, DocumentTemplate, NotaryProfile, Witness

from .base import TempMediaTestCase
from .factories import make_admin_user, make_client_profile, make_notary_profile, make_template

WIZARD_URL = reverse('notary_create')
PREFIX = 'create_document_wizard'


def post_step(client, current_step, data):
    payload = {f'{PREFIX}-current_step': current_step}
    payload.update(data)
    return client.post(WIZARD_URL, payload)


class WizardAccessTests(TestCase):
    def test_anonymous_redirected(self):
        response = self.client.get(WIZARD_URL)
        self.assertEqual(response.status_code, 302)

    def test_wrong_role_forbidden(self):
        client_profile = make_client_profile('wizardintruder')
        self.client.force_login(client_profile.user)
        response = self.client.get(WIZARD_URL)
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access(self):
        admin = make_admin_user()
        self.client.force_login(admin)
        response = self.client.get(WIZARD_URL)
        self.assertEqual(response.status_code, 200)

    def test_client_step_has_live_search_input(self):
        admin = make_admin_user()
        self.client.force_login(admin)
        response = self.client.get(WIZARD_URL)
        self.assertContains(response, 'id="client-search-input"')


class AdminCreatesDocumentTests(TempMediaTestCase):
    """Admin and Notary share the document-creation wizard; an Admin has no NotaryProfile
    of their own, so one is lazily provisioned to stand in as the document's signer."""

    def setUp(self):
        self.admin = make_admin_user()
        self.template = make_template(party_type=DocumentTemplate.PartyType.ONE, requires_witnesses=False)
        self.solo_client = make_client_profile('adminwizardclient', first='Amina', last='Yusuf', with_signature=True)
        self.client.force_login(self.admin)

    def test_admin_completes_wizard_and_is_provisioned_a_notary_profile(self):
        post_step(self.client, 'client', {'client-client': self.solo_client.pk})
        post_step(self.client, 'template', {'template-template': self.template.pk})
        response = post_step(self.client, 'confirm', {})
        doc = Document.objects.get()
        self.assertRedirects(response, reverse('notary_create_success', args=[doc.ref]))

        notary_profile = NotaryProfile.objects.get(user=self.admin)
        self.assertEqual(doc.notary, notary_profile)


class RequiredClientFieldsValidationTests(TempMediaTestCase):
    def setUp(self):
        self.notary = make_notary_profile('reqfieldsnotary')
        self.template = make_template(party_type=DocumentTemplate.PartyType.TWO, created_by=self.notary)
        self.client.force_login(self.notary.user)

    def test_blocks_client_step_when_signature_and_phone_missing(self):
        incomplete = make_client_profile('incompleteclient', first='Cabdi', last='Xasan', phone='', with_signature=False)
        response = post_step(self.client, 'client', {'client-client': incomplete.pk})
        self.assertEqual(response.context['wizard']['steps'].current, 'client')
        self.assertContains(response, 'Cabdi Xasan: phone missing, signature missing')

    def test_blocks_party2_step_when_signature_missing(self):
        complete = make_client_profile('completepartyone', with_signature=True)
        incomplete2 = make_client_profile('incompleteparty2', first='Hodan', last='Maxamed', with_signature=False)

        post_step(self.client, 'client', {'client-client': complete.pk})
        post_step(self.client, 'template', {'template-template': self.template.pk})
        response = post_step(self.client, 'party2', {'party2-client2': incomplete2.pk})
        self.assertEqual(response.context['wizard']['steps'].current, 'party2')
        self.assertContains(response, 'Hodan Maxamed: signature missing')


class TwoPartyNoWitnessWizardTests(TempMediaTestCase):
    """Lease-style template: party2 step required, witnesses step skipped."""

    def setUp(self):
        self.notary = make_notary_profile('leasewizardnotary', license_number='NOT-LEASE-1')
        self.template = make_template(
            title='Heshiiska Kirada', party_type=DocumentTemplate.PartyType.TWO, requires_witnesses=False,
            created_by=self.notary,
        )
        self.client1 = make_client_profile('leaseclient1', first='Amina', last='Yusuf', with_signature=True)
        self.client2 = make_client_profile('leaseclient2', first='Hodan', last='Maxamed', with_signature=True)
        self.client.force_login(self.notary.user)

    def test_full_flow_skips_witnesses_and_creates_document(self):
        response = self.client.get(WIZARD_URL)
        self.assertEqual(response.context['wizard']['steps'].current, 'client')

        response = post_step(self.client, 'client', {'client-client': self.client1.pk})
        self.assertEqual(response.context['wizard']['steps'].current, 'template')

        response = post_step(self.client, 'template', {'template-template': self.template.pk})
        # two-party template -> party2 step next, not witnesses (requires_witnesses=False)
        self.assertEqual(response.context['wizard']['steps'].current, 'party2')

        # party2 choices must exclude the already-selected client1
        party2_choices = list(response.context['wizard']['form']['client2'].field.queryset)
        self.assertNotIn(self.client1, party2_choices)
        self.assertIn(self.client2, party2_choices)

        response = post_step(self.client, 'party2', {'party2-client2': self.client2.pk})
        # no witnesses required -> straight to confirm, skipping the witnesses step
        self.assertEqual(response.context['wizard']['steps'].current, 'confirm')
        self.assertIn('Amina Yusuf', response.context['preview_body'])
        self.assertIn('Hodan Maxamed', response.context['preview_body'])
        self.assertTrue(response.context['is_two_party'])

        response = post_step(self.client, 'confirm', {})
        doc = Document.objects.get()
        self.assertRedirects(response, reverse('notary_create_success', args=[doc.ref]))
        self.assertEqual(doc.client, self.client1)
        self.assertEqual(doc.client2, self.client2)
        self.assertEqual(doc.notary, self.notary)
        self.assertEqual(doc.witnesses.count(), 0)
        self.assertTrue(doc.content_hash)

        self.template.refresh_from_db()
        self.assertEqual(self.template.times_used, 1)


class OnePartyWithWitnessWizardTests(TempMediaTestCase):
    """Will-style template: party2 step skipped, witnesses step required."""

    def setUp(self):
        self.notary = make_notary_profile('willwizardnotary', license_number='NOT-WILL-1')
        self.template = make_template(
            title='Dardaaran Qoyseed', party_type=DocumentTemplate.PartyType.ONE, requires_witnesses=True,
            created_by=self.notary,
        )
        self.solo_client = make_client_profile('willclient', first='Faadumo', last='Aadan', with_signature=True)
        self.client.force_login(self.notary.user)

    def test_full_flow_skips_party2_and_records_witnesses(self):
        post_step(self.client, 'client', {'client-client': self.solo_client.pk})
        response = post_step(self.client, 'template', {'template-template': self.template.pk})
        # one-party template -> party2 skipped entirely, straight to witnesses
        self.assertEqual(response.context['wizard']['steps'].current, 'witnesses')

        response = post_step(self.client, 'witnesses', {
            'witnesses-TOTAL_FORMS': '2',
            'witnesses-INITIAL_FORMS': '0',
            'witnesses-MIN_NUM_FORMS': '0',
            'witnesses-MAX_NUM_FORMS': '5',
            'witnesses-0-name': 'Cali Nuur',
            'witnesses-0-phone': '0611112222',
            'witnesses-1-name': '',
            'witnesses-1-phone': '',
        })
        self.assertEqual(response.context['wizard']['steps'].current, 'confirm')
        self.assertFalse(response.context['is_two_party'])
        self.assertTrue(response.context['show_witnesses_preview'])
        self.assertEqual(len(response.context['preview_witnesses']), 1)

        response = post_step(self.client, 'confirm', {})
        doc = Document.objects.get()
        self.assertRedirects(response, reverse('notary_create_success', args=[doc.ref]))
        self.assertIsNone(doc.client2)
        self.assertEqual(doc.witnesses.count(), 1)
        witness = doc.witnesses.get()
        self.assertEqual(witness.name, 'Cali Nuur')

    def test_blank_witness_rows_are_not_saved(self):
        post_step(self.client, 'client', {'client-client': self.solo_client.pk})
        post_step(self.client, 'template', {'template-template': self.template.pk})
        post_step(self.client, 'witnesses', {
            'witnesses-TOTAL_FORMS': '2',
            'witnesses-INITIAL_FORMS': '0',
            'witnesses-MIN_NUM_FORMS': '0',
            'witnesses-MAX_NUM_FORMS': '5',
            'witnesses-0-name': '',
            'witnesses-0-phone': '',
            'witnesses-1-name': '',
            'witnesses-1-phone': '',
        })
        post_step(self.client, 'confirm', {})
        doc = Document.objects.get()
        self.assertEqual(Witness.objects.filter(document=doc).count(), 0)
