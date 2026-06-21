from django.test import TestCase
from django.urls import reverse

from portal.models import Document, DocumentTemplate

from .factories import make_client_profile, make_notary_profile, make_template


class ClientDashboardTests(TestCase):
    def setUp(self):
        self.notary = make_notary_profile('dashnotary')
        self.template = make_template(party_type=DocumentTemplate.PartyType.TWO, created_by=self.notary)
        self.client_profile = make_client_profile('dashclient')
        self.other_profile = make_client_profile('otherclient')

        self.own_doc_as_party1 = self._make_doc(self.client_profile, self.other_profile, Document.Status.PENDING)
        self.own_doc_as_party2 = self._make_doc(self.other_profile, self.client_profile, Document.Status.COMPLETED)
        self.unrelated_doc = self._make_doc(self.other_profile, None, Document.Status.PENDING, party_type_one=True)

    def _make_doc(self, client, client2, status, party_type_one=False):
        template = self.template
        if party_type_one:
            template = make_template(title='Solo', party_type=DocumentTemplate.PartyType.ONE)
        doc = Document(template=template, notary=self.notary, client=client, client2=client2, city='Muqdisho', status=status)
        doc.finalize()
        doc.save()
        return doc

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse('client_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_wrong_role_forbidden(self):
        self.client.force_login(self.notary.user)
        response = self.client.get(reverse('client_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_shows_only_documents_where_user_is_party1_or_party2(self):
        self.client.force_login(self.client_profile.user)
        response = self.client.get(reverse('client_dashboard'))
        docs = list(response.context['docs'])
        self.assertIn(self.own_doc_as_party1, docs)
        self.assertIn(self.own_doc_as_party2, docs)
        self.assertNotIn(self.unrelated_doc, docs)

    def test_status_filter_chip_narrows_results(self):
        self.client.force_login(self.client_profile.user)
        response = self.client.get(reverse('client_dashboard'), {'status': Document.Status.COMPLETED})
        docs = list(response.context['docs'])
        self.assertEqual(docs, [self.own_doc_as_party2])

    def test_counts_are_unaffected_by_the_status_filter(self):
        self.client.force_login(self.client_profile.user)
        response = self.client.get(reverse('client_dashboard'), {'status': Document.Status.COMPLETED})
        self.assertEqual(response.context['count_total'], 2)
        self.assertEqual(response.context['count_done'], 1)
        self.assertEqual(response.context['count_pending'], 1)


class ClientDocumentPdfTests(TestCase):
    def setUp(self):
        self.notary = make_notary_profile('pdfnotary')
        self.template = make_template(created_by=self.notary)
        self.owner = make_client_profile('pdfowner')
        self.stranger = make_client_profile('pdfstranger')
        self.doc = Document(template=self.template, notary=self.notary, client=self.owner, city='Muqdisho')
        self.doc.finalize()
        self.doc.save()

    def test_owner_can_download_pdf(self):
        self.client.force_login(self.owner.user)
        response = self.client.get(reverse('client_document_pdf', args=[self.doc.ref]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_non_owner_gets_404(self):
        self.client.force_login(self.stranger.user)
        response = self.client.get(reverse('client_document_pdf', args=[self.doc.ref]))
        self.assertEqual(response.status_code, 404)
