from django.shortcuts import redirect

EXEMPT_PATHS = {'/password-change/', '/logout/'}
EXEMPT_PREFIXES = ('/static/', '/media/')


class ForcePasswordChangeMiddleware:
    """Pins any authenticated user with a temp password to the password-change page."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if (
            user is not None
            and user.is_authenticated
            and user.must_change_password
            and request.path not in EXEMPT_PATHS
            and not request.path.startswith(EXEMPT_PREFIXES)
        ):
            return redirect('password_change')
        return self.get_response(request)
