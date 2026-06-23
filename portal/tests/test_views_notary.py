from django.test import TestCase
from django.urls import reverse

from portal.models import AuditLog, Document, DocumentTemplate, Witness

from .base import TempMediaTestCase
from .factories import make_admin_user, make_client_profile, make_notary_profile, make_template


class NotaryOverviewTests(TestCase):
    def setUp(self):
        self.notary = make_notary_profile('overviewnotary')
        self.other_notary = make_notary_profile('othernotary')
        self.template = make_template(created_by=self.notary)
        self.client_profile = make_client_profile('overviewclient')

        self._make_doc(self.notary, Document.Status.PENDING)
        self._make_doc(self.notary, Document.Status.SIGNED)
        self._make_doc(self.notary, Document.Status.COMPLETED)
        self._make_doc(self.other_notary, Document.Status.PENDING)  # belongs to a different notary

    def _make_doc(self, notary, status):
        doc = Document(template=self.template, notary=notary, client=self.client_profile, city='Muqdisho', status=status)
        doc.finalize()
        doc.save()
        return doc

    def test_anonymous_redirected(self):
        response = self.client.get(reverse('notary_overview'))
        self.assertEqual(response.status_code, 302)

    def test_wrong_role_forbidden(self):
        self.client.force_login(self.client_profile.user)
        response = self.client.get(reverse('notary_overview'))
        self.assertEqual(response.status_code, 403)

    def test_admin_forbidden_overview_is_notary_only(self):
        admin = make_admin_user()
        self.client.force_login(admin)
        response = self.client.get(reverse('notary_overview'))
        self.assertEqual(response.status_code, 403)

    def test_stats_only_count_this_notarys_documents(self):
        self.client.force_login(self.notary.user)
        response = self.client.get(reverse('notary_overview'))
        stats = response.context['stats']
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['pending'], 1)
        self.assertEqual(stats['signed'], 1)
        self.assertEqual(stats['completed'], 1)


class TemplateListAndCreateTests(TestCase):
    def setUp(self):
        self.notary = make_notary_profile('tplnotary')
        make_template(title='Lease', category='Heshiis Kirada', created_by=self.notary)
        make_template(title='Will', category='Dardaaran', created_by=self.notary)

    def test_category_filter(self):
        self.client.force_login(self.notary.user)
        response = self.client.get(reverse('notary_templates'), {'category': 'Dardaaran'})
        titles = [t.title for t in response.context['templates']]
        self.assertEqual(titles, ['Will'])

    def test_create_template_assigns_created_by_to_current_notary(self):
        self.client.force_login(self.notary.user)
        response = self.client.post(reverse('notary_template_new'), {
            'title': 'Power of Attorney',
            'category': 'Wakaalad',
            'party_type': DocumentTemplate.PartyType.ONE,
            'requires_witnesses': False,
            'body': '{{client_name}} {{date}} {{city}} {{notary_name}} {{notary_license}} {{ref}}',
        })
        self.assertRedirects(response, reverse('notary_templates'))
        created = DocumentTemplate.objects.get(title='Power of Attorney')
        self.assertEqual(created.created_by, self.notary)

    def test_admin_can_list_and_create_templates(self):
        admin = make_admin_user()
        self.client.force_login(admin)
        response = self.client.get(reverse('notary_templates'))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('notary_template_new'), {
            'title': 'Admin Made Template',
            'category': 'Wakaalad',
            'party_type': DocumentTemplate.PartyType.ONE,
            'requires_witnesses': False,
            'body': '{{client_name}} {{date}} {{city}} {{notary_name}} {{notary_license}} {{ref}}',
        })
        self.assertRedirects(response, reverse('notary_templates'))
        self.assertTrue(DocumentTemplate.objects.filter(title='Admin Made Template').exists())

    def test_wrong_role_forbidden(self):
        client_profile = make_client_profile('tplaccessclient')
        self.client.force_login(client_profile.user)
        response = self.client.get(reverse('notary_templates'))
        self.assertEqual(response.status_code, 403)


