from django.db.models import F
from django.shortcuts import redirect
from formtools.wizard.views import SessionWizardView

from .forms import (
    ClientSelectForm,
    ConfirmForm,
    Party2SelectForm,
    TemplateSelectForm,
    WitnessFormSet,
)
from .models import ClientProfile, Document, DocumentTemplate, Witness


def show_party2(wizard):
    cleaned = wizard.get_cleaned_data_for_step('template') or {}
    template = cleaned.get('template')
    return bool(template and template.party_type == DocumentTemplate.PartyType.TWO)


def show_witnesses(wizard):
    cleaned = wizard.get_cleaned_data_for_step('template') or {}
    template = cleaned.get('template')
    return bool(template and template.requires_witnesses)


class CreateDocumentWizard(SessionWizardView):
    template_name = 'portal/notary/create_wizard.html'

    form_list = [
        ('client', ClientSelectForm),
        ('template', TemplateSelectForm),
        ('party2', Party2SelectForm),
        ('witnesses', WitnessFormSet),
        ('confirm', ConfirmForm),
    ]
    condition_dict = {
        'party2': show_party2,
        'witnesses': show_witnesses,
    }

    # The design's step indicator only has 4 bubbles (Macmiilka / Qaabka / Dib-u-eeg / Xaqiiji);
    # party2 and witnesses are extra data-entry sub-steps of "Qaabka" so they share its bubble.
    STEP_BUBBLE = {
        'client': 1,
        'template': 2,
        'party2': 2,
        'witnesses': 2,
        'confirm': 3,
    }

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        if step == 'party2':
            client_data = self.get_cleaned_data_for_step('client') or {}
            chosen = client_data.get('client')
            qs = ClientProfile.objects.select_related('user')
            if chosen:
                qs = qs.exclude(pk=chosen.pk)
            kwargs['queryset'] = qs
        return kwargs

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context['active_nav'] = 'create'
        context['step_bubble'] = self.STEP_BUBBLE.get(self.steps.current, 1)
        context['step_labels'] = [(1, 'Macmiilka'), (2, 'Qaabka'), (3, 'Dib-u-eeg'), (4, 'Xaqiiji')]
        if self.steps.current == 'template':
            client_data = self.get_cleaned_data_for_step('client') or {}
            context['selected_client'] = client_data.get('client')
        if self.steps.current == 'confirm':
            context.update(self._build_preview_context())
        return context

    def _safe_cleaned_data_for_step(self, step, default):
        # get_cleaned_data_for_step() KeyErrors on steps that condition_dict skipped —
        # it checks membership against the raw form_list but reads the condition-filtered one.
        if step not in self.get_form_list():
            return default
        return self.get_cleaned_data_for_step(step) or default

    def _build_preview_context(self):
        client_data = self.get_cleaned_data_for_step('client') or {}
        template_data = self.get_cleaned_data_for_step('template') or {}
        party2_data = self._safe_cleaned_data_for_step('party2', {})
        witnesses_data = self._safe_cleaned_data_for_step('witnesses', [])

        client = client_data.get('client')
        template = template_data.get('template')
        client2 = party2_data.get('client2')
        witnesses = [w for w in witnesses_data if w and w.get('name')]

        preview_body = ''
        if template and client:
            preview = Document(template=template, notary=self.request.user.notary_profile, client=client, client2=client2, city='Muqdisho')
            preview_body = preview.render_body()

        return {
            'preview_client': client,
            'preview_client2': client2,
            'preview_template': template,
            'preview_witnesses': witnesses,
            'preview_body': preview_body,
            'is_two_party': bool(template and template.party_type == DocumentTemplate.PartyType.TWO),
            'show_witnesses_preview': bool(template and template.requires_witnesses),
        }

    def done(self, form_list, form_dict, **kwargs):
        client = form_dict['client'].cleaned_data['client']
        template = form_dict['template'].cleaned_data['template']
        client2 = form_dict['party2'].cleaned_data['client2'] if 'party2' in form_dict else None
        witnesses_data = []
        if 'witnesses' in form_dict:
            witnesses_data = [w for w in form_dict['witnesses'].cleaned_data if w and w.get('name')]

        document = Document(
            template=template,
            notary=self.request.user.notary_profile,
            client=client,
            client2=client2,
            city='Muqdisho',
        )
        document.finalize()
        document.save()

        for i, w in enumerate(witnesses_data, start=1):
            Witness.objects.create(document=document, name=w['name'], phone=w.get('phone', ''), order=i)

        DocumentTemplate.objects.filter(pk=template.pk).update(times_used=F('times_used') + 1)

        return redirect('notary_create_success', ref=document.ref)
