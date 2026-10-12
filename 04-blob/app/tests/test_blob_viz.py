import hashlib
import io
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from blob_viz import create_app
from blob_viz.data import AppError, MAX_FILE_BYTES, parse_csv, validate_filename
from blob_viz.storage import Settings, StoredFile


SAMPLES = Path(__file__).resolve().parents[1] / "blob_viz/samples"
BASE = (SAMPLES / "monthly-sales.csv").read_bytes()
UPDATED = (SAMPLES / "monthly-sales-updated.csv").read_bytes()


class TestStore:
    source = "in-memory-test"

    def __init__(self):
        self.saved = {}
        self.reads = 0
        self.writes = 0
        self.failure = None

    def save(self, filename, content):
        for index in range(1, 11):
            identifier = f"file-{index:02}"
            if identifier not in self.saved:
                self.writes += 1
                record = StoredFile(identifier, filename, len(content), f'"{index}-{self.writes}"',
                                    hashlib.sha256(content).hexdigest(), "2026-10-12T00:00:00+00:00")
                self.saved[identifier] = (record, content)
                return record
        raise AppError("file_limit", "10件の上限です。", 409)

    def list_files(self):
        if self.failure:
            raise self.failure
        return [record for record, _ in self.saved.values()]

    def read(self, identifier):
        self.reads += 1
        if self.failure:
            raise self.failure
        if identifier not in self.saved:
            raise AppError("not_found", "見つかりません。", 404)
        return self.saved[identifier]

    def delete(self, identifier, etag):
        record, _ = self.read(identifier)
        if record.etag != etag:
            raise AppError("changed", "変更されています。", 409)
        del self.saved[identifier]


class DataTest(unittest.TestCase):
    def test_sample_and_updated_summary(self):
        dataset = parse_csv(BASE).as_dict()
        self.assertEqual(dataset["rowCount"], 6)
        self.assertEqual(dataset["total"], 1020)
        self.assertEqual(dataset["maximum"], 240)
        self.assertEqual(parse_csv(UPDATED).as_dict()["total"], 1080)
        self.assertEqual(parse_csv(UPDATED).as_dict()["maximum"], 300)

    def test_bom_crlf_sorting_and_zero_values(self):
        dataset = parse_csv(b"\xef\xbb\xbfmonth,value\r\n2026-02,0\r\n2026-01,0\r\n").as_dict()
        self.assertEqual(dataset["total"], 0)
        self.assertEqual(dataset["maximum"], 0)
        self.assertEqual([row["month"] for row in dataset["rows"]], ["2026-01", "2026-02"])

    def test_invalid_input_and_limits(self):
        invalid = [
            b"", b"x" * (MAX_FILE_BYTES + 1), b"\xff",
            b"date,total\n2026-01,100\n", b"month,value\n",
            b"month,value,value\n2026-01,1,2\n", b"month,value\n2026-00,1\n",
            b"month,value\n2026-13,1\n", b"month,value\n2026-01,-1\n",
            b"month,value\n2026-01,1.5\n", b"month,value\n2026-01,1000001\n",
            b"month,value\n2026-01,1\n2026-01,2\n",
            b"month,value\n2026-01,=1+2\n", b"month,value\n2026-01,1,2\n",
            b"month,value\n2026-01,\n", b"month,value\n2026-01,\x00\n",
        ]
        invalid.append(("month,value\n" + "\n".join(
            f"{2025 + index // 12}-{index % 12 + 1:02},1" for index in range(25)
        )).encode())
        for content in invalid:
            with self.subTest(content=content[:30]), self.assertRaises(AppError):
                parse_csv(content)

    def test_filenames_and_settings(self):
        self.assertEqual(validate_filename("monthly-sales.csv"), "monthly-sales.csv")
        for name in ["../sales.csv", "a\\b.csv", "a..b.csv", "<x>.csv", "sales.xlsx", "", None]:
            with self.subTest(name=name), self.assertRaises(AppError):
                validate_filename(name)
        self.assertEqual(Settings.from_env({
            "AZURE_STORAGE_ACCOUNT": "stexample",
            "AZURE_CLIENT_ID": "11111111-2222-4333-8444-555555555555",
        }).account_url, "https://stexample.blob.core.windows.net")
        for env in [{}, {"AZURE_STORAGE_ACCOUNT": "stexample"},
                    {"AZURE_STORAGE_ACCOUNT": "stexample", "AZURE_CLIENT_ID": "00000000-0000-0000-0000-000000000000"}]:
            with self.assertRaises(ValueError):
                Settings.from_env(env)


