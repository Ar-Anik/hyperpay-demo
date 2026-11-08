
from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "amount",
        "currency",
        "payment_type",
        "status",
        "checkout_id",
        "transaction_id",
        "payment_brand",
        "created_at",
    )

    list_filter = (
        "status",
        "currency",
        "payment_type",
        "created_at",
    )

    search_fields = (
        "checkout_id",
        "transaction_id",
        "result_code",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )
