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
        self.assertEqual(item.status, KnowledgeItem.Status.WANT_TO_READ)
        self.assertFalse(item.archived)
        self.assertEqual(str(item), 'Deep Work')
        self.assertIsNotNone(item.uuid)

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
            status=KnowledgeItem.Status.READING,
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
            'status': KnowledgeItem.Status.READING,
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
            status=KnowledgeItem.Status.READING,
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
            'status': KnowledgeItem.Status.READING,
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
            {'q': 'Cal', 'status': KnowledgeItem.Status.READING, 'genre': 'Productivity'},
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
