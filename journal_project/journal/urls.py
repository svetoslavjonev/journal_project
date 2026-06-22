from django.urls import path

from . import views

app_name = 'journal'

urlpatterns = [
    path('', views.journal_index, name='index'),
    path('insights/', views.insight_list, name='insight_list'),
    path('insights/new/', views.insight_create, name='insight_create'),
    path('insights/<uuid:insight_uuid>/edit/', views.insight_edit, name='insight_edit'),
    path(
        'insights/<uuid:insight_uuid>/delete/',
        views.insight_delete,
        name='insight_delete',
    ),
]
