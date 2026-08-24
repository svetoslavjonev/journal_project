from typing import Any, Mapping

from django.core.exceptions import ValidationError
from django.db import transaction

from django.utils.text import slugify

from .models import (
    ArticleDetail,
    BookDetail,
    KnowledgeItem,
    KnowledgeItemTag,
    PaperDetail,
    PodcastEpisodeDetail,
    Tag,
)


COMMON_KNOWLEDGE_ITEM_FIELDS = (
    'title',
    'subtitle',
    'creator',
    'status',
    'summary',
    'source_url',
    'date_published',
    'date_started',
    'date_finished',
    'archived',
)


@transaction.atomic
def create_knowledge_item(
    *,
    user: Any,
    source_type: str,
    data: Mapping[str, Any],
) -> KnowledgeItem:
    """Create the common record that a source-specific service can extend."""
    knowledge_item = KnowledgeItem(user=user, source_type=source_type)
    return update_knowledge_item(knowledge_item=knowledge_item, data=data)


@transaction.atomic
def update_knowledge_item(
    *,
    knowledge_item: KnowledgeItem,
    data: Mapping[str, Any],
) -> KnowledgeItem:
    """Update validated fields shared by every knowledge source."""
    for field_name in COMMON_KNOWLEDGE_ITEM_FIELDS:
        if field_name in data:
            setattr(knowledge_item, field_name, data[field_name])

    knowledge_item.full_clean()
    knowledge_item.save()
    return knowledge_item


@transaction.atomic
def archive_knowledge_item(*, knowledge_item: KnowledgeItem) -> KnowledgeItem:
    """Archive a source through the common KnowledgeItem record."""
    return update_knowledge_item(
        knowledge_item=knowledge_item,
        data={'archived': True},
    )


def _book_knowledge_item_data(data: Mapping[str, Any]) -> dict[str, Any]:
    """Translate book-form fields into common KnowledgeItem fields."""
    return {
        'title': data['title'],
        'subtitle': data.get('subtitle', ''),
        'creator': data['author'],
        'status': data['status'],
        'summary': data.get('summary', ''),
        'source_url': data.get('source_url', ''),
        'date_published': data.get('date_published'),
    }


def _paper_knowledge_item_data(data: Mapping[str, Any]) -> dict[str, Any]:
    """Translate paper-form fields into common KnowledgeItem fields."""
    return {
        'title': data['title'],
        'creator': data['authors'],
        'status': data['status'],
        'summary': data.get('summary', ''),
        'source_url': data.get('source_url', ''),
    }


def _article_knowledge_item_data(data: Mapping[str, Any]) -> dict[str, Any]:
    """Translate article-form fields into common KnowledgeItem fields."""
    return {
        'title': data['title'],
        'creator': data['authors'],
        'date_published': data.get('publication_date'),
        'source_url': data.get('source_url', ''),
        'status': data['status'],
        'summary': data.get('summary', ''),
    }


def _podcast_knowledge_item_data(data: Mapping[str, Any]) -> dict[str, Any]:
    """Translate podcast-form fields into common KnowledgeItem fields."""
    return {
        'title': data['episode_title'],
        'creator': data['hosts'],
        'status': data['status'],
        'summary': data.get('summary', ''),
        'source_url': data.get('source_url', ''),
    }


@transaction.atomic
def create_book(*, user, data):
    book = create_knowledge_item(
        user=user,
        source_type=KnowledgeItem.SourceType.BOOK,
        data=_book_knowledge_item_data(data),
    )

    detail = BookDetail(
        knowledge_item=book,
        author=data['author'],
        genre=data.get('genre', ''),
        isbn=data.get('isbn', ''),
        publisher=data.get('publisher', ''),
        page_count=data.get('page_count'),
        publication_date=data.get('date_published'),
        original_language=data.get('original_language', ''),
        edition=data.get('edition', ''),
        metadata=data.get('metadata') or {},
    )
    detail.full_clean()
    detail.save()

    return book


@transaction.atomic
def update_book(*, book, data):
    update_knowledge_item(
        knowledge_item=book,
        data=_book_knowledge_item_data(data),
    )

    try:
        detail = book.book_detail
    except BookDetail.DoesNotExist as exc:
        raise ValidationError('Book source is missing book details.') from exc

    detail.author = data['author']
    detail.genre = data.get('genre', '')
    detail.isbn = data.get('isbn', '')
    detail.publisher = data.get('publisher', '')
    detail.page_count = data.get('page_count')
    detail.publication_date = data.get('date_published')
    detail.original_language = data.get('original_language', '')
    detail.edition = data.get('edition', '')
    detail.metadata = data.get('metadata') or {}
    detail.full_clean()
    detail.save()

    return book


@transaction.atomic
def delete_book(*, book):
    book.delete()


@transaction.atomic
def create_paper(*, user: Any, data: Mapping[str, Any]) -> KnowledgeItem:
    """Create a paper source and its paper-specific detail record."""
    paper = create_knowledge_item(
        user=user,
        source_type=KnowledgeItem.SourceType.PAPER,
        data=_paper_knowledge_item_data(data),
    )
    detail = PaperDetail(
        knowledge_item=paper,
        publication_year=data.get('publication_year'),
        journal=data.get('journal', ''),
        doi=data.get('doi', ''),
        asset_class=data.get('asset_class', ''),
        sample_size_data_source=data.get('sample_size_data_source', ''),
        methodology_research_design=data.get(
            'methodology_research_design',
            '',
        ),
        key_research_question=data.get('key_research_question', ''),
        key_findings_practical_applications=data.get(
            'key_findings_practical_applications',
            '',
        ),
    )
    detail.full_clean()
    detail.save()
    return paper


