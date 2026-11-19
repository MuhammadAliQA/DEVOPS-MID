(function () {
    "use strict";

    let pendingForm = null;

    const dialog = document.createElement("dialog");
    dialog.className = "confirm-dialog";
    dialog.setAttribute("aria-labelledby", "confirm-dialog-title");

    const title = document.createElement("h2");
    title.id = "confirm-dialog-title";
    title.textContent = "Tasdiqlash";

    const message = document.createElement("p");

    const actions = document.createElement("div");
    actions.className = "confirm-actions";

    const cancelButton = document.createElement("button");
    cancelButton.type = "button";
    cancelButton.textContent = "Bekor qilish";

    const confirmButton = document.createElement("button");
    confirmButton.type = "button";
    confirmButton.textContent = "Ha, tasdiqlayman";

    actions.append(cancelButton, confirmButton);
    dialog.append(title, message, actions);
    document.body.appendChild(dialog);

    document.addEventListener("submit", function (event) {
        const form = event.target;

        if (!(form instanceof HTMLFormElement)) return;
        if (!form.hasAttribute("data-confirm")) return;
        if (form.dataset.confirmed === "true") return;

        event.preventDefault();
        pendingForm = form;
        message.textContent = form.getAttribute("data-confirm") || "Davom etasizmi?";

        if (!dialog.open) dialog.showModal();
    }, true);

    cancelButton.addEventListener("click", function () {
        pendingForm = null;
        dialog.close();
    });

    confirmButton.addEventListener("click", function () {
        if (!pendingForm) {
            dialog.close();
            return;
        }

        const form = pendingForm;
        pendingForm = null;
        form.dataset.confirmed = "true";
        dialog.close();
        form.submit();
    });

    dialog.addEventListener("cancel", function () {
        pendingForm = null;
    });
})();