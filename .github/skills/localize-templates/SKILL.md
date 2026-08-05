---
name: localize-templates
description: Use when adding or refreshing translations of the Synapse-served sign-up and login pages — filling newly-added `l10n/en.json` keys into existing locales (the l10n-sync CI gate's remediation), backfilling catalogs for languages that lack one, or re-translating a single locale. Runs the Vertex-Gemini translator with the placeholder-preservation gate, then regenerates the string tables the templates ship.
---

# Backfill / refresh sign-up and login page translations

**MUST READ [localization.instructions.md](../../instructions/localization.instructions.md) first** — it owns which surfaces are localizable and why, the browser-locale signal, the catalog-as-source-of-truth decision, fallback behavior, and the two sync rules the CI gate enforces.

Two things move together here: the **catalog** (`l10n/*.json`, the source of truth) and the **generated string tables** (`templates/l10n_*.js`, what the pages actually ship). Translating without re-emitting changes nothing a learner sees.

## Pick the right script

| Situation | Command |
| --- | --- |
| A PR added key(s) to `l10n/en.json`; the **l10n-sync gate** is failing | `uv run scripts/translate/backfill_l10n.py --refresh` |
| A language has **no `l10n/<lang>.json` at all** (new L1s) | `uv run scripts/translate/backfill_l10n.py --workers 10` |
| Translate or fully re-translate **one locale** | `uv run scripts/translate/translate_gemini.py --lang sw --name Swahili` (smoke test: `--dry`) |
| Only the emitted tables are stale (no translation needed) | `uv run scripts/translate/emit_l10n.py` |

The catalogs are ~25 strings, so `--refresh` re-translates a whole locale rather than topping up individual keys — cheaper than a per-key script and it leaves the locale internally consistent.

## Prereqs (check before running any script)

1. **Locate `uv` and `gcloud` before installing anything.** A missing command on `PATH` often means installed-but-not-wired, not absent — installing again just stacks a second copy. Check the usual homes first:

   ```sh
   for bin in uv gcloud; do
     command -v "$bin" && continue
     for dir in /opt/homebrew/bin /usr/local/bin "$HOME/.local/bin" "$HOME/google-cloud-sdk/bin"; do
       [ -x "$dir/$bin" ] && echo "$bin found at $dir/$bin — add $dir to PATH, don't reinstall" && continue 2
     done
     echo "$bin: not found anywhere — install it"
   done
   ```

   Only if genuinely absent: `brew install uv` / `brew install --cask google-cloud-sdk` (macOS). One install; if a copy exists off-PATH, fix `PATH` (or use the full path) instead.
2. **Google auth**: `gcloud auth application-default login` once per ~week (tokens expire). The scripts print exact remediation on auth failures, including whose access to request.

## After translating (required)

```sh
uv run scripts/translate/emit_l10n.py                            # regenerate templates/l10n_*.js
uv run scripts/translate/emit_l10n.py --check                    # the first CI gate, locally
uv run scripts/translate/check_l10n_sync.py --base origin/main   # the second CI gate, locally
```

Then spot-check before committing:

- **Script-variant locales.** `zh` must be Simplified and `zh-Hant` Traditional — a bare "Chinese" prompt has produced the wrong script before (client#7744). Check both.
- **Placeholders survived.** `{{ server_name }}`, `{{ display_url }}`, `{{ username }}` must be intact in a few locales; the translator refuses to write a catalog that lost one, but eyeball a non-Latin script anyway.
- **The character-list string.** `accountDetails.allowedCharacters` must still contain `. _ - / =` — those are literal, only the words around them translate.

Commit the catalogs, `l10n/ai-translated-keys.json` (machine-translation provenance, so a later native-speaker correction isn't overwritten by a re-run), and the regenerated `templates/l10n_*.js`.

## Adding new copy to a page

1. Add the key to `l10n/en.json`, namespaced by page (`accountDetails.*`, `redirectConfirm.*`, `ssoError.*`, `authSuccess.*`). A new page prefix also needs an entry in `PAGES` in `emit_l10n.py`.
2. Reference it from the template: `data-l10n="key"` (text), plus `data-l10n-attr="value"` for an attribute, or `data-l10n-html="key"` when the string carries inline markup. Leave the element **empty** — the copy is rendered from the catalog, never replaced in place. Contract details are in the header comment of `templates/l10n.js`.
3. Run `backfill_l10n.py --refresh`, then the emitter and both gates above.

## Deploying

Merging a translation does not ship it. These templates are baked into the Synapse image, so the pages change only on a Synapse redeploy via ansible.
