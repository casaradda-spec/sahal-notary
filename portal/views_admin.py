import json
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.functions import TruncDay, TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

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
def admin_reset_password(request, user_id):
    target_user = get_object_or_404(User, pk=user_id)
    redirect_to = 'admin_clients' if target_user.role == AccountsUser.Role.CLIENT else 'admin_notaries'

    if request.method != 'POST':
        return redirect(redirect_to)

    full_name = target_user.get_full_name() or target_user.username
    if target_user.pk == request.user.pk:
        messages.error(request, 'Lama beddeli karo furahaaga sirta ah halkan — isticmaal "Beddel Furaha Sirta".')
        return redirect(redirect_to)

    target_user.set_password(TEMP_PASSWORD)
    target_user.must_change_password = True
    target_user.save(update_fields=['password', 'must_change_password'])
    messages.success(request, f'Furaha sirta ah ee "{full_name}" waa la beddelay. Furaha cusub: {TEMP_PASSWORD}')
    return redirect(redirect_to)


def _next_month_start(d):
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


def _resolve_report_filter(request):
    """Resolve (filter_type, date_from, date_to) from GET params; defaults to the current month."""
    filter_type = request.GET.get('filter_type', 'month')
    today = timezone.localdate()

    if filter_type == 'day':
        try:
            d = date.fromisoformat(request.GET.get('day', ''))
        except ValueError:
            d = today
        return 'day', d, d

    if filter_type == 'custom':
        try:
            date_from = date.fromisoformat(request.GET.get('start', ''))
            date_to = date.fromisoformat(request.GET.get('end', ''))
            if date_from > date_to:
                date_from, date_to = date_to, date_from
        except ValueError:
            date_from, date_to = today.replace(day=1), today
        return 'custom', date_from, date_to

    try:
        year, month = (int(part) for part in request.GET.get('month', '').split('-'))
        date_from = date(year, month, 1)
    except (ValueError, TypeError):
        date_from = today.replace(day=1)
    date_to = _next_month_start(date_from) - timedelta(days=1)
    return 'month', date_from, date_to


def _bucket_keys(date_from, date_to):
    """Sub-period boundaries for the trend charts: daily for ranges up to ~2 months, monthly beyond."""
    daily = (date_to - date_from).days <= 62
    keys = []
    if daily:
        d = date_from
        while d <= date_to:
            keys.append(d)
            d += timedelta(days=1)
    else:
        m = date(date_from.year, date_from.month, 1)
        end_m = date(date_to.year, date_to.month, 1)
        while m <= end_m:
            keys.append(m)
            m = _next_month_start(m)
    return daily, keys


def _bucket_label(k, daily):
    return k.strftime('%d %b') if daily else k.strftime('%b %Y')


def _bucketed_counts(queryset, date_field, daily, keys):
    trunc = TruncDay if daily else TruncMonth
    rows = (
        queryset.annotate(bucket=trunc(date_field, tzinfo=timezone.get_current_timezone()))
        .values('bucket')
        .annotate(count=Count('id'))
    )
    by_key = {row['bucket'].date(): row['count'] for row in rows}
    return [by_key.get(k, 0) for k in keys]


def _period_growth(queryset, date_field, date_from, date_to):
    """Growth % of the filtered range vs. the immediately preceding period of equal length."""
    span = (date_to - date_from).days + 1
    current = queryset.filter(**{f'{date_field}__date__gte': date_from, f'{date_field}__date__lte': date_to}).count()
    prev_to = date_from - timedelta(days=1)
    prev_from = prev_to - timedelta(days=span - 1)
    previous = queryset.filter(**{f'{date_field}__date__gte': prev_from, f'{date_field}__date__lte': prev_to}).count()
    if previous == 0:
        return 0
    return round((current - previous) / previous * 100)


def _growth_color(value):
    return '#1f9d55' if value >= 0 else '#dc4545'


