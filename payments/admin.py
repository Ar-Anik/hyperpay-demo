from django.contrib import admin

from .models import Payment, DemoCustomer, SavedCard, CardRegistrationAttempt, TokenizedPayment


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


@admin.register(DemoCustomer)
class DemoCustomerAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "code",
        "name",
        "created_at",
    )


@admin.register(SavedCard)
class SavedCardAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "customer",
        "card_brand",
        "last_four_digits",
        "is_active",
        "created_at",
    )

    list_filter = (
        "card_brand",
        "is_active",
    )

    readonly_fields = (
        "registration_id",
        "created_at",
        "updated_at",
    )


@admin.register(CardRegistrationAttempt)
class CardRegistrationAttemptAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "customer",
        "checkout_id",
        "amount",
        "currency",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )


@admin.register(TokenizedPayment)
class TokenizedPaymentAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "customer",
        "saved_card",
        "amount",
        "currency",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "currency",
        "created_at",
    )

    search_fields = (
        "hyperpay_payment_id",
        "result_code",
    )
