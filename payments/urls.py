from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health_check, name="health_check"),

    path("", views.payment_page, name="payment_page"),

    # Normal Payment
    path(
        "create-checkout/",
        views.create_checkout,
        name="create_checkout",
    ),

    path(
        "shopper-result/",
        views.shopper_result,
        name="shopper_result",
    ),

    # Card Registration
    path(
        "register-card/",
        views.create_registration_checkout,
        name="register_card",
    ),

    path(
        "verify-registration/",
        views.verify_registration_payment,
        name="verify_registration",
    ),

    path(
        "registration-result/",
        views.registration_shopper_result,
        name="registration_shopper_result",
    ),

    # Saved Cards
    path(
        "saved-cards/",
        views.get_saved_cards,
        name="saved_cards",
    ),

    path(
        "pay-with-saved-card/",
        views.pay_with_saved_card,
        name="pay_with_saved_card",
    ),
    path(
        "tokenized-payment-result/",
        views.tokenized_payment_result,
        name="tokenized_payment_result",
    ),
]
