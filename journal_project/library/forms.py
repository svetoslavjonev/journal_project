from django import forms
from django.core.validators import FileExtensionValidator
from django.utils import timezone

from .models import (
    ArticleDetail,
    BookDetail,
    KnowledgeItem,
    PaperDetail,
    PodcastEpisodeDetail,
    Tag,
)


class BookForm(forms.Form):
    title = forms.CharField(max_length=500)
    author = forms.CharField(max_length=255)
    status = forms.ChoiceField(
        choices=KnowledgeItem.status_choices_for_source(
            KnowledgeItem.SourceType.BOOK
        )
    )
    genre = forms.CharField(max_length=120, required=False)
    date_published = forms.DateField(
        label='Publication date',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    summary = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 5}))
    subtitle = forms.CharField(max_length=255, required=False)
    source_url = forms.URLField(max_length=2048, required=False)
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


class PaperForm(forms.Form):
    title = forms.CharField(max_length=500)
    authors = forms.CharField(max_length=1000)
    publication_year = forms.IntegerField(required=False, min_value=1)
    status = forms.ChoiceField(
        choices=KnowledgeItem.status_choices_for_source(
            KnowledgeItem.SourceType.PAPER
        )
    )
    key_research_question = forms.CharField(
        label='Research question',
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}),
    )
    key_findings_practical_applications = forms.CharField(
        label='Key findings & practical applications',
        required=False,
        widget=forms.Textarea(attrs={'rows': 6}),
    )
    methodology_research_design = forms.CharField(
        label='Methodology & research design',
        required=False,
        widget=forms.Textarea(attrs={'rows': 5}),
    )
    sample_size_data_source = forms.CharField(
        label='Sample size, data & source',
        required=False,
        widget=forms.Textarea(attrs={'rows': 5}),
    )
    asset_class = forms.CharField(max_length=255, required=False)
    summary = forms.CharField(
        label='My summary',
        required=False,
        widget=forms.Textarea(attrs={'rows': 6}),
    )
    journal = forms.CharField(max_length=500, required=False)
    doi = forms.CharField(label='DOI', max_length=255, required=False)
    source_url = forms.URLField(label='URL', max_length=2048, required=False)

    def __init__(self, *args, paper=None, **kwargs):
        if paper is not None and not args:
            kwargs['initial'] = {
                **kwargs.get('initial', {}),
                **self._initial_from_paper(paper),
            }
        super().__init__(*args, **kwargs)

    @staticmethod
    def _initial_from_paper(paper: KnowledgeItem) -> dict[str, object]:
        """Return form initial data from a paper and its detail record."""
        detail = getattr(paper, 'paper_detail', None)
        initial: dict[str, object] = {
            'title': paper.title,
            'authors': paper.creator,
            'status': paper.status,
            'summary': paper.summary,
            'source_url': paper.source_url,
        }

        if isinstance(detail, PaperDetail):
            initial.update(
                {
                    'publication_year': detail.publication_year,
                    'journal': detail.journal,
                    'doi': detail.doi,
                    'asset_class': detail.asset_class,
                    'sample_size_data_source': detail.sample_size_data_source,
                    'methodology_research_design': (
                        detail.methodology_research_design
                    ),
                    'key_research_question': detail.key_research_question,
                    'key_findings_practical_applications': (
                        detail.key_findings_practical_applications
                    ),
                }
            )

        return initial


class PaperImportForm(forms.Form):
    json_file = forms.FileField(
        label='JSON file',
        validators=[FileExtensionValidator(allowed_extensions=['json'])],
        widget=forms.ClearableFileInput(
            attrs={'accept': '.json,application/json'}
        ),
    )


class ArticleForm(forms.Form):
    title = forms.CharField(max_length=500)
    authors = forms.CharField(max_length=1000)
    publication_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    source_url = forms.URLField(label='URL', max_length=2048, required=False)
    status = forms.ChoiceField(
        choices=KnowledgeItem.status_choices_for_source(
            KnowledgeItem.SourceType.ARTICLE
        )
    )
    summary = forms.CharField(
        label='My summary',
        required=False,
        widget=forms.Textarea(attrs={'rows': 6}),
    )
    publication_name = forms.CharField(
        label='Publication / site',
        max_length=500,
        required=False,
    )

    def __init__(self, *args, article=None, **kwargs):
        if article is not None and not args:
            kwargs['initial'] = {
                **kwargs.get('initial', {}),
                **self._initial_from_article(article),
            }
        super().__init__(*args, **kwargs)

    @staticmethod
    def _initial_from_article(article: KnowledgeItem) -> dict[str, object]:
        """Return form initial data from an article and its detail record."""
        detail = getattr(article, 'article_detail', None)
        initial: dict[str, object] = {
            'title': article.title,
            'authors': article.creator,
            'publication_date': article.date_published,
            'source_url': article.source_url,
            'status': article.status,
            'summary': article.summary,
        }
        if isinstance(detail, ArticleDetail):
            initial['publication_name'] = detail.publication_name
        return initial

    def clean_publication_date(self):
        """Reject publication dates later than today."""
        publication_date = self.cleaned_data['publication_date']
        if publication_date and publication_date > timezone.localdate():
            raise forms.ValidationError(
                'Publication date cannot be in the future.'
            )
        return publication_date


class PodcastEpisodeForm(forms.Form):
    episode_title = forms.CharField(label='Episode title', max_length=500)
    show_name = forms.CharField(label='Show name', max_length=500)
    hosts = forms.CharField(max_length=1000)
    guests = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )
    status = forms.ChoiceField(
        choices=KnowledgeItem.status_choices_for_source(
            KnowledgeItem.SourceType.PODCAST
        )
    )
    summary = forms.CharField(
        label='My summary',
        required=False,
        widget=forms.Textarea(attrs={'rows': 6}),
    )
    source_url = forms.URLField(label='URL', max_length=2048, required=False)

    def __init__(self, *args, podcast=None, **kwargs):
        if podcast is not None and not args:
            kwargs['initial'] = {
                **kwargs.get('initial', {}),
                **self._initial_from_podcast(podcast),
            }
        super().__init__(*args, **kwargs)

    @staticmethod
    def _initial_from_podcast(podcast: KnowledgeItem) -> dict[str, object]:
        """Return form initial data from an episode and its detail record."""
        detail = getattr(podcast, 'podcast_episode_detail', None)
        initial: dict[str, object] = {
            'episode_title': podcast.title,
            'hosts': podcast.creator,
            'status': podcast.status,
            'summary': podcast.summary,
            'source_url': podcast.source_url,
        }
        if isinstance(detail, PodcastEpisodeDetail):
            initial.update(
                {
                    'show_name': detail.show_name,
                    'guests': detail.guests,
                }
            )
        return initial


class TagForm(forms.Form):
    name = forms.CharField(max_length=80)


class SourceTagForm(forms.Form):
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


class BookTagForm(SourceTagForm):
    """Backward-compatible name for the existing book workflow."""
