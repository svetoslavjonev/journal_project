from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from journal_project.journal.models import Insight

from .forms import BookForm, BookTagForm
from .models import BookDetail, KnowledgeItem, KnowledgeItemTag, Tag
from .services import assign_tag_to_item


class KnowledgeItemModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='reader',
            password='StrongPass12345',
        )

    def test_knowledge_item_creation_defaults(self):
        item = KnowledgeItem.objects.create(
            user=self.user,
            title='Deep Work',
            creator='Cal Newport',
        )

        self.assertEqual(item.source_type, KnowledgeItem.SourceType.BOOK)
        self.assertEqual(item.status, KnowledgeItem.Status.QUEUED)
        self.assertFalse(item.archived)
        self.assertEqual(str(item), 'Deep Work')
        self.assertIsNotNone(item.uuid)

    def test_status_values_are_generic(self):
        self.assertEqual(
            KnowledgeItem.Status.values,
            ['queued', 'in_progress', 'completed', 'paused', 'abandoned'],
        )

    def test_status_display_labels_are_source_specific(self):
        expected_labels = {
            KnowledgeItem.SourceType.BOOK: [
                'Want to read',
                'Reading',
                'Finished',
                'Paused',
                'Abandoned',
            ],
            KnowledgeItem.SourceType.PAPER: [
                'To read',
                'Reading',
                'Read',
                'Paused',
                'Abandoned',
            ],
            KnowledgeItem.SourceType.ARTICLE: [
                'To read',
                'Reading',
                'Read',
                'Paused',
                'Abandoned',
            ],
            KnowledgeItem.SourceType.PODCAST: [
                'Queue',
                'Listening',
                'Listened',
                'Paused',
                'Abandoned',
            ],
        }

        for source_type, labels in expected_labels.items():
            with self.subTest(source_type=source_type):
                choices = KnowledgeItem.status_choices_for_source(source_type)
                self.assertEqual(
                    choices,
                    list(zip(KnowledgeItem.Status.values, labels, strict=True)),
                )

                for status, label in choices:
                    item = KnowledgeItem(
                        user=self.user,
                        source_type=source_type,
                        title='Source',
                        status=status,
                    )
                    self.assertEqual(item.get_status_display(), label)

    def test_unmapped_source_type_uses_generic_status_labels(self):
        item = KnowledgeItem(
            user=self.user,
            source_type=KnowledgeItem.SourceType.VIDEO,
            title='Lecture',
            status=KnowledgeItem.Status.IN_PROGRESS,
        )

        self.assertEqual(item.get_status_display(), 'In progress')

    def test_common_fields_accept_extended_values(self):
        title = 'T' * 500
        creator = 'C' * 1000
        source_url = f"https://example.com/{'a' * 1900}"
        item = KnowledgeItem(
            user=self.user,
            source_type=KnowledgeItem.SourceType.PAPER,
            title=title,
            creator=creator,
            source_url=source_url,
        )

        item.full_clean()
        item.save()
        item.refresh_from_db()

        self.assertEqual(item.title, title)
        self.assertEqual(item.creator, creator)
        self.assertEqual(item.source_url, source_url)

    def test_knowledge_item_rejects_future_published_date(self):
        item = KnowledgeItem(
            user=self.user,
            title='Future Book',
            date_published=timezone.localdate() + timedelta(days=1),
        )

        with self.assertRaises(ValidationError) as error:
            item.full_clean()

        self.assertIn('date_published', error.exception.message_dict)

    def test_knowledge_item_rejects_blank_title(self):
        item = KnowledgeItem(user=self.user, title='   ')

        with self.assertRaises(ValidationError) as error:
            item.full_clean()

        self.assertIn('title', error.exception.message_dict)

    def test_knowledge_item_rejects_finished_before_started(self):
        item = KnowledgeItem(
            user=self.user,
            title='Backwards Reading',
            date_started=timezone.localdate(),
            date_finished=timezone.localdate() - timedelta(days=1),
        )

        with self.assertRaises(ValidationError) as error:
            item.full_clean()

        self.assertIn('date_finished', error.exception.message_dict)


class BookDetailModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='reader',
            password='StrongPass12345',
        )
        self.book = KnowledgeItem.objects.create(
            user=self.user,
            source_type=KnowledgeItem.SourceType.BOOK,
            title='Deep Work',
        )

    def test_book_detail_attaches_to_book_knowledge_item(self):
        detail = BookDetail.objects.create(
            knowledge_item=self.book,
            author='Cal Newport',
            genre='Productivity',
            page_count=304,
        )

        self.assertEqual(detail.knowledge_item, self.book)
        self.assertEqual(self.book.book_detail, detail)
        self.assertEqual(str(detail), 'Deep Work by Cal Newport')

    def test_book_detail_rejects_non_book_knowledge_item(self):
        article = KnowledgeItem.objects.create(
            user=self.user,
            source_type=KnowledgeItem.SourceType.ARTICLE,
            title='A Useful Essay',
        )
        detail = BookDetail(knowledge_item=article, author='Author')

        with self.assertRaises(ValidationError) as error:
            detail.full_clean()

        self.assertIn('knowledge_item', error.exception.message_dict)

    def test_book_detail_rejects_blank_author(self):
        detail = BookDetail(knowledge_item=self.book, author='   ')

        with self.assertRaises(ValidationError) as error:
            detail.full_clean()

        self.assertIn('author', error.exception.message_dict)

    def test_book_detail_rejects_non_positive_page_count(self):
        detail = BookDetail(
            knowledge_item=self.book,
            author='Cal Newport',
            page_count=0,
        )

        with self.assertRaises(ValidationError) as error:
            detail.full_clean()

        self.assertIn('page_count', error.exception.message_dict)

    def test_book_detail_rejects_future_publication_date(self):
        detail = BookDetail(
            knowledge_item=self.book,
            author='Cal Newport',
            publication_date=timezone.localdate() + timedelta(days=1),
        )

        with self.assertRaises(ValidationError) as error:
            detail.full_clean()

        self.assertIn('publication_date', error.exception.message_dict)

    def test_book_detail_is_one_to_one_with_knowledge_item(self):
        BookDetail.objects.create(knowledge_item=self.book, author='Cal Newport')

        with self.assertRaises(IntegrityError):
            BookDetail.objects.create(knowledge_item=self.book, author='Duplicate')

    def test_book_detail_syncs_creator_and_publication_date_to_knowledge_item(self):
        publication_date = timezone.localdate() - timedelta(days=365)

        BookDetail.objects.create(
            knowledge_item=self.book,
            author='Cal Newport',
            publication_date=publication_date,
        )

        self.book.refresh_from_db()
        self.assertEqual(self.book.creator, 'Cal Newport')
        self.assertEqual(self.book.date_published, publication_date)


class TagModelTests(TestCase):
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

    def test_tag_sets_slug_and_is_user_scoped(self):
        tag = Tag.objects.create(user=self.user, name='Deep Focus')
        other_tag = Tag.objects.create(user=self.other_user, name='Deep Focus')

        self.assertEqual(tag.slug, 'deep-focus')
        self.assertEqual(other_tag.slug, 'deep-focus')
        self.assertEqual(str(tag), 'Deep Focus')

    def test_tag_rejects_duplicate_slug_for_same_user(self):
        Tag.objects.create(user=self.user, name='Deep Focus')

        with self.assertRaises(ValidationError):
            Tag.objects.create(user=self.user, name='Deep Focus')

    def test_knowledge_item_tag_requires_same_user(self):
        tag = Tag.objects.create(user=self.other_user, name='Other Tag')
        assignment = KnowledgeItemTag(knowledge_item=self.book, tag=tag)

        with self.assertRaises(ValidationError) as error:
            assignment.full_clean()

        self.assertIn('tag', error.exception.message_dict)

    def test_knowledge_item_tag_attaches_tag_to_item(self):
        tag = Tag.objects.create(user=self.user, name='Focus')

        KnowledgeItemTag.objects.create(knowledge_item=self.book, tag=tag)

        self.assertEqual(list(self.book.tags.all()), [tag])

    def test_assign_tag_service_rejects_cross_user_tag(self):
        tag = Tag.objects.create(user=self.other_user, name='Other Tag')

        with self.assertRaises(ValidationError):
            assign_tag_to_item(knowledge_item=self.book, tag=tag)

        self.assertFalse(KnowledgeItemTag.objects.exists())


