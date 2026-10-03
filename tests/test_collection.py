"""Exercise interruption/restart behavior without hitting Google in CI."""
import json
from selenium.common.exceptions import WebDriverException
from foodie_maps import browser
from foodie_maps.cli import main


class Driver:
    closed = False
    def quit(self):
        self.closed = True


def record(url):
    return {"place_id": url, "name": "Example", "in_paris": True, "ai_summary_status": "not_observed"}


def test_place_cap_resumes_pending_links_without_repeating_search(tmp_path, monkeypatch):
    searches, extracts = [], []
    driver = Driver()
    monkeypatch.setattr(browser, "make_driver", lambda *args: driver)

    class Browser:
        def __init__(self, *args):
            pass
        def discover(self, search, *args):
            searches.append(search.query)
            return ["https://www.google.com/maps?cid=1", "https://www.google.com/maps?cid=2"], "end_of_feed"
        def extract(self, url):
            extracts.append(url)
            return record(url)

    monkeypatch.setattr(browser, "MapsBrowser", Browser)
    args = ["collect", "--db", str(tmp_path / "test.sqlite"), "--output", str(tmp_path / "out"),
            "--categories", "bakeries", "--arrondissements", "11", "--max-places", "1"]
    assert main(args) == 0
    assert main(args) == 0
    assert main(args) == 0
    assert len(searches) == 1
    assert len(extracts) == 2
    assert driver.closed
    report = json.loads((tmp_path / "out/coverage.json").read_text())
    assert report["paris_places"] == 2


def test_block_stops_run_and_keeps_pending_place(tmp_path, monkeypatch):
    driver = Driver()
    monkeypatch.setattr(browser, "make_driver", lambda *args: driver)

    class Browser:
        def __init__(self, *args):
            pass
        def discover(self, *args):
            return ["https://www.google.com/maps?cid=1"], "end_of_feed"
        def extract(self, url):
            raise browser.Blocked("verification required")

    monkeypatch.setattr(browser, "MapsBrowser", Browser)
    args = ["collect", "--db", str(tmp_path / "test.sqlite"), "--output", str(tmp_path / "out"),
            "--categories", "bakeries", "--arrondissements", "11"]
    assert main(args) == 2
    report = json.loads((tmp_path / "out/coverage.json").read_text())
    assert report["place_statuses"] == {"pending": 1}
    assert report["paris_places"] == 0
    assert driver.closed


def test_failed_browser_start_exports_checkpoint(tmp_path, monkeypatch):
    def fail(*args):
        raise WebDriverException("no Chrome")
    monkeypatch.setattr(browser, "make_driver", fail)
    assert main(["collect", "--db", str(tmp_path / "test.sqlite"), "--output", str(tmp_path / "out")]) == 2
    assert (tmp_path / "out/coverage.json").is_file()
