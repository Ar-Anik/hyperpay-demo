from django.db import models

import uuid

class Payment(models.Model):

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Successful"
        FAILED = "FAILED", "Failed"

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    currency = models.CharField(
        max_length=3,
        default="SAR"
    )

    payment_type = models.CharField(
        max_length=2,
        default="DB"
    )

    status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )

    checkout_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True
    )

    transaction_id = models.CharField(
        max_length=255,
        blank=True
    )

    payment_brand = models.CharField(
        max_length=50,
        blank=True
    )

    result_code = models.CharField(
        max_length=50,
        blank=True
    )

    result_description = models.TextField(
        blank=True
    )

    resource_path = models.CharField(
        max_length=500,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"Payment #{self.pk} - {self.status}"


class DemoCustomer(models.Model):

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class SavedCard(models.Model):

    customer = models.ForeignKey(
        DemoCustomer,
        on_delete=models.CASCADE,
        related_name="saved_cards"
    )

    registration_id = models.CharField(
        max_length=255,
        unique=True
    )

    card_brand = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    last_four_digits = models.CharField(
        max_length=4,
        blank=True,
        null=True
    )

    expiry_month = models.CharField(
        max_length=2,
        blank=True,
        null=True
    )

    expiry_year = models.CharField(
        max_length=4,
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):

        return (
            f"{self.card_brand} ****{self.last_four_digits}"
        )


class CardRegistrationAttempt(models.Model):

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("UNKNOWN", "Unknown"),
    ]

    customer = models.ForeignKey(
        DemoCustomer,
        on_delete=models.PROTECT
    )

    checkout_id = models.CharField(
        max_length=255,
        unique=True
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    currency = models.CharField(
        max_length=3
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    saved_card = models.ForeignKey(
        SavedCard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.checkout_id



class TokenizedPayment(models.Model):

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("UNKNOWN", "Unknown"),
    ]

    customer = models.ForeignKey(
        DemoCustomer,
        on_delete=models.PROTECT
    )

    saved_card = models.ForeignKey(
        SavedCard,
        on_delete=models.PROTECT,
        related_name="payments"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    currency = models.CharField(
        max_length=3
    )

    hyperpay_payment_id = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    result_code = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    result_description = models.TextField(
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    merchant_transaction_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    def __str__(self):
        return f"{self.id} - {self.status}"
