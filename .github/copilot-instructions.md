# synapse-templates — Custom Synapse email and web page templates

Jinja2 HTML/TXT templates served by Synapse for registration verification, password reset, email notifications, and SSO pages. Deployed via ansible (`matrix_synapse_container_image_customizations_templates_*` vars). Uses `pangea.chat` asset URLs for logo and favicon.

`notices.json` names which engagement catalog notice each email template sends and gives sample values for previewing it. The engagement workspace reads it, with the templates, at the tag production deploys; keep it in step when an email template is added, renamed or gains a variable.
