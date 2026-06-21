from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import User as AccountsUser

User = get_user_model()


def make_user(username, role, must_change_password=True, password='123'):
    user = User.objects.create_user(username=username, password=password, role=role)
    user.must_change_password = must_change_password
    user.save(update_fields=['must_change_password'])
    return user


class LoginViewTests(TestCase):
    def test_login_success_redirects_to_password_change_for_temp_password(self):
        make_user('newnotary', AccountsUser.Role.NOTARY, must_change_password=True)
        response = self.client.post(reverse('login'), {'username': 'newnotary', 'password': '123'})
        self.assertRedirects(response, reverse('password_change'))

    def test_login_success_redirects_to_role_home_when_password_already_changed(self):
        make_user('settlednotary', AccountsUser.Role.NOTARY, must_change_password=False, password='RealPass123')
        response = self.client.post(
            reverse('login'), {'username': 'settlednotary', 'password': 'RealPass123'}
        )
        # fetch_redirect_response=False: the notary view itself needs a NotaryProfile,
        # which is irrelevant to what this test is checking (the redirect target).
        self.assertRedirects(response, '/notary/', fetch_redirect_response=False)

    def test_login_failure_shows_somali_error_and_does_not_authenticate(self):
        make_user('baduser', AccountsUser.Role.CLIENT)
        response = self.client.post(reverse('login'), {'username': 'baduser', 'password': 'wrong'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'khalad')
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_already_authenticated_user_redirected_away_from_login(self):
        user = make_user('alreadyin', AccountsUser.Role.ADMIN, must_change_password=False, password='AdminPass1')
        self.client.force_login(user)
        response = self.client.get(reverse('login'))
        self.assertRedirects(response, '/admin-panel/clients/')

    def test_remember_me_unchecked_expires_session_on_browser_close(self):
        make_user('forgetful', AccountsUser.Role.CLIENT, must_change_password=False, password='ClientPass1')
        self.client.post(reverse('login'), {'username': 'forgetful', 'password': 'ClientPass1'})
        # set_expiry(0) is Django's "expire at browser close" marker — get_expiry_age()
        # falls back to the default cookie age for it, so check the dedicated flag instead.
        self.assertTrue(self.client.session.get_expire_at_browser_close())


class PasswordChangeViewTests(TestCase):
    def test_requires_login(self):
        response = self.client.get(reverse('password_change'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('password_change')}")

    def test_first_login_flag_in_context(self):
        user = make_user('firsttimer', AccountsUser.Role.CLIENT, must_change_password=True)
        self.client.force_login(user)
        response = self.client.get(reverse('password_change'))
        self.assertTrue(response.context['is_first_login'])

    def test_successful_change_clears_flag_and_keeps_session_alive(self):
        user = make_user('changer', AccountsUser.Role.NOTARY, must_change_password=True)
        self.client.force_login(user)
        response = self.client.post(
            reverse('password_change'),
            {'new_password1': 'BrandNewPass1', 'new_password2': 'BrandNewPass1'},
        )
        self.assertRedirects(response, '/notary/', fetch_redirect_response=False)

        user.refresh_from_db()
        self.assertFalse(user.must_change_password)

        # session must still be authenticated after the password hash changed —
        # regression check for the update_session_auth_hash fix. Hitting any
        # login-required page (not /notary/, which needs a NotaryProfile) is enough.
        response = self.client.get(reverse('password_change'))
        self.assertEqual(response.status_code, 200)


class ForcePasswordChangeMiddlewareTests(TestCase):
    def test_pinned_to_password_change_page_until_changed(self):
        user = make_user('pinned', AccountsUser.Role.NOTARY, must_change_password=True)
        self.client.force_login(user)
        response = self.client.get('/notary/')
        self.assertRedirects(response, reverse('password_change'))

    def test_exempt_paths_not_redirected(self):
        user = make_user('exempt', AccountsUser.Role.NOTARY, must_change_password=True)
        self.client.force_login(user)
        response = self.client.get(reverse('password_change'))
        self.assertEqual(response.status_code, 200)


class RoleRequiredDecoratorTests(TestCase):
    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get('/notary/')
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_wrong_role_gets_forbidden(self):
        user = make_user('clientuser', AccountsUser.Role.CLIENT, must_change_password=False, password='ClientPass1')
        self.client.force_login(user)
        response = self.client.get('/notary/')
        self.assertEqual(response.status_code, 403)

    def test_logout_redirects_to_login(self):
        user = make_user('loggingout', AccountsUser.Role.ADMIN, must_change_password=False, password='AdminPass1')
        self.client.force_login(user)
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('login'))
