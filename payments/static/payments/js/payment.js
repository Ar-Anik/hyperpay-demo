
document.addEventListener("DOMContentLoaded", function () {

    // ==========================================
    // 1. DJANGO URL CONFIGURATION
    // ==========================================

    const config = document.getElementById("payment-config");

    if (!config) {
        console.error("Payment configuration not found.");
        return;
    }

    const API = {
        createCheckout: config.dataset.createCheckoutUrl,
        registerCard: config.dataset.registerCardUrl,
        verifyRegistration: config.dataset.verifyRegistrationUrl,
        savedCards: config.dataset.savedCardsUrl,
        payWithSavedCard: config.dataset.payWithSavedCardUrl,
        shopperResult: config.dataset.shopperResultUrl,
        registrationResult: config.dataset.registrationResultUrl,
        widgetBaseUrl: config.dataset.widgetBaseUrl,
    };


    // ==========================================
    // 2. DOM ELEMENTS
    // ==========================================

    const checkoutButton = document.getElementById("checkout-button");

    const registerCardButton = document.getElementById(
        "register-card-button"
    );

    const paymentSection = document.getElementById("payment-section");

    const paymentHeading = document.getElementById("payment-heading");

    const hyperpayForm = document.getElementById("hyperpay-form");

    const loadSavedCardsButton = document.getElementById(
        "load-saved-cards-button"
    );

    const savedCardsList = document.getElementById("saved-cards-list");

    const message = document.getElementById("message");

    let checkoutScript = null;


    // ==========================================
    // 3. CSRF TOKEN
    // ==========================================

    function getCsrfToken() {

        const csrfInput = document.querySelector(
            "#csrf-form [name=csrfmiddlewaretoken]"
        );

        return csrfInput ? csrfInput.value : "";
    }


    // ==========================================
    // 4. DISPLAY MESSAGE
    // ==========================================

    function showMessage(text) {
        message.textContent = text;
    }


    // ==========================================
    // 5. POST REQUEST
    // ==========================================

    async function postRequest(
        url,
        payload = {},
        allowUnsuccessfulResult = false
    ) {

        const response = await fetch(url, {

            method: "POST",

            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "X-CSRFToken": getCsrfToken(),
            },

            body: new URLSearchParams(payload),

        });

        let data;

        try {
            data = await response.json();
        } catch (error) {
            throw new Error("Invalid server response.");
        }

        if (!response.ok && !allowUnsuccessfulResult) {
            throw new Error(
                data.message || "Request failed."
            );
        }

        if (!data.success && !allowUnsuccessfulResult) {
            throw new Error(
                data.message || "Request failed."
            );
        }

        return data;
    }


    // ==========================================
    // 6. LOAD HYPERPAY COPYandPAY WIDGET
    // ==========================================

    function loadHyperPayWidget(checkoutId, flow, integrity = null) {

        if (!hyperpayForm || !paymentSection) {
            throw new Error("HyperPay payment form not found.");
        }

        if (!checkoutId) {
            throw new Error("Checkout ID is missing.");
        }


        // Remove previously loaded widget script.
        if (checkoutScript) {
            checkoutScript.remove();
            checkoutScript = null;
        }


        // Clear previous widget content.
        hyperpayForm.innerHTML = "";


        // Set callback URL.
        if (flow === "normal") {

            hyperpayForm.action = API.shopperResult;

            paymentHeading.textContent = "Complete Your Payment";

        } else if (flow === "registration") {

            hyperpayForm.action = API.registrationResult;

            paymentHeading.textContent = "Register Your Card";

        } else {

            throw new Error("Invalid payment flow.");
        }


        // HyperPay widget configuration.
        window.wpwlOptions = {
            style: "card",
            maskCvv: true,
        };


        // Create HyperPay widget script.
        checkoutScript = document.createElement("script");

        checkoutScript.src =
            API.widgetBaseUrl + "v1/paymentWidgets.js?checkoutId=" +
            encodeURIComponent(checkoutId);


        // Apply integrity if provided by HyperPay.
        if (integrity) {
            checkoutScript.integrity = integrity;
            checkoutScript.crossOrigin = "anonymous";
        }


        checkoutScript.onload = function () {

            paymentSection.hidden = false;

            showMessage(
                flow === "registration"
                    ? "Card registration checkout is ready."
                    : "Payment checkout is ready."
            );

        };


        checkoutScript.onerror = function () {

            showMessage(
                "Unable to load HyperPay payment widget."
            );

            checkoutButton.disabled = false;
            registerCardButton.disabled = false;
        };


        document.head.appendChild(checkoutScript);
    }


    // ==========================================
    // 7. NORMAL PAYMENT - COPYandPAY
    // ==========================================

    checkoutButton.addEventListener("click", async function () {

        checkoutButton.disabled = true;

        showMessage("Preparing payment...");


        try {

            const data = await postRequest(
                API.createCheckout
            );


            loadHyperPayWidget(
                data.checkout_id,
                "normal",
                data.integrity
            );


        } catch (error) {

            showMessage(error.message);

            checkoutButton.disabled = false;
        }

    });


    // ==========================================
    // 8. REGISTER CARD - TOKENIZATION
    // ==========================================

    registerCardButton.addEventListener("click", async function () {

        registerCardButton.disabled = true;

        showMessage("Preparing card registration...");


        try {

            const data = await postRequest(
                API.registerCard
            );


            loadHyperPayWidget(
                data.checkout_id,
                "registration",
                data.integrity
            );


        } catch (error) {

            showMessage(error.message);

            registerCardButton.disabled = false;
        }

    });


    // ==========================================
    // 9. LOAD SAVED CARDS
    // ==========================================

    async function loadSavedCards() {

        loadSavedCardsButton.disabled = true;

        savedCardsList.textContent = "Loading saved cards...";


        try {

            const response = await fetch(
                API.savedCards
            );

            const data = await response.json();


            if (!response.ok || !data.success) {

                throw new Error(
                    data.message || "Unable to load saved cards."
                );
            }


            savedCardsList.innerHTML = "";


            if (!data.cards || data.cards.length === 0) {

                savedCardsList.textContent = "No saved cards found.";

                return;
            }


            data.cards.forEach(function (card) {

                const cardContainer = document.createElement("div");

                cardContainer.style.marginBottom = "15px";


                const cardInfo = document.createElement("p");

                cardInfo.textContent =
                    `${card.brand || "Card"} ending in ${card.last_four_digits || "****"}`;


                const payButton = document.createElement("button");

                payButton.type = "button";

                payButton.textContent = "Pay with this card";


                payButton.addEventListener("click", function () {

                    payWithSavedCard(
                        card.id,
                        payButton
                    );

                });


                cardContainer.appendChild(cardInfo);

                cardContainer.appendChild(payButton);

                savedCardsList.appendChild(cardContainer);

            });


            showMessage("Saved cards loaded successfully.");


        } catch (error) {

            savedCardsList.textContent = error.message;

        } finally {

            loadSavedCardsButton.disabled = false;
        }
    }


    loadSavedCardsButton.addEventListener(
        "click",
        loadSavedCards
    );

    // Show cards already registered for this demo customer on page load.
    loadSavedCards();


    // ==========================================
    // 10. PAY WITH SAVED CARD
    // ==========================================

    async function payWithSavedCard(savedCardId, button) {

        button.disabled = true;

        showMessage("Processing saved card payment...");


        try {

            const data = await postRequest(

                API.payWithSavedCard,

                {
                    saved_card_id: savedCardId,
                },

                true

            );

            if (data.redirect && data.redirect.url) {
                const redirect = data.redirect;
                const method = (redirect.method || "POST").toUpperCase();
                const parameters = redirect.parameters || {};

                if (method === "GET") {
                    const redirectUrl = new URL(
                        redirect.url,
                        window.location.href
                    );

                    Object.entries(parameters).forEach(([name, value]) => {
                        redirectUrl.searchParams.append(name, String(value));
                    });

                    window.location.assign(redirectUrl.toString());
                    return;
                }

                if (method !== "POST") {
                    throw new Error("Unsupported HyperPay redirect method.");
                }

                const redirectForm = document.createElement("form");
                redirectForm.method = method;
                redirectForm.action = redirect.url;
                redirectForm.hidden = true;

                Object.entries(parameters).forEach(([name, value]) => {
                    const input = document.createElement("input");
                    input.type = "hidden";
                    input.name = name;
                    input.value = String(value);
                    redirectForm.appendChild(input);
                });

                document.body.appendChild(redirectForm);
                redirectForm.submit();
                return;
            }


            if (data.status === "SUCCESS") {

                showMessage("Payment successful.");

            } else if (data.status === "PENDING") {

                showMessage(
                    "Payment is pending. Verify the transaction status."
                );

            } else if (data.status === "UNKNOWN") {

                showMessage(
                    "Payment outcome is unknown. Verify before retrying."
                );

            } else {

                showMessage(
                    data.message || "Payment failed."
                );
            }


        } catch (error) {

            showMessage(error.message);

        } finally {

            button.disabled = false;
        }
    }

});
