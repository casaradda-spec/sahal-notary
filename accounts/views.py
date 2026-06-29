from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache

from .forms import SomaliAuthenticationForm


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
