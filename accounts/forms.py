from django import forms
from django.contrib.auth.forms import AuthenticationForm


class SomaliAuthenticationForm(AuthenticationForm):
    remember_me = forms.BooleanField(required=False, label='I xasuuso')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Magaca isticmaalaha'
        self.fields['username'].widget.attrs['placeholder'] = 'tusaale: amina.yusuf'
        self.fields['password'].label = 'Furaha sirta ah'
        self.fields['password'].widget.attrs['placeholder'] = '••••••••'

    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'Magaca isticmaalaha ama furaha sirta ah waa khalad.',
        'inactive': 'Akoonkan waa la joojiyay.',
    }
