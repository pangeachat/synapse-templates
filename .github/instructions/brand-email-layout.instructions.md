---
applyTo: "templates/_brand_email_*.html,templates/_brand_cta_button.html,scripts/brand_email.py"
description: "The brand email layout every Pangea email uses — its one source in this repo, the generated copies in the other senders, and the drift check that keeps them identical."
---

# Brand email layout

Every email Pangea sends looks the same: a gold bar, the purple header with the horizontal logo, the message, then the footer with the NSF badge, the links to pangea.chat, Privacy and Terms, the company's postal address, the receiving reason and unsubscribe link where the email is refusable, and the copyright line. A change to any of it (a new NSF line, a button shape) is made once, here, and reaches every sender. The layout is table-based so Gmail, Outlook and Apple Mail render it the same way.

## The one source

The layout lives in this repo, in three templates:

- [`_brand_email_base.html`](../../templates/_brand_email_base.html) — the page: header, the content slot, the footer slot.
- [`_brand_email_footer.html`](../../templates/_brand_email_footer.html) — the footer. An email that cannot be refused (the credential emails, the course invite, the course claim emails) sets `show_unsubscribe` to false.
- [`_brand_cta_button.html`](../../templates/_brand_cta_button.html) — the call-to-action button.

**Every call to action is a full-width, fully rounded button.** It matches the shape of the app's own buttons, so an email reads as part of the product (Will, 2026-10-11). The button is styled inline as well as in the page's stylesheet, because many email clients drop the stylesheet. Copy that writes its own button follows the same shape.

This repo owns the layout because it is public, so every other repo's checks can read it without a credential, and because Synapse reads its templates only from here, at the tag the ansible inventory pins. A layout change reaches Synapse's own emails with the next tag and ansible deploy.

## The generated copies

Three other systems send email and cannot read this repo when they send, so each keeps a copy generated from the source by [`scripts/brand_email.py`](../../scripts/brand_email.py). Each copy opens with a header saying it is generated; **NEVER hand-edit a generated copy**, because the next generation overwrites the edit and the drift check fails on it first.

| Sender | Its copy | What differs from the source |
|---|---|---|
| The Synapse module (synapse-pangea-chat): notice delivery and the course claim emails | The three templates, in each of the module's two template folders | Nothing but the header |
| The engagement runner | Its email shell and the button style its renderer applies to every call-to-action link | Rendered from the source with the runner's placeholders in the slots: the title, the language, the content, the receiving reason, and the unsubscribe link and postal address Synapse fills at send time |
| The CMS: the course request and conference signup confirmations | Its email shell, which it fills with each confirmation's body before writing it to Listmonk | Rendered from the source with the CMS's placeholders in the title and content slots. The confirmations are replies to a form, never refusable, so the shell carries no unsubscribe link, and the postal address is printed as is |

Only the slots differ, so a sender cannot change the look without changing the source.

## The drift check

Each sender's checks compare its copy with what the generator produces from this repo's main branch, and fail when they differ: the module's and the CMS's CI check this repo out, and the engagement test suite reads the checkout beside it. A change here therefore turns those checks red until each sender regenerates its copy, which is the point: the layout cannot fork silently. This repo's own CI generates every copy from a changed source, so a source edit that a sender's slots can no longer fill fails in the PR that made it.
