from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render

from journal_project.journal.selectors import filter_user_insights
from journal_project.journal.models import Insight
from journal_project.library.models import KnowledgeItem
from journal_project.library.selectors import filter_user_knowledge_items


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/home.html')


def health(request):
    return JsonResponse({'status': 'ok'})


@login_required
def dashboard(request):
    user_sources = filter_user_knowledge_items(request.user)
    user_insights = filter_user_insights(request.user)
    in_progress_sources = user_sources.filter(
        status=KnowledgeItem.Status.IN_PROGRESS
    )[:4]
    recent_sources = user_sources[:4]
    recent_insights = user_insights[:4]

    return render(
        request,
        'core/dashboard.html',
        {
            'source_count': user_sources.count(),
            'insight_count': user_insights.count(),
            'in_progress_count': user_sources.filter(
                status=KnowledgeItem.Status.IN_PROGRESS
            ).count(),
            'pinned_count': user_insights.filter(pinned=True).count(),
            'in_progress_sources': in_progress_sources,
            'recent_sources': recent_sources,
            'recent_insights': recent_insights,
            'insight_types': Insight.InsightType.choices,
        },
    )


@login_required
def search(request):
    query = request.GET.get('q', '').strip()
    sources = (
        filter_user_knowledge_items(request.user, query=query) if query else []
    )
    insights = filter_user_insights(request.user, query=query) if query else []

    return render(
        request,
        'core/search.html',
        {
            'query': query,
            'sources': sources,
            'insights': insights,
        },
    )
