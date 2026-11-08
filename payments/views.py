import re
from django.conf import settings
from django.http import JsonResponse

from decimal import Decimal
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from .models import Payment, SavedCard, CardRegistrationAttempt, TokenizedPayment, DemoCustomer
from .utils import HyperPayService, HyperPayError, HyperPayClient, HyperPayUnknownOutcome, get_default_customer, is_payment_successful

from django.db import transaction

app_name = "payments"

def health_check(request):
    return JsonResponse({
        "status": "success",
        "message": "Django HyperPay Demo API is running",
        "hyperpay_configured": bool(settings.HYPERPAY_ENTITY_ID and settings.HYPERPAY_ACCESS_TOKEN),
        "hyperpay_base_url": settings.HYPERPAY_BASE_URL,
    })


@require_GET
def payment_page(request):
    return render(request, 'payments/payment.html', {
        "hyperpay_base_url": settings.HYPERPAY_BASE_URL.rstrip("/") + "/",
    })


@require_POST
def create_checkout(request):

    amount = Decimal('10.00')
    currency = 'SAR'

    payment = Payment.objects.create(
        amount=amount,
        currency=currency,
        payment_type='DB',
        status=Payment.PaymentStatus.PENDING
    )

    try:
        service = HyperPayService()

        response_data = service.create_checkout(
            amount=amount,
            currency=currency,
            payment_type=payment.payment_type,
        )

        checkout_id = response_data['id']

        payment.checkout_id = checkout_id
        payment.save(update_fields=['checkout_id', 'updated_at'])

        return JsonResponse({
            'success': True,
            'checkout_id': checkout_id,
            'integrity': response_data.get('integrity'),
            'payment_id': payment.id,
        })

    except HyperPayError as exc:

        payment.status = Payment.PaymentStatus.FAILED
        payment.result_description = str(exc)
        payment.save()

        return JsonResponse({
            "success": False,
            "message": str(exc),
        }, status=502)


@require_GET
def shopper_result(request):
    resource_path = request.GET.get('resourcePath', '')

    match = re.fullmatch(
        r'/v1/checkouts/([^/]+)/payment', resource_path,
    )

    if not match:
        return JsonResponse({
            "success": False,
            "message": "Invalid resourcePath.",
        }, status=400)

    checkout_id = match.group(1)
    payment = get_object_or_404(Payment, checkout_id=checkout_id)

    if payment.status in (Payment.PaymentStatus.SUCCESS, Payment.PaymentStatus.FAILED):
        return render(
            request,
            "payments/result.html",
            {"payment": payment},
        )

    try:
        service = HyperPayService()

        response_data = service.get_payment_status(resource_path)

        result = response_data.get('result', {})
        result_code = result.get('code', '')
        result_description = result.get('description', '')

        if re.match(r'^(000\.000\.|000\.100\.1|000\.[36])', result_code):
            payment.status = Payment.PaymentStatus.SUCCESS

        elif result_code.startswith("000.200."):
            payment.status = Payment.PaymentStatus.PENDING

        else:
            payment.status = Payment.PaymentStatus.FAILED

        payment.transaction_id = response_data.get('id', '')
        payment.payment_brand = response_data.get('paymentBrand', '')
        payment.result_code = result_code
        payment.result_description = result_description
        payment.resource_path = resource_path
        payment.save()

        return render(
            request,
            "payments/result.html",
            {"payment": payment},
        )

    except HyperPayError as exc:
        return render(
            request,
            "payments/result.html",
            {
                "payment": payment,
                "verification_error": str(exc),
            },
            status=502,
        )


