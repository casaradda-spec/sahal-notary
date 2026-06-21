from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import Document
from .utils import qr_png_response


def home_redirect(request):
    if request.user.is_authenticated:
        return redirect(request.user.role_home_url())
    return redirect('login')


def verify(request, qr_token):
    document = (
        Document.objects.filter(qr_token=qr_token)
        .select_related('client__user', 'client2__user', 'notary__user', 'template')
        .first()
    )
    return render(request, 'portal/public/verify.html', {'document': document})


def qr_image(request, qr_token):
    document = get_object_or_404(Document, qr_token=qr_token)
    verify_url = request.build_absolute_uri(reverse('verify', args=[document.qr_token]))
    buf = qr_png_response(verify_url)
    return HttpResponse(buf.getvalue(), content_type='image/png')
