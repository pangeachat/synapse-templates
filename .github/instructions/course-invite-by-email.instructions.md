---
applyTo: "templates/course_invite*"
---

# Course Invite Email Template

Cross-repo design: [conference-course-invite.instructions.md](../../../.github/.github/instructions/conference-course-invite.instructions.md)
Brand tokens: [design-system.instructions.md](../../../business/instructions/design-system.instructions.md)

## Design

Jinja2 HTML + TXT templates (`course_invite.html`, `course_invite.txt`) for the invite email sent by the Synapse `invite_by_email` endpoint.

**Content** — all derived from room state, not passed by caller:
- Course title, description, banner image
- Inviter name(s) + avatar(s) — all human users at the highest power level in the room
- "Join Your Course" CTA → deep link with access code
- Optional personal message from inviter

**Constraints**:
- Standalone HTML (no `_base.html` inheritance) — matches the brand template used by campaign emails
- Table-based layout for Gmail/Outlook/Apple Mail compatibility
- Uses brand palette from the design system: purple gradient header (`#5E3ACF` → `#8560E0`), gold accents (`#FDBF01`), purple CTA button, NSF badge footer
- Deployed via ansible (same pattern as registration/password-reset templates)

## Future Work

- Localized templates for non-English conferences — no issue yet
