from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from journal_project.journal.models import Insight
from journal_project.library.models import BookDetail, KnowledgeItem, KnowledgeItemTag, Tag

from .forms import InsightForm
from .services import update_insight


class InsightModelTests(TestCase):
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
        self.book = KnowledgeItem.objects.create(
            user=self.user,
            source_type=KnowledgeItem.SourceType.BOOK,
            title='Deep Work',
        )

    def test_insight_creation_links_to_knowledge_item(self):
        insight = Insight.objects.create(
            user=self.user,
            knowledge_item=self.book,
            insight_type=Insight.InsightType.NOTE,
            title='Attention residue',
            content='Task switching carries a real cost.',
            page_number=42,
        )

        self.assertEqual(insight.knowledge_item, self.book)
        self.assertEqual(self.book.insights.get(), insight)
        self.assertEqual(str(insight), 'Attention residue')
        self.assertIsNotNone(insight.uuid)

    def test_insight_rejects_cross_user_knowledge_item(self):
        insight = Insight(
            user=self.other_user,
            knowledge_item=self.book,
            insight_type=Insight.InsightType.NOTE,
            content='This should not attach across users.',
        )

        with self.assertRaises(ValidationError) as error:
            insight.full_clean()

        self.assertIn('knowledge_item', error.exception.message_dict)

    def test_insight_requires_content(self):
        insight = Insight(
            user=self.user,
            knowledge_item=self.book,
            insight_type=Insight.InsightType.NOTE,
            content='',
        )

        with self.assertRaises(ValidationError) as error:
            insight.full_clean()

        self.assertIn('content', error.exception.message_dict)

    def test_insight_rejects_whitespace_only_content(self):
        insight = Insight(
            user=self.user,
            knowledge_item=self.book,
            insight_type=Insight.InsightType.NOTE,
            content='   ',
        )

        with self.assertRaises(ValidationError) as error:
            insight.full_clean()

        self.assertIn('content', error.exception.message_dict)

    def test_insight_rejects_invalid_type(self):
        insight = Insight(
            user=self.user,
            knowledge_item=self.book,
            insight_type='invalid',
            content='Valid content.',
        )

        with self.assertRaises(ValidationError) as error:
            insight.full_clean()

        self.assertIn('insight_type', error.exception.message_dict)

    def test_insight_rejects_non_positive_page_number(self):
        insight = Insight(
            user=self.user,
            knowledge_item=self.book,
            insight_type=Insight.InsightType.QUOTE,
            content='A quote.',
            page_number=0,
        )

        with self.assertRaises(ValidationError) as error:
            insight.full_clean()

        self.assertIn('page_number', error.exception.message_dict)

    def test_deleting_knowledge_item_deletes_insights(self):
        Insight.objects.create(
            user=self.user,
            knowledge_item=self.book,
            insight_type=Insight.InsightType.NOTE,
            content='A note.',
        )

        self.book.delete()

        self.assertEqual(Insight.objects.count(), 0)


