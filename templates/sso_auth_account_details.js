/*
  Pangea fork of Synapse's default sso_auth_account_details.js (v1.124.0).
  Delta from upstream: pressing Continue while the async username
  availability check is pending remembers the submit intent and submits the
  form automatically once the check passes. Upstream silently swallows the
  first click and requires a second one.
  - User-facing strings come from the catalog via PangeaL10n.t (see l10n.js and
  .github/instructions/localization.instructions.md), not from string literals.
*/
const usernameField = document.getElementById("field-username");
const usernameOutput = document.getElementById("field-username-output");
const form = document.getElementById("form");

// needed to validate on change event when no input was changed
let needsValidation = true;
let isValid = false;
// Pangea: set when the user tried to submit while validation was pending;
// the availability-check callback completes the submission.
let submitPending = false;

function throttle(fn, wait) {
    let timeout;
    const throttleFn = function() {
        const args = Array.from(arguments);
        if (timeout) {
            clearTimeout(timeout);
        }
        timeout = setTimeout(fn.bind.apply(fn, [null].concat(args)), wait);
    };
    throttleFn.cancelQueued = function() {
        clearTimeout(timeout);
    };
    return throttleFn;
}

function checkUsernameAvailable(username) {
    let check_uri = 'check?username=' + encodeURIComponent(username);
    return fetch(check_uri, {
        // include the cookie
        "credentials": "same-origin",
    }).then(function(response) {
        if(!response.ok) {
            // for non-200 responses, raise the body of the response as an exception
            return response.text().then((text) => { throw new Error(text); });
        } else {
            return response.json();
        }
    }).then(function(json) {
        if(json.error) {
            return {message: json.error};
        } else if(json.available) {
            return {available: true};
        } else {
            return {message: PangeaL10n.t("accountDetails.errorNotAvailable", {username: username})};
        }
    });
}

const allowedUsernameCharacters = new RegExp("^[a-z0-9\\.\\_\\-\\/\\=]+$");

function reportError(error) {
    submitPending = false;
    throttledCheckUsernameAvailable.cancelQueued();
    usernameOutput.innerText = error;
    usernameOutput.classList.add("error");
    usernameField.parentElement.classList.add("invalid");
    usernameField.focus();
}

function validateUsername(username) {
    isValid = false;
    needsValidation = false;
    usernameOutput.innerText = "";
    usernameField.parentElement.classList.remove("invalid");
    usernameOutput.classList.remove("error");
    if (!username) {
        return reportError(PangeaL10n.t("accountDetails.errorRequired"));
    }
    if (username.length > 255) {
        return reportError(PangeaL10n.t("accountDetails.errorTooLong"));
    }
    if (!allowedUsernameCharacters.test(username)) {
        return reportError(PangeaL10n.t("accountDetails.errorInvalidCharacters", {
            allowed_characters: PangeaL10n.t("accountDetails.allowedCharacters"),
        }));
    }
    usernameOutput.innerText = PangeaL10n.t("accountDetails.checking");
    throttledCheckUsernameAvailable(username);
}

function completePendingSubmit() {
    if (submitPending) {
        submitPending = false;
        // Native submit: bypasses the submit listener, so no re-validation loop.
        form.submit();
    }
}

const throttledCheckUsernameAvailable = throttle(function(username) {
    const handleError = function(err) {
        // don't prevent form submission on error
        usernameOutput.innerText = "";
        isValid = true;
        completePendingSubmit();
    };
    try {
        checkUsernameAvailable(username).then(function(result) {
            if (!result.available) {
                reportError(result.message);
            } else {
                isValid = true;
                usernameOutput.innerText = "";
                completePendingSubmit();
            }
        }, handleError);
    } catch (err) {
        handleError(err);
    }
}, 500);

form.addEventListener("submit", function(evt) {
    if (needsValidation) {
        submitPending = true;
        validateUsername(usernameField.value);
        evt.preventDefault();
        return;
    }
    if (!isValid) {
        submitPending = true;
        evt.preventDefault();
        usernameField.focus();
        return;
    }
});
usernameField.addEventListener("input", function(evt) {
    submitPending = false;
    validateUsername(usernameField.value);
});
usernameField.addEventListener("change", function(evt) {
    if (needsValidation) {
        validateUsername(usernameField.value);
    }
});
