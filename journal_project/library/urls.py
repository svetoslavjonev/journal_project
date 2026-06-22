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
    path(
        'items/<uuid:item_uuid>/insights/new/',
        journal_views.insight_create_for_item,
        name='item_insight_create',
    ),
]
