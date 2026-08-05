"""Translate one locale's `l10n/<lang>.json` from `l10n/en.json` using Gemini on
Vertex AI, preserving Jinja placeholders and validating every value before writing.

Design: see .github/instructions/localization.instructions.md and the cross-repo
language-list doc (L1 = LLM-supported). Ported from the client's
scripts/translate/translate_gemini.py; the differences are the catalog format
(flat JSON, not arb) and the validator: our placeholders are Jinja's
`{{ server_name }}`, not ICU's `{count}`, and there are no plurals to preserve
-- but a handful of strings carry inline markup, which is allowlisted instead.

Auth -- Vertex AI (SA / ADC, Cloud Billing), NOT the deprecated AI Studio
API-key path (its prepaid pool depletes silently). Set:
  GOOGLE_APPLICATION_CREDENTIALS  path to a cloud-platform-scoped SA JSON
                                  (or run `gcloud auth application-default login`)
  VERTEX_PROJECT   GCP project (default: pangea-chat-dev-llm)
  VERTEX_LOCATION  Vertex region (default: "global", serves all Gemini GA models)

Usage:
  uv run scripts/translate/translate_gemini.py --lang pt --name Portuguese
  # optional: --l10n <dir> (default l10n), --limit N (smoke test), --dry
Re-run the emitter afterwards: uv run scripts/translate/emit_l10n.py
"""

# /// script
# requires-python = ">=3.11"
# dependencies = ["google-genai>=1.0", "google-auth"]
# ///

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

BATCH = 80
# Translation needs no reasoning. Flash allows thinking_budget=0 (fastest);
# Pro forbids 0, so it gets its floor (128). Flash is ~4x faster with
# near-identical quality on short UI strings -- the default for bulk backfill;
# use Pro (--model gemini-2.5-pro) when a locale warrants the extra quality.
_THINKING_FLOOR = {"gemini-2.5-pro": 128}

# Jinja placeholders -- `{{ server_name }}`, whitespace optional. The client's
# equivalent matches single-brace ICU tokens and would match nothing here, so a
# translation that dropped `{{ server_name }}` would sail through unvalidated.
# ASCII identifiers only, matching what the templates actually pass.
VAR_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")

# Inline markup a catalog value may carry. The renderer feeds these strings to
# innerHTML (placeholder values escaped first), so anything outside this list
# is rejected rather than shipped.
TAG_RE = re.compile(r"<[^>]*>")
ALLOWED_TAGS = {"<strong>", "</strong>", "<br>"}

# Prompt language names come from the CMS `languages` collection -- the cross-service
# source of truth for language metadata (org language-list.instructions.md). Its
# `language_name` + ISO 15924 `script` fields disambiguate script-variant locales
# (zh-CN "Chinese (Simplified)" script Hans vs zh-TW "Chinese (Traditional)" script
# Hant): a bare name like "Chinese" once yielded Traditional characters for the
# Simplified `zh` catalog (caught by hand in client#7744).
CMS_LANGUAGES_URL = "https://api.staging.pangea.chat/cms/api/languages?limit=500"

# Unicode CLDR likely-subtags, NOT project opinion: the script a bare base code
# implies when its language family spans multiple scripts (CLDR says bare `zh`
# is Hans). Only consulted for base-code catalogs in multi-script families;
# extend from CLDR if such a family ever gains a bare-code catalog.
CLDR_LIKELY_SCRIPT = {"zh": "Hans"}


def fetch_cms_languages(url: str = CMS_LANGUAGES_URL) -> list:
    """The CMS `languages` docs; [] when unreachable (resolution then falls back
    to BCP-47 phrasing, which stays unambiguous for script-variant locales)."""
    import urllib.request

    try:
        return json.load(urllib.request.urlopen(url, timeout=30))["docs"]
    except Exception as e:
        print(f"CMS language fetch failed ({e}); falling back to BCP-47 tags in prompts")
        return []


