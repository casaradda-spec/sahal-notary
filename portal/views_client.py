from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext_lazy as _

from accounts.decorators import role_required
from accounts.models import User

from .models import Document
from .utils import pdf_context, render_pdf

STATUS_CHIPS = [
    ('ALL', _('All')),
    (Document.Status.PENDING, _('Pending')),
    (Document.Status.SIGNED, _('Signed')),
    (Document.Status.COMPLETED, _('Completed')),
]


@role_required(User.Role.CLIENT)
def dashboard(request):
    profile = request.user.client_profile
    status = request.GET.get('status', 'ALL')

    docs = Document.objects.filter(Q(client=profile) | Q(client2=profile)).select_related(
        'template', 'notary__user'
    )
    all_docs = docs
    if status != 'ALL':
        docs = docs.filter(status=status)

    context = {
        'docs': docs,
        'count_total': all_docs.count(),
        'count_done': all_docs.filter(status=Document.Status.COMPLETED).count(),
        'count_pending': all_docs.filter(status=Document.Status.PENDING).count(),
        'chips': STATUS_CHIPS,
        'active_status': status,
    }
    return render(request, 'portal/client/dashboard.html', context)


@role_required(User.Role.CLIENT)
def document_pdf(request, ref):
    profile = request.user.client_profile
    document = get_object_or_404(
        Document.objects.select_related('notary').filter(Q(client=profile) | Q(client2=profile)), ref=ref
    )
    return render_pdf('portal/pdf/document.html', pdf_context(request, document), f'{document.ref}.pdf')
