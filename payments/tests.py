from decimal import Decimal
from unittest.mock import Mock, patch
from uuid import uuid4

from django.test import SimpleTestCase, override_settings

from .utils import HyperPayClient


@override_settings(
    HYPERPAY_BASE_URL="https://eu-test.oppwa.com/",
    HYPERPAY_ACCESS_TOKEN="test-token",
    HYPERPAY_ENTITY_ID="test-entity",
)
class HyperPayClientTests(SimpleTestCase):
    @patch("payments.utils.requests.post")
    def test_registration_checkout_marks_initial_cardholder_payment(self, post):
        response = Mock()
        response.ok = True
        response.json.return_value = {"id": "checkout-id"}
        post.return_value = response

        HyperPayClient().create_registration_checkout(
            Decimal("10.00"),
            "SAR",
        )

        payload = post.call_args.kwargs["data"]
        self.assertEqual(payload["standingInstruction.source"], "CIT")
        self.assertEqual(payload["standingInstruction.mode"], "INITIAL")
        self.assertEqual(payload["standingInstruction.type"], "UNSCHEDULED")

    @patch("payments.utils.requests.post")
    def test_saved_card_charge_marks_repeated_cardholder_payment(self, post):
        response = Mock()
        response.ok = True
        response.json.return_value = {
            "id": "payment-id",
            "result": {"code": "000.100.110"},
        }
        post.return_value = response
        merchant_transaction_id = uuid4()

        HyperPayClient().charge_saved_card(
            registration_id="registration-id",
            payment_brand="VISA",
            amount=Decimal("20.00"),
            currency="SAR",
            merchant_transaction_id=merchant_transaction_id,
            shopper_result_url="https://merchant.example/result/",
        )

        payload = post.call_args.kwargs["data"]
        self.assertEqual(payload["standingInstruction.source"], "CIT")
        self.assertEqual(payload["standingInstruction.mode"], "REPEATED")
        self.assertEqual(payload["standingInstruction.type"], "UNSCHEDULED")
        self.assertEqual(payload["shopperResultUrl"], "https://merchant.example/result/")
