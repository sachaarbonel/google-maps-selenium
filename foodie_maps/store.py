"""SQLite checkpoints and append-only observations, plus portable exports."""
import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .parsing import place_key


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS places (
                id TEXT PRIMARY KEY, url TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
                data TEXT, error TEXT, updated_at TEXT);
            CREATE TABLE IF NOT EXISTS searches (
                id TEXT PRIMARY KEY, query TEXT NOT NULL, category TEXT NOT NULL,
                arrondissement INTEGER NOT NULL, url TEXT NOT NULL, status TEXT NOT NULL,
                count INTEGER NOT NULL, checked_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS discoveries (
                place_id TEXT, search_id TEXT, PRIMARY KEY(place_id, search_id));
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY, place_id TEXT NOT NULL, observed_at TEXT NOT NULL,
                data TEXT NOT NULL);
        ''')

    def searched(self, search_id):
        return self.db.execute("SELECT 1 FROM searches WHERE id=?", (search_id,)).fetchone() is not None

    def discovery(self, search_id, search, urls, status):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO searches VALUES (?,?,?,?,?,?,?,?)",
                            (search_id, search.query, search.category, search.arrondissement,
                             search.url, status, len(urls), now()))
            for url in urls:
                key = place_key(url)
                self.db.execute("INSERT OR IGNORE INTO places(id,url) VALUES (?,?)", (key, url))
                self.db.execute("INSERT OR IGNORE INTO discoveries VALUES (?,?)", (key, search_id))

    def pending(self):
        return self.db.execute("SELECT id,url FROM places WHERE status != 'done' ORDER BY rowid").fetchall()

    def save(self, key, data):
        # Keep the discovery identity stable even when Maps redirects the URL.
        data["place_id"] = key
        data["observed_at"] = now()
        encoded = json.dumps(data, ensure_ascii=False)
        with self.db:
            self.db.execute("UPDATE places SET status='done',data=?,error=NULL,updated_at=? WHERE id=?",
                            (encoded, data["observed_at"], key))
            self.db.execute("INSERT INTO observations(place_id,observed_at,data) VALUES (?,?,?)",
                            (key, data["observed_at"], encoded))

    def fail(self, key, error):
        with self.db:
            self.db.execute("UPDATE places SET status='error',error=?,updated_at=? WHERE id=?",
                            (str(error), now(), key))

    def refresh(self):
        with self.db:
            self.db.execute("UPDATE places SET status='pending' WHERE status='done'")

    def export(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        records = []
        for row in self.db.execute("SELECT id,data,status,error FROM places WHERE data IS NOT NULL ORDER BY id"):
            record = json.loads(row["data"])
            provenance = self.db.execute('''SELECT DISTINCT s.query,s.category,s.arrondissement
                FROM searches s JOIN discoveries d ON d.search_id=s.id WHERE d.place_id=?
                ORDER BY s.arrondissement,s.category''', (row["id"],)).fetchall()
            record["discovered_by"] = [dict(item) for item in provenance]
            record["collection_status"] = row["status"]
            record["last_error"] = row["error"]
            records.append(record)
        # Keep nearby/unknown addresses for inspection, but outside the Paris dataset.
        paris = [r for r in records if r["in_paris"]]
        self._write(directory / "places.jsonl", paris)
        self._write(directory / "outside_or_unknown_paris.jsonl", [r for r in records if not r["in_paris"]])
        fields = ["place_id", "name", "category", "address", "postal_code", "arrondissement", "rating",
                  "review_count", "price_range", "phone", "website", "latitude", "longitude", "maps_url",
                  "description", "ai_summary_status", "ai_summaries", "page_status", "language", "observed_at",
                  "discovered_by", "collection_status", "last_error"]
        with (directory / "places.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for record in paris:
                flattened = {k: json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v
                             for k, v in record.items()}
                # Spreadsheet programs must treat scraped text as text, not formulas.
                writer.writerow({k: "'" + v if isinstance(v, str) and v.startswith(("=", "+", "-", "@")) else v
                                 for k, v in flattened.items()})
        report = {
            "exported_at": now(), "paris_places": len(paris), "outside_or_unknown_paris": len(records)-len(paris),
            "with_ai_summary": sum(r["ai_summary_status"] == "found" for r in paris),
            "limited_view_places": sum(r.get("page_status") == "limited_view" for r in paris),
            "place_statuses": dict(self.db.execute("SELECT status,COUNT(*) FROM places GROUP BY status").fetchall()),
            "searches": [dict(r) for r in self.db.execute("SELECT * FROM searches ORDER BY rowid")],
            "errors": [dict(r) for r in self.db.execute("SELECT id,url,error FROM places WHERE status='error'")],
            "coverage_note": "Search results are bounded and personalized; this is not an exhaustive census or a ranking.",
        }
        (directory / "coverage.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    @staticmethod
    def _write(path, records):
        with path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def close(self):
        self.db.close()
