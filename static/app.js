function showTab(tabName) {

    document.querySelectorAll(".tab-content").forEach(section => {
        section.classList.remove("active");
    });

    document.querySelectorAll(".tab-button").forEach(button => {
        button.classList.remove("active");
    });

    document.getElementById(tabName).classList.add("active");

    event.target.classList.add("active");
}


function setQuestion(question) {
    document.getElementById("question").value = question;
}


async function askQuestion() {

    const question = document.getElementById("question").value.trim();

    if (!question) {
        alert("Please enter a question.");
        return;
    }

    document.getElementById("assistant-loading").classList.remove("hidden");
    document.getElementById("assistant-error").classList.add("hidden");
    document.getElementById("assistant-result").classList.add("hidden");

    try {

        const response = await fetch("/api/ask", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                question: question
            })
        });

        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error);
        }

        document.getElementById("answer").innerText =
            result.answer || "No answer available.";

        document.getElementById("status").innerText =
            result.status || "Unknown";

        const calculationSection =
            document.getElementById("calculation-section");

        if (result.calculation) {
            calculationSection.classList.remove("hidden");

            document.getElementById("calculation").innerText =
                result.calculation;
        } else {
            calculationSection.classList.add("hidden");
        }

        const sources = document.getElementById("sources");

        sources.innerHTML = "";

        if (result.sources && result.sources.length > 0) {

            result.sources.forEach(source => {

                const li = document.createElement("li");

                li.innerText = source;

                sources.appendChild(li);
            });

        } else {

            const li = document.createElement("li");

            li.innerText = "None";

            sources.appendChild(li);
        }

        document.getElementById("assistant-result")
            .classList.remove("hidden");

    } catch (error) {

        document.getElementById("assistant-error").innerText =
            "Could not answer question: " + error.message;

        document.getElementById("assistant-error")
            .classList.remove("hidden");

    } finally {

        document.getElementById("assistant-loading")
            .classList.add("hidden");
    }
}


function getValue(id) {
    return document.getElementById(id).value;
}


function getCheckbox(id) {
    return document.getElementById(id).checked;
}


function yesNoUnknown(id) {

    return getCheckbox(id) ? "yes" : "unknown";
}


async function scoreLead() {

    const payload = {

        source: getValue("source"),

        city: getValue("city"),

        area: getValue("area") || null,

        property_type: getValue("property_type"),

        budget_pkr_lac:
            Number(getValue("budget_pkr_lac")),

        bedrooms:
            Number(getValue("bedrooms")),

        is_overseas:
            getCheckbox("is_overseas"),

        referred_by_existing_client:
            getCheckbox("referred_by_existing_client"),

        has_financing_approved:
            getCheckbox("has_financing_approved"),

        purchase_timeframe:
            getValue("purchase_timeframe"),

        budget_inventory_match:
            getValue("budget_inventory_match"),

        payment_method:
            getValue("payment_method"),

        purpose:
            getValue("purpose"),

        selected_project_or_unit_type:
            yesNoUnknown("selected_project_or_unit_type"),

        preferred_location_match:
            yesNoUnknown("preferred_location_match"),

        contact_verified:
            yesNoUnknown("contact_verified"),

        has_prior_mgc_relationship:
            yesNoUnknown("has_prior_mgc_relationship"),

        initial_intent_level:
            getValue("initial_intent_level"),

        previous_inquiry_count:
            Number(getValue("previous_inquiry_count"))
    };


    document.getElementById("score-loading")
        .classList.remove("hidden");

    document.getElementById("score-error")
        .classList.add("hidden");

    document.getElementById("score-result")
        .classList.add("hidden");


    try {

        const response = await fetch("/api/score", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify(payload)
        });


        const result = await response.json();


        if (!result.success) {
            throw new Error(result.error);
        }


        document.getElementById("score-percent").innerText =
            result.score_percent.toFixed(1) + "%";


        document.getElementById("score-note").innerText =
            result.note ||
            "Use this estimate to prioritize sales follow-up.";


        document.getElementById("score-result")
            .classList.remove("hidden");


    } catch (error) {

        document.getElementById("score-error").innerText =
            "Could not score lead: " + error.message;

        document.getElementById("score-error")
            .classList.remove("hidden");

    } finally {

        document.getElementById("score-loading")
            .classList.add("hidden");
    }
}


async function loadModelInfo() {

    try {

        const response =
            await fetch("/api/model-info");

        const result =
            await response.json();

        if (result.model) {

            let text =
                "Model: " + result.model;

            if (typeof result.average_precision === "number") {

                text +=
                    " | Average Precision: " +
                    result.average_precision.toFixed(4);
            }

            document.getElementById("model-info")
                .innerText = text;
        }

    } catch (error) {

        console.log("Could not load model info.");
    }
}


loadModelInfo();