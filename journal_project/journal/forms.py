from django import forms

from journal_project.library.models import KnowledgeItem

from .models import Insight


class InsightForm(forms.Form):
    knowledge_item = forms.ModelChoiceField(
        label='Source',
        queryset=KnowledgeItem.objects.none(),
        required=True,
    )
    insight_type = forms.ChoiceField(choices=Insight.InsightType.choices)
    title = forms.CharField(max_length=255, required=False)
    content = forms.CharField(widget=forms.Textarea(attrs={'rows': 8}))
    location = forms.CharField(max_length=120, required=False)
    page_number = forms.IntegerField(required=False, min_value=1)
    date_captured = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    pinned = forms.BooleanField(
        label='Pin this insight',
        help_text='Mark it as important for quick reference.',
        required=False,
    )

    def __init__(self, *args, user, source=None, insight=None, **kwargs):
        initial = kwargs.pop('initial', {})

        if insight is not None and not args:
            initial = {
                **initial,
                'knowledge_item': insight.knowledge_item,
                'insight_type': insight.insight_type,
                'title': insight.title,
                'content': insight.content,
                'location': insight.location,
                'page_number': insight.page_number,
                'date_captured': insight.date_captured,
                'pinned': insight.pinned,
            }

        if source is not None:
            initial = {**initial, 'knowledge_item': source}

        super().__init__(*args, initial=initial, **kwargs)

        self.fields['knowledge_item'].queryset = KnowledgeItem.objects.filter(user=user)
        if source is not None:
            self.fields.pop('knowledge_item')