def resolve_display_name(locale_code: str, docs: list, explicit: str | None = None) -> str:
    """The prompt name for a catalog locale code, from CMS data.

    Order: an explicit operator-supplied name; the family entry matching the
    code's script (subtag, or CLDR-likely for bare codes in multi-script
    families); the exact full-code entry; the bare-base entry when the family
    has one script; else a BCP-47 tag phrase (script-tagged, so still
    unambiguous with no CMS).
    """
    if explicit:
        return explicit
    code = locale_code.replace("_", "-")
    base = code.split("-")[0].lower()
    family = [d for d in docs if d["language_code"].split("-")[0].lower() == base]
    regional_scripts = {d.get("script") for d in family if "-" in d["language_code"] and d.get("script")}
    multi_script = len(regional_scripts) > 1

    script = next((s for s in code.split("-")[1:] if len(s) == 4 and s.isalpha()), None)
    if script is None and (multi_script or not family):
        # Unknown family (CMS unreachable) counts as possibly multi-script.
        script = CLDR_LIKELY_SCRIPT.get(base)

    if script:
        for d in family:
            if (d.get("script") or "").lower() == script.lower():
                return d["language_name"]

    exact = next((d for d in family if d["language_code"].lower() == code.lower()), None)
    if exact and not (multi_script and "-" not in exact["language_code"]):
        return exact["language_name"]
    if family and not multi_script:
        return family[0]["language_name"]

    tag = code if ("-" in code or not script) else f"{code}-{script}"
    return f"the locale with BCP-47 tag '{tag}'"


PROMPT = """You are a professional software-localization translator. Translate the VALUES of the following JSON object from English into {name}. This is the sign-up and login page copy for a language-learning chat app -- the first thing a new learner reads.

Rules -- follow exactly:
- Return ONLY a JSON object mapping each original key to its translated value. No prose, no markdown fences.
- Keep every key unchanged.
- Preserve placeholders EXACTLY: double-brace tokens such as {{{{ server_name }}}}, {{{{ display_url }}}} and {{{{ username }}}} must appear verbatim, untranslated, including both braces and the spacing, in whatever position reads naturally in {name}.
- Do not add, drop, or duplicate placeholders.
- Preserve inline HTML tags exactly as they appear (<strong>, </strong>, <br>). Do not add tags that are not in the English value, and do not translate tag names.
- "Pangea Chat" is a product name: leave it untranslated.
- Punctuation-only values (for example a list of allowed characters like ". , _ - / =") must keep those characters exactly; translate only the words around them.
- Use natural, native-quality {name}; match the app's friendly, concise tone.
- Use the standard script and orthography of exactly this locale -- never substitute a different script variant of the same language (e.g. never Traditional characters for a Simplified-Chinese locale, or vice versa).

JSON to translate:
{payload}"""


def var_set(s: str) -> set:
    return set(VAR_RE.findall(s))


def tag_list(s: str) -> list:
    return sorted(t.lower().replace(" ", "").replace("/>", ">") for t in TAG_RE.findall(s))


def validate(en_val: str, tr_val: str) -> str | None:
    """Return an error string if the translation is structurally wrong, else None."""
    if not isinstance(tr_val, str) or not tr_val.strip():
        return "empty"
    if var_set(en_val) != var_set(tr_val):
        return f"placeholder mismatch en={sorted(var_set(en_val))} tr={sorted(var_set(tr_val))}"
    # A lone `{` or `}` means the model rewrote a placeholder's braces; the
    # var_set check above can't see that because the token stopped matching.
    if en_val.count("{") != tr_val.count("{") or en_val.count("}") != tr_val.count("}"):
        return f"brace count differs en={en_val.count('{')}/{en_val.count('}')} tr={tr_val.count('{')}/{tr_val.count('}')}"
    if tag_list(en_val) != tag_list(tr_val):
        return f"inline markup mismatch en={tag_list(en_val)} tr={tag_list(tr_val)}"
    disallowed = [t for t in tag_list(tr_val) if t not in ALLOWED_TAGS]
    if disallowed:
        return f"disallowed markup {disallowed}"
    if "```" in tr_val:
        return "markdown fence leaked into value"
    return None