@require_POST
def create_registration_checkout(request):
    customer = get_default_customer()
    amount = Decimal("10.00")
    currency = settings.HYPERPAY_CURRENCY

    try:
        hyperpay = HyperPayClient()
        response_data = hyperpay.create_registration_checkout(amount=amount, currency=currency)

        checkout_id = response_data.get("id")

        if not checkout_id:
            return JsonResponse({
                    "success": False,
                    "message": "Checkout ID not received",
                },
                status=502,
            )

        CardRegistrationAttempt.objects.create(
            customer=customer,
            checkout_id=checkout_id,
            amount=amount,
            currency=currency,
            status="PENDING",
        )

        return JsonResponse({
                "success": True,
                "checkout_id": checkout_id,
                "integrity": response_data.get("integrity"),
                "message": "Registration checkout created",
            }
        )

    except HyperPayUnknownOutcome:
        return JsonResponse({
                "success": False,
                "message": (
                    "Checkout creation outcome is unknown. "
                    "Do not retry blindly."
                ),
            },
            status=503,
        )

    except HyperPayError as exc:
        return JsonResponse({
                "success": False,
                "message": str(exc),
            },
            status=400,
        )


@require_POST
def verify_registration_payment(request):
    checkout_id = request.POST.get("checkout_id")

    if not checkout_id:
        return JsonResponse({
                "success": False,
                "message": "Checkout ID is required",
            },
            status=400,
        )

    customer = get_default_customer()

    try:
        attempt = CardRegistrationAttempt.objects.get(
            checkout_id=checkout_id,
            customer=customer,
        )

    except CardRegistrationAttempt.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "message": "Registration attempt not found",
            },
            status=404,
        )

    if attempt.status == "SUCCESS":
        return JsonResponse(
            {
                "success": True,
                "message": "Card already registered",
            }
        )

    try:
        hyperpay = HyperPayClient()

        response_data = hyperpay.verify_checkout_payment(checkout_id)
        result = response_data.get("result", {})

        result_code = result.get("code", "")

        if result_code == "000.200.000":
            attempt.status = "PENDING"
            attempt.save(update_fields=["status", "updated_at"])

            return JsonResponse(
                {
                    "success": False,
                    "status": "PENDING",
                    "message": "Payment is still pending",
                },
                status=202,
            )

        if not is_payment_successful(response_data):
            attempt.status = "FAILED"
            attempt.save(
                update_fields=["status", "updated_at"]
            )

            return JsonResponse({
                    "success": False,
                    "status": "FAILED",
                    "message": result.get(
                        "description",
                        "Payment was not successful",
                    ),
                },
                status=400,
            )

        registration_id = response_data.get("registrationId")

        if not registration_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Payment succeeded, but registrationId was not returned."
                    ),
                },
                status=400,
            )

        card_data = response_data.get("card", {})

        with transaction.atomic():
            saved_card, created = SavedCard.objects.get_or_create(
                registration_id=registration_id,
                defaults={
                    "customer": customer,
                    "card_brand": response_data.get("paymentBrand", ""),
                    "last_four_digits": card_data.get("last4Digits", ""),
                    "expiry_month": card_data.get("expiryMonth", ""),
                    "expiry_year": card_data.get("expiryYear", ""),
                },
            )

            if not created and saved_card.customer_id != customer.id:
                raise HyperPayError("Registration ID belongs to another customer")

            attempt.status = "SUCCESS"

            attempt.saved_card = saved_card

            attempt.save(
                update_fields=[
                    "status",
                    "saved_card",
                    "updated_at",
                ]
            )

        return JsonResponse({
                "success": True,
                "message": "Card registered successfully",
                "saved_card_id": saved_card.id,
                "card_brand": saved_card.card_brand,
                "last_four_digits": saved_card.last_four_digits,
            }
        )

    except HyperPayUnknownOutcome:
        attempt.status = "UNKNOWN"

        attempt.save(update_fields=["status", "updated_at"])

        return JsonResponse({
                "success": False,
                "status": "UNKNOWN",
                "message": (
                    "Payment verification outcome is unknown. "
                    "Verify again before making another payment."
                ),
            },
            status=503,
        )

    except HyperPayError as exc:
        return JsonResponse({
                "success": False,
                "message": str(exc),
            },
            status=400,
        )


