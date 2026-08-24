from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import (
    ArticleForm,
    BookForm,
    BookTagForm,
    PaperForm,
    PaperImportForm,
    PodcastEpisodeForm,
    SourceTagForm,
    TagForm,
)
from .models import KnowledgeItem
from .paper_import import (
    PaperImportFileError,
    import_paper_records,
    load_paper_manager_json,
)
from .selectors import (
    filter_user_articles,
    filter_user_books,
    filter_user_knowledge_items,
    filter_user_papers,
    filter_user_podcast_episodes,
    get_user_article,
    get_user_book,
    get_user_knowledge_item,
    get_user_paper,
    get_user_podcast_episode,
    get_user_tag,
    get_user_tags,
)
from .services import (
    assign_tag_to_item,
    create_article,
    create_book,
    create_paper,
    create_podcast_episode,
    create_tag,
    delete_article,
    delete_book,
    delete_paper,
    delete_podcast_episode,
    delete_tag,
    remove_tag_from_item,
    update_article,
    update_book,
    update_paper,
    update_podcast_episode,
)


def _add_validation_errors(form, error):
    if hasattr(error, 'message_dict'):
        for field, messages_for_field in error.message_dict.items():
            form.add_error(field if field in form.fields else None, messages_for_field)
    else:
        form.add_error(None, error)


@login_required
def library_index(request):
    filters = {
        'query': request.GET.get('q', '').strip(),
        'source_type': request.GET.get('source_type', '').strip(),
        'status': request.GET.get('status', '').strip(),
        'tag': request.GET.get('tag', '').strip(),
    }
    knowledge_items = filter_user_knowledge_items(request.user, **filters)

    return render(
        request,
        'library/library.html',
        {
            'knowledge_items': knowledge_items,
            'filters': filters,
            'active_source_type': filters['source_type'],
            'source_type_choices': KnowledgeItem.SourceType.choices,
            'status_choices': KnowledgeItem.status_choices_for_source(
                filters['source_type']
            ),
            'tags': get_user_tags(request.user),
        },
    )


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
            'status_choices': KnowledgeItem.status_choices_for_source(
                KnowledgeItem.SourceType.BOOK
            ),
            'tags': get_user_tags(request.user),
            'active_source_type': KnowledgeItem.SourceType.BOOK,
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
def paper_list(request):
    filters = {
        'query': request.GET.get('q', '').strip(),
        'status': request.GET.get('status', '').strip(),
        'publication_year': request.GET.get('year', '').strip(),
        'asset_class': request.GET.get('asset_class', '').strip(),
        'tag': request.GET.get('tag', '').strip(),
    }
    papers = filter_user_papers(request.user, **filters)

    return render(
        request,
        'library/paper_list.html',
        {
            'papers': papers,
            'filters': filters,
            'status_choices': KnowledgeItem.status_choices_for_source(
                KnowledgeItem.SourceType.PAPER
            ),
            'tags': get_user_tags(request.user),
            'active_source_type': KnowledgeItem.SourceType.PAPER,
        },
    )


@login_required
def paper_create(request):
    if request.method == 'POST':
        form = PaperForm(request.POST)
        if form.is_valid():
            try:
                paper = create_paper(user=request.user, data=form.cleaned_data)
            except ValidationError as error:
                _add_validation_errors(form, error)
            else:
                messages.success(request, 'Paper added.')
                return redirect('library:paper_detail', paper_uuid=paper.uuid)
    else:
        form = PaperForm()

    return render(
        request,
        'library/paper_form.html',
        {
            'form': form,
            'title': 'Add paper',
            'submit_label': 'Add paper',
            'cancel_url': reverse('library:paper_list'),
        },
    )


@login_required
def paper_import(request):
    result = None
    if request.method == 'POST':
        form = PaperImportForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                records = load_paper_manager_json(
                    form.cleaned_data['json_file']
                )
            except PaperImportFileError as error:
                form.add_error('json_file', str(error))
            else:
                result = import_paper_records(user=request.user, records=records)
    else:
        form = PaperImportForm()

    return render(
        request,
        'library/paper_import.html',
        {
            'form': form,
            'result': result,
        },
    )


@login_required
def paper_detail(request, paper_uuid):
    paper = get_user_paper(request.user, paper_uuid)
    insights = paper.insights.filter(user=request.user)[:5]
    tags = paper.tags.filter(user=request.user)

    return render(
        request,
        'library/paper_detail.html',
        {
            'paper': paper,
            'detail': paper.paper_detail,
            'insights': insights,
            'tags': tags,
            'tag_form': SourceTagForm(user=request.user),
        },
    )


