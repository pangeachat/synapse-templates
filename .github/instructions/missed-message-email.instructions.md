---
applyTo: "templates/notif_mail*,templates/notif.txt,templates/room.txt,templates/_brand_email_*"
description: "The missed-message email Synapse sends — what it contains, its footer and unsubscribe link, and the shared brand layout it and the course invite use."
---

# Missed-Message Email

Synapse sends this email when someone still has unread messages about 10 minutes after they arrive. When it is sent and how often belong to Synapse; the `missed_message` category and its rules are in the org [user-communication-controls](../../../.github/.github/instructions/user-communication-controls.instructions.md) doc. These templates decide only what the email contains and how it looks.

## Content

- A greeting, then one summary line. Synapse reuses the subject line as that summary, so the template drops its "[Pangea Chat]" prefix.
- One block per room, titled with the room name; a course ping shows the course name and the ping text. Each block lists the unread messages (sender, time, text) and one "Open in Pangea Chat" button that links to the room in the app.
- Images and files are named ("Sent an image", "Sent a file: name"), not shown. Chat media needs a signed-in request, so an email client cannot load it.
- A room invite shows a "Join the conversation" button instead of messages.
- The plain-text part carries the same content.

## Footer

The brand footer, with the receiving reason "You're receiving this because you have unread messages on Pangea Chat." and the Unsubscribe link Synapse signs. That link opens a confirm page and does not unsubscribe on its own; see the module's [notice-delivery doc](../../../synapse-pangea-chat/.github/instructions/notice-delivery.instructions.md#the-missed-message-link).

## Brand layout

`_brand_email_base.html` and `_brand_email_footer.html` are copies of the module's notice-email layout, which is generated from the marketing template in pangeachat/admin, so every Pangea email looks the same. This email and the course invite extend it. The layout is table-based so Gmail, Outlook and Apple Mail render it the same way. Keep the copies identical to the module's files, apart from the footer include name and the terms link: the source links to `/terms`, which returns 404, and the copies link to `/terms-of-service`.