class TemplateEditDeleteTests(TestCase):
    def setUp(self):
        self.notary = make_notary_profile('editdeletenotary')
        self.template = make_template(title='Editable', created_by=self.notary)

    def test_notary_can_edit_template(self):
        self.client.force_login(self.notary.user)
        response = self.client.post(reverse('notary_template_edit', args=[self.template.pk]), {
            'title': 'Renamed',
            'category': self.template.category,
            'party_type': self.template.party_type,
            'requires_witnesses': False,
            'body': self.template.body,
        })
        self.assertRedirects(response, reverse('notary_templates'))
        self.template.refresh_from_db()
        self.assertEqual(self.template.title, 'Renamed')

    def test_admin_can_edit_template(self):
        admin = make_admin_user()
        self.client.force_login(admin)
        response = self.client.post(reverse('notary_template_edit', args=[self.template.pk]), {
            'title': 'Renamed By Admin',
            'category': self.template.category,
            'party_type': self.template.party_type,
            'requires_witnesses': False,
            'body': self.template.body,
        })
        self.assertRedirects(response, reverse('notary_templates'))
        self.template.refresh_from_db()
        self.assertEqual(self.template.title, 'Renamed By Admin')

    def test_unused_template_can_be_deleted(self):
        self.client.force_login(self.notary.user)
        response = self.client.post(reverse('notary_template_delete', args=[self.template.pk]))
        self.assertRedirects(response, reverse('notary_templates'))
        self.assertFalse(DocumentTemplate.objects.filter(pk=self.template.pk).exists())

    def test_used_template_cannot_be_deleted(self):
        DocumentTemplate.objects.filter(pk=self.template.pk).update(times_used=1)
        self.client.force_login(self.notary.user)
        response = self.client.post(reverse('notary_template_delete', args=[self.template.pk]), follow=True)
        self.assertContains(response, 'lama tirtiri karo')
        self.assertTrue(DocumentTemplate.objects.filter(pk=self.template.pk).exists())


class AllDocumentsTests(TestCase):
    def setUp(self):
        self.notary = make_notary_profile('mydocsnotary')
        self.other_notary = make_notary_profile('othermydocsnotary')
        self.template = make_template(created_by=self.notary)
        self.client_profile = make_client_profile('mydocsclient')

        self.own_doc = Document(template=self.template, notary=self.notary, client=self.client_profile, city='Muqdisho')
        self.own_doc.finalize()
        self.own_doc.save()

        self.other_doc = Document(template=self.template, notary=self.other_notary, client=self.client_profile, city='Muqdisho')
        self.other_doc.finalize()
        self.other_doc.save()

    def test_notary_sees_documents_from_every_notary(self):
        self.client.force_login(self.notary.user)
        response = self.client.get(reverse('notary_documents'))
        docs = list(response.context['docs'])
        self.assertIn(self.own_doc, docs)
        self.assertIn(self.other_doc, docs)

    def test_admin_sees_documents_from_every_notary(self):
        admin = make_admin_user()
        self.client.force_login(admin)
        response = self.client.get(reverse('notary_documents'))
        docs = list(response.context['docs'])
        self.assertIn(self.own_doc, docs)
        self.assertIn(self.other_doc, docs)

    def test_client_role_forbidden(self):
        self.client.force_login(self.client_profile.user)
        response = self.client.get(reverse('notary_documents'))
        self.assertEqual(response.status_code, 403)


