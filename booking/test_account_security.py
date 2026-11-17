from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase


class PasswordChangeTests(TestCase):
    old = 'Previous-account-pass-7931'
    new = 'Updated-account-pass-6284'
    url = '/accounts/password/change/'

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = get_user_model().objects.create_user('security-customer', password=self.old)
        self.client.force_login(self.user)

    def payload(self, **overrides):
        return {'old_password': self.old, 'new_password1': self.new,
                'new_password2': self.new, **overrides}

    def test_anonymous_redirect_and_csrf_required(self):
        self.assertRedirects(Client().get(self.url), '/accounts/login/?next=' + self.url,
                             fetch_redirect_response=False)
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.user)
        self.assertEqual(protected.post(self.url, self.payload()).status_code, 403)

    def test_invalid_current_password_mismatch_and_weak_password_do_not_save(self):
        for overrides, field in [({'old_password': 'wrong'}, 'old_password'),
                                 ({'new_password2': 'mismatch'}, 'new_password2'),
                                 ({'new_password1': '123', 'new_password2': '123'}, 'new_password2')]:
            with self.subTest(field=field):
                response = self.client.post(self.url, self.payload(**overrides))
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context['form'].errors)
                self.user.refresh_from_db()
                self.assertTrue(self.user.check_password(self.old))

    def test_success_preserves_current_session_and_revokes_other_session(self):
        other = Client()
        other.force_login(self.user)
        response = self.client.post(self.url, self.payload())
        self.assertRedirects(response, '/accounts/password/changed/')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new))
        self.assertFalse(self.user.check_password(self.old))
        self.assertEqual(self.client.get('/profile/').status_code, 200)
        self.assertRedirects(other.get('/profile/'), '/accounts/login/?next=/profile/',
                             fetch_redirect_response=False)

    def test_profile_link_and_three_languages(self):
        self.assertContains(self.client.get('/profile/'), self.url)
        for language, title in [('uz', 'Parolni almashtirish'), ('ru', 'Изменить пароль'),
                                 ('en', 'Change password')]:
            with self.subTest(language=language):
                self.client.cookies['ticketflow_language'] = language
                response = self.client.get(self.url)
                self.assertContains(response, title)
                self.assertContains(response, 'autocomplete="current-password"')
                self.assertContains(response, 'autocomplete="new-password"')