class AppTest(unittest.TestCase):
    def setUp(self):
        self.store = TestStore()
        self.app = create_app({}, self.store)
        self.app.testing = True
        self.client = self.app.test_client()
        token = self.client.get("/api/session").json["csrf"]
        self.headers = {"Origin": "http://localhost", "X-CSRF-Token": token}

    def upload(self, content=BASE, name="monthly-sales.csv", headers=None):
        return self.client.post(
            "/api/files", headers=self.headers if headers is None else headers,
            data={"file": (io.BytesIO(content), name)}, content_type="multipart/form-data",
        )

    def test_upload_then_read_download_and_new_browser(self):
        uploaded = self.upload()
        self.assertEqual(uploaded.status_code, 201)
        self.assertEqual(self.store.reads, 0)
        identifier = uploaded.json["file"]["id"]
        data = self.client.get(f"/api/files/{identifier}/data")
        self.assertEqual(data.json["dataset"]["total"], 1020)
        self.assertEqual(data.json["readFrom"], "test")
        self.assertEqual(self.store.reads, 1)
        self.assertEqual(self.client.get(f"/api/files/{identifier}/download").data, BASE)
        new_client = self.app.test_client()
        self.assertEqual(len(new_client.get("/api/files").json["files"]), 1)
        self.assertEqual(new_client.get(f"/api/files/{identifier}/data").json["dataset"]["total"], 1020)
        self.assertEqual(data.headers["Cache-Control"], "no-store")

    def test_second_file_does_not_overwrite(self):
        first = self.upload()
        second = self.upload(UPDATED)
        self.assertNotEqual(first.json["file"]["id"], second.json["file"]["id"])
        self.assertEqual(len(self.store.saved), 2)
        self.assertEqual(self.client.get("/api/files/file-01/data").json["dataset"]["total"], 1020)
        self.assertEqual(self.client.get("/api/files/file-02/data").json["dataset"]["total"], 1080)

    def test_invalid_csv_does_not_write(self):
        for content in [b"date,total\n2026-01,1\n", b"", b"x" * (MAX_FILE_BYTES + 1)]:
            response = self.upload(content)
            self.assertIn(response.status_code, [400, 413])
            self.assertIn("error", response.json)
        self.assertEqual(self.store.writes, 0)

    def test_csrf_origin_and_delete_etag(self):
        for headers in [{}, {**self.headers, "Origin": "https://evil.invalid"},
                        {**self.headers, "Sec-Fetch-Site": "cross-site"},
                        {**self.headers, "X-CSRF-Token": "wrong"}]:
            self.assertEqual(self.upload(headers=headers).status_code, 403)
        created = self.upload().json["file"]
        self.assertEqual(self.client.delete("/api/files/file-01", headers=self.headers).status_code, 428)
        wrong = self.client.delete("/api/files/file-01", headers={**self.headers, "If-Match": '"wrong"'})
        self.assertEqual(wrong.status_code, 409)
        deleted = self.client.delete("/api/files/file-01", headers={**self.headers, "If-Match": created["etag"]})
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.client.get("/api/files/file-01/data").status_code, 404)

    def test_store_failure_is_explicit_not_empty_success(self):
        self.store.failure = AppError("storage_forbidden", "講師が権限を確認してください。", 503)
        response = self.client.get("/api/files")
        self.assertEqual(response.status_code, 503)
        self.assertIn("error", response.json)
        self.assertNotIn("files", response.json)

    def test_security_headers_test_banner_and_no_production_fallback(self):
        response = self.client.get("/")
        self.assertIn("Azureには保存しません", response.text)
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(self.client.get("/samples/secret.env").status_code, 404)
        with self.assertRaises(ValueError):
            create_app({})


if __name__ == "__main__":
    unittest.main()
