# Handoff: continue on the user's Mac

## Goal and user decisions

Build a dataset of food places in Paris: restaurants, bakeries, pâtisseries, cafés, markets, specialist food shops, and related categories. Retain information that can support rankings later. The user explicitly clarified that **AI overviews means Google Maps place summaries, not Google Search AI Overviews**.

The user chose to continue locally on their Mac instead of signing into a browser on Hetzner. Continue from branch `codex/paris-foodie-dataset` in `sachaarbonel/google-maps-selenium`. Implementation commit: `0eb789b`. Do not rebuild the project from scratch.

## What exists

- Python 3.10+, Selenium 4, Beautiful Soup; install with `python -m pip install -e '.[test]'` in a virtual environment.
- `maps.py` delegates to `foodie_maps/cli.py`: `plan`, `collect`, and `export` commands.
- `plan.py`: 24 categories × 20 arrondissements, 480 planned searches.
- `browser.py`: browser startup, cookie dialog handling, bounded result scrolling, place-panel extraction, and optional screenshots/HTML. Verification pages stop collection.
- `parsing.py`: place details and heuristics for explicitly labelled French/English AI summary sections. Ordinary descriptions and review snippets are separate.
- `store.py`: SQLite checkpoints, identity-based deduplication, discovery provenance, historical observations, CSV/JSONL exports, and coverage reports. Unknown/non-Paris addresses have a separate export.
- Ratings, review counts, categories, addresses, coordinates, contact details, source URLs and timestamps are available fields. Missing values remain null. No ranking algorithm has been implemented.

## What was verified, and what was not

**22 offline tests passed on Linux**, including localized parsing, AI-vs-editorial separation, limited-view detection, resumability, exports, and blocked-run behavior. Package installation and CLI entry points were checked.

A live run on 3 October 2026 collected **20 actual Paris places** across six categories, with no pending places left in that small sample. Google served a visibly labelled limited Maps view: ratings/contact details were present, but review counts and AI summaries were unavailable. **Zero AI summaries were collected. AI extraction is tested on synthetic fixtures and is NOT yet verified against a live AI summary.** Signing in may help, but is not a proven fix.

Status values are `found`, `not_observed`, and `unavailable_limited_view`. Preserve this distinction. Do not relabel generic descriptions as AI summaries or fabricate missing text.

The full city collection has not run. Even all 480 searches would be a bounded discovery process, not a guaranteed census of every Paris food business.

## Next work on the Mac

1. Read `README.md`, install the project, and run the tests on macOS. Verify Chrome is installed.
2. Help the user sign into Google Maps manually in a **dedicated local Chrome profile**. The server login/profile does not transfer to the Mac. From the repository directory, a standard macOS launch command is:

   ```sh
   open -na "Google Chrome" --args \
     --user-data-dir="$PWD/.chrome-profile" \
     'https://www.google.com/maps/search/restaurants+Paris/'
   ```

   Have the user check whether an actual AI summary is visible for a place. Login is a user action; do not read or export credentials/cookies. Close the dedicated Chrome instance completely before Selenium reuses its profile.

3. Start with a visible browser and a small collection:

   ```sh
   source .venv/bin/activate
   python maps.py collect --profile-dir "$PWD/.chrome-profile" \
     --categories restaurants bakeries --arrondissements 11 \
     --max-queries 2 --max-places 5 --max-results 5 --save-evidence
   ```

   Do not use the Linux `--no-sandbox` flag on the Mac. Use `--refresh` deliberately when revisiting already-saved places after login or a parser fix. A database processes its existing pending queue first, even if the new command selects different categories.

4. Inspect a real place that exposes an AI summary. Validate its disclosure, summary boundaries, source links, review count, and exported record. The current collector only scrolls the overview panel; it may need targeted expansion or another tab if that is where the actual summary appears. Fix against observed markup and add a regression fixture with account details removed. If summaries remain unavailable, report that rather than claiming live support.
5. Once the small run is verified, expand coverage gradually. Keep category, review volume, freshness, and provenance available for later ranking work.

## Files that are not on GitHub

`data/`, `.chrome-profile/`, virtual environments, and browser evidence are ignored. The 20-place sample and SQLite history remain only on the Hetzner workspace; cloning this branch will not download them. The old tracked `results.csv` is a historical hotel dataset, not the new Paris sample.

The temporary remote-browser services on Hetzner were stopped. No remote desktop or SSH tunnel is needed for the Mac workflow. Do not restart that setup unless the user asks.
