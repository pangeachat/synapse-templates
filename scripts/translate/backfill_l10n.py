"""Backfill sign-up/login page translations for every L1 language that lacks a catalog.

Fetches the L1 language list from the CMS (the cross-service source of truth --
every language there is LLM-supported, so it belongs as an L1), diffs it against
the existing `l10n/*.json` catalogs, and runs `translate_gemini.py` for each
missing one, several in parallel. Resumable (skips locales that already exist)
and tolerant of a single language failing (logged, not fatal).

`--refresh` also re-runs any existing catalog that is missing an English key --
the remediation for the blocking half of the l10n-sync CI gate. These catalogs
are ~25 strings, so re-translating a whole locale is cheaper than the client's
per-key top-up script and leaves the locale internally consistent.

Design: .github/instructions/localization.instructions.md.

Prereqs: Vertex auth as documented in translate_gemini.py. Run
`uv run scripts/translate/emit_l10n.py` afterwards to regenerate the templates.

Usage:
  uv run scripts/translate/backfill_l10n.py [--refresh] [--workers 10] [--cms-url <url>]
"""

# /// script
# requires-python = ">=3.11"
# dependencies = ["google-genai>=1.0", "google-auth"]
# ///

import argparse
import concurrent.futures
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

from translate_gemini import record_provenance

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
L10N = REPO / "l10n"
DEFAULT_CMS = "https://api.staging.pangea.chat/cms/api/languages?limit=500"

# Script-variant catalogs the browser can ask for that aren't bare base codes
# in the CMS list. `zh-TW`/`zh-HK`/`zh-Hant` all resolve to this one catalog in
# templates/l10n.js; every other regional variant falls back to its base
# language, whose copy is identical.
EXTRA_LOCALES = ["zh-Hant"]

SOURCE = "en"  # hand-authored; never a translation target
RESERVED = {SOURCE, "ai-translated-keys"}


def existing_locales() -> set:
    """Translated locales -- excludes the English source and the provenance file."""
    return {p.stem for p in L10N.glob("*.json")} - RESERVED


def english_keys() -> set:
    en = json.loads((L10N / "en.json").read_text(encoding="utf-8"))
    return {k for k in en if not k.startswith("@")}


def incomplete_locales() -> list:
    """Existing catalogs missing at least one English key -- what the CI gate blocks on."""
    wanted = english_keys()
    out = []
    for locale in sorted(existing_locales()):
        have = json.loads((L10N / f"{locale}.json").read_text(encoding="utf-8"))
        if wanted - set(have):
            out.append((locale, None))
    return out


def missing_l1s(cms_url: str) -> list:
    docs = json.load(urllib.request.urlopen(cms_url, timeout=30))["docs"]
    # English is an L1 in the CMS list, but its catalog is the source the
    # others are translated from -- never round-trip it through the translator.
    have = existing_locales() | {SOURCE}
    seen, rows = set(), []
    for d in docs:
        code = d["language_code"]
        if "-" in code:  # translate by base locale, not regional variant
            continue
        base = code.split("-")[0]
        if base in have or base in seen:
            continue
        seen.add(base)
        rows.append((base, d.get("language_name", "").strip()))
    for code in EXTRA_LOCALES:
        if code not in have:
            rows.append((code, None))  # name resolves from the CMS script subtag
    return sorted(rows)


def run_one(cn: tuple) -> str:
    code, name = cn
    cmd = [sys.executable, str(HERE / "translate_gemini.py"),
           "--lang", code, "--l10n", str(L10N), "--no-provenance"]
    if name:
        cmd += ["--name", name]
    r = subprocess.run(cmd, capture_output=True, text=True)
    (HERE / f".backfill_{code}.log").write_text(r.stdout + r.stderr)
    return f"{'OK' if r.returncode == 0 else 'FAIL'} {code} ({name or 'name from CMS'})"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--cms-url", default=DEFAULT_CMS)
    ap.add_argument(
        "--refresh", action="store_true",
        help="also re-translate existing catalogs that are missing an English key",
    )
    args = ap.parse_args()

    langs = missing_l1s(args.cms_url)
    print(f"{len(langs)} L1 language(s) missing a catalog")
    if args.refresh:
        stale = [row for row in incomplete_locales() if row[0] not in {c for c, _ in langs}]
        print(f"{len(stale)} existing catalog(s) missing English key(s)")
        langs += stale

    if not langs:
        print("Nothing to do.")
        return

    done, failed = 0, []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for result in ex.map(run_one, langs):
            done += 1
            print(f"[{done}/{len(langs)}] {result}", flush=True)
            if result.startswith("FAIL"):
                failed.append(result)

    # Provenance is recorded here, once: the workers run with --no-provenance
    # because parallel read-modify-write of one JSON file loses entries.
    wrote = sorted(existing_locales() & {c for c, _ in langs})
    record_provenance(L10N, {c: sorted(english_keys() & set(
        json.loads((L10N / f"{c}.json").read_text(encoding="utf-8")))) for c in wrote})

    print(f"\n=== done. {len(failed)} failures ===")
    for f in failed:
        print(" ", f)
    print("\nNext: uv run scripts/translate/emit_l10n.py")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
