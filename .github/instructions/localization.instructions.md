---
applyTo: "templates/**,l10n/**,scripts/translate/**"
description: "Localization of Synapse-served sign-up, login, and email copy — which surfaces we can localize and why, the browser-locale signal, the string catalog as source of truth, and the translation and drift gates."
---

# Localization — Synapse Templates

Every learner meets Pangea Chat in these pages before they meet the app. A learner whose phone is set to Portuguese should not hit English mid-signup — we offer a language as an L1 only if we can teach in it, so showing English here contradicts the offer. See the client's [localization doc](../../../client/.github/instructions/localization.instructions.md) for the same principle applied to the app UI, and the cross-service [language list](../../.github/.github/instructions/language-list.instructions.md) for what makes a language an L1.

## What we can localize, and what we can't

Synapse has no template localization of its own, so what we can do depends entirely on who renders a given page.

| Surface | Rendered by | Status |
| --- | --- | --- |
| SSO sign-up and login pages | Synapse core | Localized in the browser (below) |
| Registration and course-invite emails | Our own Synapse module | Localizable — the sender chooses the language |
| Password reset, notification, and expiry emails | Synapse core | English. No hook and no language signal exists |

Synapse builds each page's template environment once at startup and renders with a fixed set of values that carries no language. The visitor's browser language reaches the server on every request but is never passed through to the page. Both are true on the current upstream release, and the request to change it has been open upstream since 2021 — so **treat server-side localization of the SSO pages as unavailable** rather than as a near-term option.

## Which language the pages use

The **browser's language setting**, which on a phone follows the system language. No account exists yet at sign-up, so there is no stored L1 to read — the browser is the only signal we have, and it is also the one the learner expects.

Language is resolved by base language, ignoring region, because region doesn't change the copy. Traditional Chinese is the exception and is treated as its own language. Any language we haven't translated, and any individual phrase we haven't translated yet, **falls back to English** rather than rendering blank.

## The string catalog is the source of truth

All user-facing copy lives in a **string catalog**, separate from the pages that display it. The pages are generated from the catalog; the copy is never edited directly in a page. This keeps translation independent of how the pages happen to be rendered today — if Synapse later lets us localize on the server, or we move these pages elsewhere, the catalog and every translation carry over unchanged.

Translations are machine-generated per language and then validated. **A translation that drops or corrupts a placeholder is never written** — a page that has lost its `server name` or `sign-in provider` slot is worse than an English one. Machine-translated copy is recorded as such, so native-speaker corrections can replace it later without being overwritten by a re-run.

## Keeping copy in sync

English copy changes; translations go stale silently. Two rules, enforced automatically on every change:

- **New English copy must be translated before it ships.** Otherwise that phrase reaches every learner in English while the page around it is translated — the exact failure this system exists to prevent. This blocks.
- **Changed English copy warns.** The page still renders in the learner's language, just slightly behind, so re-translating every language isn't worth blocking a copy tweak.

Deployment note: these pages reach learners only when Synapse is redeployed. Merging a translation does not ship it.
