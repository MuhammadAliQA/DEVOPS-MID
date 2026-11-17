import hashlib
import hmac
import json
import uuid
from django.test import SimpleTestCase, override_settings


@override_settings(ROOT_URLCONF='payment_service.urls', SECRET_KEY='test-payment-secret')
class PaymentTests(SimpleTestCase):
    def payload(self, **changes):
        data = {'booking': str(uuid.uuid4()), 'amount': 100000, 'currency': 'UZS', 'outcome': 'approve'}
        data.update(changes)
        return json.dumps(data).encode()

    def send(self, body):
        signature = hmac.new(b'test-payment-secret', body, hashlib.sha256).hexdigest()
        return self.client.post('/charge/', body, content_type='application/json', HTTP_X_SIGNATURE=signature)

    def test_requires_signature(self):
        self.assertEqual(self.client.post('/charge/', self.payload(), content_type='application/json').status_code, 403)

    def test_retries_have_identical_reference(self):
        body = self.payload()
        first = self.send(body)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()['status'], 'approved')
        self.assertEqual(first.json(), self.send(body).json())

    def test_decline(self):
        self.assertEqual(self.send(self.payload(outcome='decline')).json()['status'], 'declined')

    def test_invalid_payloads(self):
        for body in [b'null', b'[]', b'not-json', self.payload(amount=-1), self.payload(amount=True), self.payload(currency='USD'), self.payload(booking='invalid')]:
            with self.subTest(body=body):
                self.assertEqual(self.send(body).status_code, 400)