class BookFormTests(TestCase):
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
            creator='Cal Newport',
            status=KnowledgeItem.Status.IN_PROGRESS,
        )
        BookDetail.objects.create(
            knowledge_item=self.book,
            author='Cal Newport',
            genre='Productivity',
            page_count=304,
        )

    def valid_book_data(self, **overrides):
        data = {
            'title': 'Deep Work',
            'author': 'Cal Newport',
            'status': KnowledgeItem.Status.IN_PROGRESS,
            'genre': 'Productivity',
            'date_published': '2016-01-05',
            'summary': 'A book about focused work.',
            'subtitle': '',
            'source_url': '',
            'isbn': '9781455586691',
            'publisher': 'Grand Central Publishing',
            'page_count': '304',
            'original_language': 'English',
            'edition': 'Hardcover',
            'metadata': '{"shelf": "work"}',
        }
        data.update(overrides)
        return data

    def test_book_form_accepts_valid_book_data(self):
        form = BookForm(self.valid_book_data())

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['metadata'], {'shelf': 'work'})

    def test_book_form_uses_book_status_labels_with_generic_values(self):
        choices = dict(BookForm().fields['status'].choices)

        self.assertEqual(choices[KnowledgeItem.Status.QUEUED], 'Want to read')
        self.assertEqual(choices[KnowledgeItem.Status.IN_PROGRESS], 'Reading')
        self.assertEqual(choices[KnowledgeItem.Status.COMPLETED], 'Finished')
        self.assertNotIn('want_to_read', choices)

    def test_book_form_rejects_invalid_status(self):
        form = BookForm(self.valid_book_data(status='not-a-status'))

        self.assertFalse(form.is_valid())
        self.assertIn('status', form.errors)

    def test_book_form_rejects_future_publication_date(self):
        form = BookForm(
            self.valid_book_data(
                date_published=str(timezone.localdate() + timedelta(days=1))
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn('date_published', form.errors)

    def test_book_form_loads_existing_book_initial_values(self):
        form = BookForm(knowledge_item=self.book)

        self.assertEqual(form.initial['title'], 'Deep Work')
        self.assertEqual(form.initial['author'], 'Cal Newport')
        self.assertEqual(form.initial['genre'], 'Productivity')
        self.assertEqual(form.initial['page_count'], 304)


class BookTagFormTests(TestCase):
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
        self.user_tag = Tag.objects.create(user=self.user, name='Research')
        self.other_tag = Tag.objects.create(user=self.other_user, name='Private Tag')

    def test_tag_choices_are_limited_to_current_user(self):
        form = BookTagForm(user=self.user)

        self.assertIn(self.user_tag, form.fields['tag'].queryset)
        self.assertNotIn(self.other_tag, form.fields['tag'].queryset)

    def test_cross_user_tag_selection_is_invalid(self):
        form = BookTagForm({'tag': str(self.other_tag.pk)}, user=self.user)

        self.assertFalse(form.is_valid())
        self.assertIn('tag', form.errors)

    def test_requires_existing_or_new_tag(self):
        form = BookTagForm({}, user=self.user)

        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)


class BookCrudViewTests(TestCase):
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

    def create_book(self, *, user, title='Deep Work', author='Cal Newport'):
        book = KnowledgeItem.objects.create(
            user=user,
            source_type=KnowledgeItem.SourceType.BOOK,
            title=title,
            creator=author,
            status=KnowledgeItem.Status.IN_PROGRESS,
        )
        BookDetail.objects.create(
            knowledge_item=book,
            author=author,
            genre='Productivity',
            page_count=304,
        )
        return book

    def valid_book_data(self, **overrides):
        data = {
            'title': 'Deep Work',
            'author': 'Cal Newport',
            'status': KnowledgeItem.Status.IN_PROGRESS,
            'genre': 'Productivity',
            'date_published': '2016-01-05',
            'summary': 'A book about focused work.',
            'subtitle': '',
            'source_url': '',
            'isbn': '9781455586691',
            'publisher': 'Grand Central Publishing',
            'page_count': '304',
            'original_language': 'English',
            'edition': 'Hardcover',
            'metadata': '{"shelf": "work"}',
        }
        data.update(overrides)
        return data

    def test_anonymous_users_are_redirected_from_book_pages(self):
        book = self.create_book(user=self.user)
        urls = [
            reverse('library:book_list'),
            reverse('library:book_create'),
            reverse('library:book_detail', kwargs={'book_uuid': book.uuid}),
            reverse('library:book_edit', kwargs={'book_uuid': book.uuid}),
            reverse('library:book_delete', kwargs={'book_uuid': book.uuid}),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response['Location'].startswith(reverse('accounts:login')))

    def test_book_list_is_user_scoped(self):
        self.create_book(user=self.user, title='Deep Work')
        self.create_book(user=self.other_user, title='Private Other Book')
        self.client.force_login(self.user)

        response = self.client.get(reverse('library:book_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Deep Work')
        self.assertNotContains(response, 'Private Other Book')

    def test_book_list_filters_by_query_status_and_genre(self):
        self.create_book(user=self.user, title='Deep Work')
        self.create_book(user=self.user, title='A Novel', author='Novelist')
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('library:book_list'),
            {
                'q': 'Cal',
                'status': KnowledgeItem.Status.IN_PROGRESS,
                'genre': 'Productivity',
            },
        )

        self.assertContains(response, 'Deep Work')
        self.assertNotContains(response, 'A Novel')

    def test_book_list_filters_by_tag(self):
        tagged_book = self.create_book(user=self.user, title='Tagged Book')
        untagged_book = self.create_book(user=self.user, title='Untagged Book')
        tag = Tag.objects.create(user=self.user, name='Research')
        KnowledgeItemTag.objects.create(knowledge_item=tagged_book, tag=tag)
        self.client.force_login(self.user)

        response = self.client.get(reverse('library:book_list'), {'tag': tag.slug})

        self.assertContains(response, 'Tagged Book')
        self.assertNotContains(response, 'Untagged Book')

    def test_create_book_creates_knowledge_item_and_book_detail(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('library:book_create'), self.valid_book_data())

        book = KnowledgeItem.objects.get(user=self.user, title='Deep Work')
        self.assertRedirects(
            response,
            reverse('library:book_detail', kwargs={'book_uuid': book.uuid}),
        )
        self.assertEqual(book.source_type, KnowledgeItem.SourceType.BOOK)
        self.assertEqual(book.creator, 'Cal Newport')
        self.assertEqual(book.book_detail.author, 'Cal Newport')
        self.assertEqual(book.book_detail.metadata, {'shelf': 'work'})

    def test_create_book_shows_errors_for_invalid_data(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('library:book_create'),
            self.valid_book_data(author='', page_count='0'),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'author', 'This field is required.')
        self.assertEqual(KnowledgeItem.objects.count(), 0)

    def test_book_detail_is_user_scoped(self):
        other_book = self.create_book(user=self.other_user)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('library:book_detail', kwargs={'book_uuid': other_book.uuid})
        )

        self.assertEqual(response.status_code, 404)

    def test_edit_book_page_is_user_scoped(self):
        other_book = self.create_book(user=self.other_user)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('library:book_edit', kwargs={'book_uuid': other_book.uuid})
        )

        self.assertEqual(response.status_code, 404)

    def test_edit_book_updates_knowledge_item_and_book_detail(self):
        book = self.create_book(user=self.user)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('library:book_edit', kwargs={'book_uuid': book.uuid}),
            self.valid_book_data(
                title='Deep Work Updated',
                author='C. Newport',
                genre='Focus',
                page_count='320',
            ),
        )

        self.assertRedirects(
            response,
            reverse('library:book_detail', kwargs={'book_uuid': book.uuid}),
        )
        book.refresh_from_db()
        book.book_detail.refresh_from_db()
        self.assertEqual(book.title, 'Deep Work Updated')
        self.assertEqual(book.creator, 'C. Newport')
        self.assertEqual(book.book_detail.author, 'C. Newport')
        self.assertEqual(book.book_detail.genre, 'Focus')
        self.assertEqual(book.book_detail.page_count, 320)

    def test_edit_book_is_user_scoped(self):
        other_book = self.create_book(user=self.other_user, title='Other Book')
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('library:book_edit', kwargs={'book_uuid': other_book.uuid}),
            self.valid_book_data(title='Changed'),
        )

        self.assertEqual(response.status_code, 404)
        other_book.refresh_from_db()
        self.assertEqual(other_book.title, 'Other Book')

    def test_delete_book_confirmation_is_user_scoped(self):
        other_book = self.create_book(user=self.other_user)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('library:book_delete', kwargs={'book_uuid': other_book.uuid})
        )

        self.assertEqual(response.status_code, 404)

    def test_delete_book_removes_book_detail_and_insights(self):
        book = self.create_book(user=self.user)
        Insight.objects.create(
            user=self.user,
            knowledge_item=book,
            insight_type=Insight.InsightType.NOTE,
            content='A note.',
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('library:book_delete', kwargs={'book_uuid': book.uuid})
        )

        self.assertRedirects(response, reverse('library:book_list'))
        self.assertEqual(KnowledgeItem.objects.count(), 0)
        self.assertEqual(BookDetail.objects.count(), 0)
        self.assertEqual(Insight.objects.count(), 0)

    def test_delete_book_is_user_scoped(self):
        other_book = self.create_book(user=self.other_user, title='Other Book')
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('library:book_delete', kwargs={'book_uuid': other_book.uuid})
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(KnowledgeItem.objects.filter(pk=other_book.pk).exists())

    def test_book_search_does_not_leak_cross_user_matching_results(self):
        self.create_book(user=self.user, title='Visible Book', author='Author')
        self.create_book(user=self.other_user, title='Secret Research', author='Author')
        self.client.force_login(self.user)

        response = self.client.get(reverse('library:book_list'), {'q': 'Secret'})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Secret Research')
        self.assertNotContains(response, 'Visible Book')


class TagViewTests(TestCase):
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
            creator='Cal Newport',
        )
        BookDetail.objects.create(knowledge_item=self.book, author='Cal Newport')

    def test_anonymous_users_are_redirected_from_tags(self):
        response = self.client.get(reverse('tag_list'))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(reverse('accounts:login')))

    def test_tag_list_is_user_scoped_and_can_create_tag(self):
        Tag.objects.create(user=self.other_user, name='Private Other Tag')
        self.client.force_login(self.user)

        response = self.client.post(reverse('tag_list'), {'name': 'Research'}, follow=True)

        self.assertContains(response, 'Research')
        self.assertNotContains(response, 'Private Other Tag')
        self.assertTrue(Tag.objects.filter(user=self.user, slug='research').exists())

    def test_delete_tag_removes_assignments_not_books(self):
        tag = Tag.objects.create(user=self.user, name='Research')
        KnowledgeItemTag.objects.create(knowledge_item=self.book, tag=tag)
        self.client.force_login(self.user)

        response = self.client.post(reverse('tag_delete', kwargs={'tag_id': tag.id}))

        self.assertRedirects(response, reverse('tag_list'))
        self.assertFalse(Tag.objects.filter(pk=tag.pk).exists())
        self.assertTrue(KnowledgeItem.objects.filter(pk=self.book.pk).exists())

    def test_delete_tag_is_user_scoped(self):
        other_tag = Tag.objects.create(user=self.other_user, name='Other Tag')
        self.client.force_login(self.user)

        response = self.client.post(reverse('tag_delete', kwargs={'tag_id': other_tag.id}))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Tag.objects.filter(pk=other_tag.pk).exists())

    def test_delete_tag_confirmation_is_user_scoped(self):
        other_tag = Tag.objects.create(user=self.other_user, name='Other Tag')
        self.client.force_login(self.user)

        response = self.client.get(reverse('tag_delete', kwargs={'tag_id': other_tag.id}))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Tag.objects.filter(pk=other_tag.pk).exists())

    def test_add_new_tag_to_book(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('library:book_tag_add', kwargs={'book_uuid': self.book.uuid}),
            {'new_tag': 'Research'},
        )

        self.assertRedirects(
            response,
            reverse('library:book_detail', kwargs={'book_uuid': self.book.uuid}),
        )
        self.assertTrue(self.book.tags.filter(slug='research').exists())

    def test_add_existing_tag_to_book(self):
        tag = Tag.objects.create(user=self.user, name='Research')
        self.client.force_login(self.user)

        self.client.post(
            reverse('library:book_tag_add', kwargs={'book_uuid': self.book.uuid}),
            {'tag': str(tag.pk)},
        )

        self.assertTrue(self.book.tags.filter(pk=tag.pk).exists())

    def test_cannot_add_other_users_tag_to_book(self):
        other_tag = Tag.objects.create(user=self.other_user, name='Other Tag')
        self.client.force_login(self.user)

        self.client.post(
            reverse('library:book_tag_add', kwargs={'book_uuid': self.book.uuid}),
            {'tag': str(other_tag.pk)},
        )

        self.assertFalse(self.book.tags.filter(pk=other_tag.pk).exists())

    def test_cannot_add_tag_to_other_users_book(self):
        other_book = KnowledgeItem.objects.create(
            user=self.other_user,
            source_type=KnowledgeItem.SourceType.BOOK,
            title='Other Book',
        )
        BookDetail.objects.create(knowledge_item=other_book, author='Other Author')
        tag = Tag.objects.create(user=self.user, name='Research')
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('library:book_tag_add', kwargs={'book_uuid': other_book.uuid}),
            {'tag': str(tag.pk)},
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(other_book.tags.filter(pk=tag.pk).exists())

    def test_cannot_remove_other_users_tag_from_book(self):
        other_tag = Tag.objects.create(user=self.other_user, name='Other Tag')
        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                'library:book_tag_remove',
                kwargs={'book_uuid': self.book.uuid, 'tag_id': other_tag.id},
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(KnowledgeItem.objects.filter(pk=self.book.pk).exists())

    def test_remove_tag_from_book(self):
        tag = Tag.objects.create(user=self.user, name='Research')
        KnowledgeItemTag.objects.create(knowledge_item=self.book, tag=tag)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                'library:book_tag_remove',
                kwargs={'book_uuid': self.book.uuid, 'tag_id': tag.id},
            )
        )

        self.assertRedirects(
            response,
            reverse('library:book_detail', kwargs={'book_uuid': self.book.uuid}),
        )
        self.assertFalse(self.book.tags.filter(pk=tag.pk).exists())


