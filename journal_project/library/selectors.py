from typing import Any
from uuid import UUID

from django.db.models import Count, Q
from django.db.models.query import QuerySet
from django.shortcuts import get_object_or_404

from .models import KnowledgeItem, Tag


def get_user_books(user):
    return (
        get_user_knowledge_items(user)
        .filter(
            source_type=KnowledgeItem.SourceType.BOOK,
        )
        .select_related('book_detail')
    )


def get_user_papers(user: Any) -> QuerySet[KnowledgeItem]:
    """Return user-owned papers with their detail records."""
    return (
        get_user_knowledge_items(user)
        .filter(source_type=KnowledgeItem.SourceType.PAPER)
        .select_related('paper_detail')
    )


def get_user_articles(user: Any) -> QuerySet[KnowledgeItem]:
    """Return user-owned articles with their detail records."""
    return (
        get_user_knowledge_items(user)
        .filter(source_type=KnowledgeItem.SourceType.ARTICLE)
        .select_related('article_detail')
    )


def get_user_podcast_episodes(user: Any) -> QuerySet[KnowledgeItem]:
    """Return user-owned podcast episodes with their detail records."""
    return (
        get_user_knowledge_items(user)
        .filter(source_type=KnowledgeItem.SourceType.PODCAST)
        .select_related('podcast_episode_detail')
    )


def get_user_knowledge_items(user: Any) -> QuerySet[KnowledgeItem]:
    """Return source-card-ready knowledge items owned by one user."""
    return (
        KnowledgeItem.objects.filter(user=user)
        .select_related(
            'book_detail',
            'paper_detail',
            'article_detail',
            'podcast_episode_detail',
        )
        .prefetch_related('tags')
        .annotate(insight_count=Count('insights', distinct=True))
    )


def get_user_tags(user):
    return Tag.objects.filter(user=user)


def filter_user_books(user, *, query='', status='', genre='', tag=''):
    books = get_user_books(user)

    if query:
        books = books.filter(
            Q(title__icontains=query)
            | Q(creator__icontains=query)
            | Q(summary__icontains=query)
            | Q(book_detail__author__icontains=query)
            | Q(book_detail__genre__icontains=query)
        )

    if status:
        books = books.filter(status=status)

    if genre:
        books = books.filter(book_detail__genre__icontains=genre)

    if tag:
        books = books.filter(tag_assignments__tag__user=user, tag_assignments__tag__slug=tag)

    return books.distinct()


def filter_user_knowledge_items(
    user: Any,
    *,
    query: str = '',
    source_type: str = '',
    status: str = '',
    tag: str = '',
) -> QuerySet[KnowledgeItem]:
    """Filter one user's sources using fields shared by all source types."""
    items = get_user_knowledge_items(user)

    if query:
        items = items.filter(_knowledge_item_search_query(user, query))

    if source_type:
        items = items.filter(source_type=source_type)

    if status:
        items = items.filter(status=status)

    if tag:
        items = items.filter(
            tag_assignments__tag__user=user,
            tag_assignments__tag__slug=tag,
        )

    return items.distinct()


def _knowledge_item_search_query(user: Any, query: str) -> Q:
    """Return common and source-specific search conditions."""
    return (
        Q(title__icontains=query)
        | Q(creator__icontains=query)
        | Q(summary__icontains=query)
        | Q(
            tag_assignments__tag__user=user,
            tag_assignments__tag__name__icontains=query,
        )
        | Q(paper_detail__key_research_question__icontains=query)
        | Q(
            paper_detail__key_findings_practical_applications__icontains=query
        )
        | Q(paper_detail__methodology_research_design__icontains=query)
        | Q(paper_detail__sample_size_data_source__icontains=query)
        | Q(paper_detail__asset_class__icontains=query)
        | Q(paper_detail__journal__icontains=query)
        | Q(paper_detail__doi__icontains=query)
        | Q(article_detail__publication_name__icontains=query)
        | Q(podcast_episode_detail__show_name__icontains=query)
        | Q(podcast_episode_detail__guests__icontains=query)
    )


