from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from accounts.models import User as AccountsUser

from .forms import ClientCreateForm, ClientEditForm, NotaryCreateForm, NotaryEditForm
from .models import ClientProfile, Document, NotaryProfile
from .utils import decode_signature_data_url, generate_username, role_base_template

User = get_user_model()
TEMP_PASSWORD = '123'


def _split_name(full_name):
    parts = full_name.strip().split()
    first = parts[0] if parts else full_name
    last = ' '.join(parts[1:])
    return first, last


@role_required(AccountsUser.Role.ADMIN, AccountsUser.Role.NOTARY)
def clients_view(request):
    if request.method == 'POST':
        form = ClientCreateForm(request.POST)
        if form.is_valid():
            full_name = form.cleaned_data['full_name'].strip()
            first, last = _split_name(full_name)
            signature_file = decode_signature_data_url(request.POST.get('signature_data', ''))
            with transaction.atomic():
                username = generate_username(User, full_name)
                user = User.objects.create_user(
                    username=username,
                    password=TEMP_PASSWORD,
                    first_name=first,
                    last_name=last,
                    email=form.cleaned_data.get('email') or '',
                    role=AccountsUser.Role.CLIENT,
                )
                ClientProfile.objects.create(
                    user=user,
                    national_id=form.cleaned_data.get('national_id', ''),
                    phone=form.cleaned_data.get('phone', ''),
                    city=form.cleaned_data.get('city', ''),
                    address=form.cleaned_data.get('address', ''),
                    signature=signature_file,
                )
            messages.success(
                request,
                f'Macmiilka "{full_name}" waa la diiwaangeliyay. '
                f'Username: {username} · Furaha hore: {TEMP_PASSWORD}',
            )
            return redirect('admin_clients')
        tab = 'add'
    else:
        form = ClientCreateForm()
        tab = request.GET.get('tab', 'list')

    clients = ClientProfile.objects.select_related('user').order_by('-created_at')
    return render(
        request,
        'portal/admin/clients.html',
        {'form': form, 'clients': clients, 'tab': tab, 'active_nav': 'clients', 'base_template': role_base_template(request.user)},
    )


@role_required(AccountsUser.Role.ADMIN, AccountsUser.Role.NOTARY)
def client_signature(request, pk):
    profile = get_object_or_404(ClientProfile.objects.select_related('user'), pk=pk)
    if request.method == 'POST':
        signature_file = decode_signature_data_url(request.POST.get('signature_data', ''))
        if signature_file is not None:
            profile.signature = signature_file
            profile.save(update_fields=['signature'])
            messages.success(request, f'Saxiixa {profile.user.get_full_name()} waa la kaydiyay.')
        return redirect('admin_clients')

    return render(
        request,
        'portal/admin/client_signature.html',
        {'profile': profile, 'active_nav': 'clients', 'base_template': role_base_template(request.user)},
    )


@role_required(AccountsUser.Role.ADMIN, AccountsUser.Role.NOTARY)
def client_edit(request, pk):
    profile = get_object_or_404(ClientProfile.objects.select_related('user'), pk=pk)
    if request.method == 'POST':
        form = ClientEditForm(request.POST, instance_pk=profile.pk)
        if form.is_valid():
            full_name = form.cleaned_data['full_name'].strip()
            first, last = _split_name(full_name)
            signature_file = decode_signature_data_url(request.POST.get('signature_data', ''))
            with transaction.atomic():
                profile.user.first_name = first
                profile.user.last_name = last
                profile.user.email = form.cleaned_data.get('email') or ''
                profile.user.save(update_fields=['first_name', 'last_name', 'email'])

                profile.phone = form.cleaned_data['phone']
                profile.national_id = form.cleaned_data['national_id']
                profile.address = form.cleaned_data['address']
                profile.city = form.cleaned_data['city']
                if signature_file is not None:
                    profile.signature = signature_file
                profile.save()
            messages.success(request, f'Macmiilka "{full_name}" waa la cusbooneysiiyay.')
            return redirect('admin_clients')
    else:
        form = ClientEditForm(instance_pk=profile.pk, initial={
            'full_name': profile.user.get_full_name(),
            'phone': profile.phone,
            'national_id': profile.national_id,
            'address': profile.address,
            'city': profile.city,
            'email': profile.user.email,
        })

    return render(
        request,
        'portal/admin/client_edit.html',
        {'form': form, 'profile': profile, 'active_nav': 'clients', 'base_template': role_base_template(request.user)},
    )


@role_required(AccountsUser.Role.ADMIN, AccountsUser.Role.NOTARY)
def client_delete(request, pk):
    profile = get_object_or_404(ClientProfile.objects.select_related('user'), pk=pk)
    if request.method != 'POST':
        return redirect('admin_clients')

    if profile.doc_count > 0:
        messages.error(request, 'Macmiilkan lama tirtiri karo — dokumeentiyada xidhan ayuu leeyahay.')
        return redirect('admin_clients')

    full_name = profile.user.get_full_name()
    profile.user.delete()  # cascades to the OneToOne ClientProfile
    messages.success(request, f'Macmiilka "{full_name}" waa la tirtiray.')
    return redirect('admin_clients')


