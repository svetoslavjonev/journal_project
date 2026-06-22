import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from journal_project.library.models import KnowledgeItem


class Insight(models.Model):
    class InsightType(models.TextChoices):
        QUOTE = 'quote', 'Quote'
        NOTE = 'note', 'Note'
        IDEA = 'idea', 'Idea'
        QUESTION = 'question', 'Question'
        REFLECTION = 'reflection', 'Reflection'
        SUMMARY = 'summary', 'Summary'

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='insights',
    )
    knowledge_item = models.ForeignKey(
        KnowledgeItem,
        on_delete=models.CASCADE,
        related_name='insights',
    )
    insight_type = models.CharField(max_length=20, choices=InsightType.choices)
    title = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    location = models.CharField(max_length=120, blank=True)
    page_number = models.PositiveIntegerField(null=True, blank=True)
    date_captured = models.DateField(null=True, blank=True)
    pinned = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'insight_type']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['user', 'knowledge_item']),
        ]

    def __str__(self):
        if self.title:
            return self.title
        return f'{self.get_insight_type_display()} for {self.knowledge_item}'

    def clean(self):
        errors = {}

        if not self.content.strip():
            errors['content'] = 'Content is required.'

        if (
            self.user_id
            and self.knowledge_item_id
            and self.knowledge_item.user_id != self.user_id
        ):
            errors['knowledge_item'] = 'Insight source must belong to the same user.'

        if self.page_number is not None and self.page_number <= 0:
            errors['page_number'] = 'Page number must be positive.'

        if errors:
            raise ValidationError(errors)
