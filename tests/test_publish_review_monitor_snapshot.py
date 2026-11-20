import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


MODULE = Path(__file__).resolve().parents[1] / "tools" / "publish_review_monitor_snapshot.py"
SPEC = importlib.util.spec_from_file_location("publish_review_monitor_snapshot", MODULE)
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


class PublishMonitorSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name) / "crawler"
        self.feed = self.source / "reviews" / "monitor-data.json"
        self.feed.parent.mkdir(parents=True)
        self.output = Path(self.directory.name) / "site" / "review-monitor.json"
        self.snapshot = {
            "generated_at": "2026-11-20T03:03:09+00:00",
            "commit": "a" * 40,
            "years": [{"year": 2025, "sources": [{
                "code": "test", "owner": "test", "included": 3,
                "missing_abstract": 2, "included_missing_abstract": 1,
                "pending_sync": 1, "issues": ["real unresolved evidence"],
            }]}],
        }

    def write_feed(self):
        payload = (json.dumps(self.snapshot, indent=2) + "\n").encode()
        self.feed.write_bytes(payload)
        return payload

    def test_publishes_exact_bytes_including_real_pending_items_and_provenance(self):
        payload = self.write_feed()
        result = publisher.publish_snapshot(self.source, self.output)
        self.assertEqual(self.output.read_bytes(), payload)
        self.assertEqual(result, self.snapshot)

    def test_invalid_snapshot_does_not_overwrite_previous_published_feed(self):
        self.output.parent.mkdir()
        self.output.write_bytes(b"previous snapshot")
        invalid = [
            {"generated_at": "2026-11-20T03:03:09"},
            {"commit": "unverified"},
            {"years": []},
            {"years": [{"year": 2025, "sources": []}] * 2},
            {"years": [{"year": 2025, "sources": [None]}]},
        ]
        original = self.snapshot.copy()
        for changes in invalid:
            with self.subTest(changes=changes):
                self.snapshot = {**original, **changes}
                self.write_feed()
                with self.assertRaises(ValueError):
                    publisher.publish_snapshot(self.source, self.output)
                self.assertEqual(self.output.read_bytes(), b"previous snapshot")

    def test_missing_or_malformed_feed_never_regenerates_legacy_results(self):
        with self.assertRaises(FileNotFoundError):
            publisher.publish_snapshot(self.source, self.output)
        self.feed.write_text("{invalid")
        with self.assertRaises(ValueError):
            publisher.publish_snapshot(self.source, self.output)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
