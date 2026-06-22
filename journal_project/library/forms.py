from django import forms
from django.utils import timezone

from .models import BookDetail, KnowledgeItem, Tag


class BookForm(forms.Form):
    title = forms.CharField(max_length=255)
    author = forms.CharField(max_length=255)
    status = forms.ChoiceField(choices=KnowledgeItem.Status.choices)
    genre = forms.CharField(max_length=120, required=False)
    date_published = forms.DateField(
        label='Publication date',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    summary = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 5}))
    subtitle = forms.CharField(max_length=255, required=False)
    source_url = forms.URLField(required=False)
    isbn = forms.CharField(label='ISBN', max_length=32, required=False)
    publisher = forms.CharField(max_length=255, required=False)
    page_count = forms.IntegerField(required=False, min_value=1)
    original_language = forms.CharField(max_length=80, required=False)
    edition = forms.CharField(max_length=120, required=False)
    metadata = forms.JSONField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}),
        help_text='Optional JSON object for extra book metadata.',
    )

    def __init__(self, *args, knowledge_item=None, **kwargs):
        if knowledge_item is not None and not args:
            kwargs['initial'] = {
                **kwargs.get('initial', {}),
                **self._initial_from_book(knowledge_item),
            }
        super().__init__(*args, **kwargs)

    def _initial_from_book(self, knowledge_item):
        detail = getattr(knowledge_item, 'book_detail', None)
        initial = {
            'title': knowledge_item.title,
            'subtitle': knowledge_item.subtitle,
            'status': knowledge_item.status,
            'summary': knowledge_item.summary,
            'source_url': knowledge_item.source_url,
            'date_published': knowledge_item.date_published,
        }

        if isinstance(detail, BookDetail):
            initial.update(
                {
                    'author': detail.author,
                    'genre': detail.genre,
                    'isbn': detail.isbn,
                    'publisher': detail.publisher,
                    'page_count': detail.page_count,
                    'original_language': detail.original_language,
                    'edition': detail.edition,
                    'metadata': detail.metadata,
                    'date_published': detail.publication_date,
                }
            )

        return initial

    def clean_date_published(self):
        date_published = self.cleaned_data['date_published']
        if date_published and date_published > timezone.localdate():
            raise forms.ValidationError('Publication date cannot be in the future.')
        return date_published

    def clean_metadata(self):
        metadata = self.cleaned_data['metadata']
        return metadata or {}


class TagForm(forms.Form):
    name = forms.CharField(max_length=80)


class BookTagForm(forms.Form):
    tag = forms.ModelChoiceField(queryset=Tag.objects.none(), required=False)
    new_tag = forms.CharField(label='New tag', max_length=80, required=False)

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tag'].queryset = Tag.objects.filter(user=user)

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('tag') and not cleaned_data.get('new_tag', '').strip():
            raise forms.ValidationError('Choose a tag or enter a new one.')
        return cleaned_data
