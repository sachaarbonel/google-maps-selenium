import csv
import json
from foodie_maps.store import Store
from foodie_maps.plan import make_plan
from foodie_maps.parsing import parse_place, place_key

URL = "https://www.google.com/maps?cid=123"


def test_resume_deduplication_history_and_exports(tmp_path):
    db = tmp_path / "test.sqlite"
    store = Store(db)
    searches = list(make_plan(["bakeries", "pastries"], [11]))
    store.discovery("one", searches[0], [URL, URL], "end_of_feed")
    store.discovery("two", searches[1], [URL], "result_limit")
    assert len(store.pending()) == 1
    data = parse_place('<h1>=Bakery</h1><button data-item-id="address">75011 Paris</button>', URL, "fr")
    store.save(place_key(URL), data)
    store.close()
    store = Store(db)
    assert store.searched("one")
    assert not store.pending()
    store.refresh()
    assert len(store.pending()) == 1
    store.save(place_key(URL), {**data, "rating": 4.8})
    assert store.db.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 2
    report = store.export(tmp_path / "export")
    assert report["paris_places"] == 1
    record = json.loads((tmp_path / "export/places.jsonl").read_text())
    assert record["name"] == "=Bakery"
    assert len(record["discovered_by"]) == 2
    with (tmp_path / "export/places.csv").open(encoding="utf-8-sig") as f:
        assert next(csv.DictReader(f))["name"] == "'=Bakery"
    store.close()


def test_failures_retry_and_unknown_addresses_are_not_paris(tmp_path):
    store = Store(tmp_path / "test.sqlite")
    store.discovery("one", next(make_plan(["bakeries"], [11])), [URL], "stalled")
    store.fail(place_key(URL), "timeout")
    assert len(store.pending()) == 1
    assert len(store.export(tmp_path / "out")["errors"]) == 1
    store.save(place_key(URL), parse_place('<h1>Nearby bakery</h1>', URL, "fr"))
    report = store.export(tmp_path / "out")
    assert report["paris_places"] == 0
    assert report["outside_or_unknown_paris"] == 1
    assert report["errors"] == []
    store.close()


def test_default_plan_covers_20_districts_and_24_categories():
    plan = list(make_plan())
    assert len(plan) == 480
    assert len({s.url for s in plan}) == 480
    assert {s.arrondissement for s in plan} == set(range(1,21))
