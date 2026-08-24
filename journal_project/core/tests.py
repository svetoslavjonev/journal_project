from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from journal_project.journal.models import Insight
from journal_project.library.models import (
    ArticleDetail,
    BookDetail,
    KnowledgeItem,
    KnowledgeItemTag,
    PaperDetail,
    PodcastEpisodeDetail,
    Tag,
)


class SearchViewTests(TestCase):
    def setUp(self) -> None:
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='reader',
            password='StrongPass12345',
        )
        self.other_user = user_model.objects.create_user(
            username='other-reader',
            password='StrongPass12345',
        )
        self.book = self.create_source(
            source_type=KnowledgeItem.SourceType.BOOK,
            title='Deep Work',
            creator='Cal Newport',
            summary='A guide to concentrated effort.',
        )
        BookDetail.objects.create(
            knowledge_item=self.book,
            author='Cal Newport',
        )
        self.paper = self.create_source(
            source_type=KnowledgeItem.SourceType.PAPER,
            title='Momentum Crashes',
            creator='Daniel & Moskowitz',
            summary='A factor investing overview.',
        )
        PaperDetail.objects.create(
            knowledge_item=self.paper,
            publication_year=2016,
            key_research_question='When does crashtiming become predictable?',
            key_findings_practical_applications='Drawdownclusters follow rebounds.',
            methodology_research_design='Crosssectional portfolio analysis.',
            sample_size_data_source='CRSPdatabase observations since 1927.',
            asset_class='Globalstocks',
            journal='FinanceReview',
            doi='10.1234/searchable-doi',
        )
        self.article = self.create_source(
            source_type=KnowledgeItem.SourceType.ARTICLE,
            title='Building a Durable Process',
            creator='Alex Researcher',
            summary='A convexityoverview for investors.',
        )
        ArticleDetail.objects.create(
            knowledge_item=self.article,
            publication_name='Research Gazette',
        )
        self.podcast = self.create_source(
            source_type=KnowledgeItem.SourceType.PODCAST,
            title='Building Better Portfolios',
            creator='Jane Host',
            summary='A robustallocation discussion.',
        )
        PodcastEpisodeDetail.objects.create(
            knowledge_item=self.podcast,
            show_name='Capital Allocators',
            guests='Tobias Guest',
        )
        searchable_tag = Tag.objects.create(user=self.user, name='AllocatorTag')
        KnowledgeItemTag.objects.create(
            knowledge_item=self.podcast,
            tag=searchable_tag,
        )
        self.book_insight = Insight.objects.create(
            user=self.user,
            knowledge_item=self.book,
            insight_type=Insight.InsightType.NOTE,
            title='Focus note',
            content='Focused work matters.',
        )

        other_paper = KnowledgeItem.objects.create(
            user=self.other_user,
            source_type=KnowledgeItem.SourceType.PAPER,
            title='Private Other Paper',
            creator='Private Author',
        )
        PaperDetail.objects.create(
            knowledge_item=other_paper,
            key_findings_practical_applications='Privatealpha findings.',
        )
        Insight.objects.create(
            user=self.other_user,
            knowledge_item=other_paper,
            insight_type=Insight.InsightType.NOTE,
            title='Private other note',
            content='Privatealpha insight content.',
        )

    def create_source(
        self,
        *,
        source_type: str,
        title: str,
        creator: str,
        summary: str,
    ) -> KnowledgeItem:
        """Create a user-owned common source record for search tests."""
        return KnowledgeItem.objects.create(
            user=self.user,
            source_type=source_type,
            title=title,
            creator=creator,
            summary=summary,
        )

    def test_anonymous_user_is_redirected_from_search(self) -> None:
        response = self.client.get(reverse('search'))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(reverse('accounts:login')))

    def test_searches_common_fields_across_source_types(self) -> None:
        self.client.force_login(self.user)
        cases = (
            ('Deep Work', self.book),
            ('Daniel', self.paper),
            ('convexityoverview', self.article),
            ('AllocatorTag', self.podcast),
        )

        for query, expected_source in cases:
            with self.subTest(query=query):
                response = self.client.get(reverse('search'), {'q': query})
                self.assertEqual(
                    list(response.context['sources']),
                    [expected_source],
                )

    def test_searches_every_paper_specific_field(self) -> None:
        self.client.force_login(self.user)
        queries = (
            'crashtiming',
            'drawdownclusters',
            'crosssectional',
            'CRSPdatabase',
            'Globalstocks',
            'FinanceReview',
            'searchable-doi',
        )

        for query in queries:
            with self.subTest(query=query):
                response = self.client.get(reverse('search'), {'q': query})
                self.assertEqual(list(response.context['sources']), [self.paper])

    def test_searches_article_publication(self) -> None:
        self.client.force_login(self.user)

        response = self.client.get(reverse('search'), {'q': 'Gazette'})

        self.assertEqual(list(response.context['sources']), [self.article])

    def test_searches_podcast_show_and_guest(self) -> None:
        self.client.force_login(self.user)

        for query in ('Capital Allocators', 'Tobias Guest'):
            with self.subTest(query=query):
                response = self.client.get(reverse('search'), {'q': query})
                self.assertEqual(list(response.context['sources']), [self.podcast])

    def test_source_results_are_grouped_and_identify_each_type(self) -> None:
        shared_tag = Tag.objects.create(user=self.user, name='StageSevenShared')
        for source in (self.book, self.paper, self.article, self.podcast):
            KnowledgeItemTag.objects.create(
                knowledge_item=source,
                tag=shared_tag,
            )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('search'),
            {'q': 'StageSevenShared'},
        )

        self.assertContains(response, '<h2>Sources</h2>', html=True)
        self.assertContains(response, '<h2>Insights</h2>', html=True)
        for source_type in ('BOOK', 'PAPER', 'ARTICLE', 'PODCAST'):
            self.assertContains(response, source_type)
        self.assertContains(response, 'Daniel &amp; Moskowitz · 2016')
        self.assertContains(response, 'Capital Allocators')

    def test_insights_show_their_parent_source(self) -> None:
        self.client.force_login(self.user)

        response = self.client.get(reverse('search'), {'q': 'Deep'})

        self.assertContains(response, 'Focus note')
        self.assertContains(response, 'Book ·')
        self.assertContains(response, self.book.get_absolute_url())

    def test_search_is_isolated_to_authenticated_user(self) -> None:
        self.client.force_login(self.user)

        response = self.client.get(reverse('search'), {'q': 'Privatealpha'})

        self.assertEqual(list(response.context['sources']), [])
        self.assertEqual(list(response.context['insights']), [])
        self.assertNotContains(response, 'Private Other Paper')
        self.assertNotContains(response, 'Private other note')


