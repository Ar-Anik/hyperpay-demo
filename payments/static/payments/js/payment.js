
document.addEventListener("DOMContentLoaded", function () {

    const checkoutForm = document.getElementById("checkout-form");

    const checkoutButton = document.getElementById("checkout-button");

    const paymentSection = document.getElementById("payment-section");

    const message = document.getElementById("message");


    checkoutForm.addEventListener("submit", async function (event) {

        event.preventDefault();

        checkoutButton.disabled = true;

        message.textContent = "Preparing payment...";

        try {

            const csrfToken = document.querySelector(
                "[name=csrfmiddlewaretoken]"
            ).value;


            // Request Checkout ID from Django Backend.

            const response = await fetch(
                "/payments/create-checkout/",
                {
                    method: "POST",

                    headers: {
                        "X-CSRFToken": csrfToken,
                    },
                }
            );



            const data = await response.json();


            if (!response.ok || !data.success) {

                throw new Error(
                    data.message || "Unable to create checkout."
                );

            }


            // Configure COPYandPAY before loading its script.

            window.wpwlOptions = {
                style: "card",
                maskCvv: true,
            };


            // Configure payment form.

            const paymentForm = document.querySelector(
                ".paymentWidgets"
            );

            paymentForm.action = window.location.origin +
                "/payments/shopper-result/";


            // Load HyperPay COPYandPAY JavaScript.

            const script = document.createElement("script");

            script.src =
                "https://eu-test.oppwa.com/v1/paymentWidgets.js?checkoutId=" +
                encodeURIComponent(data.checkout_id);


            if (data.integrity) {
                script.integrity = data.integrity;
                script.crossOrigin = "anonymous";
            }


            script.onload = function () {
                paymentSection.hidden = false;
                checkoutForm.hidden = true;
                message.textContent = "Checkout is ready.";
            };


            script.onerror = function () {
                message.textContent = "Unable to load HyperPay payment widget.";
                checkoutButton.disabled = false;
            };

            document.head.appendChild(script);

        } catch (error) {
            message.textContent = error.message;
            checkoutButton.disabled = false;
        }
    });
});
