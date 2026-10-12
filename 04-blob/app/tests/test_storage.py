from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from azure.core.exceptions import HttpResponseError, ResourceExistsError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from blob_viz.data import AppError
from blob_viz.storage import AzureBlobStore, Settings


CONTENT = b"month,value\n2026-01,100\n"


def properties(content=CONTENT, **changes):
    values = {
        "size": len(content), "etag": '"0x123"', "last_modified": datetime.now(timezone.utc),
        "metadata": {"schema": "hol04-v1", "filename": "sample.csv",
                     "sha256": hashlib.sha256(content).hexdigest()},
    }
    values.update(changes)
    return SimpleNamespace(**values)


class StorageTest(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.store = AzureBlobStore(Settings("stexample", "11111111-2222-4333-8444-555555555555"),
                                    container_client=self.client)

    def test_atomic_slots_never_overwrite_existing(self):
        first, second = Mock(), Mock()
        first.upload_blob.side_effect = ResourceExistsError("occupied")
        second.get_blob_properties.return_value = properties()
        self.client.get_blob_client.side_effect = [first, second]
        record = self.store.save("sample.csv", CONTENT)
        self.assertEqual(record.identifier, "file-02")
        self.assertFalse(first.upload_blob.call_args.kwargs["overwrite"])
        self.assertFalse(second.upload_blob.call_args.kwargs["overwrite"])
        self.assertEqual(second.upload_blob.call_args.args[0], CONTENT)
        self.assertEqual(second.upload_blob.call_args.kwargs["metadata"]["sha256"], hashlib.sha256(CONTENT).hexdigest())

    def test_ten_slots_are_a_hard_limit(self):
        blob = Mock()
        blob.upload_blob.side_effect = ResourceExistsError("occupied")
        self.client.get_blob_client.return_value = blob
        with self.assertRaises(AppError) as result:
            self.store.save("sample.csv", CONTENT)
        self.assertEqual(result.exception.code, "file_limit")
        self.assertEqual(blob.upload_blob.call_count, 10)

    def test_read_downloads_from_blob_and_checks_integrity(self):
        blob = self.client.get_blob_client.return_value
        blob.get_blob_properties.return_value = properties()
        blob.download_blob.return_value.readall.return_value = CONTENT
        record, content = self.store.read("file-01")
        self.assertEqual(content, CONTENT)
        self.assertEqual(record.sha256, hashlib.sha256(CONTENT).hexdigest())
        self.assertEqual(blob.download_blob.call_args.kwargs["etag"], '"0x123"')
        blob.download_blob.return_value.readall.return_value = b"changed"
        with self.assertRaises(AppError) as result:
            self.store.read("file-01")
        self.assertEqual(result.exception.code, "blob_integrity")

    def test_invalid_metadata_and_unknown_blob_are_errors(self):
        blob = self.client.get_blob_client.return_value
        blob.get_blob_properties.return_value = properties(metadata={})
        with self.assertRaises(AppError) as result:
            self.store.read("file-01")
        self.assertEqual(result.exception.status, 502)
        self.client.list_blobs.return_value = [SimpleNamespace(name="files/unknown.csv")]
        with self.assertRaises(AppError) as result:
            self.store.list_files()
        self.assertEqual(result.exception.code, "unknown_blob")

    def test_forbidden_is_not_suppressed_or_changed_to_keys(self):
        error = HttpResponseError("forbidden")
        error.status_code = 403
        self.client.list_blobs.side_effect = error
        with self.assertRaises(AppError) as result:
            self.store.list_files()
        self.assertEqual(result.exception.code, "storage_forbidden")
        self.assertEqual(result.exception.status, 503)

    def test_delete_requires_conditional_etag_and_valid_id(self):
        blob = self.client.get_blob_client.return_value
        self.store.delete("file-01", '"0x123"')
        self.assertEqual(blob.delete_blob.call_args.kwargs["etag"], '"0x123"')
        with self.assertRaises(AppError):
            self.store.read("../../secret")


if __name__ == "__main__":
    unittest.main()
