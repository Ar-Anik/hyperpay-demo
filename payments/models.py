from django.db import models

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

