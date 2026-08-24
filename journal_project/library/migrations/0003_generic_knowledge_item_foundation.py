from typing import Any

from django.db import migrations, models


FORWARD_STATUS_MAP = {
    'want_to_read': 'queued',
    'reading': 'in_progress',
    'finished': 'completed',
    'paused': 'paused',
    'abandoned': 'abandoned',
}

REVERSE_STATUS_MAP = {
    generic_status: legacy_status
    for legacy_status, generic_status in FORWARD_STATUS_MAP.items()
}


def migrate_statuses_forward(apps: Any, _schema_editor: Any) -> None:
    """Convert legacy book statuses to generic consumption statuses."""
    knowledge_item = apps.get_model('library', 'KnowledgeItem')
    for legacy_status, generic_status in FORWARD_STATUS_MAP.items():
        knowledge_item.objects.filter(status=legacy_status).update(
            status=generic_status
        )


def migrate_statuses_backward(apps: Any, _schema_editor: Any) -> None:
    """Restore legacy book statuses when reversing the migration."""
    knowledge_item = apps.get_model('library', 'KnowledgeItem')
    for generic_status, legacy_status in REVERSE_STATUS_MAP.items():
        knowledge_item.objects.filter(status=generic_status).update(
            status=legacy_status
        )


class Migration(migrations.Migration):
    dependencies = [
        ('library', '0002_tag_knowledgeitemtag_knowledgeitem_tags_and_more'),
    ]

    operations = [
        migrations.RunPython(
            migrate_statuses_forward,
            migrate_statuses_backward,
        ),
        migrations.AlterField(
            model_name='knowledgeitem',
            name='status',
            field=models.CharField(
                choices=[
                    ('queued', 'Queued'),
                    ('in_progress', 'In progress'),
                    ('completed', 'Completed'),
                    ('paused', 'Paused'),
                    ('abandoned', 'Abandoned'),
                ],
                default='queued',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='knowledgeitem',
            name='title',
            field=models.CharField(max_length=500),
        ),
        migrations.AlterField(
            model_name='knowledgeitem',
            name='creator',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name='knowledgeitem',
            name='source_url',
            field=models.URLField(blank=True, max_length=2048),
        ),
    ]