class DashboardViewTests(TestCase):
    def setUp(self) -> None:
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='dashboard-reader')
        self.other_user = user_model.objects.create_user(username='dashboard-other')
        self.book = self.create_source(
            source_type=KnowledgeItem.SourceType.BOOK,
            title='Current Book',
            status=KnowledgeItem.Status.IN_PROGRESS,
        )
        BookDetail.objects.create(knowledge_item=self.book, author='Book Author')
        self.paper = self.create_source(
            source_type=KnowledgeItem.SourceType.PAPER,
            title='Current Paper',
            status=KnowledgeItem.Status.IN_PROGRESS,
        )
        PaperDetail.objects.create(knowledge_item=self.paper, publication_year=2024)
        self.article = self.create_source(
            source_type=KnowledgeItem.SourceType.ARTICLE,
            title='Queued Article',
            status=KnowledgeItem.Status.QUEUED,
        )
        ArticleDetail.objects.create(
            knowledge_item=self.article,
            publication_name='Example Site',
        )
        self.podcast = self.create_source(
            source_type=KnowledgeItem.SourceType.PODCAST,
            title='Finished Episode',
            status=KnowledgeItem.Status.COMPLETED,
        )
        PodcastEpisodeDetail.objects.create(
            knowledge_item=self.podcast,
            show_name='Example Show',
        )
        self.pinned_insight = Insight.objects.create(
            user=self.user,
            knowledge_item=self.paper,
            insight_type=Insight.InsightType.NOTE,
            title='Pinned finding',
            content='Important.',
            pinned=True,
        )
        Insight.objects.create(
            user=self.user,
            knowledge_item=self.article,
            insight_type=Insight.InsightType.QUESTION,
            title='Open question',
            content='What follows?',
        )
        other_source = KnowledgeItem.objects.create(
            user=self.other_user,
            source_type=KnowledgeItem.SourceType.BOOK,
            title='Private Other Book',
            status=KnowledgeItem.Status.IN_PROGRESS,
        )
        BookDetail.objects.create(
            knowledge_item=other_source,
            author='Private Author',
        )
        Insight.objects.create(
            user=self.other_user,
            knowledge_item=other_source,
            insight_type=Insight.InsightType.NOTE,
            title='Private pinned insight',
            content='Private.',
            pinned=True,
        )

    def create_source(
        self,
        *,
        source_type: str,
        title: str,
        status: str,
    ) -> KnowledgeItem:
        """Create one dashboard source owned by the primary test user."""
        return KnowledgeItem.objects.create(
            user=self.user,
            source_type=source_type,
            title=title,
            creator='Creator',
            status=status,
        )

    def test_dashboard_metrics_include_all_owned_source_types(self) -> None:
        self.client.force_login(self.user)

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.context['source_count'], 4)
        self.assertEqual(response.context['insight_count'], 2)
        self.assertEqual(response.context['in_progress_count'], 2)
        self.assertEqual(response.context['pinned_count'], 1)
        self.assertContains(response, '<span class="stat-label">Sources</span>')
        self.assertContains(response, 'Pinned insights')

    def test_in_progress_sources_work_across_source_types(self) -> None:
        self.client.force_login(self.user)

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(
            set(response.context['in_progress_sources']),
            {self.book, self.paper},
        )
        self.assertContains(response, 'Current Book')
        self.assertContains(response, 'Current Paper')
        self.assertNotContains(response, 'Private Other Book')

    def test_recent_sources_mix_types_and_preserve_ownership(self) -> None:
        self.client.force_login(self.user)

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(
            set(response.context['recent_sources']),
            {self.book, self.paper, self.article, self.podcast},
        )
        for source_type in ('BOOK', 'PAPER', 'ARTICLE', 'PODCAST'):
            self.assertContains(response, source_type)
        self.assertContains(response, '<h2>Recent sources</h2>', html=True)
        self.assertNotContains(response, 'Recent books')

    def test_recent_insights_retain_pinned_insight_behavior(self) -> None:
        self.client.force_login(self.user)

        response = self.client.get(reverse('dashboard'))

        self.assertIn(self.pinned_insight, response.context['recent_insights'])
        self.assertContains(response, 'Pinned finding')
        self.assertNotContains(response, 'Private pinned insight')


class HealthViewTests(TestCase):
    def test_health_endpoint_is_public(self) -> None:
        response = self.client.get(reverse('health'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})
