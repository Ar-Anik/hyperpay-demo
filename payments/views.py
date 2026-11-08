import re
from django.conf import settings
from django.http import JsonResponse

from decimal import Decimal
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from .models import Payment
from .utils import HyperPayService, HyperPayError

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
    return render(request, 'payments/payment.html')


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
