from django.test import TestCase
from django.utils.safestring import SafeString

from portal.models import Document, DocumentTemplate

from .base import TempMediaTestCase
from .factories import make_client_profile, make_notary_profile, make_template


class DocumentRenderingTests(TestCase):
    def setUp(self):
        self.notary = make_notary_profile('notary1', first='Maxamed', last='Daahir', license_number='NOT-001')
        self.client1 = make_client_profile('client1', first='Amina', last='Yusuf')
        self.client2 = make_client_profile('client2', first='Hodan', last='Maxamed')
        self.template = make_template(party_type=DocumentTemplate.PartyType.TWO, created_by=self.notary)

    def test_render_body_substitutes_all_placeholders(self):
        doc = Document(template=self.template, notary=self.notary, client=self.client1, client2=self.client2, city='Muqdisho')
        doc.ref = 'SNS-9001'
        rendered = doc.render_body()
        self.assertIn('Amina Yusuf', rendered)
        self.assertIn('Hodan Maxamed', rendered)
        self.assertIn('Muqdisho', rendered)
        self.assertIn('Maxamed Daahir', rendered)
        self.assertIn('NOT-001', rendered)
        self.assertIn('SNS-9001', rendered)
        self.assertNotIn('{{', rendered)
        self.assertNotIn('}}', rendered)

    def test_render_body_blanks_unknown_or_missing_placeholder(self):
        one_party_template = make_template(
            party_type=DocumentTemplate.PartyType.ONE,
            body='Solo: {{client_name}} / partner: {{client2_name}} / mystery: {{not_a_real_token}}',
        )
        doc = Document(template=one_party_template, notary=self.notary, client=self.client1, city='Muqdisho')
        doc.ref = 'SNS-9002'
        rendered = doc.render_body()
        self.assertIn('Solo: Amina Yusuf', rendered)
        self.assertIn('partner:  /', rendered)  # client2_name blank when no client2
        self.assertIn('mystery: ', rendered)  # unknown token blanked, not left as literal {{...}}

    def test_finalize_assigns_ref_snapshots_body_and_hashes_it(self):
        doc = Document(template=self.template, notary=self.notary, client=self.client1, client2=self.client2, city='Muqdisho')
        doc.finalize()
        self.assertTrue(doc.ref.startswith('SNS-'))
        self.assertTrue(doc.rendered_body)
        self.assertEqual(len(doc.content_hash), 64)  # sha256 hex digest length

        import hashlib
        expected_hash = hashlib.sha256(doc.rendered_body.encode('utf-8')).hexdigest()
        self.assertEqual(doc.content_hash, expected_hash)

    def test_finalize_does_not_overwrite_an_already_assigned_ref(self):
        doc = Document(template=self.template, notary=self.notary, client=self.client1, client2=self.client2, city='Muqdisho', ref='SNS-CUSTOM')
        doc.finalize()
        self.assertEqual(doc.ref, 'SNS-CUSTOM')

    def test_next_ref_increments_based_on_existing_rows(self):
        first_ref = Document.next_ref()
        doc = Document(template=self.template, notary=self.notary, client=self.client1, client2=self.client2, city='Muqdisho')
        doc.finalize()
        doc.save()
        second_ref = Document.next_ref()
        self.assertNotEqual(first_ref, second_ref)

    def test_body_paragraphs_splits_on_newlines_and_drops_blank_lines(self):
        doc = Document(template=self.template, notary=self.notary, client=self.client1, client2=self.client2, city='Muqdisho')
        doc.rendered_body = 'Paragraph one.\n\nParagraph two.\n   \nParagraph three.'
        self.assertEqual(doc.body_paragraphs, ['Paragraph one.', 'Paragraph two.', 'Paragraph three.'])


class ClientProfileDocCountTests(TestCase):
    def test_doc_count_includes_both_party1_and_party2_documents(self):
        notary = make_notary_profile('notary2')
        template = make_template(party_type=DocumentTemplate.PartyType.TWO, created_by=notary)
        c1 = make_client_profile('cdoc1')
        c2 = make_client_profile('cdoc2')

        self.assertEqual(c1.doc_count, 0)

        doc1 = Document(template=template, notary=notary, client=c1, client2=c2, city='Muqdisho')
        doc1.finalize()
        doc1.save()

        doc2 = Document(template=template, notary=notary, client=c2, client2=c1, city='Muqdisho')
        doc2.finalize()
        doc2.save()

        self.assertEqual(c1.doc_count, 2)  # one as party1, one as party2
        self.assertEqual(c2.doc_count, 2)


