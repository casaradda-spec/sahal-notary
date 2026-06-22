from django import forms

from .models import ClientProfile, DocumentTemplate, NotaryProfile


class ClientCreateForm(forms.Form):
    full_name = forms.CharField(label='Magaca oo dhan', max_length=150)
    phone = forms.CharField(label='Telefoonka', max_length=30, required=False)
    email = forms.EmailField(label='Iimaylka', required=False)
    national_id = forms.CharField(label='Aqoonsiga Qaranka (National ID)', max_length=40, required=False)
    address = forms.CharField(label='Cinwaanka', max_length=200, required=False)
    city = forms.CharField(label='Magaalada', max_length=80, required=False)


class NotaryCreateForm(forms.Form):
    full_name = forms.CharField(label='Magaca oo dhan', max_length=150)
    license_number = forms.CharField(label='Lambarka Ruqsadda', max_length=40, required=False)
    region = forms.CharField(label='Gobolka', max_length=80, required=False)
    seal_image = forms.ImageField(label='Sawirka Shaambooyinka', required=False)


class DocumentTemplateForm(forms.ModelForm):
    class Meta:
        model = DocumentTemplate
        fields = ['title', 'category', 'party_type', 'requires_witnesses', 'body']
        labels = {
            'title': 'Cinwaanka Qaabka',
            'category': 'Nooca',
            'party_type': 'Dhinacyada',
            'requires_witnesses': 'U baahan yahay marqaatiyaal',
            'body': 'Qoraalka',
        }
        widgets = {
            'body': forms.Textarea(attrs={'rows': 12}),
        }


class NotaryProfileForm(forms.ModelForm):
    class Meta:
        model = NotaryProfile
        fields = ['phone', 'bio', 'seal_image']
        labels = {
            'phone': 'Telefoonka',
            'bio': 'Taariikhda Shaqsiyeed',
            'seal_image': 'Sawirka Shaambooyinka',
        }
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }


class ClientModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f'{obj.user.get_full_name()} — {obj.city or "—"} · {obj.doc_count} dokumeenti'


class TemplateModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f'{obj.title} — {obj.category} · {obj.party_label}'


class ClientSelectForm(forms.Form):
    client = ClientModelChoiceField(
        queryset=ClientProfile.objects.select_related('user'),
        widget=forms.RadioSelect,
        label='',
        empty_label=None,
    )


class TemplateSelectForm(forms.Form):
    template = TemplateModelChoiceField(
        queryset=DocumentTemplate.objects.all(),
        widget=forms.RadioSelect,
        label='',
        empty_label=None,
    )


class Party2SelectForm(forms.Form):
    client2 = ClientModelChoiceField(
        queryset=ClientProfile.objects.none(),
        widget=forms.RadioSelect,
        label='',
        empty_label=None,
    )

    def __init__(self, *args, queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if queryset is not None:
            self.fields['client2'].queryset = queryset


class WitnessForm(forms.Form):
    name = forms.CharField(label='Magaca marqaatiga', max_length=150, required=False)
    phone = forms.CharField(label='Telefoonka', max_length=30, required=False)


WitnessFormSet = forms.formset_factory(WitnessForm, extra=2, max_num=5)


class ConfirmForm(forms.Form):
    """Empty — the confirm step is a read-only review; submitting it creates the document."""