class InsightFormTests(TestCase):
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
        self.other_book = self.create_book(user=self.other_user, title='Other Book')

    def create_book(self, *, user, title):
        book = KnowledgeItem.objects.create(
            user=user,
            source_type=KnowledgeItem.SourceType.BOOK,
            title=title,
            creator='Author',
        )
        BookDetail.objects.create(knowledge_item=book, author='Author')
        return book

    def valid_insight_data(self, **overrides):
        data = {
            'knowledge_item': str(self.book.pk),
            'insight_type': Insight.InsightType.NOTE,
            'title': 'Attention residue',
            'content': 'Task switching carries a real cost.',
            'location': 'Chapter 3',
            'page_number': '42',
            'date_captured': '2024-01-15',
            'pinned': 'on',
        }
        data.update(overrides)
        return data

    def test_source_choices_are_limited_to_current_user(self):
        form = InsightForm(user=self.user)

        self.assertIn(self.book, form.fields['knowledge_item'].queryset)
        self.assertNotIn(self.other_book, form.fields['knowledge_item'].queryset)

    def test_cross_user_source_selection_is_invalid(self):
        form = InsightForm(
            self.valid_insight_data(knowledge_item=str(self.other_book.pk)),
            user=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('knowledge_item', form.errors)

    def test_source_bound_form_hides_knowledge_item_field(self):
        form = InsightForm(user=self.user, source=self.book)

        self.assertNotIn('knowledge_item', form.fields)
        self.assertEqual(form.initial['knowledge_item'], self.book)

    def test_insight_form_rejects_invalid_type_and_page_number(self):
        form = InsightForm(
            self.valid_insight_data(insight_type='invalid', page_number='0'),
            user=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('insight_type', form.errors)
        self.assertIn('page_number', form.errors)


class InsightCrudViewTests(TestCase):
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
        self.other_book = self.create_book(user=self.other_user, title='Other Book')

    def create_book(self, *, user, title='Deep Work', author='Cal Newport'):
        book = KnowledgeItem.objects.create(
            user=user,
            source_type=KnowledgeItem.SourceType.BOOK,
            title=title,
            creator=author,
            status=KnowledgeItem.Status.READING,
        )
        BookDetail.objects.create(knowledge_item=book, author=author)
        return book

    def create_insight(
        self,
        *,
        user=None,
        book=None,
        title='Attention residue',
        insight_type=Insight.InsightType.NOTE,
        content='Task switching carries a real cost.',
    ):
        return Insight.objects.create(
            user=user or self.user,
            knowledge_item=book or self.book,
            insight_type=insight_type,
            title=title,
            content=content,
        )

    def valid_insight_data(self, **overrides):
        data = {
            'knowledge_item': str(self.book.pk),
            'insight_type': Insight.InsightType.NOTE,
            'title': 'Attention residue',
            'content': 'Task switching carries a real cost.',
            'location': 'Chapter 3',
            'page_number': '42',
            'date_captured': '2024-01-15',
            'pinned': 'on',
        }
        data.update(overrides)
        return data

    def test_anonymous_users_are_redirected_from_insight_pages(self):
        insight = self.create_insight()
        urls = [
            reverse('journal:insight_list'),
            reverse('journal:insight_create'),
            reverse('library:item_insight_create', kwargs={'item_uuid': self.book.uuid}),
            reverse('journal:insight_edit', kwargs={'insight_uuid': insight.uuid}),
            reverse('journal:insight_delete', kwargs={'insight_uuid': insight.uuid}),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response['Location'].startswith(reverse('accounts:login')))

    def test_insight_list_is_user_scoped(self):
        self.create_insight(title='My private insight')
        self.create_insight(
            user=self.other_user,
            book=self.other_book,
            title='Other private insight',
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('journal:insight_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My private insight')
        self.assertNotContains(response, 'Other private insight')

    def test_insight_list_filters_by_query_type_and_source_type(self):
        self.create_insight(title='Focus note', content='Focused work matters.')
        self.create_insight(
            title='Question',
            insight_type=Insight.InsightType.QUESTION,
            content='What about rest?',
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('journal:insight_list'),
            {
                'q': 'Focused',
                'type': Insight.InsightType.NOTE,
                'source_type': KnowledgeItem.SourceType.BOOK,
            },
        )

        self.assertContains(response, 'Focus note')
        self.assertNotContains(response, 'What about rest?')

    def test_insight_list_filters_by_source_tag(self):
        tagged_book = self.book
        other_book = self.create_book(user=self.user, title='Other Book')
        tag = Tag.objects.create(user=self.user, name='Research')
        KnowledgeItemTag.objects.create(knowledge_item=tagged_book, tag=tag)
        self.create_insight(book=tagged_book, title='Tagged insight')
        self.create_insight(book=other_book, title='Untagged insight')
        self.client.force_login(self.user)

        response = self.client.get(reverse('journal:insight_list'), {'tag': tag.slug})

        self.assertContains(response, 'Tagged insight')
        self.assertNotContains(response, 'Untagged insight')

    def test_create_insight_from_book_page_links_to_book(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('library:item_insight_create', kwargs={'item_uuid': self.book.uuid}),
            {
                'insight_type': Insight.InsightType.QUOTE,
                'title': 'A useful quote',
                'content': 'A quote from the book.',
                'location': '',
                'page_number': '12',
                'date_captured': '',
            },
        )

        insight = Insight.objects.get(title='A useful quote')
        self.assertEqual(insight.user, self.user)
        self.assertEqual(insight.knowledge_item, self.book)
        self.assertRedirects(
            response,
            reverse('library:book_detail', kwargs={'book_uuid': self.book.uuid}),
        )

    def test_create_insight_from_other_users_book_is_blocked(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('library:item_insight_create', kwargs={'item_uuid': self.other_book.uuid}),
            {
                'insight_type': Insight.InsightType.NOTE,
                'content': 'Should not be created.',
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(Insight.objects.filter(content='Should not be created.').exists())

    def test_create_insight_page_for_other_users_book_is_blocked(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('library:item_insight_create', kwargs={'item_uuid': self.other_book.uuid})
        )

        self.assertEqual(response.status_code, 404)

    def test_generic_create_insight_uses_user_scoped_source_choices(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('journal:insight_create'),
            self.valid_insight_data(knowledge_item=str(self.other_book.pk)),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'],
            'knowledge_item',
            'Select a valid choice. That choice is not one of the available choices.',
        )
        self.assertEqual(Insight.objects.count(), 0)

    def test_generic_create_insight_succeeds(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('journal:insight_create'),
            self.valid_insight_data(),
        )

        self.assertRedirects(response, reverse('journal:insight_list'))
        insight = Insight.objects.get(title='Attention residue')
        self.assertEqual(insight.knowledge_item, self.book)
        self.assertTrue(insight.pinned)

    def test_edit_insight_updates_record(self):
        insight = self.create_insight()
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('journal:insight_edit', kwargs={'insight_uuid': insight.uuid}),
            self.valid_insight_data(
                insight_type=Insight.InsightType.REFLECTION,
                title='Updated reflection',
                content='Updated content.',
                page_number='55',
                pinned='',
            ),
        )

        self.assertRedirects(response, reverse('journal:insight_list'))
        insight.refresh_from_db()
        self.assertEqual(insight.insight_type, Insight.InsightType.REFLECTION)
        self.assertEqual(insight.title, 'Updated reflection')
        self.assertEqual(insight.page_number, 55)
        self.assertFalse(insight.pinned)

    def test_edit_insight_page_is_user_scoped(self):
        other_insight = self.create_insight(
            user=self.other_user,
            book=self.other_book,
            title='Other insight',
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('journal:insight_edit', kwargs={'insight_uuid': other_insight.uuid})
        )

        self.assertEqual(response.status_code, 404)

    def test_edit_insight_is_user_scoped(self):
        other_insight = self.create_insight(
            user=self.other_user,
            book=self.other_book,
            title='Other insight',
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('journal:insight_edit', kwargs={'insight_uuid': other_insight.uuid}),
            self.valid_insight_data(title='Changed'),
        )

        self.assertEqual(response.status_code, 404)
        other_insight.refresh_from_db()
        self.assertEqual(other_insight.title, 'Other insight')

    def test_edit_insight_cannot_move_to_other_users_source(self):
        insight = self.create_insight()
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('journal:insight_edit', kwargs={'insight_uuid': insight.uuid}),
            self.valid_insight_data(knowledge_item=str(self.other_book.pk)),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'],
            'knowledge_item',
            'Select a valid choice. That choice is not one of the available choices.',
        )
        insight.refresh_from_db()
        self.assertEqual(insight.knowledge_item, self.book)

    def test_update_insight_service_rejects_cross_user_source(self):
        insight = self.create_insight()

        with self.assertRaises(ValidationError):
            update_insight(
                insight=insight,
                data={
                    'knowledge_item': self.other_book,
                    'insight_type': Insight.InsightType.NOTE,
                    'title': 'Moved',
                    'content': 'Should not move.',
                    'location': '',
                    'page_number': None,
                    'date_captured': None,
                    'pinned': False,
                },
            )

        insight.refresh_from_db()
        self.assertEqual(insight.knowledge_item, self.book)

    def test_delete_insight_confirmation_is_user_scoped(self):
        other_insight = self.create_insight(
            user=self.other_user,
            book=self.other_book,
            title='Other insight',
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('journal:insight_delete', kwargs={'insight_uuid': other_insight.uuid})
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Insight.objects.filter(pk=other_insight.pk).exists())

    def test_delete_insight_does_not_delete_book(self):
        insight = self.create_insight()
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('journal:insight_delete', kwargs={'insight_uuid': insight.uuid})
        )

        self.assertRedirects(response, reverse('journal:insight_list'))
        self.assertEqual(Insight.objects.count(), 0)
        self.assertTrue(KnowledgeItem.objects.filter(pk=self.book.pk).exists())

    def test_delete_insight_is_user_scoped(self):
        other_insight = self.create_insight(
            user=self.other_user,
            book=self.other_book,
            title='Other insight',
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('journal:insight_delete', kwargs={'insight_uuid': other_insight.uuid})
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Insight.objects.filter(pk=other_insight.pk).exists())

    def test_insight_search_does_not_leak_cross_user_matching_results(self):
        self.create_insight(title='Visible note', content='Ordinary content.')
        self.create_insight(
            user=self.other_user,
            book=self.other_book,
            title='Secret note',
            content='Private research content.',
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('journal:insight_list'), {'q': 'Secret'})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Secret note')
        self.assertNotContains(response, 'Visible note')
