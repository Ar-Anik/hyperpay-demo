import requests
from django.conf import settings

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

    def create_checkout(self, amount, currency, payment_type='DB'):
        url = f"{self.base_url}/v1/checkouts"

        payload = {
            "entityId": self.entity_id,
            "amount": str(amount),
            "currency": currency,
            "paymentType": payment_type,
            "integrity": "true",
        }

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

