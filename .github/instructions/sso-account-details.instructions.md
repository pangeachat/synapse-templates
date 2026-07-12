---
description: SSO account-details (username picker) page — design intent for the customized Synapse template.
applyTo: templates/sso_auth_account_details.html, templates/sso_auth_account_details.js
---

# SSO Account Details (Username Picker)

Shown once, during first-time SSO registration, when the Synapse OIDC provider
config sets `confirm_localpart: true` (see the Google provider in the ansible
inventories). The user confirms or edits their suggested username; the rest of
the account is created from IdP data. Context: pangeachat/ansible#184.

## Design intent

- **The user chooses exactly one thing: their username.** The upstream
  template offers opt-out checkboxes for avatar, display name, and e-mail from
  the identity provider. We do not offer that choice: the template always
  submits `use_avatar` / `use_display_name` / `use_email` via hidden inputs.
  Rationale: unchecking e-mail silently breaks email-keyed features (course
  invite matching, account communications) with no user benefit — the address
  was already shared with us by signing in through the IdP.
- **One click submits.** Upstream's JS swallows the first Continue click to
  run an async username-availability check and requires a second click. Our
  fork remembers the submit intent and auto-submits when the check passes
  (`submitPending` in the JS). An unavailable or invalid username still shows
  the inline error instead of submitting.

## Upstream tracking

Both files are forks of Synapse `v1.124.0` defaults
(`synapse/res/templates/sso_auth_account_details.{html,js}`); the delta of
each fork is listed in a comment at the top of the file. When bumping
`matrix_synapse_version` in ansible, diff upstream's copies of these files
between versions and port any changes (the POST contract — `username`,
`use_avatar`, `use_display_name`, `use_email` — is defined by
`synapse/rest/synapse/client/pick_username.py`).

## Testing

Use the ansible repo's local stack (`./scripts/local-synapse.sh up`, then
`new-sso-user`) — see "Local SSO Testing (OIDC mock)" in
ansible/.github/instructions/ansible-for-developers.instructions.md. The
local compose mounts this repo's `templates/` into the Synapse container, so
edits here are testable by reloading the flow (restart the synapse container
to pick up template changes).
