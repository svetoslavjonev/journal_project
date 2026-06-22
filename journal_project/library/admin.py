from django.contrib import admin

from .models import BookDetail, KnowledgeItem, KnowledgeItemTag, Tag


class BookDetailInline(admin.StackedInline):
    model = BookDetail
    extra = 0
    max_num = 1


@admin.register(KnowledgeItem)
class KnowledgeItemAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'creator',
        'source_type',
        'status',
        'user',
        'archived',
        'updated_at',
    )
    list_filter = ('source_type', 'status', 'archived', 'user')
    search_fields = ('title', 'subtitle', 'creator', 'summary', 'tags__name')
    readonly_fields = ('uuid', 'created_at', 'updated_at')
    inlines = [BookDetailInline]


@admin.register(BookDetail)
class BookDetailAdmin(admin.ModelAdmin):
    list_display = ('knowledge_item', 'author', 'genre', 'publisher', 'page_count')
    list_filter = ('genre', 'publisher', 'original_language')
    search_fields = (
        'knowledge_item__title',
        'author',
        'genre',
        'isbn',
        'publisher',
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'user', 'created_at')
    list_filter = ('user',)
    search_fields = ('name', 'slug')
    readonly_fields = ('created_at',)


@admin.register(KnowledgeItemTag)
class KnowledgeItemTagAdmin(admin.ModelAdmin):
    list_display = ('knowledge_item', 'tag', 'created_at')
    list_filter = ('tag',)
    search_fields = ('knowledge_item__title', 'tag__name')
    readonly_fields = ('created_at',)
