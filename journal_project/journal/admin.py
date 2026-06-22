from django.contrib import admin

from .models import Insight


@admin.register(Insight)
class InsightAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'insight_type',
        'knowledge_item',
        'user',
        'pinned',
        'archived',
        'created_at',
    )
    list_filter = ('insight_type', 'pinned', 'archived', 'user')
    search_fields = ('title', 'content', 'knowledge_item__title')
    readonly_fields = ('uuid', 'created_at', 'updated_at')
