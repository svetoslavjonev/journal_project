from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse

from journal_project.library.models import KnowledgeItem
from journal_project.library.selectors import get_user_knowledge_item, get_user_tags

from .forms import InsightForm
from .models import Insight
from .selectors import filter_user_insights, get_user_insight
from .services import create_insight, delete_insight, update_insight


def _add_validation_errors(form, error):
    if hasattr(error, 'message_dict'):
        for field, messages_for_field in error.message_dict.items():
            form.add_error(field if field in form.fields else None, messages_for_field)
    else:
        form.add_error(None, error)


@login_required
def journal_index(request):
    return redirect('journal:insight_list')


@login_required
def insight_list(request):
    filters = {
        'query': request.GET.get('q', '').strip(),
        'insight_type': request.GET.get('type', '').strip(),
        'source_type': request.GET.get('source_type', '').strip(),
        'tag': request.GET.get('tag', '').strip(),
    }
    insights = filter_user_insights(request.user, **filters)

    return render(
        request,
        'journal/insight_list.html',
        {
            'insights': insights,
            'filters': filters,
            'insight_type_choices': Insight.InsightType.choices,
            'source_type_choices': KnowledgeItem.SourceType.choices,
            'tags': get_user_tags(request.user),
        },
    )


@login_required
def insight_create(request):
    if request.method == 'POST':
        form = InsightForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                create_insight(user=request.user, data=form.cleaned_data)
            except ValidationError as error:
                _add_validation_errors(form, error)
            else:
                messages.success(request, 'Insight added.')
                return redirect('journal:insight_list')
    else:
        form = InsightForm(user=request.user)

    return render(
        request,
        'journal/insight_form.html',
        {
            'form': form,
            'title': 'Add insight',
            'submit_label': 'Add insight',
            'cancel_url': reverse('journal:insight_list'),
        },
    )


@login_required
def insight_create_for_item(request, item_uuid):
    source = get_user_knowledge_item(request.user, item_uuid)

    if request.method == 'POST':
        form = InsightForm(request.POST, user=request.user, source=source)
        if form.is_valid():
            try:
                create_insight(user=request.user, data=form.cleaned_data, source=source)
            except ValidationError as error:
                _add_validation_errors(form, error)
            else:
                messages.success(request, 'Insight added.')
                return redirect(source.get_absolute_url())
    else:
        form = InsightForm(user=request.user, source=source)

    return render(
        request,
        'journal/insight_form.html',
        {
            'form': form,
            'source': source,
            'title': f'Add insight for {source.title}',
            'submit_label': 'Add insight',
            'cancel_url': source.get_absolute_url(),
        },
    )


@login_required
def insight_edit(request, insight_uuid):
    insight = get_user_insight(request.user, insight_uuid)

    if request.method == 'POST':
        form = InsightForm(request.POST, user=request.user, insight=insight)
        if form.is_valid():
            try:
                update_insight(insight=insight, data=form.cleaned_data)
            except ValidationError as error:
                _add_validation_errors(form, error)
            else:
                messages.success(request, 'Insight updated.')
                return redirect('journal:insight_list')
    else:
        form = InsightForm(user=request.user, insight=insight)

    return render(
        request,
        'journal/insight_form.html',
        {
            'form': form,
            'insight': insight,
            'title': 'Edit insight',
            'submit_label': 'Save changes',
            'cancel_url': reverse('journal:insight_list'),
        },
    )


@login_required
def insight_delete(request, insight_uuid):
    insight = get_user_insight(request.user, insight_uuid)

    if request.method == 'POST':
        delete_insight(insight=insight)
        messages.success(request, 'Insight deleted.')
        return redirect('journal:insight_list')

    return render(
        request,
        'journal/insight_confirm_delete.html',
        {
            'insight': insight,
            'cancel_url': reverse('journal:insight_list'),
        },
    )