def record_provenance(l10n: Path, per_locale: dict) -> None:
    """Mark keys as machine-translated, so a later native-speaker correction is
    distinguishable from AI output. Lists are sorted, so a new key adds one line."""
    path = l10n / "ai-translated-keys.json"
    prov = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    for locale, keys in per_locale.items():
        prov[locale] = sorted(set(prov.get(locale, [])) | set(keys))
    path.write_text(
        json.dumps(dict(sorted(prov.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


def vertex_client() -> genai.Client:
    import google.auth
    import google.auth.exceptions

    try:
        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
    except google.auth.exceptions.DefaultCredentialsError:
        sys.exit(
            "No Google credentials found. Run:\n"
            "    gcloud auth application-default login\n"
            "(ADC tokens expire roughly weekly -- re-run it if this worked before.)"
        )
    # Default to the dev LLM pool (the project that backs engineers' local
    # creds) rather than the ADC default -- user accounts typically lack
    # Vertex perms on whatever project gcloud happens to default to.
    project = os.environ.get("VERTEX_PROJECT") or "pangea-chat-dev-llm"
    location = os.environ.get("VERTEX_LOCATION", "global")
    print(f"Vertex: project={project} location={location}")
    return genai.Client(vertexai=True, project=project, location=location, credentials=creds)


def translate_batch(client: genai.Client, model: str, name: str, batch: dict) -> dict:
    prompt = PROMPT.format(name=name, payload=json.dumps(batch, ensure_ascii=False, indent=2))
    thinking = _THINKING_FLOOR.get(model, 0)
    for attempt in range(6):
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json",
                    thinking_config=types.ThinkingConfig(thinking_budget=thinking),
                ),
            )
        except genai_errors.APIError as e:
            code = getattr(e, "code", None)
            if code in (401, 403):
                sys.exit(
                    f"Vertex AI rejected the request ({code}). Either your ADC token "
                    "expired -- re-run `gcloud auth application-default login` -- or your "
                    "Google account lacks roles/aiplatform.user on the target project "
                    "(default: pangea-chat-dev-llm). Ask Will to add you as a "
                    "vertex_operator in devops/terraform/gcp/dev/llm."
                )
            if code in (429, 500, 503) and attempt < 5:
                time.sleep(2 ** attempt)
                continue
            raise
        text = (resp.text or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```\w*\n?|\n?```$", "", text).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"    JSON parse fail (attempt {attempt + 1}): {e}; retrying")
            time.sleep(2)
    raise RuntimeError("batch failed to parse after retries")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True, help="target locale code, e.g. pt or zh-Hant")
    ap.add_argument("--name", help="prompt language name; omit to resolve from the CMS language list")
    ap.add_argument("--cms-url", default=CMS_LANGUAGES_URL, help="CMS languages endpoint for name resolution")
    ap.add_argument("--l10n", default="l10n", help="catalog dir (default l10n)")
    ap.add_argument("--limit", type=int, default=0, help="translate only first N keys (smoke test)")
    ap.add_argument("--dry", action="store_true", help="validate but do not write the catalog")
    ap.add_argument(
        "--no-provenance", action="store_true",
        help="skip the ai-translated-keys.json update; backfill_l10n.py sets this and "
             "records provenance once, since parallel workers would clobber each other",
    )
    ap.add_argument(
        "--model", default="gemini-2.5-flash",
        help="Gemini model (default gemini-2.5-flash; use gemini-2.5-pro for higher quality)",
    )
    args = ap.parse_args()

    l10n = Path(args.l10n)
    en = json.loads((l10n / "en.json").read_text(encoding="utf-8"))
    keys = [k for k in en if not k.startswith("@")]
    if args.limit:
        keys = keys[: args.limit]

    client = vertex_client()
    docs = [] if args.name else fetch_cms_languages(args.cms_url)
    name = resolve_display_name(args.lang, docs, explicit=args.name)
    print(f"prompt language name: {name}")
    out: dict[str, str] = {}
    errors: list[str] = []
    for i in range(0, len(keys), BATCH):
        chunk = keys[i : i + BATCH]
        tr = translate_batch(client, args.model, name, {k: en[k] for k in chunk})
        for k in chunk:
            if k not in tr:
                errors.append(f"{k}: MISSING from response")
                continue
            err = validate(en[k], tr[k])
            if err:
                errors.append(f"{k}: {err} | en={en[k]!r} tr={tr[k]!r}")
            out[k] = tr[k]
        print(f"  {min(i + BATCH, len(keys))}/{len(keys)} translated")

    print(f"\nTranslated {len(out)}/{len(keys)} keys, {len(errors)} validation errors")
    for e in errors[:40]:
        print("  ERR", e)

    if args.dry:
        print("(dry run -- not writing)")
        return
    if errors:
        # A page that lost its `server_name` slot, or gained a stray tag the
        # renderer would inject verbatim, is worse than an English one.
        sys.exit("Refusing to write catalog with validation errors. Fix and retry.")

    doc = {"@@locale": args.lang, "@@last_modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")}
    doc.update(out)
    (l10n / f"{args.lang}.json").write_text(
        json.dumps(doc, indent=4, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"wrote {args.lang}.json ({len(out)} keys)")

    if not args.no_provenance:
        record_provenance(l10n, {args.lang: sorted(out)})


if __name__ == "__main__":
    main()
