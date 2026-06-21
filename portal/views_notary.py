import hashlib

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import User

from .forms import DocumentTemplateForm
from .models import AuditLog, Document, DocumentTemplate
from .utils import render_pdf, render_pdf_bytes


@role_required(User.Role.NOTARY)
def overview(request):
    notary = request.user.notary_profile
    docs = notary.documents.select_related('client__user').order_by('-created_at')
    stats = {
        'total': docs.count(),
        'signed': docs.filter(status=Document.Status.SIGNED).count(),
        'pending': docs.filter(status=Document.Status.PENDING).count(),
        'completed': docs.filter(status=Document.Status.COMPLETED).count(),
    }
    return render(request, 'portal/notary/overview.html', {'stats': stats, 'recent_docs': docs[:8], 'active_nav': 'overview'})


@role_required(User.Role.NOTARY)
def template_list(request):
    category = request.GET.get('category') or None
    templates = DocumentTemplate.objects.all().order_by('-created_at')
    if category:
        templates = templates.filter(category=category)
    categories = list(DocumentTemplate.objects.values_list('category', flat=True).distinct())
    return render(
        request,
        'portal/notary/template_list.html',
        {'templates': templates, 'categories': categories, 'active_category': category, 'active_nav': 'templates'},
    )


@role_required(User.Role.NOTARY)
def template_new(request):
    form = DocumentTemplateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        template = form.save(commit=False)
        template.created_by = request.user.notary_profile
        template.save()
        messages.success(request, f'Qaabka "{template.title}" waa la kaydiyay.')
        return redirect('notary_templates')
    return render(request, 'portal/notary/template_form.html', {'form': form, 'active_nav': 'templates'})


@role_required(User.Role.NOTARY)
def my_documents(request):
    notary = request.user.notary_profile
    docs = notary.documents.select_related('client__user', 'template').order_by('-created_at')
    return render(request, 'portal/notary/my_documents.html', {'docs': docs, 'active_nav': 'documents'})


@role_required(User.Role.NOTARY)
def profile(request):
    return render(
        request, 'portal/notary/profile.html', {'profile': request.user.notary_profile, 'active_nav': 'profile'}
    )


@role_required(User.Role.NOTARY)
def create_success(request, ref):
    document = get_object_or_404(Document, ref=ref, notary=request.user.notary_profile)
    qr_url = request.build_absolute_uri(reverse('verify', args=[document.qr_token]))
    return render(
        request,
        'portal/notary/create_success.html',
        {'document': document, 'qr_url': qr_url, 'active_nav': 'create'},
    )


@role_required(User.Role.NOTARY)
def document_pdf(request, ref):
    document = get_object_or_404(Document, ref=ref, notary=request.user.notary_profile)
    return render_pdf('portal/pdf/document.html', {'document': document}, f'{document.ref}.pdf')


@role_required(User.Role.NOTARY)
def document_detail(request, ref):
    document = get_object_or_404(
        Document.objects.select_related('client__user', 'client2__user', 'template', 'notary__user'),
        ref=ref, notary=request.user.notary_profile,
    )
    return render(request, 'portal/notary/document_detail.html', {'document': document, 'active_nav': 'documents'})


@role_required(User.Role.NOTARY)
def document_complete(request, ref):
    document = get_object_or_404(
        Document.objects.select_related('client__user', 'client2__user', 'template', 'notary__user'),
        ref=ref, notary=request.user.notary_profile,
    )
    if request.method != 'POST':
        return redirect('notary_document_detail', ref=ref)

    if document.status != Document.Status.PENDING:
        messages.error(request, 'Dokumeentigan horeyba ayuu u dhammaystirmay.')
        return redirect('notary_document_detail', ref=ref)

    missing = document.missing_signature_labels()
    if missing:
        messages.error(
            request,
            'Lama dhammaystirin karo — waxaa loo baahan yahay: ' + ', '.join(missing) + '.',
        )
        return redirect('notary_document_detail', ref=ref)

    document.status = Document.Status.COMPLETED
    document.signed_at = timezone.now()
    pdf_bytes = render_pdf_bytes('portal/pdf/document.html', {'document': document})
    document.pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    document.save(update_fields=['status', 'signed_at', 'pdf_hash'])

    AuditLog.objects.create(
        user=request.user,
        action=AuditLog.Action.DOCUMENT_COMPLETED,
        document=document,
        details=f'Dokumeenti {document.ref} waa la dhammaystiray oo la saxiixay.',
    )
    messages.success(request, f'Dokumeentiga {document.ref} waa la dhammaystiray oo la saxiixay.')
    return redirect('notary_document_detail', ref=ref)
