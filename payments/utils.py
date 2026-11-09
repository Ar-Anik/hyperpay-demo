import re

import requests
from django.conf import settings

from .models import DemoCustomer

HYPERPAY_SUCCESS_CODES = {
    "000.000.000",
}

class HyperPayError(Exception):
    """Custom exception for HyperPay API errors."""
    pass


class HyperPayService:

    def __init__(self):
        self.base_url = settings.HYPERPAY_BASE_URL.rstrip('/')
        self.access_token = settings.HYPERPAY_ACCESS_TOKEN
        self.entity_id = settings.HYPERPAY_ENTITY_ID

        if not self.access_token:
            raise HyperPayError("HyperPay access token is missing.")

        if not self.entity_id:
            raise HyperPayError("HyperPay entity ID is missing.")

    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
        }

    def create_checkout(self, amount, currency, payment_type='DB', shopper_result_url=None):
        url = f"{self.base_url}/v1/checkouts"

        payload = {
            "entityId": self.entity_id,
            "amount": str(amount),
            "currency": currency,
            "paymentType": payment_type,
            "integrity": "true",
        }
        if shopper_result_url:
            payload["shopperResultUrl"] = shopper_result_url

        try:
            response = requests.post(
                url,
                data=payload,
                headers=self.headers,
                timeout=30,
            )

            response.raise_for_status()

            data = response.json()

        except requests.RequestException as exc:
            raise HyperPayError(
                f"HyperPay checkout request failed: {exc}"
            ) from exc

        except ValueError as exc:
            raise HyperPayError(
                f"HyperPay returned an invalid JSON response."
            ) from exc

        checkout_id = data.get('id')

        if not checkout_id:
            raise HyperPayError(
                f"Checkout ID missing from response: "
                f"{data.get('result', {})}"
            )

        return data


    def get_payment_status(self, resource_path):

        url = f'{self.base_url}/{resource_path.lstrip("/")}'

        try:
            response = requests.get(
                url,
                params={"entityId": self.entity_id},
                headers=self.headers,
                timeout=30,
            )

            response.raise_for_status()

            return response.json()

        except requests.RequestException as exc:
            raise HyperPayError(
                f"Payment verification request failed: {exc}"
            ) from exc

        except ValueError as exc:
            raise HyperPayError(
                "HyperPay returned an invalid JSON response."
            ) from exc


def get_default_customer():
    customer, created = DemoCustomer.objects.get_or_create(
        code="1234",
        defaults={
            "name": "aranik",
        }
    )

    return customer


class HyperPayUnknownOutcome(HyperPayError):
    """
    The request may have reached HyperPay,
    but the final transaction outcome is unknown.
    """
    pass


class HyperPayClient:

    def __init__(self):
        self.base_url = settings.HYPERPAY_BASE_URL.rstrip("/")
        self.access_token = settings.HYPERPAY_ACCESS_TOKEN
        self.entity_id = settings.HYPERPAY_ENTITY_ID

        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
        }

        self.timeout = 30

        if not self.access_token:
            raise HyperPayError("HyperPay Access Token is missing")

        if not self.entity_id:
            raise HyperPayError("HyperPay Entity ID is missing")

    def _handle_response(self, response):

        try:
            data = response.json()

        except ValueError:
            raise HyperPayError(
                "Invalid JSON response from HyperPay"
            )

        if not response.ok:
            result = data.get("result", {})
            code = result.get("code", "unknown code")
            description = result.get(
                "description", f"HyperPay HTTP error: {response.status_code}"
            )
            details = data.get("resultDetails") or result.get("parameterErrors")
            detail_text = f"; details: {details}" if details else ""

            raise HyperPayError(f"{code}: {description}{detail_text}")

        return data

    def create_registration_checkout(self, amount, currency, shopper_result_url=None):
        url = f"{self.base_url}/v1/checkouts"

        payload = {
            "entityId": self.entity_id,
            "amount": str(amount),
            "currency": currency,
            "paymentType": "DB",
            "createRegistration": "true",
            "standingInstruction.source": "CIT",
            "standingInstruction.mode": "INITIAL",
            "standingInstruction.type": "UNSCHEDULED",
        }
        if shopper_result_url:
            payload["shopperResultUrl"] = shopper_result_url

        try:
            response = requests.post(
                url,
                data=payload,
                headers=self.headers,
                timeout=self.timeout,
            )

        except requests.Timeout as exc:
            raise HyperPayUnknownOutcome(
                "Checkout creation timed out. Verify before retrying."
            ) from exc

        except requests.RequestException as exc:

            raise HyperPayUnknownOutcome(
                "Could not confirm checkout creation."
            ) from exc

        return self._handle_response(response)

    def verify_checkout_payment(self, checkout_id):
        url = f"{self.base_url}/v1/checkouts/{checkout_id}/payment"

        try:
            response = requests.get(
                url,
                params={
                    "entityId": self.entity_id,
                },
                headers=self.headers,
                timeout=self.timeout,
            )

        except requests.RequestException as exc:
            raise HyperPayUnknownOutcome(
                "Could not verify checkout status."
            ) from exc

        return self._handle_response(response)

    def charge_saved_card(
        self, registration_id, payment_brand, amount, currency,
        merchant_transaction_id, shopper_result_url,
    ):
        url = f"{self.base_url}/v1/registrations/{registration_id}/payments"

        payload = {
            "entityId": self.entity_id,
            "paymentBrand": payment_brand,
            "amount": str(amount),
            "currency": currency,
            "paymentType": "DB",
            "merchantTransactionId": str(merchant_transaction_id),
            "shopperResultUrl": shopper_result_url,
            "standingInstruction.source": "CIT",
            "standingInstruction.mode": "REPEATED",
            "standingInstruction.type": "UNSCHEDULED",
        }

        try:
            response = requests.post(
                url,
                data=payload,
                headers=self.headers,
                timeout=self.timeout,
            )

        except requests.Timeout as exc:
            raise HyperPayUnknownOutcome(
                "Payment request timed out. "
                "Verify transaction status before retrying."
            ) from exc

        except requests.RequestException as exc:
            raise HyperPayUnknownOutcome(
                "Payment outcome could not be confirmed."
            ) from exc

        return self._handle_response(response)


def is_payment_successful(data):
    result_code = data.get("result", {}).get("code")
    if not result_code:
        return False

    # Keep this consistent with the result-code handling used by COPYandPAY.
    return bool(re.match(r"^(000\.000\.|000\.100\.1|000\.[36])", result_code))