from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .admin import (
    ArticleDetailInline,
    BookDetailInline,
    PaperDetailInline,
    PodcastEpisodeDetailInline,
)
from .models import (
    ArticleDetail,
    KnowledgeItem,
    PaperDetail,
    PodcastEpisodeDetail,
)


class SourceDetailModelTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(username='reader')
        self.book = self.create_item(KnowledgeItem.SourceType.BOOK, 'A Book')
        self.paper = self.create_item(
            KnowledgeItem.SourceType.PAPER,
            'Value and Momentum Everywhere',
        )
        self.article = self.create_item(
            KnowledgeItem.SourceType.ARTICLE,
            'The Case Against Market Timing',
        )
        self.podcast = self.create_item(
            KnowledgeItem.SourceType.PODCAST,
            'How Markets Become Efficient',
        )

    def create_item(self, source_type: str, title: str) -> KnowledgeItem:
        return KnowledgeItem.objects.create(
            user=self.user,
            source_type=source_type,
            title=title,
        )

    def test_paper_detail_creation(self) -> None:
        detail = PaperDetail(
            knowledge_item=self.paper,
            publication_year=2013,
            journal='Journal of Finance',
            doi='10.1111/jofi.12021',
            asset_class='Global equities',
            sample_size_data_source='Eight markets from 1972 to 2011.',
            methodology_research_design='Cross-sectional factor portfolios.',
            key_research_question='Do value and momentum effects persist?',
            key_findings_practical_applications='The effects complement each other.',
        )

        detail.full_clean()
        detail.save()

        self.assertEqual(self.paper.paper_detail, detail)
        self.assertEqual(detail.knowledge_item.user, self.user)
        self.assertEqual(detail.publication_year, 2013)
        self.assertEqual(
            str(detail),
            'Paper details for Value and Momentum Everywhere',
        )

    def test_article_detail_creation(self) -> None:
        detail = ArticleDetail(
            knowledge_item=self.article,
            publication_name='Financial Times',
        )

        detail.full_clean()
        detail.save()

        self.assertEqual(self.article.article_detail, detail)
        self.assertEqual(detail.knowledge_item.user, self.user)
        self.assertEqual(detail.publication_name, 'Financial Times')
        self.assertEqual(
            str(detail),
            'Article details for The Case Against Market Timing',
        )

    def test_podcast_episode_detail_creation(self) -> None:
        detail = PodcastEpisodeDetail(
            knowledge_item=self.podcast,
            show_name='The Investors Podcast',
            guests='Jane Smith; John Doe',
        )

        detail.full_clean()
        detail.save()

        self.assertEqual(self.podcast.podcast_episode_detail, detail)
        self.assertEqual(detail.knowledge_item.user, self.user)
        self.assertEqual(detail.show_name, 'The Investors Podcast')
        self.assertEqual(
            str(detail),
            'Podcast episode details for How Markets Become Efficient',
        )

    def test_all_source_specific_fields_are_optional(self) -> None:
        details = (
            PaperDetail(knowledge_item=self.paper),
            ArticleDetail(knowledge_item=self.article),
            PodcastEpisodeDetail(knowledge_item=self.podcast),
        )

        for detail in details:
            with self.subTest(detail_type=type(detail).__name__):
                detail.full_clean()
                detail.save()

        self.assertIsNone(details[0].publication_year)
        self.assertEqual(details[0].journal, '')
        self.assertEqual(details[1].publication_name, '')
        self.assertEqual(details[2].show_name, '')
        self.assertEqual(details[2].guests, '')

    def test_details_reject_wrong_source_types(self) -> None:
        invalid_details = (
            PaperDetail(knowledge_item=self.book),
            ArticleDetail(knowledge_item=self.book),
            PodcastEpisodeDetail(knowledge_item=self.book),
        )

        for detail in invalid_details:
            with self.subTest(detail_type=type(detail).__name__):
                with self.assertRaises(ValidationError) as error:
                    detail.full_clean()

                self.assertIn('knowledge_item', error.exception.message_dict)

    def test_each_detail_relationship_is_one_to_one(self) -> None:
        detail_models_and_items = (
            (PaperDetail, self.paper),
            (ArticleDetail, self.article),
            (PodcastEpisodeDetail, self.podcast),
        )

        for detail_model, knowledge_item in detail_models_and_items:
            with self.subTest(detail_type=detail_model.__name__):
                detail_model.objects.create(knowledge_item=knowledge_item)

                with self.assertRaises(IntegrityError), transaction.atomic():
                    detail_model.objects.create(knowledge_item=knowledge_item)

    def test_paper_publication_year_zero_is_rejected(self) -> None:
        detail = PaperDetail(
            knowledge_item=self.paper,
            publication_year=0,
        )

        with self.assertRaises(ValidationError) as error:
            detail.full_clean()

        self.assertIn('publication_year', error.exception.message_dict)


class SourceDetailAdminTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(username='admin-reader')

    def test_new_detail_models_are_registered(self) -> None:
        self.assertTrue(admin.site.is_registered(PaperDetail))
        self.assertTrue(admin.site.is_registered(ArticleDetail))
        self.assertTrue(admin.site.is_registered(PodcastEpisodeDetail))

    def test_knowledge_item_admin_uses_source_specific_inline(self) -> None:
        knowledge_item_admin = admin.site._registry[KnowledgeItem]
        expected_inlines = {
            KnowledgeItem.SourceType.BOOK: BookDetailInline,
            KnowledgeItem.SourceType.PAPER: PaperDetailInline,
            KnowledgeItem.SourceType.ARTICLE: ArticleDetailInline,
            KnowledgeItem.SourceType.PODCAST: PodcastEpisodeDetailInline,
        }

        for source_type, expected_inline in expected_inlines.items():
            item = KnowledgeItem.objects.create(
                user=self.user,
                source_type=source_type,
                title=f'{source_type} source',
            )
            with self.subTest(source_type=source_type):
                self.assertEqual(
                    knowledge_item_admin.get_inlines(request=None, obj=item),
                    [expected_inline],
                )

from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import TestCase
from django.urls import reverse

from .models import (
    ArticleDetail,
    BookDetail,
    KnowledgeItem,
    KnowledgeItemTag,
    PaperDetail,
    PodcastEpisodeDetail,
    Tag,
)
from .selectors import (
    filter_user_knowledge_items,
    get_user_knowledge_item,
    get_user_knowledge_items,
)
from .services import (
    archive_knowledge_item,
    create_knowledge_item,
    update_knowledge_item,
)


class GenericKnowledgeItemSelectorTests(TestCase):
    def setUp(self) -> None:
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='reader')
        self.other_user = user_model.objects.create_user(username='other-reader')
        self.book = KnowledgeItem.objects.create(
            user=self.user,
            source_type=KnowledgeItem.SourceType.BOOK,
            title='Deep Work',
            creator='Cal Newport',
            status=KnowledgeItem.Status.IN_PROGRESS,
        )
        self.paper = KnowledgeItem.objects.create(
            user=self.user,
            source_type=KnowledgeItem.SourceType.PAPER,
            title='Value and Momentum Everywhere',
            creator='Asness, Moskowitz, and Pedersen',
            status=KnowledgeItem.Status.QUEUED,
            summary='Research on value and momentum effects.',
        )
        self.other_item = KnowledgeItem.objects.create(
            user=self.other_user,
            source_type=KnowledgeItem.SourceType.PAPER,
            title='Private Research',
        )
        self.tag = Tag.objects.create(user=self.user, name='Research')
        KnowledgeItemTag.objects.create(knowledge_item=self.paper, tag=self.tag)

    def test_generic_items_are_scoped_to_user(self) -> None:
        self.assertEqual(
            set(get_user_knowledge_items(self.user)),
            {self.book, self.paper},
        )
        self.assertNotIn(self.other_item, get_user_knowledge_items(self.user))

    def test_generic_filter_combines_common_source_fields(self) -> None:
        results = filter_user_knowledge_items(
            self.user,
            query='Moskowitz',
            source_type=KnowledgeItem.SourceType.PAPER,
            status=KnowledgeItem.Status.QUEUED,
            tag=self.tag.slug,
        )

        self.assertEqual(list(results), [self.paper])

    def test_generic_item_lookup_rejects_other_users_item(self) -> None:
        with self.assertRaises(Http404):
            get_user_knowledge_item(self.user, self.other_item.uuid)


class GenericKnowledgeItemServiceTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(username='reader')

    def test_create_knowledge_item_stores_common_source_fields(self) -> None:
        item = create_knowledge_item(
            user=self.user,
            source_type=KnowledgeItem.SourceType.ARTICLE,
            data={
                'title': 'A Useful Article',
                'creator': 'Jane Smith',
                'status': KnowledgeItem.Status.QUEUED,
                'summary': 'A concise source summary.',
                'source_url': 'https://example.com/article',
            },
        )

        self.assertEqual(item.user, self.user)
        self.assertEqual(item.source_type, KnowledgeItem.SourceType.ARTICLE)
        self.assertEqual(item.title, 'A Useful Article')
        self.assertEqual(item.status, KnowledgeItem.Status.QUEUED)

    def test_update_and_archive_use_common_knowledge_item_operations(self) -> None:
        item = create_knowledge_item(
            user=self.user,
            source_type=KnowledgeItem.SourceType.PAPER,
            data={
                'title': 'Draft Title',
                'status': KnowledgeItem.Status.QUEUED,
            },
        )

        update_knowledge_item(
            knowledge_item=item,
            data={
                'title': 'Final Title',
                'status': KnowledgeItem.Status.COMPLETED,
                'source_type': KnowledgeItem.SourceType.BOOK,
            },
        )
        archive_knowledge_item(knowledge_item=item)
        item.refresh_from_db()

        self.assertEqual(item.title, 'Final Title')
        self.assertEqual(item.status, KnowledgeItem.Status.COMPLETED)
        self.assertEqual(item.source_type, KnowledgeItem.SourceType.PAPER)
        self.assertTrue(item.archived)


class GenericLibraryViewTests(TestCase):
    def setUp(self) -> None:
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='reader')
        self.other_user = user_model.objects.create_user(username='other-reader')
        self.book = KnowledgeItem.objects.create(
            user=self.user,
            source_type=KnowledgeItem.SourceType.BOOK,
            title='Deep Work',
            creator='Cal Newport',
            status=KnowledgeItem.Status.IN_PROGRESS,
        )
        BookDetail.objects.create(
            knowledge_item=self.book,
            author='Cal Newport',
            genre='Productivity',
        )
        self.paper = KnowledgeItem.objects.create(
            user=self.user,
            source_type=KnowledgeItem.SourceType.PAPER,
            title='Value and Momentum Everywhere',
            creator='Asness, Moskowitz, and Pedersen',
            status=KnowledgeItem.Status.QUEUED,
        )
        KnowledgeItem.objects.create(
            user=self.other_user,
            source_type=KnowledgeItem.SourceType.ARTICLE,
            title='Private Other Article',
        )
        self.tag = Tag.objects.create(user=self.user, name='Research')
        KnowledgeItemTag.objects.create(knowledge_item=self.paper, tag=self.tag)

    def test_anonymous_user_is_redirected_from_library(self) -> None:
        response = self.client.get(reverse('library:index'))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(reverse('accounts:login')))

    def test_library_lists_user_sources_with_generic_cards(self) -> None:
        self.client.force_login(self.user)

        response = self.client.get(reverse('library:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Deep Work')
        self.assertContains(response, 'Value and Momentum Everywhere')
        self.assertContains(response, 'Reading')
        self.assertContains(response, 'To read')
        self.assertContains(response, 'Research')
        self.assertNotContains(response, 'Private Other Article')

    def test_library_filters_by_source_type(self) -> None:
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('library:index'),
            {'source_type': KnowledgeItem.SourceType.PAPER},
        )

        self.assertContains(response, 'Value and Momentum Everywhere')
        self.assertNotContains(response, 'Deep Work')
        self.assertContains(response, 'aria-current="page"', html=False)

    def test_library_tabs_link_all_supported_source_formats(self) -> None:
        self.client.force_login(self.user)

        response = self.client.get(reverse('library:index'))

        expected_tabs = {
            'All': reverse('library:index'),
            'Books': reverse('library:book_list'),
            'Papers': reverse('library:paper_list'),
            'Articles': reverse('library:article_list'),
            'Podcasts': reverse('library:podcast_list'),
        }
        for label, url in expected_tabs.items():
            with self.subTest(label=label):
                self.assertContains(response, f'href="{url}"')
                self.assertContains(response, f'>{label}</a>')

    def test_library_filters_by_query_status_and_tag(self) -> None:
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('library:index'),
            {
                'q': 'Moskowitz',
                'status': KnowledgeItem.Status.QUEUED,
                'tag': self.tag.slug,
            },
        )

        self.assertContains(response, 'Value and Momentum Everywhere')
        self.assertNotContains(response, 'Deep Work')

    def test_empty_source_tab_uses_source_specific_status_labels(self) -> None:
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('library:index'),
            {'source_type': KnowledgeItem.SourceType.PODCAST},
        )

        self.assertContains(response, 'No sources found')
        self.assertContains(response, 'Listening')
        self.assertContains(response, 'Listened')

    def test_primary_navigation_links_to_library(self) -> None:
        self.client.force_login(self.user)

        response = self.client.get(reverse('library:index'))
        html = response.content.decode()
        primary_nav = html.split('<nav id="primary-nav"', 1)[1].split('</nav>', 1)[0]

        self.assertIn(f'href="{reverse("library:index")}">Library</a>', primary_nav)
        self.assertNotIn('>Books</a>', primary_nav)

    def test_existing_book_library_remains_available(self) -> None:
        self.client.force_login(self.user)

        response = self.client.get(reverse('library:book_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Deep Work')
        self.assertNotContains(response, 'Value and Momentum Everywhere')


class LibraryViewModeTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(username='view-reader')
        self.book = self.create_source(
            KnowledgeItem.SourceType.BOOK,
            'A Very Long Book Title That Should Wrap Without Truncation',
        )
        BookDetail.objects.create(
            knowledge_item=self.book,
            author='Book Author',
            genre='Investing',
        )
        self.paper = self.create_source(
            KnowledgeItem.SourceType.PAPER,
            'A Research Paper',
        )
        PaperDetail.objects.create(
            knowledge_item=self.paper,
            publication_year=2024,
            asset_class='Equities',
        )
        self.article = self.create_source(
            KnowledgeItem.SourceType.ARTICLE,
            'A Useful Article',
        )
        ArticleDetail.objects.create(
            knowledge_item=self.article,
            publication_name='Example Journal',
        )
        self.podcast = self.create_source(
            KnowledgeItem.SourceType.PODCAST,
            'A Podcast Episode',
        )
        PodcastEpisodeDetail.objects.create(
            knowledge_item=self.podcast,
            show_name='Example Show',
        )
        self.client.force_login(self.user)

    def create_source(self, source_type: str, title: str) -> KnowledgeItem:
        """Create one source for shared grid/list rendering tests."""
        return KnowledgeItem.objects.create(
            user=self.user,
            source_type=source_type,
            title=title,
            creator='Source Creator',
        )

    def test_every_library_page_offers_grid_and_list_views(self) -> None:
        urls = (
            reverse('library:index'),
            reverse('library:book_list'),
            reverse('library:paper_list'),
            reverse('library:article_list'),
            reverse('library:podcast_list'),
        )

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'data-library-collection')
                self.assertContains(response, 'data-library-view-button="grid"')
                self.assertContains(response, 'data-library-view-button="list"')
                self.assertContains(response, 'data-library-view-panel="grid"')
                self.assertContains(response, 'data-library-view-panel="list"')

    def test_list_view_contains_aligned_actions_for_every_source(self) -> None:
        response = self.client.get(reverse('library:index'))

        self.assertContains(response, 'class="source-row-actions"', count=4)
        for source in (self.book, self.paper, self.article, self.podcast):
            with self.subTest(source_type=source.source_type):
                self.assertContains(response, source.get_edit_url())
                self.assertContains(response, source.get_delete_url())

    def test_grid_and_list_views_render_long_titles_in_full(self) -> None:
        response = self.client.get(reverse('library:book_list'))

        self.assertContains(response, self.book.title, count=2)

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from journal_project.journal.models import Insight

from .forms import PaperForm
from .models import KnowledgeItem, KnowledgeItemTag, PaperDetail, Tag
from .selectors import filter_user_papers
from .services import create_paper, update_paper


def valid_paper_data(**overrides: str) -> dict[str, str]:
    """Return complete valid POST data for the manual paper form."""
    data = {
        'title': 'Value and Momentum Everywhere',
        'authors': 'Asness, Moskowitz, and Pedersen',
        'publication_year': '2013',
        'status': KnowledgeItem.Status.QUEUED,
        'key_research_question': 'Do value and momentum effects persist?',
        'key_findings_practical_applications': (
            'Value and momentum effects complement each other.'
        ),
        'methodology_research_design': 'Cross-sectional factor portfolios.',
        'sample_size_data_source': 'Eight markets from 1972 to 2011.',
        'asset_class': 'Global equities',
        'summary': 'A useful framework for combining factors.',
        'journal': 'Journal of Finance',
        'doi': '10.1111/jofi.12021',
        'source_url': 'https://example.com/value-momentum',
    }
    data.update(overrides)
    return data


class PaperFormTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(username='reader')
        self.paper = KnowledgeItem.objects.create(
            user=self.user,
            source_type=KnowledgeItem.SourceType.PAPER,
            title='Existing Paper',
            creator='Existing Authors',
            status=KnowledgeItem.Status.COMPLETED,
            summary='Existing summary.',
            source_url='https://example.com/existing',
        )
        PaperDetail.objects.create(
            knowledge_item=self.paper,
            publication_year=2020,
            journal='Existing Journal',
            asset_class='Fixed income',
        )

    def test_paper_form_accepts_valid_data_and_uses_paper_status_labels(self) -> None:
        form = PaperForm(valid_paper_data())
        choices = dict(form.fields['status'].choices)

        self.assertTrue(form.is_valid())
        self.assertEqual(choices[KnowledgeItem.Status.QUEUED], 'To read')
        self.assertEqual(choices[KnowledgeItem.Status.COMPLETED], 'Read')

    def test_paper_form_rejects_zero_publication_year(self) -> None:
        form = PaperForm(valid_paper_data(publication_year='0'))

        self.assertFalse(form.is_valid())
        self.assertIn('publication_year', form.errors)

    def test_paper_form_loads_common_and_detail_initial_values(self) -> None:
        form = PaperForm(paper=self.paper)

        self.assertEqual(form.initial['title'], 'Existing Paper')
        self.assertEqual(form.initial['authors'], 'Existing Authors')
        self.assertEqual(form.initial['publication_year'], 2020)
        self.assertEqual(form.initial['journal'], 'Existing Journal')
        self.assertEqual(form.initial['asset_class'], 'Fixed income')


class PaperServiceTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(username='reader')

    def test_create_paper_rolls_back_common_record_when_detail_is_invalid(self) -> None:
        data = valid_paper_data()
        data['publication_year'] = 0

        with self.assertRaises(ValidationError):
            create_paper(user=self.user, data=data)

        self.assertFalse(KnowledgeItem.objects.exists())
        self.assertFalse(PaperDetail.objects.exists())

    def test_update_paper_rolls_back_when_detail_record_is_missing(self) -> None:
        paper = KnowledgeItem.objects.create(
            user=self.user,
            source_type=KnowledgeItem.SourceType.PAPER,
            title='Original Title',
        )

        with self.assertRaises(ValidationError):
            update_paper(
                paper=paper,
                data=valid_paper_data(title='Changed Title'),
            )

        paper.refresh_from_db()
        self.assertEqual(paper.title, 'Original Title')


class PaperSelectorTests(TestCase):
    def test_paper_filters_are_user_scoped_and_source_specific(self) -> None:
        user_model = get_user_model()
        user = user_model.objects.create_user(username='reader')
        other_user = user_model.objects.create_user(username='other-reader')
        matching = self.create_paper_for_user(
            user,
            title='Momentum Paper',
            year=2013,
            asset_class='Global equities',
        )
        self.create_paper_for_user(
            user,
            title='Bond Paper',
            year=2020,
            asset_class='Fixed income',
        )
        self.create_paper_for_user(
            other_user,
            title='Private Momentum Paper',
            year=2013,
            asset_class='Global equities',
        )

        results = filter_user_papers(
            user,
            query='Momentum',
            publication_year='2013',
            asset_class='equities',
        )

        self.assertEqual(list(results), [matching])
        self.assertEqual(
            list(filter_user_papers(user, publication_year=2013)),
            [matching],
        )
        self.assertFalse(
            filter_user_papers(user, publication_year='not-a-year').exists()
        )

    @staticmethod
    def create_paper_for_user(
        user,
        *,
        title: str,
        year: int,
        asset_class: str,
    ) -> KnowledgeItem:
        paper = KnowledgeItem.objects.create(
            user=user,
            source_type=KnowledgeItem.SourceType.PAPER,
            title=title,
            creator='Research Authors',
        )
        PaperDetail.objects.create(
            knowledge_item=paper,
            publication_year=year,
            asset_class=asset_class,
        )
        return paper


class PaperCrudViewTests(TestCase):
    def setUp(self) -> None:
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='reader')
        self.other_user = user_model.objects.create_user(username='other-reader')
        self.paper = self.create_paper_for_user(self.user)
        self.other_paper = self.create_paper_for_user(
            self.other_user,
            title='Private Other Paper',
        )

    def create_paper_for_user(
        self,
        user,
        *,
        title: str = 'Value and Momentum Everywhere',
        year: int = 2013,
        asset_class: str = 'Global equities',
    ) -> KnowledgeItem:
        paper = KnowledgeItem.objects.create(
            user=user,
            source_type=KnowledgeItem.SourceType.PAPER,
            title=title,
            creator='Asness, Moskowitz, and Pedersen',
            status=KnowledgeItem.Status.QUEUED,
            summary='A practical factor framework.',
        )
        PaperDetail.objects.create(
            knowledge_item=paper,
            publication_year=year,
            journal='Journal of Finance',
            doi='10.1111/jofi.12021',
            asset_class=asset_class,
            sample_size_data_source='Eight global markets.',
            methodology_research_design='Cross-sectional portfolios.',
            key_research_question='Do the effects persist?',
            key_findings_practical_applications='The effects complement each other.',
        )
        return paper

    def test_anonymous_users_are_redirected_from_paper_pages(self) -> None:
        urls = (
            reverse('library:paper_list'),
            reverse('library:paper_create'),
            reverse('library:paper_detail', args=[self.paper.uuid]),
            reverse('library:paper_edit', args=[self.paper.uuid]),
            reverse('library:paper_delete', args=[self.paper.uuid]),
        )

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response['Location'].startswith(reverse('accounts:login')))

    def test_paper_list_is_user_scoped_and_cards_are_concise(self) -> None:
        tag = Tag.objects.create(user=self.user, name='Momentum')
        KnowledgeItemTag.objects.create(knowledge_item=self.paper, tag=tag)
        self.client.force_login(self.user)

        response = self.client.get(reverse('library:paper_list'))

        self.assertContains(response, self.paper.title)
        self.assertContains(response, 'Asness, Moskowitz, and Pedersen · 2013')
        self.assertContains(response, 'To read')
        self.assertContains(response, 'Momentum')
        self.assertNotContains(response, 'Private Other Paper')
        self.assertNotContains(response, 'The effects complement each other.')

    def test_create_paper_creates_common_and_detail_records(self) -> None:
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('library:paper_create'),
            valid_paper_data(title='New Research Paper'),
        )

        paper = KnowledgeItem.objects.get(user=self.user, title='New Research Paper')
        self.assertRedirects(response, paper.get_absolute_url())
        self.assertEqual(paper.source_type, KnowledgeItem.SourceType.PAPER)
        self.assertEqual(paper.creator, 'Asness, Moskowitz, and Pedersen')
        self.assertEqual(paper.paper_detail.publication_year, 2013)
        self.assertEqual(paper.paper_detail.asset_class, 'Global equities')

    def test_paper_detail_prioritizes_analysis_and_shared_content(self) -> None:
        tag = Tag.objects.create(user=self.user, name='Research')
        KnowledgeItemTag.objects.create(knowledge_item=self.paper, tag=tag)
        Insight.objects.create(
            user=self.user,
            knowledge_item=self.paper,
            insight_type=Insight.InsightType.NOTE,
            title='Factor interaction',
            content='Value and momentum diversify each other.',
        )
        self.client.force_login(self.user)

        response = self.client.get(self.paper.get_absolute_url())

        self.assertContains(response, 'Research Question')
        self.assertContains(response, 'Key Findings &amp; Practical Applications')
        self.assertContains(response, 'The effects complement each other.')
        self.assertContains(response, 'A practical factor framework.')
        self.assertContains(response, 'Research')
        self.assertContains(response, 'Factor interaction')

    def test_edit_paper_updates_common_and_detail_fields(self) -> None:
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('library:paper_edit', args=[self.paper.uuid]),
            valid_paper_data(
                title='Updated Paper',
                authors='Updated Authors',
                publication_year='2014',
                asset_class='Commodities',
                status=KnowledgeItem.Status.COMPLETED,
            ),
        )

        self.assertRedirects(response, self.paper.get_absolute_url())
        self.paper.refresh_from_db()
        self.paper.paper_detail.refresh_from_db()
        self.assertEqual(self.paper.title, 'Updated Paper')
        self.assertEqual(self.paper.creator, 'Updated Authors')
        self.assertEqual(self.paper.status, KnowledgeItem.Status.COMPLETED)
        self.assertEqual(self.paper.paper_detail.publication_year, 2014)
        self.assertEqual(self.paper.paper_detail.asset_class, 'Commodities')

    def test_paper_list_filters_by_author_year_asset_status_and_tag(self) -> None:
        self.create_paper_for_user(
            self.user,
            title='Other Research',
            year=2020,
            asset_class='Fixed income',
        )
        tag = Tag.objects.create(user=self.user, name='Momentum')
        KnowledgeItemTag.objects.create(knowledge_item=self.paper, tag=tag)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('library:paper_list'),
            {
                'q': 'Moskowitz',
                'year': '2013',
                'asset_class': 'equities',
                'status': KnowledgeItem.Status.QUEUED,
                'tag': tag.slug,
            },
        )

        self.assertContains(response, self.paper.title)
        self.assertNotContains(response, 'Other Research')

    def test_paper_views_reject_wrong_user_access(self) -> None:
        self.client.force_login(self.user)
        urls = (
            reverse('library:paper_detail', args=[self.other_paper.uuid]),
            reverse('library:paper_edit', args=[self.other_paper.uuid]),
            reverse('library:paper_delete', args=[self.other_paper.uuid]),
        )

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(
                    self.client.post(url, valid_paper_data()).status_code,
                    404,
                )

        self.other_paper.refresh_from_db()
        self.assertEqual(self.other_paper.title, 'Private Other Paper')

    def test_delete_paper_removes_detail_and_insights(self) -> None:
        insight = Insight.objects.create(
            user=self.user,
            knowledge_item=self.paper,
            insight_type=Insight.InsightType.NOTE,
            content='A paper insight.',
        )
        paper_pk = self.paper.pk
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('library:paper_delete', args=[self.paper.uuid])
        )

        self.assertRedirects(response, reverse('library:paper_list'))
        self.assertFalse(KnowledgeItem.objects.filter(pk=paper_pk).exists())
        self.assertFalse(PaperDetail.objects.filter(knowledge_item_id=paper_pk).exists())
        self.assertFalse(Insight.objects.filter(pk=insight.pk).exists())

    def test_paper_uses_shared_tag_workflow_with_user_isolation(self) -> None:
        other_tag = Tag.objects.create(user=self.other_user, name='Private Tag')
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('library:item_tag_add', args=[self.paper.uuid]),
            {'new_tag': 'Research'},
        )

        self.assertRedirects(response, self.paper.get_absolute_url())
        tag = self.paper.tags.get(slug='research')

        self.client.post(
            reverse('library:item_tag_add', args=[self.paper.uuid]),
            {'tag': str(other_tag.pk)},
        )
        self.assertFalse(self.paper.tags.filter(pk=other_tag.pk).exists())

        response = self.client.post(
            reverse('library:item_tag_remove', args=[self.paper.uuid, tag.pk])
        )
        self.assertRedirects(response, self.paper.get_absolute_url())
        self.assertFalse(self.paper.tags.filter(pk=tag.pk).exists())

    def test_paper_uses_shared_insight_workflow_and_return_url(self) -> None:
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('library:item_insight_create', args=[self.paper.uuid]),
            {
                'insight_type': Insight.InsightType.NOTE,
                'title': 'Paper note',
                'content': 'A reusable paper insight.',
                'location': '',
                'page_number': '',
                'date_captured': '',
            },
        )

        self.assertRedirects(response, self.paper.get_absolute_url())
        insight = Insight.objects.get(title='Paper note')
        self.assertEqual(insight.knowledge_item, self.paper)

        detail_response = self.client.get(self.paper.get_absolute_url())
        self.assertContains(detail_response, 'Paper note')

        list_response = self.client.get(reverse('journal:insight_list'))
        self.assertContains(list_response, f'href="{self.paper.get_absolute_url()}"')

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from journal_project.journal.models import Insight