@require_GET
def get_saved_cards(request):
    customer = get_default_customer()
    cards = SavedCard.objects.filter(customer=customer,is_active=True)

    card_list = []

    for card in cards:

        card_list.append({
            "id": card.id,
            "brand": card.card_brand,
            "last_four_digits": card.last_four_digits,
            "expiry_month": card.expiry_month,
            "expiry_year": card.expiry_year,
        })

    return JsonResponse({
        "success": True,
        "cards": card_list,
    })



@require_POST
def pay_with_saved_card(request):

    customer = get_default_customer()
    saved_card_id = request.POST.get("saved_card_id")

    if not saved_card_id:
        return JsonResponse({
                "success": False,
                "message": "Saved Card ID is required",
            },
            status=400,
        )

    try:
        saved_card = SavedCard.objects.get(
            id=saved_card_id,
            customer=customer,
            is_active=True,
        )

    except (SavedCard.DoesNotExist, ValueError, TypeError):
        return JsonResponse({
                "success": False,
                "message": "Saved card not found",
            },
            status=404,
        )

    # Demo amount: fixed on the backend.
    # Production: retrieve amount from a verified order.
    amount = Decimal("20.00")

    currency = settings.HYPERPAY_CURRENCY

    payment = TokenizedPayment.objects.create(
        customer=customer,
        saved_card=saved_card,
        amount=amount,
        currency=currency,
        status="PENDING",
    )

    try:
        hyperpay = HyperPayClient()

        response_data = hyperpay.charge_saved_card(
            registration_id=saved_card.registration_id,
            payment_brand=saved_card.card_brand,
            amount=amount,
            currency=currency,
            merchant_transaction_id=payment.merchant_transaction_id,
            shopper_result_url=request.build_absolute_uri(
                reverse("tokenized_payment_result")
            ),
        )

        result = response_data.get("result", {})

        payment.hyperpay_payment_id = response_data.get("id")

        payment.result_code = result.get("code")

        payment.result_description = result.get("description")

        if is_payment_successful(response_data):
            payment.status = "SUCCESS"

        elif result.get("code") == "000.200.000":
            payment.status = "PENDING"

        else:
            payment.status = "FAILED"

        payment.save()

        redirect_data = response_data.get("redirect")
        if redirect_data and redirect_data.get("url"):
            return JsonResponse({
                "success": True,
                "payment_id": payment.id,
                "status": payment.status,
                "message": "Additional card authentication is required.",
                "redirect": redirect_data,
            })

        return JsonResponse(
            {
                "success": payment.status == "SUCCESS",
                "payment_id": payment.id,
                "status": payment.status,
                "message": payment.result_description,
            }
        )

    except HyperPayUnknownOutcome:
        payment.status = "UNKNOWN"

        payment.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return JsonResponse(
            {
                "success": False,
                "payment_id": payment.id,
                "status": "UNKNOWN",
                "message": (
                    "Payment outcome is unknown. Verify the transaction before retrying."
                ),
            },
            status=503,
        )

    except HyperPayError as exc:
        payment.status = "FAILED"

        payment.result_description = str(exc)

        payment.save(
            update_fields=[
                "status",
                "result_description",
                "updated_at",
            ]
        )

        return JsonResponse(
            {
                "success": False,
                "payment_id": payment.id,
                "status": "FAILED",
                "message": str(exc),
            },
            status=400,
        )


@require_GET
def tokenized_payment_result(request):
    resource_path = request.GET.get("resourcePath", "")
    match = re.fullmatch(r"/v1/payments/([^/]+)", resource_path)
    if not match:
        return JsonResponse({
            "success": False,
            "message": "Invalid payment resourcePath.",
        }, status=400)

    payment = get_object_or_404(TokenizedPayment, hyperpay_payment_id=match.group(1))
    try:
        service = HyperPayService()
        response_data = service.get_payment_status(resource_path)
        result = response_data.get("result", {})
        code = result.get("code", "")

        if is_payment_successful(response_data):
            payment.status = "SUCCESS"
        elif code == "000.200.000":
            payment.status = "PENDING"
        else:
            payment.status = "FAILED"

        payment.result_code = code
        payment.result_description = result.get("description", "")
        payment.save(update_fields=[
            "status", "result_code", "result_description", "updated_at",
        ])

        return render(request, "payments/tokenized_payment_result.html", {
            "payment": payment,
        })
    except HyperPayError as exc:
        return render(request, "payments/tokenized_payment_result.html", {
            "payment": payment,
            "verification_error": str(exc),
        }, status=502)