def _notary_bucketed_trend(notaries, date_from, date_to, daily, keys):
    """Per-notary document counts for each bucket, for notaries with >=1 document in the range."""
    active = [n for n in notaries if n.doc_count > 0]
    if not active:
        return []

    trunc = TruncDay if daily else TruncMonth
    rows = (
        Document.objects.filter(notary__in=active, created_at__date__gte=date_from, created_at__date__lte=date_to)
        .annotate(bucket=trunc('created_at', tzinfo=timezone.get_current_timezone()))
        .values('notary_id', 'bucket')
        .annotate(count=Count('id'))
    )
    by_notary = {}
    for row in rows:
        by_notary.setdefault(row['notary_id'], {})[row['bucket'].date()] = row['count']

    return [
        {
            'name': n.user.get_full_name() or n.user.username,
            'data': [by_notary.get(n.id, {}).get(k, 0) for k in keys],
        }
        for n in active
    ]


@role_required(AccountsUser.Role.ADMIN)
def reports(request):
    filter_type, date_from, date_to = _resolve_report_filter(request)

    docs = Document.objects.filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
    period_clients = ClientProfile.objects.filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
    period_notaries = NotaryProfile.objects.filter(
        user__role=AccountsUser.Role.NOTARY, created_at__date__gte=date_from, created_at__date__lte=date_to
    )

    notaries = (
        NotaryProfile.objects.filter(user__role=AccountsUser.Role.NOTARY)
        .select_related('user')
        .annotate(
            doc_count=Count(
                'documents',
                filter=Q(documents__created_at__date__gte=date_from, documents__created_at__date__lte=date_to),
            )
        )
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
    recent = docs.select_related('client__user', 'template').order_by('-created_at')[:8]

    daily, bucket_keys = _bucket_keys(date_from, date_to)
    labels = [_bucket_label(k, daily) for k in bucket_keys]

    trend_data = {
        'labels': labels,
        'documents': _bucketed_counts(docs, 'created_at', daily, bucket_keys),
        'clients': _bucketed_counts(period_clients, 'created_at', daily, bucket_keys),
        'notaries': _bucketed_counts(period_notaries, 'created_at', daily, bucket_keys),
    }
    notary_trend_data = {
        'labels': labels,
        'notaries': _notary_bucketed_trend(notaries, date_from, date_to, daily, bucket_keys),
    }

    range_label = (
        date_from.strftime('%d %b %Y')
        if date_from == date_to
        else f'{date_from.strftime("%d %b %Y")} – {date_to.strftime("%d %b %Y")}'
    )

    doc_growth = _period_growth(Document.objects.all(), 'created_at', date_from, date_to)
    client_growth = _period_growth(ClientProfile.objects.all(), 'created_at', date_from, date_to)
    notary_growth = _period_growth(
        NotaryProfile.objects.filter(user__role=AccountsUser.Role.NOTARY), 'created_at', date_from, date_to
    )

    context = {
        'total_docs': docs.count(),
        'total_clients': period_clients.count(),
        'total_notaries': period_notaries.count(),
        'notary_bars': notary_bars,
        'recent': recent,
        'active_nav': 'reports',
        'trend_data': json.dumps(trend_data),
        'trend_range_label': range_label,
        'doc_growth': doc_growth,
        'client_growth': client_growth,
        'notary_growth': notary_growth,
        'doc_growth_color': _growth_color(doc_growth),
        'client_growth_color': _growth_color(client_growth),
        'notary_growth_color': _growth_color(notary_growth),
        'notary_trend_data': json.dumps(notary_trend_data),
        'filter_type': filter_type,
        'filter_month_value': date_from.strftime('%Y-%m'),
        'filter_day_value': (date_from if filter_type == 'day' else timezone.localdate()).isoformat(),
        'filter_start_value': date_from.isoformat(),
        'filter_end_value': date_to.isoformat(),
    }
    return render(request, 'portal/admin/reports.html', context)
