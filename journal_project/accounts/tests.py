from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AuthenticationTests(TestCase):
    def test_signup_creates_user_and_logs_them_in(self):
        response = self.client.post(
            reverse('accounts:signup'),
            {
                'username': 'reader',
                'email': 'reader@example.com',
                'password1': 'StrongPass12345',
                'password2': 'StrongPass12345',
            },
        )

        self.assertRedirects(response, reverse('dashboard'))
        user = get_user_model().objects.get(username='reader')
        self.assertEqual(user.email, 'reader@example.com')
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_login_authenticates_user(self):
        get_user_model().objects.create_user(
            username='reader',
            password='StrongPass12345',
        )

        response = self.client.post(
            reverse('accounts:login'),
            {'username': 'reader', 'password': 'StrongPass12345'},
        )

        self.assertRedirects(response, reverse('dashboard'))
        self.assertIn('_auth_user_id', self.client.session)

    def test_logout_ends_session(self):
        user = get_user_model().objects.create_user(
            username='reader',
            password='StrongPass12345',
        )
        self.client.force_login(user)

        response = self.client.post(reverse('accounts:logout'))

        self.assertRedirects(response, reverse('home'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_anonymous_user_is_redirected_from_dashboard(self):
        response = self.client.get(reverse('dashboard'))

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('dashboard')}",
        )

    def test_authenticated_user_can_open_dashboard(self):
        user = get_user_model().objects.create_user(
            username='reader',
            password='StrongPass12345',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your journal workspace.')