@role_required(AccountsUser.Role.ADMIN)
def notaries_view(request):
    if request.method == 'POST':
        form = NotaryCreateForm(request.POST, request.FILES)
        if form.is_valid():
            full_name = form.cleaned_data['full_name'].strip()
            first, last = _split_name(full_name)
            with transaction.atomic():
                username = generate_username(User, full_name)
                user = User.objects.create_user(
                    username=username,
                    password=TEMP_PASSWORD,
                    first_name=first,
                    last_name=last,
                    role=AccountsUser.Role.NOTARY,
                )
                NotaryProfile.objects.create(
                    user=user,
                    phone=form.cleaned_data.get('phone', ''),
                    license_number=form.cleaned_data.get('license_number', ''),
                    region=form.cleaned_data.get('region', ''),
                    signature=form.cleaned_data.get('signature_data'),
                    seal_image=form.cleaned_data.get('seal_image'),
                )
            messages.success(
                request,
                f'Notaayada "{full_name}" waa lagu daray. '
                f'Username: {username} · Furaha hore: {TEMP_PASSWORD}',
            )
            return redirect('admin_notaries')
        tab = 'add'
    else:
        form = NotaryCreateForm()
        tab = request.GET.get('tab', 'list')

    notaries = (
        NotaryProfile.objects.filter(user__role=AccountsUser.Role.NOTARY)
        .select_related('user')
        .annotate(doc_count=Count('documents'))
        .order_by('-created_at')
    )
    return render(
        request,
        'portal/admin/notaries.html',
        {'form': form, 'notaries': notaries, 'tab': tab, 'active_nav': 'notaries'},
    )


@role_required(AccountsUser.Role.ADMIN)
def notary_edit(request, pk):
    profile = get_object_or_404(NotaryProfile.objects.select_related('user'), pk=pk)
    if request.method == 'POST':
        form = NotaryEditForm(request.POST, request.FILES, instance_pk=profile.pk)
        if form.is_valid():
            full_name = form.cleaned_data['full_name'].strip()
            first, last = _split_name(full_name)
            with transaction.atomic():
                profile.user.first_name = first
                profile.user.last_name = last
                profile.user.email = form.cleaned_data.get('email') or ''
                profile.user.save(update_fields=['first_name', 'last_name', 'email'])

                profile.phone = form.cleaned_data['phone']
                profile.license_number = form.cleaned_data['license_number']
                profile.region = form.cleaned_data['region']
                profile.bio = form.cleaned_data.get('bio') or ''
                if form.cleaned_data.get('seal_image'):
                    profile.seal_image = form.cleaned_data['seal_image']
                profile.save()
            messages.success(request, f'Notaayada "{full_name}" waa la cusbooneysiiyay.')
            return redirect('admin_notaries')
    else:
        form = NotaryEditForm(instance_pk=profile.pk, initial={
            'full_name': profile.user.get_full_name(),
            'phone': profile.phone,
            'license_number': profile.license_number,
            'region': profile.region,
            'email': profile.user.email,
            'bio': profile.bio,
        })

    return render(
        request,
        'portal/admin/notary_edit.html',
        {'form': form, 'profile': profile, 'active_nav': 'notaries'},
    )


@role_required(AccountsUser.Role.ADMIN)
def notary_delete(request, pk):
    profile = get_object_or_404(NotaryProfile.objects.select_related('user'), pk=pk)
    if request.method != 'POST':
        return redirect('admin_notaries')

    if profile.documents.exists() or profile.templates.exists():
        messages.error(
            request,
            'Notaayadan lama tirtiri karo — dokumeentiyo ama qaabab ayuu leeyahay.',
        )
        return redirect('admin_notaries')

    full_name = profile.user.get_full_name()
    profile.user.delete()  # cascades to the OneToOne NotaryProfile
    messages.success(request, f'Notaayada "{full_name}" waa la tirtiray.')
    return redirect('admin_notaries')


@role_required(AccountsUser.Role.ADMIN)
def reports(request):
    notaries = (
        NotaryProfile.objects.filter(user__role=AccountsUser.Role.NOTARY)
        .select_related('user')
        .annotate(doc_count=Count('documents'))
        .order_by('-doc_count')
    )
    max_count = max((n.doc_count for n in notaries), default=0) or 1
    notary_bars = [
        {
            'name': n.user.get_full_name() or n.user.username,
            'count': n.doc_count,
            'pct': round(n.doc_count / max_count * 100),
        }
        for n in notaries
    ]
    recent = Document.objects.select_related('client__user', 'template').order_by('-created_at')[:8]

    context = {
        'total_docs': Document.objects.count(),
        'total_clients': ClientProfile.objects.count(),
        'total_notaries': notaries.count(),
        'notary_bars': notary_bars,
        'recent': recent,
        'active_nav': 'reports',
    }
    return render(request, 'portal/admin/reports.html', context)
