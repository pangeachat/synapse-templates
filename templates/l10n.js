/*
  Client-side localization runtime for the Synapse-served pages.

  Synapse renders these templates with no locale in scope (see
  .github/instructions/localization.instructions.md), so the copy is shipped as
  a per-page string table and rendered in the browser instead. _base.html
  includes this file in <head> and calls PangeaL10n.apply() at the end of
  <body>; each localized page includes its generated table
  (templates/l10n_<page>.js, emitted by scripts/translate/emit_l10n.py) and,
  where its copy has placeholders, sets window.PANGEA_L10N_VARS from Jinja.

  Markup contract for a page:
    data-l10n="key"                  set the element's text from the catalog
    data-l10n="key" data-l10n-attr="value"
                                     set that attribute instead (e.g. submit
                                     buttons, whose label is an attribute)
    data-l10n-html="key"             set innerHTML; only for catalog strings
                                     that carry inline markup. Placeholder
                                     values are HTML-escaped on the way in.
    window.PANGEA_L10N_TITLE = "key" set document.title

  Elements carrying data-l10n are left EMPTY in the template on purpose: text
  is rendered from the catalog rather than replacing English already on the
  page, so a learner never sees a flash of English before their own language.

  Jinja note: this file is pulled into the templates by an include tag, so it
  is itself parsed as a Jinja template and must never contain a Jinja
  delimiter -- an open brace followed by another brace, a percent, or a hash.
  The placeholder regex below is written with escaped braces for that reason;
  do not "simplify" it. Same constraint on the generated tables, which is why
  emit_l10n.py escapes every brace it writes.
*/
(function (global) {
    "use strict";

    var FALLBACK = "en";
    // Right-to-left base languages we ship a catalog for. Without this the
    // Arabic/Hebrew/Persian copy renders into an LTR layout, which is its own
    // kind of "not in your language".
    var RTL = ["ar", "fa", "he", "ps", "sd", "ug", "ur", "yi"];
    var PLACEHOLDER = /\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}/g;
    var HTML_ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

    var resolved = null;

    function strings() {
        return global.PANGEA_L10N_STRINGS || null;
    }

    // Match by base language, dropping region -- region doesn't change the
    // copy. Traditional Chinese is the one exception: it is a separate
    // catalog, so the script subtag (and the regions that imply it) wins.
    // Mirrors LocaleProvider.setLocale in the client.
    function normalize(tag) {
        var parts = String(tag).replace(/_/g, "-").split("-");
        var base = parts[0].toLowerCase();
        if (base === "zh") {
            for (var i = 1; i < parts.length; i++) {
                var sub = parts[i].toLowerCase();
                if (sub === "hant" || sub === "tw" || sub === "hk" || sub === "mo") {
                    return "zh-Hant";
                }
            }
        }
        return base;
    }

    function locale() {
        if (resolved !== null) {
            return resolved;
        }
        var table = strings();
        var prefs = (global.navigator && navigator.languages && navigator.languages.length)
            ? navigator.languages
            : [(global.navigator && navigator.language) || FALLBACK];
        resolved = FALLBACK;
        if (table) {
            for (var i = 0; i < prefs.length; i++) {
                if (!prefs[i]) {
                    continue;
                }
                var code = normalize(prefs[i]);
                if (table[code]) {
                    resolved = code;
                    break;
                }
            }
        }
        return resolved;
    }

    function escapeHtml(value) {
        return String(value).replace(/[&<>"']/g, function (ch) {
            return HTML_ESCAPES[ch];
        });
    }

    function merge(extra) {
        var out = {};
        var page = global.PANGEA_L10N_VARS || {};
        var key;
        for (key in page) {
            if (Object.prototype.hasOwnProperty.call(page, key)) {
                out[key] = page[key];
            }
        }
        for (key in extra) {
            if (Object.prototype.hasOwnProperty.call(extra, key)) {
                out[key] = extra[key];
            }
        }
        return out;
    }

    // Per-key fallback: a locale that is missing (or has an empty) value for
    // one key still renders every other key in its own language.
    function lookup(key) {
        var table = strings();
        if (!table || !key) {
            return null;
        }
        var own = table[locale()];
        var value = own ? own[key] : null;
        if (typeof value !== "string" || value === "") {
            value = table[FALLBACK] ? table[FALLBACK][key] : null;
        }
        return typeof value === "string" ? value : null;
    }

    function substitute(template, vars, escape) {
        return template.replace(PLACEHOLDER, function (match, name) {
            if (!Object.prototype.hasOwnProperty.call(vars, name)) {
                return "";
            }
            var value = vars[name];
            if (value === null || value === undefined) {
                return "";
            }
            return escape ? escapeHtml(value) : String(value);
        });
    }

    function t(key, vars) {
        var raw = lookup(key);
        return raw === null ? "" : substitute(raw, merge(vars), false);
    }

    // Only the catalog string may carry markup (an allowlist the translation
    // validator enforces); placeholder values are always escaped, so a server
    // value such as display_url can never inject markup.
    function tHtml(key, vars) {
        var raw = lookup(key);
        return raw === null ? "" : substitute(raw, merge(vars), true);
    }

    function each(nodes, fn) {
        for (var i = 0; i < nodes.length; i++) {
            fn(nodes[i]);
        }
    }

    function apply(root) {
        if (!strings()) {
            return;
        }
        var code = locale();
        document.documentElement.setAttribute("lang", code);
        document.documentElement.setAttribute("dir", RTL.indexOf(code) === -1 ? "ltr" : "rtl");
        if (global.PANGEA_L10N_TITLE) {
            document.title = t(global.PANGEA_L10N_TITLE);
        }
        var scope = root || document;
        each(scope.querySelectorAll("[data-l10n]"), function (el) {
            var text = t(el.getAttribute("data-l10n"));
            var attr = el.getAttribute("data-l10n-attr");
            if (attr) {
                el.setAttribute(attr, text);
            } else {
                el.textContent = text;
            }
        });
        each(scope.querySelectorAll("[data-l10n-html]"), function (el) {
            el.innerHTML = tHtml(el.getAttribute("data-l10n-html"));
        });
    }

    global.PangeaL10n = { t: t, tHtml: tHtml, apply: apply, locale: locale };
})(window);
