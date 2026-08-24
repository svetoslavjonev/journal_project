from django.urls import path

from journal_project.journal import views as journal_views

from . import views

app_name = 'library'

urlpatterns = [
    path('', views.library_index, name='index'),
    path('books/', views.book_list, name='book_list'),
    path('books/new/', views.book_create, name='book_create'),
    path('books/<uuid:book_uuid>/', views.book_detail, name='book_detail'),
    path('books/<uuid:book_uuid>/edit/', views.book_edit, name='book_edit'),
    path('books/<uuid:book_uuid>/delete/', views.book_delete, name='book_delete'),
    path('books/<uuid:book_uuid>/tags/add/', views.book_tag_add, name='book_tag_add'),
    path(
        'books/<uuid:book_uuid>/tags/<int:tag_id>/remove/',
        views.book_tag_remove,
        name='book_tag_remove',
    ),
    path('papers/', views.paper_list, name='paper_list'),
    path('papers/new/', views.paper_create, name='paper_create'),
    path('papers/import/', views.paper_import, name='paper_import'),
    path('papers/<uuid:paper_uuid>/', views.paper_detail, name='paper_detail'),
    path('papers/<uuid:paper_uuid>/edit/', views.paper_edit, name='paper_edit'),
    path(
        'papers/<uuid:paper_uuid>/delete/',
        views.paper_delete,
        name='paper_delete',
    ),
    path('articles/', views.article_list, name='article_list'),
    path('articles/new/', views.article_create, name='article_create'),
    path(
        'articles/<uuid:article_uuid>/',
        views.article_detail,
        name='article_detail',
    ),
    path(
        'articles/<uuid:article_uuid>/edit/',
        views.article_edit,
        name='article_edit',
    ),
    path(
        'articles/<uuid:article_uuid>/delete/',
        views.article_delete,
        name='article_delete',
    ),
    path('podcasts/', views.podcast_list, name='podcast_list'),
    path('podcasts/new/', views.podcast_create, name='podcast_create'),
    path(
        'podcasts/<uuid:podcast_uuid>/',
        views.podcast_detail,
        name='podcast_detail',
    ),
    path(
        'podcasts/<uuid:podcast_uuid>/edit/',
        views.podcast_edit,
        name='podcast_edit',
    ),
    path(
        'podcasts/<uuid:podcast_uuid>/delete/',
        views.podcast_delete,
        name='podcast_delete',
    ),
    path(
        'items/<uuid:item_uuid>/tags/add/',
        views.source_tag_add,
        name='item_tag_add',
    ),
    path(
        'items/<uuid:item_uuid>/tags/<int:tag_id>/remove/',
        views.source_tag_remove,
        name='item_tag_remove',
    ),
    path(
        'items/<uuid:item_uuid>/insights/new/',
        journal_views.insight_create_for_item,
        name='item_insight_create',
    ),
]
