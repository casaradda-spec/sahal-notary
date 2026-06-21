import uuid

from django.test import TestCase
from django.urls import reverse

from portal.models import Document

from .factories import make_client_profile, make_notary_profile, make_template


class VerifyPageTests(TestCase):
    def setUp(self):
        notary = make_notary_profile('verifynotary')
        template = make_template(created_by=notary)
        client_profile = make_client_profile('verifyclient', first='Amina', last='Yusuf')
        self.doc = Document(template=template, notary=notary, client=client_profile, city='Muqdisho')
        self.doc.finalize()
        self.doc.save()

    def test_valid_token_shows_document_details_no_auth_required(self):
        response = self.client.get(reverse('verify', args=[self.doc.qr_token]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['document'], self.doc)
        self.assertContains(response, 'Amina Yusuf')
        self.assertContains(response, self.doc.content_hash)
        self.assertContains(response, 'XAQIIJISAN')

    def test_unknown_token_shows_not_found_state_not_404(self):
        random_token = uuid.uuid4()
        response = self.client.get(reverse('verify', args=[random_token]))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['document'])
        self.assertContains(response, 'lama xaqiijin karo')


class QrImageTests(TestCase):
    def setUp(self):
        notary = make_notary_profile('qrnotary')
        template = make_template(created_by=notary)
        client_profile = make_client_profile('qrclient')
        self.doc = Document(template=template, notary=notary, client=client_profile, city='Muqdisho')
        self.doc.finalize()
        self.doc.save()

    def test_returns_png_for_valid_token_no_auth_required(self):
        response = self.client.get(reverse('qr_image', args=[self.doc.qr_token]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertGreater(len(response.content), 0)

    def test_unknown_token_404s(self):
        response = self.client.get(reverse('qr_image', args=[uuid.uuid4()]))
        self.assertEqual(response.status_code, 404)
