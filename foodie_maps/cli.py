import argparse
import hashlib
import json
import logging
from pathlib import Path
from .plan import CATEGORIES, make_plan
from .store import Store

LOG = logging.getLogger(__name__)


def nonnegative(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return number


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def delay_value(value):
    number = float(value)
    if not 0.5 <= number <= 60:
        raise argparse.ArgumentTypeError("must be between 0.5 and 60 seconds")
    return number


def parser():
    root = argparse.ArgumentParser(description="Build a Paris foodie dataset from Google Maps.")
    sub = root.add_subparsers(dest="command", required=True)
    for command in ("plan", "collect"):
        p = sub.add_parser(command)
        p.add_argument("--categories", nargs="+", choices=CATEGORIES, default=list(CATEGORIES))
        p.add_argument("--arrondissements", nargs="+", type=int, choices=range(1, 21), default=list(range(1, 21)))
        p.add_argument("--language", choices=("fr", "en"), default="fr")
        if command == "collect":
            p.add_argument("--db", default="data/paris.sqlite")
            p.add_argument("--output", default="data/paris")
            p.add_argument("--headless", action="store_true")
            p.add_argument("--chrome-binary")
            p.add_argument("--profile-dir", help="Dedicated local Chrome profile; close its other browser windows first")
            p.add_argument("--rediscover", action="store_true", help="Repeat searches already checkpointed")
            p.add_argument("--no-sandbox", action="store_true", help="Only for trusted root containers")
            p.add_argument("--delay", type=delay_value, default=2.0)
            p.add_argument("--max-results", type=positive, default=120, help="Per search")
            p.add_argument("--max-scrolls", type=positive, default=40)
            p.add_argument("--max-queries", type=nonnegative, default=20, help="New searches per run; 0 = all")
            p.add_argument("--max-places", type=nonnegative, default=100, help="Place attempts per run; 0 = all")
            p.add_argument("--refresh", action="store_true", help="Revisit saved places, retaining historical observations")
            p.add_argument("--save-evidence", action="store_true", help="Save rendered HTML and screenshots locally")
    p = sub.add_parser("export")
    p.add_argument("--db", default="data/paris.sqlite")
    p.add_argument("--output", default="data/paris")
    return root


def collect(args):
    from selenium.common.exceptions import WebDriverException
    from .browser import Blocked, MapsBrowser, make_driver
    store = Store(args.db)
    driver = None
    attempted, searched = set(), 0
    exit_code = 0
    evidence_dir = Path(args.output) / "evidence"
    try:
        if args.refresh:
            store.refresh()
        driver = make_driver(args.headless, args.chrome_binary, args.no_sandbox, args.profile_dir)
        browser = MapsBrowser(driver, args.language, args.delay)

        def process_pending():
            for row in store.pending():
                if row["id"] in attempted:
                    continue
                if args.max_places and len(attempted) >= args.max_places:
                    return False
                attempted.add(row["id"])
                LOG.info("Collecting place %s", row["id"])
                try:
                    data = browser.extract(row["url"])
                    store.save(row["id"], data)
                    LOG.info("Saved %s (%s)", data["name"], data["ai_summary_status"])
                    if args.save_evidence:
                        browser.evidence(evidence_dir, hashlib.sha256(row["id"].encode()).hexdigest()[:16])
                except Blocked:
                    raise
                except (WebDriverException, ValueError) as exc:
                    store.fail(row["id"], exc)
                    LOG.warning("Place failed: %s", exc)
            return not args.max_places or len(attempted) < args.max_places

        if process_pending():
            for search in make_plan(args.categories, args.arrondissements, args.language):
                search_id = hashlib.sha256(f"{search.url}:{args.max_results}:{args.max_scrolls}".encode()).hexdigest()[:24]
                if store.searched(search_id) and not args.rediscover:
                    continue
                if args.max_queries and searched >= args.max_queries:
                    break
                LOG.info("Searching %s", search.query)
                urls, status = browser.discover(search, args.max_results, args.max_scrolls)
                store.discovery(search_id, search, urls, status)
                searched += 1
                LOG.info("Discovered %s links (%s)", len(urls), status)
                if not process_pending():
                    break
    except KeyboardInterrupt:
        LOG.warning("Interrupted. Progress saved; repeat the command to resume.")
        exit_code = 130
    except (Blocked, WebDriverException, ValueError) as exc:
        LOG.error("Collection stopped: %s", exc)
        exit_code = 2
        if driver and args.save_evidence:
            try:
                browser.evidence(evidence_dir, "stopped")
            except WebDriverException:
                pass
    finally:
        report = store.export(args.output)
        LOG.info("Exported %s Paris places; %s have an observed AI summary. %s",
                 report["paris_places"], report["with_ai_summary"], args.output)
        if report["place_statuses"].get("error") and not exit_code:
            exit_code = 1
        store.close()
        if driver:
            driver.quit()
    return exit_code


def main(argv=None):
    args = parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if args.command == "plan":
        print(json.dumps([s.to_dict() for s in make_plan(args.categories, args.arrondissements, args.language)],
                         ensure_ascii=False, indent=2))
        return 0
    if args.command == "export":
        if not Path(args.db).is_file():
            parser().error(f"Database does not exist: {args.db}")
        store = Store(args.db)
        try:
            report = store.export(args.output)
            print(json.dumps({k: v for k, v in report.items() if k != "searches"}, indent=2))
        finally:
            store.close()
        return 0
    return collect(args)
