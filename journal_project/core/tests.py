from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from journal_project.journal.models import Insight
from journal_project.library.models import BookDetail, KnowledgeItem


class SearchViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username='reader',
            password='StrongPass12345',
        )
        self.other_user = User.objects.create_user(
            username='other-reader',
            password='StrongPass12345',
        )
        self.book = self.create_book(user=self.user, title='Deep Work')
        self.other_book = self.create_book(user=self.other_user, title='Private Other Book')
        Insight.objects.create(
            user=self.user,
            knowledge_item=self.book,
            insight_type=Insight.InsightType.NOTE,
            title='Focus note',
            content='Focused work matters.',
        )
        Insight.objects.create(
            user=self.other_user,
            knowledge_item=self.other_book,
            insight_type=Insight.InsightType.NOTE,
            title='Private other note',
            content='Focused private content.',
        )

    def create_book(self, *, user, title):
        book = KnowledgeItem.objects.create(
            user=user,
            source_type=KnowledgeItem.SourceType.BOOK,
            title=title,
            creator='Author',
        )
        BookDetail.objects.create(knowledge_item=book, author='Author')
        return book

    def test_anonymous_user_is_redirected_from_search(self):
        response = self.client.get(reverse('search'))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(reverse('accounts:login')))

    def test_search_returns_user_scoped_books_and_insights(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('search'), {'q': 'Deep'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Deep Work')
        self.assertContains(response, 'Focus note')
        self.assertNotContains(response, 'Private Other Book')
        self.assertNotContains(response, 'Private other note')


class HealthViewTests(TestCase):
    def test_health_endpoint_is_public(self):
        response = self.client.get(reverse('health'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})
