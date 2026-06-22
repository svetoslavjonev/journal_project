from django.db import transaction

from .models import Insight


@transaction.atomic
def create_insight(*, user, data, source=None):
    knowledge_item = source or data['knowledge_item']
    insight = Insight(
        user=user,
        knowledge_item=knowledge_item,
        insight_type=data['insight_type'],
        title=data.get('title', ''),
        content=data['content'],
        location=data.get('location', ''),
        page_number=data.get('page_number'),
        date_captured=data.get('date_captured'),
        pinned=data.get('pinned', False),
    )
    insight.full_clean()
    insight.save()
    return insight


@transaction.atomic
def update_insight(*, insight, data):
    insight.knowledge_item = data.get('knowledge_item', insight.knowledge_item)
    insight.insight_type = data['insight_type']
    insight.title = data.get('title', '')
    insight.content = data['content']
    insight.location = data.get('location', '')
    insight.page_number = data.get('page_number')
    insight.date_captured = data.get('date_captured')
    insight.pinned = data.get('pinned', False)
    insight.full_clean()
    insight.save()
    return insight


@transaction.atomic
def delete_insight(*, insight):
    insight.delete()