from .forms import ArticleForm, PodcastEpisodeForm
from .models import (
    ArticleDetail,
    KnowledgeItem,
    PodcastEpisodeDetail,
)
from .selectors import filter_user_articles, filter_user_podcast_episodes
from .services import update_article, update_podcast_episode


def valid_article_data(**overrides: str) -> dict[str, str]:
    """Return valid POST data for the manual article form."""
    data = {
        'title': 'How to Build a Durable Investment Process',
        'authors': 'Alex Researcher',
        'publication_date': '2024-05-04',
        'source_url': 'https://example.com/durable-process',
        'status': KnowledgeItem.Status.QUEUED,
        'summary': 'A practical framework for repeatable decisions.',
        'publication_name': 'The Quantitative Investor',
    }
    data.update(overrides)
    return data


def valid_podcast_data(**overrides: str) -> dict[str, str]:
    """Return valid POST data for the manual podcast episode form."""
    data = {
        'episode_title': 'Building Better Portfolios',
        'show_name': 'Capital Allocators',
        'hosts': 'Jane Host',
        'guests': 'Sam Investor',
        'status': KnowledgeItem.Status.QUEUED,
        'summary': 'A discussion of robust allocation choices.',
        'source_url': 'https://example.com/portfolio-podcast',
    }
    data.update(overrides)
    return data


class ArticlePodcastFormTests(TestCase):
    def test_forms_use_source_specific_status_labels(self) -> None:
        article_form = ArticleForm(valid_article_data())
        podcast_form = PodcastEpisodeForm(valid_podcast_data())

        self.assertTrue(article_form.is_valid())
        self.assertTrue(podcast_form.is_valid())
        self.assertEqual(
            dict(article_form.fields['status'].choices)[KnowledgeItem.Status.QUEUED],
            'To read',
        )
        self.assertEqual(
            dict(podcast_form.fields['status'].choices)[KnowledgeItem.Status.QUEUED],
            'Queue',
        )
        self.assertEqual(
            dict(podcast_form.fields['status'].choices)[
                KnowledgeItem.Status.COMPLETED
            ],
            'Listened',
        )

    def test_article_form_rejects_future_publication_date(self) -> None:
        future_date = timezone.localdate() + timedelta(days=1)
        form = ArticleForm(
            valid_article_data(publication_date=future_date.isoformat())
        )

        self.assertFalse(form.is_valid())
        self.assertIn('publication_date', form.errors)

    def test_forms_load_common_and_detail_initial_values(self) -> None:
        user = get_user_model().objects.create_user(username='reader')
        article = create_article_for_user(user)
        podcast = create_podcast_for_user(user)

        article_form = ArticleForm(article=article)
        podcast_form = PodcastEpisodeForm(podcast=podcast)

        self.assertEqual(article_form.initial['authors'], 'Alex Researcher')
        self.assertEqual(
            article_form.initial['publication_name'],
            'The Quantitative Investor',
        )
        self.assertEqual(podcast_form.initial['episode_title'], podcast.title)
        self.assertEqual(podcast_form.initial['show_name'], 'Capital Allocators')
        self.assertEqual(podcast_form.initial['guests'], 'Sam Investor')


class ArticlePodcastServiceTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(username='reader')

    def test_article_update_rolls_back_without_detail_record(self) -> None:
        article = KnowledgeItem.objects.create(
            user=self.user,
            source_type=KnowledgeItem.SourceType.ARTICLE,
            title='Original article',
        )

        with self.assertRaises(ValidationError):
            update_article(
                article=article,
                data=valid_article_data(title='Changed article'),
            )

        article.refresh_from_db()
        self.assertEqual(article.title, 'Original article')

    def test_podcast_update_rolls_back_without_detail_record(self) -> None:
        podcast = KnowledgeItem.objects.create(
            user=self.user,
            source_type=KnowledgeItem.SourceType.PODCAST,
            title='Original episode',
        )

        with self.assertRaises(ValidationError):
            update_podcast_episode(
                podcast=podcast,
                data=valid_podcast_data(episode_title='Changed episode'),
            )

        podcast.refresh_from_db()
        self.assertEqual(podcast.title, 'Original episode')


class ArticlePodcastSelectorTests(TestCase):
    def test_source_filters_are_user_scoped_and_source_specific(self) -> None:
        user_model = get_user_model()
        user = user_model.objects.create_user(username='reader')
        other_user = user_model.objects.create_user(username='other-reader')
        article = create_article_for_user(user)
        podcast = create_podcast_for_user(user)
        create_article_for_user(other_user, title='Private durable process')
        create_podcast_for_user(other_user, title='Private portfolio episode')

        articles = filter_user_articles(
            user,
            query='Alex',
            publication_name='Quantitative',
            status=KnowledgeItem.Status.QUEUED,
        )
        podcasts = filter_user_podcast_episodes(
            user,
            query='Sam Investor',
            show_name='Capital',
            status=KnowledgeItem.Status.QUEUED,
        )

        self.assertEqual(list(articles), [article])
        self.assertEqual(list(podcasts), [podcast])


