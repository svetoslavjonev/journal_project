from django.core.exceptions import ValidationError
from django.db import transaction

from django.utils.text import slugify

from .models import BookDetail, KnowledgeItem, KnowledgeItemTag, Tag


@transaction.atomic
def create_book(*, user, data):
    book = KnowledgeItem(
        user=user,
        source_type=KnowledgeItem.SourceType.BOOK,
        title=data['title'],
        subtitle=data.get('subtitle', ''),
        creator=data['author'],
        status=data['status'],
        summary=data.get('summary', ''),
        source_url=data.get('source_url', ''),
        date_published=data.get('date_published'),
    )
    book.full_clean()
    book.save()

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
    book.title = data['title']
    book.subtitle = data.get('subtitle', '')
    book.creator = data['author']
    book.status = data['status']
    book.summary = data.get('summary', '')
    book.source_url = data.get('source_url', '')
    book.date_published = data.get('date_published')
    book.full_clean()
    book.save()

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