@require_GET
def registration_shopper_result(request):
    resource_path = request.GET.get("resourcePath", "")

    match = re.fullmatch(
        r"/v1/checkouts/([^/]+)/payment",
        resource_path,
    )

    if not match:
        return JsonResponse({
            "success": False,
            "message": "Invalid resourcePath.",
        }, status=400)

    checkout_id = match.group(1)
    customer = get_default_customer()

    try:
        attempt = CardRegistrationAttempt.objects.get(
            checkout_id=checkout_id,
            customer=customer,
        )
    except CardRegistrationAttempt.DoesNotExist:
        return JsonResponse({
            "success": False,
            "message": "Registration attempt not found.",
        }, status=404)

    if attempt.status == "SUCCESS":
        return render(request, "payments/registration_result.html", {
            "success": True,
            "status": "SUCCESS",
            "message": "Card already registered.",
            "saved_card": attempt.saved_card,
        })

    try:
        hyperpay = HyperPayClient()
        response_data = hyperpay.verify_checkout_payment(checkout_id)

        result = response_data.get("result", {})
        result_code = result.get("code", "")

        if result_code == "000.200.000":
            attempt.status = "PENDING"
            attempt.save(update_fields=["status", "updated_at"])

            return render(request, "payments/registration_result.html", {
                "success": False,
                "status": "PENDING",
                "message": "Registration payment is still pending.",
            }, status=202)

        if not is_payment_successful(response_data):
            attempt.status = "FAILED"
            attempt.save(update_fields=["status", "updated_at"])

            return render(request, "payments/registration_result.html", {
                "success": False,
                "status": "FAILED",
                "message": result.get(
                    "description",
                    "Registration payment was not successful.",
                ),
            }, status=400)

        registration_id = response_data.get("registrationId")

        if not registration_id:
            attempt.status = "UNKNOWN"
            attempt.save(update_fields=["status", "updated_at"])

            return render(request, "payments/registration_result.html", {
                "success": False,
                "status": "UNKNOWN",
                "message": (
                    "Payment succeeded, but registrationId was not returned. "
                    "Verify the transaction before retrying."
                ),
            }, status=502)

        card_data = response_data.get("card", {})

        with transaction.atomic():
            saved_card, created = SavedCard.objects.get_or_create(
                registration_id=registration_id,
                defaults={
                    "customer": customer,
                    "card_brand": response_data.get("paymentBrand", ""),
                    "last_four_digits": card_data.get("last4Digits", ""),
                    "expiry_month": card_data.get("expiryMonth", ""),
                    "expiry_year": card_data.get("expiryYear", ""),
                },
            )

            if saved_card.customer_id != customer.id:
                raise HyperPayError(
                    "Registration ID belongs to another customer."
                )

            attempt.status = "SUCCESS"
            attempt.saved_card = saved_card
            attempt.save(
                update_fields=["status", "saved_card", "updated_at"]
            )

        return render(request, "payments/registration_result.html", {
            "success": True,
            "status": "SUCCESS",
            "message": "Card registered successfully.",
            "saved_card": saved_card,
        })

    except HyperPayUnknownOutcome:
        attempt.status = "UNKNOWN"
        attempt.save(update_fields=["status", "updated_at"])

        return render(request, "payments/registration_result.html", {
            "success": False,
            "status": "UNKNOWN",
            "message": (
                "Verification outcome is unknown. "
                "Verify the transaction before retrying."
            ),
        }, status=503)

    except HyperPayError as exc:
        return render(request, "payments/registration_result.html", {
            "success": False,
            "status": "ERROR",
            "message": str(exc),
        }, status=502)