class DocumentTemplatePartyLabelTests(TestCase):
    def test_party_label_reflects_party_type(self):
        one = make_template(title='One', party_type=DocumentTemplate.PartyType.ONE)
        two = make_template(title='Two', party_type=DocumentTemplate.PartyType.TWO)
        self.assertEqual(one.party_label, 'Hal Dhinac')
        self.assertEqual(two.party_label, 'Laba Dhinac')


class SignatureEmbeddingTests(TempMediaTestCase):
    def setUp(self):
        self.notary = make_notary_profile('signotary')
        self.signed_client = make_client_profile('signedclient', first='Amina', last='Yusuf', with_signature=True)
        self.unsigned_client = make_client_profile('unsignedclient', first='Hodan', last='Maxamed')

    def test_signature_image_is_embedded_for_one_party_token(self):
        template = make_template(
            party_type=DocumentTemplate.PartyType.ONE,
            body='Saxiixa: {{client_signature}}',
        )
        doc = Document(template=template, notary=self.notary, client=self.signed_client, city='Muqdisho')
        doc.ref = 'SNS-9100'
        rendered = doc.render_body()
        self.assertIn('<img src=', rendered)
        self.assertIn(self.signed_client.signature.url, rendered)
        self.assertNotIn('sig-missing', rendered)

    def test_missing_signature_shows_warning_instead_of_breaking(self):
        template = make_template(
            party_type=DocumentTemplate.PartyType.ONE,
            body='Saxiixa: {{client_signature}}',
        )
        doc = Document(template=template, notary=self.notary, client=self.unsigned_client, city='Muqdisho')
        doc.ref = 'SNS-9101'
        rendered = doc.render_body()
        self.assertIn('Saxiix lama helin', rendered)
        self.assertNotIn('<img', rendered)

    def test_client1_and_client2_signature_tokens_resolve_independently(self):
        template = make_template(
            party_type=DocumentTemplate.PartyType.TWO,
            body='P1: {{client1_signature}} / P2: {{client2_signature}}',
        )
        doc = Document(
            template=template, notary=self.notary, client=self.signed_client,
            client2=self.unsigned_client, city='Muqdisho',
        )
        doc.ref = 'SNS-9102'
        rendered = doc.render_body()
        self.assertIn(self.signed_client.signature.url, rendered)
        self.assertIn('Saxiix lama helin', rendered)

    def test_client2_signature_blank_when_no_second_party(self):
        template = make_template(
            party_type=DocumentTemplate.PartyType.ONE,
            body='Solo sig: [{{client_signature}}] Party2 sig: [{{client2_signature}}]',
        )
        doc = Document(template=template, notary=self.notary, client=self.signed_client, city='Muqdisho')
        doc.ref = 'SNS-9103'
        rendered = doc.render_body()
        self.assertIn('Party2 sig: []', rendered)  # no client2 -> blank, not an error

    def test_text_values_are_html_escaped(self):
        malicious_client = make_client_profile('xssclient', first='<script>alert(1)</script>', last='X')
        template = make_template(party_type=DocumentTemplate.PartyType.ONE, body='Name: {{client_name}}')
        doc = Document(template=template, notary=self.notary, client=malicious_client, city='Muqdisho')
        doc.ref = 'SNS-9104'
        rendered = doc.render_body()
        self.assertNotIn('<script>', rendered)
        self.assertIn('&lt;script&gt;', rendered)

    def test_render_body_result_is_marked_safe_and_survives_paragraph_split(self):
        template = make_template(
            party_type=DocumentTemplate.PartyType.ONE,
            body='Line one.\nSaxiixa: {{client_signature}}',
        )
        doc = Document(template=template, notary=self.notary, client=self.signed_client, city='Muqdisho')
        doc.finalize()
        self.assertIsInstance(doc.rendered_body, SafeString)

        paragraphs = doc.body_paragraphs
        self.assertEqual(len(paragraphs), 2)
        for p in paragraphs:
            self.assertIsInstance(p, SafeString)
        self.assertIn('<img src=', paragraphs[1])
