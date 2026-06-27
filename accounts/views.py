from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.cache import never_cache

from .forms import ForgotPasswordForm, SomaliAuthenticationForm

User = get_user_model()


@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect(request.user.role_home_url())

    form = SomaliAuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        auth_login(request, user)
        if not form.cleaned_data.get('remember_me'):
            request.session.set_expiry(0)
        if user.must_change_password:
            return redirect('password_change')
        return redirect(user.role_home_url())

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    auth_logout(request)
    return redirect('login')


@login_required
@never_cache
def password_change_view(request):
    is_first_login = request.user.must_change_password
    form = SetPasswordForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        user.must_change_password = False
        user.save(update_fields=['must_change_password'])
        update_session_auth_hash(request, user)
        return redirect(user.role_home_url())

    return render(
        request,
        'accounts/password_change.html',
        {'form': form, 'is_first_login': is_first_login},
    )


@never_cache
def forgot_password_view(request):
    form = ForgotPasswordForm(request.POST or None)
    sent = False
    no_email = False
    if request.method == 'POST' and form.is_valid():
        user = User.objects.filter(username__iexact=form.cleaned_data['username']).first()
        if user is not None and not user.email:
            # Username exists but has no email on file — can't send a link, so say so.
            no_email = True
        elif user is not None:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = request.build_absolute_uri(
                reverse('reset_password', kwargs={'uidb64': uid, 'token': token})
            )
            send_mail(
                subject='Password Reset — Sahal Notary System',
                message=(
                    f'Hello {user.get_full_name() or user.username},\n\n'
                    'A password reset was requested for your Sahal Notary System account.\n\n'
                    f'Click the link below to set a new password:\n{reset_link}\n\n'
                    'This link expires in 24 hours and can only be used once.\n\n'
                    'If you did not request this, you can ignore this email — '
                    'your password will not change.\n\n'
                    '— Sahal Notary System'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

        if not no_email:
            # Always show the same outcome whether or not the username is registered,
            # so the form can't be used to enumerate usernames.
            sent = True
            form = ForgotPasswordForm()

    return render(request, 'accounts/forgot_password.html', {'form': form, 'sent': sent, 'no_email': no_email})


def reset_password_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None

    link_valid = user is not None and default_token_generator.check_token(user, token)
    if not link_valid:
        return render(request, 'accounts/reset_password.html', {'link_valid': False})

    form = SetPasswordForm(user, request.POST or None)
    form.fields['new_password1'].widget.attrs.update({'placeholder': '••••••••', 'style': 'padding-right:42px;'})
    form.fields['new_password2'].widget.attrs.update({'placeholder': '••••••••', 'style': 'padding-right:42px;'})
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('login')

    return render(request, 'accounts/reset_password.html', {'form': form, 'link_valid': True})
