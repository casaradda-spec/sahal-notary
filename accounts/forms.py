from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _


class SomaliAuthenticationForm(AuthenticationForm):
    remember_me = forms.BooleanField(required=False, label=_('Remember me'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = _('Username')
        self.fields['username'].widget.attrs['placeholder'] = 'e.g. amina.yusuf'
        self.fields['password'].label = _('Password')
        self.fields['password'].widget.attrs['placeholder'] = '••••••••'

    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'Magaca isticmaalaha ama furaha sirta ah waa khalad.',
        'inactive': 'Akoonkan waa la joojiyay.',
    }