def filter_user_papers(
    user: Any,
    *,
    query: str = '',
    status: str = '',
    publication_year: str | int = '',
    asset_class: str = '',
    tag: str = '',
) -> QuerySet[KnowledgeItem]:
    """Filter one user's papers using common and paper-specific fields."""
    papers = get_user_papers(user)

    if query:
        papers = papers.filter(
            Q(title__icontains=query)
            | Q(creator__icontains=query)
            | Q(summary__icontains=query)
            | Q(paper_detail__journal__icontains=query)
            | Q(paper_detail__doi__icontains=query)
            | Q(paper_detail__asset_class__icontains=query)
            | Q(paper_detail__key_research_question__icontains=query)
            | Q(
                paper_detail__key_findings_practical_applications__icontains=query
            )
        )

    if status:
        papers = papers.filter(status=status)

    if publication_year:
        try:
            normalized_year = int(publication_year)
        except (TypeError, ValueError):
            return papers.none()
        if normalized_year <= 0:
            return papers.none()
        papers = papers.filter(paper_detail__publication_year=normalized_year)

    if asset_class:
        papers = papers.filter(paper_detail__asset_class__icontains=asset_class)

    if tag:
        papers = papers.filter(
            tag_assignments__tag__user=user,
            tag_assignments__tag__slug=tag,
        )

    return papers.distinct()


def filter_user_articles(
    user: Any,
    *,
    query: str = '',
    status: str = '',
    publication_name: str = '',
    tag: str = '',
) -> QuerySet[KnowledgeItem]:
    """Filter one user's articles by shared and article-specific fields."""
    articles = get_user_articles(user)

    if query:
        articles = articles.filter(
            Q(title__icontains=query)
            | Q(creator__icontains=query)
            | Q(summary__icontains=query)
            | Q(article_detail__publication_name__icontains=query)
        )
    if status:
        articles = articles.filter(status=status)
    if publication_name:
        articles = articles.filter(
            article_detail__publication_name__icontains=publication_name
        )
    if tag:
        articles = articles.filter(
            tag_assignments__tag__user=user,
            tag_assignments__tag__slug=tag,
        )
    return articles.distinct()


def filter_user_podcast_episodes(
    user: Any,
    *,
    query: str = '',
    status: str = '',
    show_name: str = '',
    tag: str = '',
) -> QuerySet[KnowledgeItem]:
    """Filter one user's episodes by shared and podcast-specific fields."""
    episodes = get_user_podcast_episodes(user)

    if query:
        episodes = episodes.filter(
            Q(title__icontains=query)
            | Q(creator__icontains=query)
            | Q(summary__icontains=query)
            | Q(podcast_episode_detail__show_name__icontains=query)
            | Q(podcast_episode_detail__guests__icontains=query)
        )
    if status:
        episodes = episodes.filter(status=status)
    if show_name:
        episodes = episodes.filter(
            podcast_episode_detail__show_name__icontains=show_name
        )
    if tag:
        episodes = episodes.filter(
            tag_assignments__tag__user=user,
            tag_assignments__tag__slug=tag,
        )
    return episodes.distinct()


def get_user_book(user, book_uuid):
    return get_object_or_404(get_user_books(user), uuid=book_uuid)


def get_user_paper(user: Any, paper_uuid: UUID) -> KnowledgeItem:
    """Return one user-owned paper or raise a 404 response."""
    return get_object_or_404(get_user_papers(user), uuid=paper_uuid)


def get_user_article(user: Any, article_uuid: UUID) -> KnowledgeItem:
    """Return one user-owned article or raise a 404 response."""
    return get_object_or_404(get_user_articles(user), uuid=article_uuid)


def get_user_podcast_episode(user: Any, podcast_uuid: UUID) -> KnowledgeItem:
    """Return one user-owned podcast episode or raise a 404 response."""
    return get_object_or_404(
        get_user_podcast_episodes(user),
        uuid=podcast_uuid,
    )


def get_user_knowledge_item(user: Any, item_uuid: UUID) -> KnowledgeItem:
    """Return one user-owned knowledge item or raise a 404 response."""
    return get_object_or_404(get_user_knowledge_items(user), uuid=item_uuid)


def get_user_tag(user, tag_id):
    return get_object_or_404(get_user_tags(user), pk=tag_id)
