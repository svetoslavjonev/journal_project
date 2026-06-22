from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import Insight


def get_user_insights(user):
    return (
        Insight.objects.filter(user=user)
        .select_related('knowledge_item')
        .prefetch_related('knowledge_item__tags')
    )


def filter_user_insights(user, *, query='', insight_type='', source_type='', tag=''):
    insights = get_user_insights(user)

    if query:
        insights = insights.filter(
            Q(title__icontains=query)
            | Q(content__icontains=query)
            | Q(knowledge_item__title__icontains=query)
            | Q(knowledge_item__creator__icontains=query)
        )

    if insight_type:
        insights = insights.filter(insight_type=insight_type)

    if source_type:
        insights = insights.filter(knowledge_item__source_type=source_type)

    if tag:
        insights = insights.filter(
            knowledge_item__tag_assignments__tag__user=user,
            knowledge_item__tag_assignments__tag__slug=tag,
        )

    return insights.distinct()


def get_user_insight(user, insight_uuid):
    return get_object_or_404(get_user_insights(user), uuid=insight_uuid)
