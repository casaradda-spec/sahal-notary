from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase

from portal.models import Document, DocumentTemplate
from portal.utils import generate_username, pdf_context, qr_data_uri, slugify_ascii

from .base import TempMediaTestCase
from .factories import make_client_profile, make_notary_profile, make_template, tiny_png_bytes

User = get_user_model()


class SlugifyAsciiTests(TestCase):
    def test_basic_two_word_name(self):
        self.assertEqual(slugify_ascii('Farhan.Axmed'), 'farhan.axmed')

    def test_strips_non_alphanumeric_and_lowercases(self):
        self.assertEqual(slugify_ascii("Ka'ase Nuur"), 'ka.ase.nuur')

    def test_empty_input_falls_back_to_user(self):
        self.assertEqual(slugify_ascii(''), 'user')


class GenerateUsernameTests(TestCase):
    def test_two_word_name_uses_first_dot_last(self):
        self.assertEqual(generate_username(User, 'Farhan Axmed'), 'farhan.axmed')

    def test_single_word_name(self):
        self.assertEqual(generate_username(User, 'Madonna'), 'madonna')

    def test_collision_appends_incrementing_suffix(self):
        User.objects.create_user(username='farhan.axmed', password='123')
        self.assertEqual(generate_username(User, 'Farhan Axmed'), 'farhan.axmed2')

        User.objects.create_user(username='farhan.axmed2', password='123')
        self.assertEqual(generate_username(User, 'Farhan Axmed'), 'farhan.axmed3')

    def test_many_word_name_uses_first_and_last_only(self):
        self.assertEqual(generate_username(User, 'Maxamed Daahir Axmed'), 'maxamed.axmed')


class QrDataUriTests(TestCase):
    def test_returns_a_base64_png_data_uri(self):
        uri = qr_data_uri('https://example.com/verify/abc/')
        self.assertTrue(uri.startswith('data:image/png;base64,'))


class PdfContextTests(TestCase):
    def test_includes_document_and_qr_data_uri_pointing_at_verify_url(self):
        notary = make_notary_profile('pdfcontextnotary')
        client = make_client_profile('pdfcontextclient')
        template = make_template(party_type=DocumentTemplate.PartyType.ONE, created_by=notary)
        doc = Document(template=template, notary=notary, client=client, city='Muqdisho')
        doc.finalize()
        doc.save()

        request = RequestFactory().get('/')
        context = pdf_context(request, doc)
        self.assertEqual(context['document'], doc)
        self.assertTrue(context['qr_data_uri'].startswith('data:image/png;base64,'))

    def test_document_pdf_template_embeds_the_qr_code(self):
        notary = make_notary_profile('pdftemplatenotary')
        client = make_client_profile('pdftemplateclient')
        template = make_template(party_type=DocumentTemplate.PartyType.ONE, created_by=notary)
        doc = Document(template=template, notary=notary, client=client, city='Muqdisho')
        doc.finalize()
        doc.save()

        context = pdf_context(RequestFactory().get('/'), doc)
        html = render_to_string('portal/pdf/document.html', context)
        self.assertIn(context['qr_data_uri'], html)


class PdfNotarySignatureTests(TempMediaTestCase):
    def _build_doc(self, notary):
        client = make_client_profile('pdfsignatureclient')
        template = make_template(party_type=DocumentTemplate.PartyType.ONE, created_by=notary)
        doc = Document(template=template, notary=notary, client=client, city='Muqdisho')
        doc.finalize()
        doc.save()
        return doc

    def test_renders_notary_signature_image_when_present(self):
        notary = make_notary_profile('pdfsignaturenotary')
        notary.signature.save('signature.png', ContentFile(tiny_png_bytes()), save=True)
        doc = self._build_doc(notary)

        context = pdf_context(RequestFactory().get('/'), doc)
        html = render_to_string('portal/pdf/document.html', context)
        self.assertIn(notary.signature.url, html)

    def test_renders_blank_underline_when_signature_missing(self):
        notary = make_notary_profile('pdfnosignaturenotary')
        doc = self._build_doc(notary)

        context = pdf_context(RequestFactory().get('/'), doc)
        html = render_to_string('portal/pdf/document.html', context)
        self.assertNotIn('<img src="" alt="Saxiixa', html)
        self.assertIn('class="sig-line" style="width:110px;"', html)
