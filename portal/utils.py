import base64
import io
import re
import unicodedata

import qrcode
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa


def slugify_ascii(value):
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^a-zA-Z0-9]+', '.', value).strip('.').lower()
    return value or 'user'


def generate_username(user_model, full_name):
    parts = full_name.strip().split()
    base = slugify_ascii(f'{parts[0]}.{parts[-1]}') if len(parts) > 1 else slugify_ascii(full_name)
    username = base
    n = 1
    while user_model.objects.filter(username=username).exists():
        n += 1
        username = f'{base}{n}'
    return username


def decode_signature_data_url(data_url):
    """Decode a `data:image/png;base64,...` string from the signature pad into a ContentFile.

    Returns None for an empty/untouched canvas, so "leave unchanged" works on the edit form.
    """
    if not data_url or ',' not in data_url:
        return None
    header, encoded = data_url.split(',', 1)
    if not encoded:
        return None
    return ContentFile(base64.b64decode(encoded), name='signature.png')


def pdf_link_callback(uri, rel):
    """Map a MEDIA_URL/STATIC_URL-prefixed URI to an absolute filesystem path.

    xhtml2pdf can't fetch /media/ or /static/ URLs over HTTP from inside the
    Django process, so embedded images (e.g. a client's signature) need this
    to resolve to a real file on disk instead.
    """
    if uri.startswith(settings.MEDIA_URL):
        return str(settings.MEDIA_ROOT / uri[len(settings.MEDIA_URL):])
    if uri.startswith(settings.STATIC_URL):
        path = finders.find(uri[len(settings.STATIC_URL):])
        if path:
            return path
    return uri


def qr_png_response(data_url):
    img = qrcode.make(data_url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


def render_pdf_bytes(template_name, context):
    """Render a template to PDF and return the raw bytes (e.g. for hashing) without
    tying the result to an HTTP response."""
    html = render_to_string(template_name, context)
    buf = io.BytesIO()
    pisa.CreatePDF(src=html, dest=buf, link_callback=pdf_link_callback)
    return buf.getvalue()


def render_pdf(template_name, context, filename):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    response.write(render_pdf_bytes(template_name, context))
    return response
