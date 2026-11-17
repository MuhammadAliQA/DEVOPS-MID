
import io
import uuid
from pathlib import Path

from PIL import Image

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, TransactionTestCase, override_settings

from booking.forms import EventForm
from booking.tests import inventory


User = get_user_model()


class ReliabilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=f"user-{uuid.uuid4().hex[:8]}",
            password="test-password-123",
        )

    def test_health_check_endpoint(self):
        for route in ("/health/live/", "/health/ready/"):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route).status_code, 200)

    def test_homepage_does_not_crash(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)


class PermissionAndUploadTests(TransactionTestCase):
    # Streaming response.close() emits request_finished and closes DB connections.
    # Do not wrap these HTTP lifecycle tests in TestCase's enclosing transaction.
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username=f"staff-{uuid.uuid4().hex[:8]}",
            password="test-password-123",
            is_staff=True,
        )

        self.normal_user = User.objects.create_user(
            username=f"user-{uuid.uuid4().hex[:8]}",
            password="test-password-123",
        )

        self.event, self.seats = inventory()

    def _make_png(self):
        stream = io.BytesIO()
        Image.new("RGB", (20, 20), "blue").save(stream, format="PNG")
        return stream.getvalue()

    def test_staff_flag_alone_grants_no_operations_access(self):
        self.client.force_login(self.staff_user)

        response = self.client.get("/operations/")

        self.assertEqual(response.status_code, 403)

    def test_real_png_accepted_and_svg_rejected(self):
        png_file = SimpleUploadedFile(
            "poster.png",
            self._make_png(),
            content_type="image/png",
        )

        data = {'title': self.event.title, 'category': self.event.category,
                'venue': self.event.venue, 'starts_at': self.event.starts_at.isoformat(),
                'description': 'Poster validation', 'artwork': 'music'}
        form = EventForm(data, {'poster': png_file}, instance=self.event)
        self.assertTrue(form.is_valid(), form.errors)

        svg_file = SimpleUploadedFile(
            "poster.svg",
            b'<svg xmlns="http://www.w3.org/2000/svg"></svg>',
            content_type="image/svg+xml",
        )

        form = EventForm(data, {'poster': svg_file}, instance=self.event)
        self.assertFalse(form.is_valid())
        self.assertIn('poster', form.errors)

    def test_poster_serves_with_debug_disabled_and_hides_drafts(self):
        media_root = (
            Path(settings.BASE_DIR) / ".tmp" / "poster-tests"
        )
        media_root.mkdir(parents=True, exist_ok=True)

        stream = io.BytesIO()
        Image.new("RGB", (20, 20), "blue").save(
            stream,
            format="PNG",
        )

        with override_settings(
            MEDIA_ROOT=media_root,
            DEBUG=False,
        ):
            self.event.poster.save(
                f"test-{uuid.uuid4().hex}.png",
                SimpleUploadedFile(
                    "poster.png",
                    stream.getvalue(),
                    content_type="image/png",
                ),
                save=True,
            )

            try:
                response = self.client.get(
                    f"/events/{self.event.pk}/poster/"
                )

                self.assertEqual(response.status_code, 200)

                content = b"".join(response.streaming_content)
                self.assertTrue(
                    content.startswith(b"\x89PNG")
                )

                response.close()

                self.event.published = False
                self.event.save(update_fields=["published"])

                hidden_response = self.client.get(
                    f"/events/{self.event.pk}/poster/"
                )

                self.assertEqual(hidden_response.status_code, 404)
                hidden_response.close()

            finally:
                # Remove the uploaded file without another DB save.
                self.event.poster.delete(save=False)

    def test_unpublished_event_is_not_visible_to_anonymous_user(self):
        self.event.published = False
        self.event.save(update_fields=["published"])

        response = self.client.get(
            f"/events/{self.event.pk}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_cannot_access_operations(self):
        response = self.client.get("/operations/")

        self.assertRedirects(response, '/accounts/login/?next=/operations/',
                             fetch_redirect_response=False)
