from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render

from journal_project.journal.selectors import filter_user_insights
from journal_project.journal.models import Insight
from journal_project.library.models import KnowledgeItem
from journal_project.library.selectors import filter_user_books


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/home.html')


def health(request):
    return JsonResponse({'status': 'ok'})


@login_required
def dashboard(request):
    user_books = filter_user_books(request.user)
    user_insights = filter_user_insights(request.user)
    currently_reading = user_books.filter(status=KnowledgeItem.Status.READING)[:4]
    recent_books = user_books[:4]
    recent_insights = user_insights[:4]

    return render(
        request,
        'core/dashboard.html',
        {
            'book_count': user_books.count(),
            'insight_count': user_insights.count(),
            'current_count': user_books.filter(status=KnowledgeItem.Status.READING).count(),
            'pinned_count': user_insights.filter(pinned=True).count(),
            'currently_reading': currently_reading,
            'recent_books': recent_books,
            'recent_insights': recent_insights,
            'insight_types': Insight.InsightType.choices,
        },
    )


@login_required
def search(request):
    query = request.GET.get('q', '').strip()
    books = filter_user_books(request.user, query=query) if query else []
    insights = filter_user_insights(request.user, query=query) if query else []

    return render(
        request,
        'core/search.html',
        {
            'query': query,
            'books': books,
            'insights': insights,
        },
    )
