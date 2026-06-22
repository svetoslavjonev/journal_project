"""
URL configuration for journal_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

from journal_project.library import views as library_views

urlpatterns = [
    path('', include('journal_project.core.urls')),
    path('accounts/', include('journal_project.accounts.urls')),
    path('admin/', admin.site.urls),
    path('library/', include('journal_project.library.urls')),
    path('journal/', include('journal_project.journal.urls')),
    path('tags/', library_views.tag_list, name='tag_list'),
    path('tags/<int:tag_id>/delete/', library_views.tag_delete, name='tag_delete'),
]