class NotaryDocumentPdfAndSuccessTests(TestCase):
    def setUp(self):
        self.notary = make_notary_profile('pdfnotary2')
        self.other_notary = make_notary_profile('otherpdfnotary2')
        self.template = make_template(created_by=self.notary)
        self.client_profile = make_client_profile('pdfclient2')
        self.doc = Document(template=self.template, notary=self.notary, client=self.client_profile, city='Muqdisho')
        self.doc.finalize()
        self.doc.save()

    def test_owning_notary_can_download_pdf(self):
        self.client.force_login(self.notary.user)
        response = self.client.get(reverse('notary_document_pdf', args=[self.doc.ref]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_other_notary_can_also_download_pdf(self):
        self.client.force_login(self.other_notary.user)
        response = self.client.get(reverse('notary_document_pdf', args=[self.doc.ref]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_other_notary_gets_404_for_success_page(self):
        self.client.force_login(self.other_notary.user)
        response = self.client.get(reverse('notary_create_success', args=[self.doc.ref]))
        self.assertEqual(response.status_code, 404)

    def test_owning_notary_sees_success_page_with_qr_url(self):
        self.client.force_login(self.notary.user)
        response = self.client.get(reverse('notary_create_success', args=[self.doc.ref]))
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(self.doc.qr_token), response.context['qr_url'])


class NotaryDocumentDetailTests(TestCase):
    def setUp(self):
        self.notary = make_notary_profile('detailnotary')
        self.other_notary = make_notary_profile('otherdetailnotary')
        self.template = make_template(created_by=self.notary)
        self.client_profile = make_client_profile('detailclient')
        self.doc = Document(template=self.template, notary=self.notary, client=self.client_profile, city='Muqdisho')
        self.doc.finalize()
        self.doc.save()

    def test_owning_notary_can_view_detail_page(self):
        self.client.force_login(self.notary.user)
        response = self.client.get(reverse('notary_document_detail', args=[self.doc.ref]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['document'], self.doc)

    def test_other_notary_can_also_view_detail_page(self):
        self.client.force_login(self.other_notary.user)
        response = self.client.get(reverse('notary_document_detail', args=[self.doc.ref]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['document'], self.doc)

    def test_admin_can_view_detail_page(self):
        admin = make_admin_user()
        self.client.force_login(admin)
        response = self.client.get(reverse('notary_document_detail', args=[self.doc.ref]))
        self.assertEqual(response.status_code, 200)

    def test_client_role_forbidden(self):
        self.client.force_login(self.client_profile.user)
        response = self.client.get(reverse('notary_document_detail', args=[self.doc.ref]))
        self.assertEqual(response.status_code, 403)

    def test_complete_button_only_shown_when_pending(self):
        self.client.force_login(self.notary.user)
        response = self.client.get(reverse('notary_document_detail', args=[self.doc.ref]))
        self.assertContains(response, 'Complete')

        self.doc.status = Document.Status.COMPLETED
        self.doc.save(update_fields=['status'])
        response = self.client.get(reverse('notary_document_detail', args=[self.doc.ref]))
        self.assertNotContains(response, 'Complete &amp; Sign')

    def test_edit_button_only_shown_when_pending(self):
        self.client.force_login(self.notary.user)
        edit_url = reverse('notary_document_edit', args=[self.doc.ref])
        response = self.client.get(reverse('notary_document_detail', args=[self.doc.ref]))
        self.assertContains(response, edit_url)

        self.doc.status = Document.Status.COMPLETED
        self.doc.save(update_fields=['status'])
        response = self.client.get(reverse('notary_document_detail', args=[self.doc.ref]))
        self.assertNotContains(response, edit_url)


class DocumentEditTests(TempMediaTestCase):
    def setUp(self):
        self.notary = make_notary_profile('editnotary')
        self.one_party_template = make_template(
            title='Original', party_type=DocumentTemplate.PartyType.ONE, created_by=self.notary,
        )
        self.two_party_template = make_template(
            title='TwoParty', party_type=DocumentTemplate.PartyType.TWO, created_by=self.notary,
        )
        self.original_client = make_client_profile('editorigclient', first='Amina', last='Yusuf', with_signature=True)
        self.new_client = make_client_profile('editnewclient', first='Cabdi', last='Xasan', with_signature=True)
        self.doc = Document(template=self.one_party_template, notary=self.notary, client=self.original_client, city='Muqdisho')
        self.doc.finalize()
        self.doc.save()
        self.client.force_login(self.notary.user)

    def test_get_prefills_current_selections(self):
        response = self.client.get(reverse('notary_document_edit', args=[self.doc.ref]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form'].initial['client'], self.original_client)
        self.assertEqual(response.context['form'].initial['template'], self.one_party_template)

    def test_completed_document_cannot_be_edited(self):
        self.doc.status = Document.Status.COMPLETED
        self.doc.save(update_fields=['status'])
        response = self.client.get(reverse('notary_document_edit', args=[self.doc.ref]))
        self.assertEqual(response.status_code, 404)

    def test_changing_client_and_template_regenerates_rendered_body(self):
        old_hash = self.doc.content_hash
        response = self.client.post(reverse('notary_document_edit', args=[self.doc.ref]), {
            'template': self.one_party_template.pk,
            'client': self.new_client.pk,
        })
        self.assertRedirects(response, reverse('notary_document_detail', args=[self.doc.ref]))

        self.doc.refresh_from_db()
        self.assertEqual(self.doc.client, self.new_client)
        self.assertEqual(self.doc.status, Document.Status.PENDING)
        self.assertIn('Cabdi Xasan', self.doc.rendered_body)
        self.assertNotEqual(self.doc.content_hash, old_hash)

    def test_two_party_template_requires_client2(self):
        response = self.client.post(reverse('notary_document_edit', args=[self.doc.ref]), {
            'template': self.two_party_template.pk,
            'client': self.original_client.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'macmiilka labaad')
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.template, self.one_party_template)

    def test_incomplete_new_client_blocks_save(self):
        incomplete = make_client_profile('editincomplete', first='Faadumo', last='Aadan', with_signature=False)
        response = self.client.post(reverse('notary_document_edit', args=[self.doc.ref]), {
            'template': self.one_party_template.pk,
            'client': incomplete.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Faadumo Aadan: signature missing')
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.client, self.original_client)


class DocumentCompletionTests(TempMediaTestCase):
    def setUp(self):
        self.notary = make_notary_profile('completenotary')
        self.other_notary = make_notary_profile('othercompletenotary')

    def _make_doc(self, template=None, client=None, client2=None):
        template = template or make_template(party_type=DocumentTemplate.PartyType.ONE, created_by=self.notary)
        client = client or make_client_profile('completeclient', with_signature=True)
        doc = Document(template=template, notary=self.notary, client=client, client2=client2, city='Muqdisho')
        doc.finalize()
        doc.save()
        return doc

    def test_get_request_does_not_complete_the_document(self):
        doc = self._make_doc()
        self.client.force_login(self.notary.user)
        self.client.get(reverse('notary_document_complete', args=[doc.ref]))
        doc.refresh_from_db()
        self.assertEqual(doc.status, Document.Status.PENDING)

    def test_other_notary_can_also_complete_the_document(self):
        doc = self._make_doc()
        self.client.force_login(self.other_notary.user)
        response = self.client.post(reverse('notary_document_complete', args=[doc.ref]))
        self.assertRedirects(response, reverse('notary_document_detail', args=[doc.ref]))
        doc.refresh_from_db()
        self.assertEqual(doc.status, Document.Status.COMPLETED)

    def test_admin_can_complete_the_document(self):
        doc = self._make_doc()
        admin = make_admin_user()
        self.client.force_login(admin)
        response = self.client.post(reverse('notary_document_complete', args=[doc.ref]))
        self.assertRedirects(response, reverse('notary_document_detail', args=[doc.ref]))
        doc.refresh_from_db()
        self.assertEqual(doc.status, Document.Status.COMPLETED)

    def test_blocks_completion_when_client_signature_missing(self):
        unsigned_client = make_client_profile('nosigclient')
        doc = self._make_doc(client=unsigned_client)
        self.client.force_login(self.notary.user)
        response = self.client.post(reverse('notary_document_complete', args=[doc.ref]), follow=True)
        doc.refresh_from_db()
        self.assertEqual(doc.status, Document.Status.PENDING)
        self.assertContains(response, 'Lama dhammaystirin karo')
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_blocks_completion_when_party2_signature_missing(self):
        signed = make_client_profile('p1signed', with_signature=True)
        unsigned = make_client_profile('p2unsigned')
        template = make_template(party_type=DocumentTemplate.PartyType.TWO, created_by=self.notary)
        doc = self._make_doc(template=template, client=signed, client2=unsigned)
        self.client.force_login(self.notary.user)
        self.client.post(reverse('notary_document_complete', args=[doc.ref]))
        doc.refresh_from_db()
        self.assertEqual(doc.status, Document.Status.PENDING)

    def test_blocks_completion_when_required_witnesses_missing(self):
        template = make_template(party_type=DocumentTemplate.PartyType.ONE, requires_witnesses=True, created_by=self.notary)
        doc = self._make_doc(template=template)
        self.client.force_login(self.notary.user)
        self.client.post(reverse('notary_document_complete', args=[doc.ref]))
        doc.refresh_from_db()
        self.assertEqual(doc.status, Document.Status.PENDING)

    def test_completes_when_required_witnesses_present(self):
        template = make_template(party_type=DocumentTemplate.PartyType.ONE, requires_witnesses=True, created_by=self.notary)
        doc = self._make_doc(template=template)
        Witness.objects.create(document=doc, name='Cali Nuur', order=1)
        self.client.force_login(self.notary.user)
        response = self.client.post(reverse('notary_document_complete', args=[doc.ref]))
        self.assertRedirects(response, reverse('notary_document_detail', args=[doc.ref]))
        doc.refresh_from_db()
        self.assertEqual(doc.status, Document.Status.COMPLETED)

    def test_successful_completion_sets_status_hash_and_signed_at(self):
        doc = self._make_doc()
        self.client.force_login(self.notary.user)
        response = self.client.post(reverse('notary_document_complete', args=[doc.ref]))
        self.assertRedirects(response, reverse('notary_document_detail', args=[doc.ref]))

        doc.refresh_from_db()
        self.assertEqual(doc.status, Document.Status.COMPLETED)
        self.assertIsNotNone(doc.signed_at)
        self.assertEqual(len(doc.pdf_hash), 64)  # sha256 hex digest length

    def test_successful_completion_writes_audit_log(self):
        doc = self._make_doc()
        self.client.force_login(self.notary.user)
        self.client.post(reverse('notary_document_complete', args=[doc.ref]))

        entry = AuditLog.objects.get(document=doc)
        self.assertEqual(entry.user, self.notary.user)
        self.assertEqual(entry.action, AuditLog.Action.DOCUMENT_COMPLETED)

    def test_cannot_complete_an_already_completed_document(self):
        doc = self._make_doc()
        doc.status = Document.Status.COMPLETED
        doc.save(update_fields=['status'])
        self.client.force_login(self.notary.user)
        response = self.client.post(reverse('notary_document_complete', args=[doc.ref]), follow=True)
        self.assertContains(response, 'horeyba')
        self.assertEqual(AuditLog.objects.count(), 0)
