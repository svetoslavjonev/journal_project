from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import BookForm, BookTagForm, TagForm
from .models import KnowledgeItem
from .selectors import filter_user_books, get_user_book, get_user_tag, get_user_tags
from .services import (
    assign_tag_to_item,
    create_book,
    create_tag,
    delete_book,
    delete_tag,
    remove_tag_from_item,
    update_book,
)


def _add_validation_errors(form, error):
    if hasattr(error, 'message_dict'):
        for field, messages_for_field in error.message_dict.items():
            form.add_error(field if field in form.fields else None, messages_for_field)
    else:
        form.add_error(None, error)


@login_required
def library_index(request):
    return redirect('library:book_list')


@login_required
def book_list(request):
    filters = {
        'query': request.GET.get('q', '').strip(),
        'status': request.GET.get('status', '').strip(),
        'genre': request.GET.get('genre', '').strip(),
        'tag': request.GET.get('tag', '').strip(),
    }
    books = filter_user_books(request.user, **filters)

    return render(
        request,
        'library/book_list.html',
        {
            'books': books,
            'filters': filters,
            'status_choices': KnowledgeItem.Status.choices,
            'tags': get_user_tags(request.user),
        },
    )


@login_required
def book_create(request):
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            try:
                book = create_book(user=request.user, data=form.cleaned_data)
            except ValidationError as error:
                _add_validation_errors(form, error)
            else:
                messages.success(request, 'Book added.')
                return redirect('library:book_detail', book_uuid=book.uuid)
    else:
        form = BookForm()

    return render(
        request,
        'library/book_form.html',
        {
            'form': form,
            'title': 'Add book',
            'submit_label': 'Add book',
            'cancel_url': reverse('library:book_list'),
        },
    )


@login_required
def book_detail(request, book_uuid):
    book = get_user_book(request.user, book_uuid)
    insights = book.insights.filter(user=request.user)[:5]
    tags = book.tags.filter(user=request.user)

    return render(
        request,
        'library/book_detail.html',
        {
            'book': book,
            'detail': book.book_detail,
            'insights': insights,
            'tags': tags,
            'tag_form': BookTagForm(user=request.user),
        },
    )


@login_required
def book_edit(request, book_uuid):
    book = get_user_book(request.user, book_uuid)

    if request.method == 'POST':
        form = BookForm(request.POST, knowledge_item=book)
        if form.is_valid():
            try:
                update_book(book=book, data=form.cleaned_data)
            except ValidationError as error:
                _add_validation_errors(form, error)
            else:
                messages.success(request, 'Book updated.')
                return redirect('library:book_detail', book_uuid=book.uuid)
    else:
        form = BookForm(knowledge_item=book)

    return render(
        request,
        'library/book_form.html',
        {
            'form': form,
            'book': book,
            'title': 'Edit book',
            'submit_label': 'Save changes',
            'cancel_url': reverse('library:book_detail', kwargs={'book_uuid': book.uuid}),
        },
    )


@login_required
def book_delete(request, book_uuid):
    book = get_user_book(request.user, book_uuid)

    if request.method == 'POST':
        delete_book(book=book)
        messages.success(request, 'Book deleted.')
        return redirect('library:book_list')

    return render(
        request,
        'library/book_confirm_delete.html',
        {
            'book': book,
            'detail': book.book_detail,
            'cancel_url': reverse('library:book_detail', kwargs={'book_uuid': book.uuid}),
        },
    )


@login_required
def book_tag_add(request, book_uuid):
    book = get_user_book(request.user, book_uuid)

    if request.method != 'POST':
        return redirect('library:book_detail', book_uuid=book.uuid)

    form = BookTagForm(request.POST, user=request.user)
    if form.is_valid():
        assign_tag_to_item(
            knowledge_item=book,
            tag=form.cleaned_data.get('tag'),
            new_tag_name=form.cleaned_data.get('new_tag', ''),
        )
        messages.success(request, 'Tag added.')
    else:
        messages.error(request, 'Choose a tag or enter a new one.')

    return redirect('library:book_detail', book_uuid=book.uuid)


@login_required
def book_tag_remove(request, book_uuid, tag_id):
    book = get_user_book(request.user, book_uuid)
    tag = get_user_tag(request.user, tag_id)

    if request.method == 'POST':
        remove_tag_from_item(knowledge_item=book, tag=tag)
        messages.success(request, 'Tag removed.')

    return redirect('library:book_detail', book_uuid=book.uuid)


@login_required
def tag_list(request):
    if request.method == 'POST':
        form = TagForm(request.POST)
        if form.is_valid():
            try:
                create_tag(user=request.user, name=form.cleaned_data['name'])
            except ValidationError as error:
                _add_validation_errors(form, error)
            else:
                messages.success(request, 'Tag created.')
                return redirect('tag_list')
    else:
        form = TagForm()

    return render(
        request,
        'library/tag_list.html',
        {
            'form': form,
            'tags': get_user_tags(request.user),
        },
    )


@login_required
def tag_delete(request, tag_id):
    tag = get_user_tag(request.user, tag_id)

    if request.method == 'POST':
        delete_tag(tag=tag)
        messages.success(request, 'Tag deleted.')
        return redirect('tag_list')

    return render(
        request,
        'library/tag_confirm_delete.html',
        {
            'tag': tag,
            'cancel_url': reverse('tag_list'),
        },
    )
