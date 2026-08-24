from typing import Any

from django.contrib import admin

from .models import (
    ArticleDetail,
    BookDetail,
    KnowledgeItem,
    KnowledgeItemTag,
    PaperDetail,
    PodcastEpisodeDetail,
    Tag,
)


class BookDetailInline(admin.StackedInline):
    model = BookDetail
    extra = 0
    max_num = 1


class PaperDetailInline(admin.StackedInline):
    model = PaperDetail
    extra = 0
    max_num = 1


class ArticleDetailInline(admin.StackedInline):
    model = ArticleDetail
    extra = 0
    max_num = 1


class PodcastEpisodeDetailInline(admin.StackedInline):
    model = PodcastEpisodeDetail
    extra = 0
    max_num = 1


DETAIL_INLINE_BY_SOURCE_TYPE = {
    KnowledgeItem.SourceType.BOOK: BookDetailInline,
    KnowledgeItem.SourceType.PAPER: PaperDetailInline,
    KnowledgeItem.SourceType.ARTICLE: ArticleDetailInline,
    KnowledgeItem.SourceType.PODCAST: PodcastEpisodeDetailInline,
}


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

    def get_inlines(
        self,
        request: Any,
        obj: KnowledgeItem | None = None,
    ) -> list[type[admin.StackedInline]]:
        """Show only the detail inline matching the source type."""
        if obj is None:
            return [BookDetailInline]

        detail_inline = DETAIL_INLINE_BY_SOURCE_TYPE.get(obj.source_type)
        return [detail_inline] if detail_inline else []


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


@admin.register(PaperDetail)
class PaperDetailAdmin(admin.ModelAdmin):
    list_display = (
        'knowledge_item',
        'publication_year',
        'journal',
        'doi',
        'asset_class',
    )
    list_filter = ('publication_year', 'journal', 'asset_class')
    search_fields = (
        'knowledge_item__title',
        'knowledge_item__creator',
        'journal',
        'doi',
        'asset_class',
        'sample_size_data_source',
        'methodology_research_design',
        'key_research_question',
        'key_findings_practical_applications',
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ArticleDetail)
class ArticleDetailAdmin(admin.ModelAdmin):
    list_display = ('knowledge_item', 'publication_name', 'updated_at')
    list_filter = ('publication_name',)
    search_fields = (
        'knowledge_item__title',
        'knowledge_item__creator',
        'publication_name',
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(PodcastEpisodeDetail)
class PodcastEpisodeDetailAdmin(admin.ModelAdmin):
    list_display = ('knowledge_item', 'show_name', 'guests', 'updated_at')
    list_filter = ('show_name',)
    search_fields = (
        'knowledge_item__title',
        'knowledge_item__creator',
        'show_name',
        'guests',
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