@login_required
def paper_edit(request, paper_uuid):
    paper = get_user_paper(request.user, paper_uuid)

    if request.method == 'POST':
        form = PaperForm(request.POST, paper=paper)
        if form.is_valid():
            try:
                update_paper(paper=paper, data=form.cleaned_data)
            except ValidationError as error:
                _add_validation_errors(form, error)
            else:
                messages.success(request, 'Paper updated.')
                return redirect('library:paper_detail', paper_uuid=paper.uuid)
    else:
        form = PaperForm(paper=paper)

    return render(
        request,
        'library/paper_form.html',
        {
            'form': form,
            'paper': paper,
            'title': 'Edit paper',
            'submit_label': 'Save changes',
            'cancel_url': reverse(
                'library:paper_detail',
                kwargs={'paper_uuid': paper.uuid},
            ),
        },
    )


@login_required
def paper_delete(request, paper_uuid):
    paper = get_user_paper(request.user, paper_uuid)

    if request.method == 'POST':
        delete_paper(paper=paper)
        messages.success(request, 'Paper deleted.')
        return redirect('library:paper_list')

    return render(
        request,
        'library/paper_confirm_delete.html',
        {
            'paper': paper,
            'cancel_url': reverse(
                'library:paper_detail',
                kwargs={'paper_uuid': paper.uuid},
            ),
        },
    )


@login_required
def article_list(request):
    filters = {
        'query': request.GET.get('q', '').strip(),
        'status': request.GET.get('status', '').strip(),
        'publication_name': request.GET.get('publication', '').strip(),
        'tag': request.GET.get('tag', '').strip(),
    }
    articles = filter_user_articles(request.user, **filters)
    return render(
        request,
        'library/simple_source_list.html',
        {
            'items': articles,
            'filters': filters,
            'page_title': 'Articles',
            'page_description': 'Manage articles and the knowledge captured from them.',
            'source_plural': 'articles',
            'create_label': 'Add article',
            'create_url': reverse('library:article_create'),
            'clear_url': reverse('library:article_list'),
            'specific_filter_name': 'publication',
            'specific_filter_label': 'Publication / site',
            'specific_filter_value': filters['publication_name'],
            'status_choices': KnowledgeItem.status_choices_for_source(
                KnowledgeItem.SourceType.ARTICLE
            ),
            'tags': get_user_tags(request.user),
            'active_source_type': KnowledgeItem.SourceType.ARTICLE,
        },
    )


@login_required
def article_create(request):
    if request.method == 'POST':
        form = ArticleForm(request.POST)
        if form.is_valid():
            try:
                article = create_article(user=request.user, data=form.cleaned_data)
            except ValidationError as error:
                _add_validation_errors(form, error)
            else:
                messages.success(request, 'Article added.')
                return redirect(article.get_absolute_url())
    else:
        form = ArticleForm()
    return render(
        request,
        'library/simple_source_form.html',
        {
            'form': form,
            'source_label': 'Article',
            'title': 'Add article',
            'submit_label': 'Add article',
            'cancel_url': reverse('library:article_list'),
        },
    )


@login_required
def article_detail(request, article_uuid):
    article = get_user_article(request.user, article_uuid)
    return render(
        request,
        'library/article_detail.html',
        {
            'article': article,
            'detail': article.article_detail,
            'insights': article.insights.filter(user=request.user)[:5],
            'tags': article.tags.filter(user=request.user),
            'tag_form': SourceTagForm(user=request.user),
        },
    )


@login_required
def article_edit(request, article_uuid):
    article = get_user_article(request.user, article_uuid)
    if request.method == 'POST':
        form = ArticleForm(request.POST, article=article)
        if form.is_valid():
            try:
                update_article(article=article, data=form.cleaned_data)
            except ValidationError as error:
                _add_validation_errors(form, error)
            else:
                messages.success(request, 'Article updated.')
                return redirect(article.get_absolute_url())
    else:
        form = ArticleForm(article=article)
    return render(
        request,
        'library/simple_source_form.html',
        {
            'form': form,
            'source_label': 'Article',
            'title': 'Edit article',
            'submit_label': 'Save changes',
            'cancel_url': article.get_absolute_url(),
        },
    )


@login_required
def article_delete(request, article_uuid):
    article = get_user_article(request.user, article_uuid)
    if request.method == 'POST':
        delete_article(article=article)
        messages.success(request, 'Article deleted.')
        return redirect('library:article_list')
    return render(
        request,
        'library/simple_source_confirm_delete.html',
        {
            'item': article,
            'source_label': 'article',
            'cancel_url': article.get_absolute_url(),
        },
    )