@transaction.atomic
def update_paper(
    *,
    paper: KnowledgeItem,
    data: Mapping[str, Any],
) -> KnowledgeItem:
    """Update a paper source and its paper-specific detail record."""
    update_knowledge_item(
        knowledge_item=paper,
        data=_paper_knowledge_item_data(data),
    )

    try:
        detail = paper.paper_detail
    except PaperDetail.DoesNotExist as exc:
        raise ValidationError('Paper source is missing paper details.') from exc

    detail.publication_year = data.get('publication_year')
    detail.journal = data.get('journal', '')
    detail.doi = data.get('doi', '')
    detail.asset_class = data.get('asset_class', '')
    detail.sample_size_data_source = data.get('sample_size_data_source', '')
    detail.methodology_research_design = data.get(
        'methodology_research_design',
        '',
    )
    detail.key_research_question = data.get('key_research_question', '')
    detail.key_findings_practical_applications = data.get(
        'key_findings_practical_applications',
        '',
    )
    detail.full_clean()
    detail.save()
    return paper


@transaction.atomic
def delete_paper(*, paper: KnowledgeItem) -> None:
    """Delete a paper source using the existing permanent-delete convention."""
    paper.delete()


@transaction.atomic
def create_article(*, user: Any, data: Mapping[str, Any]) -> KnowledgeItem:
    """Create an article source and its detail record."""
    article = create_knowledge_item(
        user=user,
        source_type=KnowledgeItem.SourceType.ARTICLE,
        data=_article_knowledge_item_data(data),
    )
    detail = ArticleDetail(
        knowledge_item=article,
        publication_name=data.get('publication_name', ''),
    )
    detail.full_clean()
    detail.save()
    return article


@transaction.atomic
def update_article(
    *,
    article: KnowledgeItem,
    data: Mapping[str, Any],
) -> KnowledgeItem:
    """Update an article source and its detail record."""
    update_knowledge_item(
        knowledge_item=article,
        data=_article_knowledge_item_data(data),
    )
    try:
        detail = article.article_detail
    except ArticleDetail.DoesNotExist as exc:
        raise ValidationError('Article source is missing article details.') from exc
    detail.publication_name = data.get('publication_name', '')
    detail.full_clean()
    detail.save()
    return article


@transaction.atomic
def delete_article(*, article: KnowledgeItem) -> None:
    """Delete an article using the existing permanent-delete convention."""
    article.delete()


@transaction.atomic
def create_podcast_episode(
    *,
    user: Any,
    data: Mapping[str, Any],
) -> KnowledgeItem:
    """Create a podcast episode source and its detail record."""
    podcast = create_knowledge_item(
        user=user,
        source_type=KnowledgeItem.SourceType.PODCAST,
        data=_podcast_knowledge_item_data(data),
    )
    detail = PodcastEpisodeDetail(
        knowledge_item=podcast,
        show_name=data.get('show_name', ''),
        guests=data.get('guests', ''),
    )
    detail.full_clean()
    detail.save()
    return podcast


@transaction.atomic
def update_podcast_episode(
    *,
    podcast: KnowledgeItem,
    data: Mapping[str, Any],
) -> KnowledgeItem:
    """Update a podcast episode source and its detail record."""
    update_knowledge_item(
        knowledge_item=podcast,
        data=_podcast_knowledge_item_data(data),
    )
    try:
        detail = podcast.podcast_episode_detail
    except PodcastEpisodeDetail.DoesNotExist as exc:
        raise ValidationError(
            'Podcast source is missing podcast episode details.'
        ) from exc
    detail.show_name = data.get('show_name', '')
    detail.guests = data.get('guests', '')
    detail.full_clean()
    detail.save()
    return podcast


@transaction.atomic
def delete_podcast_episode(*, podcast: KnowledgeItem) -> None:
    """Delete an episode using the existing permanent-delete convention."""
    podcast.delete()


@transaction.atomic
def create_tag(*, user, name):
    tag = Tag(user=user, name=name, slug=slugify(name.strip()))
    tag.save()
    return tag


@transaction.atomic
def delete_tag(*, tag):
    tag.delete()


@transaction.atomic
def assign_tag_to_item(*, knowledge_item, tag=None, new_tag_name=''):
    if tag is None:
        tag_name = new_tag_name.strip()
        tag_slug = slugify(tag_name)
        tag, _ = Tag.objects.get_or_create(
            user=knowledge_item.user,
            slug=tag_slug,
            defaults={'name': tag_name},
        )

    assignment, _ = KnowledgeItemTag.objects.get_or_create(
        knowledge_item=knowledge_item,
        tag=tag,
    )
    return assignment


@transaction.atomic
def remove_tag_from_item(*, knowledge_item, tag):
    KnowledgeItemTag.objects.filter(knowledge_item=knowledge_item, tag=tag).delete()
