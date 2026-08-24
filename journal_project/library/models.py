import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone


class KnowledgeItem(models.Model):
    class SourceType(models.TextChoices):
        BOOK = 'book', 'Book'
        ARTICLE = 'article', 'Article'
        PODCAST = 'podcast', 'Podcast'
        VIDEO = 'video', 'Video'
        PAPER = 'paper', 'Paper'
        COURSE = 'course', 'Course'
        MISC = 'misc', 'Miscellaneous'

    class Status(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        IN_PROGRESS = 'in_progress', 'In progress'
        COMPLETED = 'completed', 'Completed'
        PAUSED = 'paused', 'Paused'
        ABANDONED = 'abandoned', 'Abandoned'

    STATUS_LABELS_BY_SOURCE = {
        SourceType.BOOK: {
            Status.QUEUED: 'Want to read',
            Status.IN_PROGRESS: 'Reading',
            Status.COMPLETED: 'Finished',
        },
        SourceType.PAPER: {
            Status.QUEUED: 'To read',
            Status.IN_PROGRESS: 'Reading',
            Status.COMPLETED: 'Read',
        },
        SourceType.ARTICLE: {
            Status.QUEUED: 'To read',
            Status.IN_PROGRESS: 'Reading',
            Status.COMPLETED: 'Read',
        },
        SourceType.PODCAST: {
            Status.QUEUED: 'Queue',
            Status.IN_PROGRESS: 'Listening',
            Status.COMPLETED: 'Listened',
        },
    }

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='knowledge_items',
    )
    tags = models.ManyToManyField(
        'Tag',
        through='KnowledgeItemTag',
        related_name='knowledge_items',
        blank=True,
    )
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.BOOK,
    )
    title = models.CharField(max_length=500)
    subtitle = models.CharField(max_length=255, blank=True)
    creator = models.CharField(max_length=1000, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED,
    )
    summary = models.TextField(blank=True)
    source_url = models.URLField(blank=True, max_length=2048)
    date_published = models.DateField(null=True, blank=True)
    date_started = models.DateField(null=True, blank=True)
    date_finished = models.DateField(null=True, blank=True)
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-created_at']
        indexes = [
            models.Index(fields=['user', 'source_type']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'updated_at']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self) -> str:
        """Return the implemented detail URL for this source type."""
        if self.source_type == self.SourceType.BOOK:
            return reverse('library:book_detail', kwargs={'book_uuid': self.uuid})
        if self.source_type == self.SourceType.PAPER:
            return reverse('library:paper_detail', kwargs={'paper_uuid': self.uuid})
        if self.source_type == self.SourceType.ARTICLE:
            return reverse(
                'library:article_detail',
                kwargs={'article_uuid': self.uuid},
            )
        if self.source_type == self.SourceType.PODCAST:
            return reverse(
                'library:podcast_detail',
                kwargs={'podcast_uuid': self.uuid},
            )
        return f"{reverse('library:index')}?source_type={self.source_type}"

    def get_edit_url(self) -> str:
        """Return the edit URL for an implemented source type."""
        route_names = {
            self.SourceType.BOOK: ('library:book_edit', 'book_uuid'),
            self.SourceType.PAPER: ('library:paper_edit', 'paper_uuid'),
            self.SourceType.ARTICLE: ('library:article_edit', 'article_uuid'),
            self.SourceType.PODCAST: ('library:podcast_edit', 'podcast_uuid'),
        }
        route = route_names.get(self.source_type)
        if route is None:
            return ''
        route_name, parameter_name = route
        return reverse(route_name, kwargs={parameter_name: self.uuid})

    def get_delete_url(self) -> str:
        """Return the delete URL for an implemented source type."""
        route_names = {
            self.SourceType.BOOK: ('library:book_delete', 'book_uuid'),
            self.SourceType.PAPER: ('library:paper_delete', 'paper_uuid'),
            self.SourceType.ARTICLE: ('library:article_delete', 'article_uuid'),
            self.SourceType.PODCAST: ('library:podcast_delete', 'podcast_uuid'),
        }
        route = route_names.get(self.source_type)
        if route is None:
            return ''
        route_name, parameter_name = route
        return reverse(route_name, kwargs={parameter_name: self.uuid})

    @classmethod
    def status_label(cls, status: str, source_type: str) -> str:
        """Return the natural display label for a source and stored status."""
        source_labels = cls.STATUS_LABELS_BY_SOURCE.get(source_type, {})
        if status in source_labels:
            return source_labels[status]

        try:
            return cls.Status(status).label
        except ValueError:
            return status.replace('_', ' ').capitalize()

    @classmethod
    def status_choices_for_source(cls, source_type: str) -> list[tuple[str, str]]:
        """Return generic status values paired with source-specific labels."""
        return [
            (status, cls.status_label(status, source_type))
            for status in cls.Status.values
        ]

    def get_status_display(self) -> str:
        """Return this item's source-specific status label."""
        return self.status_label(self.status, self.source_type)

    def clean(self):
        errors = {}
        today = timezone.localdate()

        if not self.title.strip():
            errors['title'] = 'Title is required.'

        if self.date_published and self.date_published > today:
            errors['date_published'] = 'Published date cannot be in the future.'

        if (
            self.date_started
            and self.date_finished
            and self.date_finished < self.date_started
        ):
            errors['date_finished'] = 'Finished date cannot be before started date.'

        if errors:
            raise ValidationError(errors)