class ArticlePodcastCrudViewTests(TestCase):
    def setUp(self) -> None:
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='reader')
        self.other_user = user_model.objects.create_user(username='other-reader')
        self.article = create_article_for_user(self.user)
        self.podcast = create_podcast_for_user(self.user)
        self.other_article = create_article_for_user(
            self.other_user,
            title='Private article',
        )
        self.other_podcast = create_podcast_for_user(
            self.other_user,
            title='Private episode',
        )

    def test_anonymous_users_are_redirected_from_stage_five_pages(self) -> None:
        urls = (
            reverse('library:article_list'),
            reverse('library:article_create'),
            self.article.get_absolute_url(),
            reverse('library:article_edit', args=[self.article.uuid]),
            reverse('library:article_delete', args=[self.article.uuid]),
            reverse('library:podcast_list'),
            reverse('library:podcast_create'),
            self.podcast.get_absolute_url(),
            reverse('library:podcast_edit', args=[self.podcast.uuid]),
            reverse('library:podcast_delete', args=[self.podcast.uuid]),
        )

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(
                    response['Location'].startswith(reverse('accounts:login'))
                )

    def test_lists_show_source_labels_and_filter_owned_items(self) -> None:
        self.client.force_login(self.user)

        article_response = self.client.get(
            reverse('library:article_list'),
            {
                'q': 'Alex',
                'publication': 'Quantitative',
                'status': KnowledgeItem.Status.QUEUED,
            },
        )
        podcast_response = self.client.get(
            reverse('library:podcast_list'),
            {
                'q': 'Sam Investor',
                'show': 'Capital',
                'status': KnowledgeItem.Status.QUEUED,
            },
        )

        self.assertContains(article_response, self.article.title)
        self.assertContains(article_response, 'To read')
        self.assertNotContains(article_response, self.other_article.title)
        self.assertContains(podcast_response, self.podcast.title)
        self.assertContains(podcast_response, 'Queue')
        self.assertNotContains(podcast_response, self.other_podcast.title)

    def test_create_article_and_podcast_store_common_and_detail_fields(self) -> None:
        self.client.force_login(self.user)

        article_response = self.client.post(
            reverse('library:article_create'),
            valid_article_data(title='New article'),
        )
        podcast_response = self.client.post(
            reverse('library:podcast_create'),
            valid_podcast_data(episode_title='New episode'),
        )

        article = KnowledgeItem.objects.get(user=self.user, title='New article')
        podcast = KnowledgeItem.objects.get(user=self.user, title='New episode')
        self.assertRedirects(article_response, article.get_absolute_url())
        self.assertRedirects(podcast_response, podcast.get_absolute_url())
        self.assertEqual(article.creator, 'Alex Researcher')
        self.assertEqual(article.date_published, date(2024, 5, 4))
        self.assertEqual(
            article.article_detail.publication_name,
            'The Quantitative Investor',
        )
        self.assertEqual(podcast.creator, 'Jane Host')
        self.assertEqual(podcast.podcast_episode_detail.show_name, 'Capital Allocators')
        self.assertEqual(podcast.podcast_episode_detail.guests, 'Sam Investor')

    def test_detail_pages_show_required_fields(self) -> None:
        self.client.force_login(self.user)

        article_response = self.client.get(self.article.get_absolute_url())
        podcast_response = self.client.get(self.podcast.get_absolute_url())

        for content in (
            self.article.title,
            'Alex Researcher',
            'The Quantitative Investor',
            '4 May 2024',
            'To read',
            'A practical framework for repeatable decisions.',
            'Tags',
            'Recent insights',
        ):
            self.assertContains(article_response, content)
        for content in (
            self.podcast.title,
            'Capital Allocators',
            'Jane Host',
            'Sam Investor',
            'Queue',
            'A discussion of robust allocation choices.',
            'Tags',
            'Recent insights',
        ):
            self.assertContains(podcast_response, content)

    def test_edit_article_and_podcast_updates_both_records(self) -> None:
        self.client.force_login(self.user)

        article_response = self.client.post(
            reverse('library:article_edit', args=[self.article.uuid]),
            valid_article_data(
                title='Updated article',
                authors='Updated Author',
                publication_name='Updated Site',
                status=KnowledgeItem.Status.COMPLETED,
            ),
        )
        podcast_response = self.client.post(
            reverse('library:podcast_edit', args=[self.podcast.uuid]),
            valid_podcast_data(
                episode_title='Updated episode',
                show_name='Updated Show',
                hosts='Updated Host',
                guests='Updated Guest',
                status=KnowledgeItem.Status.COMPLETED,
            ),
        )

        self.assertRedirects(article_response, self.article.get_absolute_url())
        self.assertRedirects(podcast_response, self.podcast.get_absolute_url())
        self.article.refresh_from_db()
        self.podcast.refresh_from_db()
        self.article.article_detail.refresh_from_db()
        self.podcast.podcast_episode_detail.refresh_from_db()
        self.assertEqual(self.article.title, 'Updated article')
        self.assertEqual(self.article.creator, 'Updated Author')
        self.assertEqual(self.article.article_detail.publication_name, 'Updated Site')
        self.assertEqual(self.article.get_status_display(), 'Read')
        self.assertEqual(self.podcast.title, 'Updated episode')
        self.assertEqual(self.podcast.creator, 'Updated Host')
        self.assertEqual(
            self.podcast.podcast_episode_detail.show_name,
            'Updated Show',
        )
        self.assertEqual(self.podcast.get_status_display(), 'Listened')

    def test_wrong_user_cannot_view_edit_or_delete_sources(self) -> None:
        self.client.force_login(self.user)
        urls = (
            self.other_article.get_absolute_url(),
            reverse('library:article_edit', args=[self.other_article.uuid]),
            reverse('library:article_delete', args=[self.other_article.uuid]),
            self.other_podcast.get_absolute_url(),
            reverse('library:podcast_edit', args=[self.other_podcast.uuid]),
            reverse('library:podcast_delete', args=[self.other_podcast.uuid]),
        )

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(self.client.post(url, {}).status_code, 404)

    def test_both_sources_use_shared_tags_and_insights(self) -> None:
        self.client.force_login(self.user)

        for item in (self.article, self.podcast):
            with self.subTest(source_type=item.source_type):
                tag_response = self.client.post(
                    reverse('library:item_tag_add', args=[item.uuid]),
                    {'new_tag': f'{item.source_type} notes'},
                )
                insight_response = self.client.post(
                    reverse('library:item_insight_create', args=[item.uuid]),
                    {
                        'insight_type': Insight.InsightType.NOTE,
                        'title': f'{item.source_type} insight',
                        'content': 'A reusable observation.',
                        'location': '',
                        'page_number': '',
                        'date_captured': '',
                    },
                )

                self.assertRedirects(tag_response, item.get_absolute_url())
                self.assertRedirects(insight_response, item.get_absolute_url())
                detail_response = self.client.get(item.get_absolute_url())
                self.assertContains(detail_response, f'{item.source_type} notes')
                self.assertContains(detail_response, f'{item.source_type} insight')

    def test_generic_library_filters_and_links_both_source_types(self) -> None:
        self.client.force_login(self.user)

        article_response = self.client.get(
            reverse('library:index'),
            {'source_type': KnowledgeItem.SourceType.ARTICLE, 'q': 'Durable'},
        )
        podcast_response = self.client.get(
            reverse('library:index'),
            {'source_type': KnowledgeItem.SourceType.PODCAST, 'q': 'Portfolios'},
        )

        self.assertContains(article_response, self.article.get_absolute_url())
        self.assertNotContains(article_response, self.podcast.title)
        self.assertContains(podcast_response, self.podcast.get_absolute_url())
        self.assertNotContains(podcast_response, self.article.title)

    def test_delete_article_and_podcast_cascades_details_and_insights(self) -> None:
        article_insight = Insight.objects.create(
            user=self.user,
            knowledge_item=self.article,
            insight_type=Insight.InsightType.NOTE,
            content='Article note.',
        )
        podcast_insight = Insight.objects.create(
            user=self.user,
            knowledge_item=self.podcast,
            insight_type=Insight.InsightType.NOTE,
            content='Podcast note.',
        )
        article_pk = self.article.pk
        podcast_pk = self.podcast.pk
        self.client.force_login(self.user)

        article_response = self.client.post(
            reverse('library:article_delete', args=[self.article.uuid])
        )
        podcast_response = self.client.post(
            reverse('library:podcast_delete', args=[self.podcast.uuid])
        )

        self.assertRedirects(article_response, reverse('library:article_list'))
        self.assertRedirects(podcast_response, reverse('library:podcast_list'))
        self.assertFalse(ArticleDetail.objects.filter(knowledge_item_id=article_pk).exists())
        self.assertFalse(
            PodcastEpisodeDetail.objects.filter(
                knowledge_item_id=podcast_pk
            ).exists()
        )
        self.assertFalse(Insight.objects.filter(pk=article_insight.pk).exists())
        self.assertFalse(Insight.objects.filter(pk=podcast_insight.pk).exists())


def create_article_for_user(
    user,
    *,
    title: str = 'How to Build a Durable Investment Process',
) -> KnowledgeItem:
    """Create an article fixture with representative Stage 5 fields."""
    article = KnowledgeItem.objects.create(
        user=user,
        source_type=KnowledgeItem.SourceType.ARTICLE,
        title=title,
        creator='Alex Researcher',
        date_published=date(2024, 5, 4),
        source_url='https://example.com/durable-process',
        status=KnowledgeItem.Status.QUEUED,
        summary='A practical framework for repeatable decisions.',
    )
    ArticleDetail.objects.create(
        knowledge_item=article,
        publication_name='The Quantitative Investor',
    )
    return article


def create_podcast_for_user(
    user,
    *,
    title: str = 'Building Better Portfolios',
) -> KnowledgeItem:
    """Create a podcast fixture with representative Stage 5 fields."""
    podcast = KnowledgeItem.objects.create(
        user=user,
        source_type=KnowledgeItem.SourceType.PODCAST,
        title=title,
        creator='Jane Host',
        source_url='https://example.com/portfolio-podcast',
        status=KnowledgeItem.Status.QUEUED,
        summary='A discussion of robust allocation choices.',
    )
    PodcastEpisodeDetail.objects.create(
        knowledge_item=podcast,
        show_name='Capital Allocators',
        guests='Sam Investor',
    )
    return podcast

import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from journal_project.journal.models import Insight

from .forms import PaperImportForm
from .models import KnowledgeItem, KnowledgeItemTag, PaperDetail, Tag
from .paper_import import (
    PaperImportFileError,
    import_paper_records,
    load_paper_manager_json,
    paper_fingerprint,
)
from .services import create_paper


def paper_manager_record(**overrides):
    """Return one complete record using the paper-manager JSON schema."""
    record = {
        'title': 'Momentum Crashes',
        'year': 2016,
        'authors': 'Kent Daniel; Tobias Moskowitz',
        'asset class': 'Equities',
        'sample size, data and source': 'US equity data from 1927 onward.',
        'methodology and research design': 'Momentum portfolio analysis.',
        'key research question': 'When does momentum crash?',
        'key findings and practical applications': 'Crashes cluster after rebounds.',
    }
    record.update(overrides)
    return record


def json_upload(records, *, name='papers.json') -> SimpleUploadedFile:
    """Return an in-memory JSON upload for view tests."""
    return SimpleUploadedFile(
        name,
        json.dumps(records).encode('utf-8'),
        content_type='application/json',
    )


class PaperImportParsingTests(TestCase):
    def test_fingerprint_normalizes_case_whitespace_punctuation_and_year(self) -> None:
        first = paper_fingerprint(
            title='  Momentum:   Crashes ',
            publication_year=None,
            authors='Kent Daniel; Tobias Moskowitz',
        )
        second = paper_fingerprint(
            title='momentum crashes',
            publication_year=None,
            authors=' kent daniel,  tobias moskowitz ',
        )

        self.assertEqual(first, second)

    def test_loader_rejects_malformed_json_and_non_list_roots(self) -> None:
        malformed = SimpleUploadedFile('papers.json', b'[{')
        object_root = SimpleUploadedFile('papers.json', b'{"title": "Paper"}')

        with self.assertRaises(PaperImportFileError):
            load_paper_manager_json(malformed)
        with self.assertRaises(PaperImportFileError):
            load_paper_manager_json(object_root)


class PaperImportServiceTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(username='reader')

    def test_single_record_maps_all_fields_and_import_defaults(self) -> None:
        result = import_paper_records(
            user=self.user,
            records=[paper_manager_record()],
        )

        paper = KnowledgeItem.objects.get(user=self.user)
        detail = paper.paper_detail
        self.assertEqual(result.imported, 1)
        self.assertEqual(result.skipped_duplicates, 0)
        self.assertEqual(result.invalid, 0)
        self.assertEqual(paper.source_type, KnowledgeItem.SourceType.PAPER)
        self.assertEqual(paper.creator, 'Kent Daniel; Tobias Moskowitz')
        self.assertEqual(paper.status, KnowledgeItem.Status.QUEUED)
        self.assertFalse(paper.archived)
        self.assertEqual(paper.summary, '')
        self.assertIsNone(paper.date_started)
        self.assertIsNone(paper.date_finished)
        self.assertEqual(detail.publication_year, 2016)
        self.assertEqual(detail.asset_class, 'Equities')
        self.assertEqual(
            detail.sample_size_data_source,
            'US equity data from 1927 onward.',
        )
        self.assertEqual(
            detail.methodology_research_design,
            'Momentum portfolio analysis.',
        )
        self.assertEqual(detail.key_research_question, 'When does momentum crash?')
        self.assertEqual(
            detail.key_findings_practical_applications,
            'Crashes cluster after rebounds.',
        )
        self.assertFalse(paper.tags.exists())
        self.assertFalse(paper.insights.exists())

    def test_zero_year_becomes_null_without_fabricated_publication_date(self) -> None:
        import_paper_records(
            user=self.user,
            records=[paper_manager_record(year=0)],
        )

        paper = KnowledgeItem.objects.get(user=self.user)
        self.assertIsNone(paper.paper_detail.publication_year)
        self.assertIsNone(paper.date_published)

    def test_missing_optional_fields_are_accepted(self) -> None:
        result = import_paper_records(
            user=self.user,
            records=[{'title': 'Title Only'}],
        )

        paper = KnowledgeItem.objects.get(user=self.user)
        self.assertEqual(result.imported, 1)
        self.assertEqual(paper.creator, '')
        self.assertEqual(paper.summary, '')
        self.assertIsNone(paper.paper_detail.publication_year)
        self.assertEqual(paper.paper_detail.asset_class, '')

    def test_invalid_records_do_not_block_valid_records(self) -> None:
        records = [
            paper_manager_record(title='Valid Paper'),
            paper_manager_record(title='   '),
            paper_manager_record(title='Bad Year', year='not-a-year'),
            'not an object',
        ]

        result = import_paper_records(user=self.user, records=records)

        self.assertEqual(result.imported, 1)
        self.assertEqual(result.invalid, 3)
        self.assertEqual(
            [record.record_number for record in result.invalid_records],
            [2, 3, 4],
        )
        self.assertEqual(result.invalid_records[0].reason, 'missing title')
        self.assertEqual(result.invalid_records[1].reason, 'invalid year')
        self.assertEqual(KnowledgeItem.objects.count(), 1)

    def test_existing_duplicate_is_skipped_without_updates(self) -> None:
        existing = create_paper(
            user=self.user,
            data={
                'title': 'Momentum Crashes',
                'authors': 'Kent Daniel; Tobias Moskowitz',
                'publication_year': 2016,
                'status': KnowledgeItem.Status.COMPLETED,
                'summary': 'My protected summary.',
                'key_findings_practical_applications': 'My edited findings.',
            },
        )
        tag = Tag.objects.create(user=self.user, name='Protected')
        KnowledgeItemTag.objects.create(knowledge_item=existing, tag=tag)
        insight = Insight.objects.create(
            user=self.user,
            knowledge_item=existing,
            insight_type=Insight.InsightType.NOTE,
            content='My protected insight.',
        )

        result = import_paper_records(
            user=self.user,
            records=[paper_manager_record()],
        )

        existing.refresh_from_db()
        existing.paper_detail.refresh_from_db()
        self.assertEqual(result.imported, 0)
        self.assertEqual(result.skipped_duplicates, 1)
        self.assertEqual(existing.status, KnowledgeItem.Status.COMPLETED)
        self.assertEqual(existing.summary, 'My protected summary.')
        self.assertEqual(
            existing.paper_detail.key_findings_practical_applications,
            'My edited findings.',
        )
        self.assertTrue(existing.tags.filter(pk=tag.pk).exists())
        self.assertTrue(Insight.objects.filter(pk=insight.pk).exists())

    def test_duplicate_within_upload_is_skipped_after_normalization(self) -> None:
        records = [
            paper_manager_record(title='Momentum: Crashes'),
            paper_manager_record(
                title=' momentum crashes ',
                authors='Kent Daniel, Tobias Moskowitz',
            ),
        ]

        result = import_paper_records(user=self.user, records=records)

        self.assertEqual(result.imported, 1)
        self.assertEqual(result.skipped_duplicates, 1)
        self.assertEqual(KnowledgeItem.objects.count(), 1)

    def test_same_title_with_different_author_or_year_is_not_duplicate(self) -> None:
        records = [
            paper_manager_record(title='Shared Title', year=2020, authors='Author A'),
            paper_manager_record(title='Shared Title', year=2021, authors='Author A'),
            paper_manager_record(title='Shared Title', year=2020, authors='Author B'),
        ]

        result = import_paper_records(user=self.user, records=records)

        self.assertEqual(result.imported, 3)
        self.assertEqual(result.skipped_duplicates, 0)

    def test_reimporting_exact_records_is_idempotent(self) -> None:
        records = [
            paper_manager_record(title='First Paper'),
            paper_manager_record(title='Second Paper', year=2022),
        ]

        first_result = import_paper_records(user=self.user, records=records)
        second_result = import_paper_records(user=self.user, records=records)

        self.assertEqual(first_result.imported, 2)
        self.assertEqual(second_result.imported, 0)
        self.assertEqual(second_result.skipped_duplicates, 2)
        self.assertEqual(KnowledgeItem.objects.count(), 2)

    def test_duplicate_detection_is_isolated_by_user(self) -> None:
        other_user = get_user_model().objects.create_user(username='other-reader')
        import_paper_records(
            user=other_user,
            records=[paper_manager_record()],
        )

        result = import_paper_records(
            user=self.user,
            records=[paper_manager_record()],
        )

        self.assertEqual(result.imported, 1)
        self.assertEqual(result.skipped_duplicates, 0)
        self.assertEqual(KnowledgeItem.objects.filter(user=self.user).count(), 1)
        self.assertEqual(KnowledgeItem.objects.filter(user=other_user).count(), 1)

    def test_one_hundred_papers_can_be_reimported_without_duplicates(self) -> None:
        records = [
            paper_manager_record(
                title=f'Paper {index}',
                year=2000 + index,
                authors=f'Author {index}',
            )
            for index in range(100)
        ]

        first_result = import_paper_records(user=self.user, records=records)
        second_result = import_paper_records(user=self.user, records=records)

        self.assertEqual(first_result.imported, 100)
        self.assertEqual(first_result.skipped_duplicates, 0)
        self.assertEqual(second_result.imported, 0)
        self.assertEqual(second_result.skipped_duplicates, 100)
        self.assertEqual(
            KnowledgeItem.objects.filter(
                user=self.user,
                source_type=KnowledgeItem.SourceType.PAPER,
            ).count(),
            100,
        )


class PaperImportViewTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(username='reader')
        self.url = reverse('library:paper_import')

    def test_import_requires_authentication(self) -> None:
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(reverse('accounts:login')))

    def test_import_page_explains_behavior_and_accepts_json(self) -> None:
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertContains(response, 'Existing papers will be skipped.')
        self.assertContains(
            response,
            'New papers will be added with status “To read”.',
        )
        form = response.context['form']
        self.assertIsInstance(form, PaperImportForm)
        self.assertIn('.json', form.fields['json_file'].widget.attrs['accept'])

    def test_valid_upload_displays_import_report(self) -> None:
        self.client.force_login(self.user)

        response = self.client.post(
            self.url,
            {'json_file': json_upload([paper_manager_record()])},
        )

        self.assertEqual(response.status_code, 200)
        result = response.context['result']
        self.assertEqual(result.imported, 1)
        self.assertEqual(result.skipped_duplicates, 0)
        self.assertEqual(result.invalid, 0)
        self.assertContains(response, 'Import complete')
        self.assertContains(response, 'Skipped duplicates')

    def test_malformed_json_is_reported_without_database_changes(self) -> None:
        self.client.force_login(self.user)
        upload = SimpleUploadedFile(
            'papers.json',
            b'[{',
            content_type='application/json',
        )

        response = self.client.post(self.url, {'json_file': upload})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Upload a valid UTF-8 JSON file.')
        self.assertEqual(KnowledgeItem.objects.count(), 0)

    def test_non_json_extension_is_rejected(self) -> None:
        self.client.force_login(self.user)

        response = self.client.post(
            self.url,
            {'json_file': json_upload([paper_manager_record()], name='papers.txt')},
        )

        self.assertContains(response, 'File extension “txt” is not allowed.')
        self.assertEqual(KnowledgeItem.objects.count(), 0)

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class GenericKnowledgeItemFoundationMigrationTests(TransactionTestCase):
    migrate_from = [
        ('library', '0002_tag_knowledgeitemtag_knowledgeitem_tags_and_more'),
    ]
    migrate_to = [
        ('library', '0003_generic_knowledge_item_foundation'),
    ]

    def tearDown(self) -> None:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def setUp(self) -> None:
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps

        user_model = old_apps.get_model('accounts', 'User')
        knowledge_item_model = old_apps.get_model('library', 'KnowledgeItem')
        book_detail_model = old_apps.get_model('library', 'BookDetail')

        user = user_model.objects.create(username='migration-reader')
        self.expected_statuses = {
            'Want to read': 'queued',
            'Reading': 'in_progress',
            'Finished': 'completed',
            'Paused': 'paused',
            'Abandoned': 'abandoned',
        }
        self.expected_legacy_statuses = {
            'Want to read': 'want_to_read',
            'Reading': 'reading',
            'Finished': 'finished',
            'Paused': 'paused',
            'Abandoned': 'abandoned',
        }

        for title, legacy_status in self.expected_legacy_statuses.items():
            item = knowledge_item_model.objects.create(
                user_id=user.pk,
                source_type='book',
                title=title,
                creator='Existing Author',
                status=legacy_status,
            )
            if legacy_status == 'reading':
                self.book_pk = item.pk
                book_detail_model.objects.create(
                    knowledge_item_id=item.pk,
                    author='Existing Author',
                )

        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        self.new_apps = executor.loader.project_state(self.migrate_to).apps

    def test_migration_maps_statuses_and_preserves_existing_book(self) -> None:
        knowledge_item_model = self.new_apps.get_model('library', 'KnowledgeItem')
        book_detail_model = self.new_apps.get_model('library', 'BookDetail')

        migrated_statuses = dict(
            knowledge_item_model.objects.values_list('title', 'status')
        )

        self.assertEqual(migrated_statuses, self.expected_statuses)
        self.assertTrue(
            book_detail_model.objects.filter(
                knowledge_item_id=self.book_pk,
                author='Existing Author',
            ).exists()
        )

    def test_migration_enlarges_common_fields(self) -> None:
        knowledge_item_model = self.new_apps.get_model('library', 'KnowledgeItem')

        self.assertEqual(
            knowledge_item_model._meta.get_field('title').max_length,
            500,
        )
        self.assertEqual(
            knowledge_item_model._meta.get_field('creator').max_length,
            1000,
        )
        self.assertEqual(
            knowledge_item_model._meta.get_field('source_url').max_length,
            2048,
        )

    def test_reverse_migration_restores_legacy_statuses(self) -> None:
        try:
            executor = MigrationExecutor(connection)
            executor.migrate(self.migrate_from)
            old_apps = executor.loader.project_state(self.migrate_from).apps
            knowledge_item_model = old_apps.get_model('library', 'KnowledgeItem')

            restored_statuses = dict(
                knowledge_item_model.objects.values_list('title', 'status')
            )

            self.assertEqual(restored_statuses, self.expected_legacy_statuses)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(self.migrate_to)
