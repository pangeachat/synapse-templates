---
applyTo: "templates/course_invite*"
---

# Course Invite Email Template

Cross-repo design: [conference-course-invite.instructions.md](../../../.github/.github/instructions/teacher-funnel.instructions.md)
Brand tokens: [design-tokens.instructions.md](../../../.github/.github/instructions/design-tokens.instructions.md)
Brand assets (the logo this template loads from the CDN): [design-system.instructions.md](../../../business/.github/instructions/design-system.instructions.md)

## Design

Jinja2 HTML + TXT templates (`course_invite.html`, `course_invite.txt`) for the invite email sent by the Synapse `invite_by_email` endpoint.

**Content** — all derived from room state, not passed by caller:
- Course title, description, banner image
- Inviter name(s) + avatar(s) — all human users at the highest power level in the room
- "Join Your Course" CTA → deep link with access code
- Optional personal message from inviter

**Constraints**:
- Extends the shared brand layout `_brand_email_base.html`, the same one the missed-message email uses; see [missed-message-email.instructions.md](missed-message-email.instructions.md#brand-layout). It shows no Unsubscribe link, because course invitations are not yet refusable.
- Deployed via ansible (same pattern as registration/password-reset templates)

## Future Work

- Localized templates for non-English conferences — no issue yet