class BookDetail(models.Model):
    knowledge_item = models.OneToOneField(
        KnowledgeItem,
        on_delete=models.CASCADE,
        related_name='book_detail',
    )
    author = models.CharField(max_length=255)
    genre = models.CharField(max_length=120, blank=True)
    isbn = models.CharField(max_length=32, blank=True)
    publisher = models.CharField(max_length=255, blank=True)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    publication_date = models.DateField(null=True, blank=True)
    original_language = models.CharField(max_length=80, blank=True)
    edition = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['knowledge_item__title']

    def __str__(self):
        return f'{self.knowledge_item.title} by {self.author}'

    def clean(self):
        errors = {}

        if not self.author.strip():
            errors['author'] = 'Author is required.'

        if (
            self.knowledge_item_id
            and self.knowledge_item.source_type != KnowledgeItem.SourceType.BOOK
        ):
            errors['knowledge_item'] = 'Book details can only attach to book sources.'

        if self.page_count is not None and self.page_count <= 0:
            errors['page_count'] = 'Page count must be positive.'

        if self.publication_date and self.publication_date > timezone.localdate():
            errors['publication_date'] = 'Publication date cannot be in the future.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        updates = {}
        if self.knowledge_item.creator != self.author:
            updates['creator'] = self.author
        if self.knowledge_item.date_published != self.publication_date:
            updates['date_published'] = self.publication_date

        if updates:
            KnowledgeItem.objects.filter(pk=self.knowledge_item_id).update(**updates)
            for field, value in updates.items():
                setattr(self.knowledge_item, field, value)


class PaperDetail(models.Model):
    knowledge_item = models.OneToOneField(
        KnowledgeItem,
        on_delete=models.CASCADE,
        related_name='paper_detail',
    )
    publication_year = models.PositiveIntegerField(null=True, blank=True)
    journal = models.CharField(max_length=500, blank=True)
    doi = models.CharField(max_length=255, blank=True)
    asset_class = models.CharField(max_length=255, blank=True)
    sample_size_data_source = models.TextField(blank=True)
    methodology_research_design = models.TextField(blank=True)
    key_research_question = models.TextField(blank=True)
    key_findings_practical_applications = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['knowledge_item__title']

    def __str__(self) -> str:
        return f'Paper details for {self.knowledge_item.title}'

    def clean(self) -> None:
        errors = {}

        if (
            self.knowledge_item_id
            and self.knowledge_item.source_type != KnowledgeItem.SourceType.PAPER
        ):
            errors['knowledge_item'] = (
                'Paper details can only attach to paper sources.'
            )

        if self.publication_year is not None and self.publication_year <= 0:
            errors['publication_year'] = (
                'Publication year must be positive or left blank.'
            )

        if errors:
            raise ValidationError(errors)


class ArticleDetail(models.Model):
    knowledge_item = models.OneToOneField(
        KnowledgeItem,
        on_delete=models.CASCADE,
        related_name='article_detail',
    )
    publication_name = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['knowledge_item__title']

    def __str__(self) -> str:
        return f'Article details for {self.knowledge_item.title}'

    def clean(self) -> None:
        if (
            self.knowledge_item_id
            and self.knowledge_item.source_type != KnowledgeItem.SourceType.ARTICLE
        ):
            raise ValidationError(
                {
                    'knowledge_item': (
                        'Article details can only attach to article sources.'
                    )
                }
            )


class PodcastEpisodeDetail(models.Model):
    knowledge_item = models.OneToOneField(
        KnowledgeItem,
        on_delete=models.CASCADE,
        related_name='podcast_episode_detail',
    )
    show_name = models.CharField(max_length=500, blank=True)
    guests = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['knowledge_item__title']

    def __str__(self) -> str:
        return f'Podcast episode details for {self.knowledge_item.title}'

    def clean(self) -> None:
        if (
            self.knowledge_item_id
            and self.knowledge_item.source_type != KnowledgeItem.SourceType.PODCAST
        ):
            raise ValidationError(
                {
                    'knowledge_item': (
                        'Podcast episode details can only attach to podcast sources.'
                    )
                }
            )


class Tag(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tags',
    )
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=90)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['user', 'slug'], name='unique_tag_slug_per_user'),
        ]
        indexes = [
            models.Index(fields=['user', 'slug']),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        errors = {}
        name = self.name.strip()

        if not name:
            errors['name'] = 'Name is required.'

        slug = self.slug or slugify(name)
        if not slug:
            errors['slug'] = 'Slug is required.'

        existing = Tag.objects.filter(user=self.user, slug=slug)
        if self.pk:
            existing = existing.exclude(pk=self.pk)
        if self.user_id and slug and existing.exists():
            errors['name'] = 'You already have a tag with this name.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        self.slug = self.slug or slugify(self.name)
        self.full_clean()
        super().save(*args, **kwargs)


class KnowledgeItemTag(models.Model):
    knowledge_item = models.ForeignKey(
        KnowledgeItem,
        on_delete=models.CASCADE,
        related_name='tag_assignments',
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name='item_assignments',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['tag__name']
        constraints = [
            models.UniqueConstraint(
                fields=['knowledge_item', 'tag'],
                name='unique_tag_assignment_per_item',
            ),
        ]

    def __str__(self):
        return f'{self.knowledge_item} tagged {self.tag}'

    def clean(self):
        if (
            self.knowledge_item_id
            and self.tag_id
            and self.knowledge_item.user_id != self.tag.user_id
        ):
            raise ValidationError(
                {'tag': 'Tag must belong to the same user as the knowledge item.'}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
