# Google Maps foodie dataset — Paris

Discover food places across Paris and collect their Google Maps details, including **explicitly labelled AI summaries when Maps makes them available**. This replaces the original hardcoded hotel experiment with a Selenium 4 command-line collector.

The default search plan covers **24 food categories × 20 arrondissements = 480 searches**: restaurants, bakeries, pâtisseries, cafés, bistros, brasseries, fine dining, street food, brunch, vegetarian/vegan restaurants, crêperies, pizzerias, ice cream, chocolate, cheese, delis, markets, wine bars serving food, seafood, butchers, fishmongers, tea rooms, and food halls.

## Install

Use Python 3.10+ and Chrome/Chromium. Selenium Manager handles the matching driver (network access required on first run).

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python maps.py --help
```

`foodie-maps` and `python -m foodie_maps` are equivalent entry points after installation.

## Start small

Inspect the plan without opening a browser:

```sh
python maps.py plan --categories restaurants bakeries pastries cafes --arrondissements 1 2 3 4
```

Collect an initial sample in the 11th:

```sh
python maps.py collect --categories restaurants bakeries pastries cafes \
  --arrondissements 11 --max-queries 4 --max-places 20 --max-results 10
```

Repeat the command to resume. Places are saved after every successful visit. Searches save their discovered links before place visits, so interrupted runs retain the queue. Failed place visits are retried on the next run. A shared database resumes its existing pending queue first, including discoveries from earlier category/district selections; use a separate `--db` and `--output` for an independent collection.

Start all 480 searches:

```sh
python maps.py collect --max-queries 0 --max-places 0
```

This can take hours. The defaults limit each run to 20 new searches and 100 place attempts, each search to 120 results and 40 scrolls, with a 2-second delay. `0` removes the run limit for queries/places only. Ctrl+C saves progress and exports current records. CAPTCHA or verification pages stop the run; the collector does not bypass them.

Other controls:

- `--headless`: run without a browser window.
- `--language fr` / `--language en`: request the page language; French is the default.
- `--chrome-binary /path/to/chrome`: use a specific installed browser.
- `--profile-dir .chrome-profile`: reuse a **dedicated** Chrome profile, such as one where you have already signed in manually. Close other Chrome windows using that profile first. Login is never automated. Keep the profile local.
- `--refresh`: revisit saved places and append observations. Use this after changing language or browser access. Latest records are exported; historical observations remain in SQLite.
- `--rediscover`: repeat the selected searches, including previously capped or stalled searches. Raising `--max-results` or `--max-scrolls` also creates a new search checkpoint.
- `--save-evidence`: save rendered HTML and screenshots under the output directory for selector diagnosis. These may contain account-visible page content; they are ignored by Git.
- `--no-sandbox`: only for trusted containers running Chrome as root; leave this off on your computer.

## AI summary handling

The collector inspects the place overview panel and scrolls to load sections below the fold. It captures bounded sections with an explicit English/French AI disclosure, retaining the text, disclosure, and any source links. It **does not generate its own summary**, and generic review snippets or editorial descriptions are not classified as AI.

`ai_summary_status` distinguishes:

| Status | Meaning |
| --- | --- |
| `found` | An explicitly labelled AI section was captured. |
| `not_observed` | No supported AI-labelled section was observed in the loaded panel. This does not prove the place has no summary. |
| `unavailable_limited_view` | Google explicitly served its limited Maps view, which may omit review counts and summaries. |

Availability depends on the place, language, region, account, and Maps interface. App-only or differently labelled summaries may not be accessible to this desktop collector. Live validation on 3 October 2026 collected Paris place details, but Google served a limited view and **no AI summary was available to validate live**. Summary extraction is covered by synthetic French/English fixtures; its live selectors still need validation against a Maps page that exposes an AI summary. Ordinary descriptions are stored separately and may also be absent.

Google documents the distinction between [business descriptions, editorial summaries, and review snippets](https://support.google.com/business/answer/6088158?hl=en). The parser deliberately avoids treating all of these as AI-generated content.

## Dataset and future rankings

The default database is `data/paris.sqlite`. Exports in `data/paris/` are:

- **`places.csv`**: spreadsheet-friendly Paris records (UTF-8 with BOM). Nested summaries and discovery provenance are JSON cells. Potential formula-like text is escaped for spreadsheet safety.
- **`places.jsonl`**: one complete Paris record per line, preserving source text and structured summaries.
- **`outside_or_unknown_paris.jsonl`**: nearby results and places without a verified Paris postal code, for inspection. Searches do not guarantee the returned place is in the requested district.
- **`coverage.json`**: search queries, observed result counts, why searches stopped, errors, pending counts, and summary availability.

Records contain a stable Maps identity when exposed (otherwise a URL hash), name, actual Maps category, address, arrondissement, rating, review count, price range, contact details, coordinates, source URL, observation timestamp, requested language, description, AI summaries, and the queries/categories that discovered them. Missing fields are null, never zero. French narrow-space thousands separators and decimal commas are supported. Paris scope is determined from postal codes 75001–75020 plus 75116; records without a matching visible address are kept in the separate inspection file.

SQLite also keeps an append-only `observations` table for later comparisons. Duplicate discoveries use Maps IDs instead of business names, preserving different branches of the same business. URL-hash fallback identities may need manual reconciliation. `collection_status` and `last_error` show when a refresh failed and an older observation remains in the export.

This builds a **candidate dataset**, not a complete census or an objective list of the best food. Search results are bounded, can include nearby/sponsored results, and vary between runs. `coverage.json` records `end_of_feed`, `result_limit`, `scroll_limit`, `stalled`, `single_place`, or `no_results`; even an exhausted feed is not exhaustive city coverage. Verify the actual category before ranking. Rating and review count are retained separately so a later ranking can account for evidence volume, freshness, and category instead of simply sorting by stars. No invented scores are added.

Re-export without visiting Google:

```sh
python maps.py export --db data/paris.sqlite --output data/paris
```

The original `results.csv` and `processing.py` remain historical hotel-experiment artifacts and are not used by this collector. Collected data is ignored by Git.

## Tests

```sh
python -m pytest -q
```

Tests cover Paris scope, localized numbers, identity deduplication, AI-vs-editorial separation, limited-view detection, provenance, resumable collection, blocked pages, exports, and observation history. They run offline. Google can change its markup; enable evidence capture to diagnose missing fields before running a large collection.