@login_required
def podcast_list(request):
    filters = {
        'query': request.GET.get('q', '').strip(),
        'status': request.GET.get('status', '').strip(),
        'show_name': request.GET.get('show', '').strip(),
        'tag': request.GET.get('tag', '').strip(),
    }
    podcasts = filter_user_podcast_episodes(request.user, **filters)
    return render(
        request,
        'library/simple_source_list.html',
        {
            'items': podcasts,
            'filters': filters,
            'page_title': 'Podcast episodes',
            'page_description': 'Manage individual episodes and your listening notes.',
            'source_plural': 'podcast episodes',
            'create_label': 'Add podcast episode',
            'create_url': reverse('library:podcast_create'),
            'clear_url': reverse('library:podcast_list'),
            'specific_filter_name': 'show',
            'specific_filter_label': 'Show name',
            'specific_filter_value': filters['show_name'],
            'status_choices': KnowledgeItem.status_choices_for_source(
                KnowledgeItem.SourceType.PODCAST
            ),
            'tags': get_user_tags(request.user),
            'active_source_type': KnowledgeItem.SourceType.PODCAST,
        },
    )


@login_required
def podcast_create(request):
    if request.method == 'POST':
        form = PodcastEpisodeForm(request.POST)
        if form.is_valid():
            try:
                podcast = create_podcast_episode(
                    user=request.user,
                    data=form.cleaned_data,
                )
            except ValidationError as error:
                _add_validation_errors(form, error)
            else:
                messages.success(request, 'Podcast episode added.')
                return redirect(podcast.get_absolute_url())
    else:
        form = PodcastEpisodeForm()
    return render(
        request,
        'library/simple_source_form.html',
        {
            'form': form,
            'source_label': 'Podcast episode',
            'title': 'Add podcast episode',
            'submit_label': 'Add episode',
            'cancel_url': reverse('library:podcast_list'),
        },
    )


@login_required
def podcast_detail(request, podcast_uuid):
    podcast = get_user_podcast_episode(request.user, podcast_uuid)
    return render(
        request,
        'library/podcast_detail.html',
        {
            'podcast': podcast,
            'detail': podcast.podcast_episode_detail,
            'insights': podcast.insights.filter(user=request.user)[:5],
            'tags': podcast.tags.filter(user=request.user),
            'tag_form': SourceTagForm(user=request.user),
        },
    )


@login_required
def podcast_edit(request, podcast_uuid):
    podcast = get_user_podcast_episode(request.user, podcast_uuid)
    if request.method == 'POST':
        form = PodcastEpisodeForm(request.POST, podcast=podcast)
        if form.is_valid():
            try:
                update_podcast_episode(
                    podcast=podcast,
                    data=form.cleaned_data,
                )
            except ValidationError as error:
                _add_validation_errors(form, error)
            else:
                messages.success(request, 'Podcast episode updated.')
                return redirect(podcast.get_absolute_url())
    else:
        form = PodcastEpisodeForm(podcast=podcast)
    return render(
        request,
        'library/simple_source_form.html',
        {
            'form': form,
            'source_label': 'Podcast episode',
            'title': 'Edit podcast episode',
            'submit_label': 'Save changes',
            'cancel_url': podcast.get_absolute_url(),
        },
    )


@login_required
def podcast_delete(request, podcast_uuid):
    podcast = get_user_podcast_episode(request.user, podcast_uuid)
    if request.method == 'POST':
        delete_podcast_episode(podcast=podcast)
        messages.success(request, 'Podcast episode deleted.')
        return redirect('library:podcast_list')
    return render(
        request,
        'library/simple_source_confirm_delete.html',
        {
            'item': podcast,
            'source_label': 'podcast episode',
            'cancel_url': podcast.get_absolute_url(),
        },
    )


@login_required
def source_tag_add(request, item_uuid):
    source = get_user_knowledge_item(request.user, item_uuid)

    if request.method != 'POST':
        return redirect(source.get_absolute_url())

    form = SourceTagForm(request.POST, user=request.user)
    if form.is_valid():
        assign_tag_to_item(
            knowledge_item=source,
            tag=form.cleaned_data.get('tag'),
            new_tag_name=form.cleaned_data.get('new_tag', ''),
        )
        messages.success(request, 'Tag added.')
    else:
        messages.error(request, 'Choose a tag or enter a new one.')

    return redirect(source.get_absolute_url())


@login_required
def source_tag_remove(request, item_uuid, tag_id):
    source = get_user_knowledge_item(request.user, item_uuid)
    tag = get_user_tag(request.user, tag_id)

    if request.method == 'POST':
        remove_tag_from_item(knowledge_item=source, tag=tag)
        messages.success(request, 'Tag removed.')

    return redirect(source.get_absolute_url())


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
