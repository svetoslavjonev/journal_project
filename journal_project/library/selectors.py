from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from .models import KnowledgeItem, Tag


def get_user_books(user):
    return (
        KnowledgeItem.objects.filter(
            user=user,
            source_type=KnowledgeItem.SourceType.BOOK,
        )
        .select_related('book_detail')
        .prefetch_related('tags')
        .annotate(insight_count=Count('insights'))
    )


def get_user_knowledge_items(user):
    return KnowledgeItem.objects.filter(user=user)


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


def get_user_book(user, book_uuid):
    return get_object_or_404(get_user_books(user), uuid=book_uuid)


def get_user_knowledge_item(user, item_uuid):
    return get_object_or_404(get_user_knowledge_items(user), uuid=item_uuid)


def get_user_tag(user, tag_id):
    return get_object_or_404(get_user_tags(user), pk=tag_id)
