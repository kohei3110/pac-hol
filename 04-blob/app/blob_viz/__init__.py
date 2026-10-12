import atexit
import io
import logging
import os
from pathlib import Path
import secrets
from urllib.parse import urlsplit
from uuid import uuid4

from flask import Flask, g, jsonify, render_template, request, send_file, session
from werkzeug.exceptions import HTTPException

from .data import AppError, MAX_FILE_BYTES, parse_csv, validate_filename
from .storage import AzureBlobStore, Settings, UploadStore


class SafeFlask(Flask):
    def log_exception(self, exc_info):
        self.logger.error("code=internal request_id=%s exception_type=%s",
                          getattr(g, "request_id", "none"), exc_info[0].__name__)


def create_app(environ=None, store: UploadStore | None = None):
    env = dict(os.environ if environ is None else environ)
    if store is None:
        settings = Settings.from_env(env)
        store = AzureBlobStore(settings)
        atexit.register(store.close)
    app = SafeFlask(__name__)
    app.config.update(
        SECRET_KEY=secrets.token_hex(32),
        MAX_CONTENT_LENGTH=96 * 1024,
        MAX_FORM_MEMORY_SIZE=MAX_FILE_BYTES,
        MAX_FORM_PARTS=4,
        SESSION_COOKIE_NAME="blob_viz_csrf",
        SESSION_COOKIE_SECURE=store.source == "azure-blob",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        DEBUG=False,
    )
    app.json.ensure_ascii = False
    app.extensions["upload_store"] = store
    logging.getLogger("azure").setLevel(logging.WARNING)

    def response(data, status=200):
        return jsonify({"requestId": g.request_id, "source": store.source, **data}), status

    @app.before_request
    def protect():
        g.request_id = uuid4().hex
        g.nonce = secrets.token_urlsafe(24)
        if request.method not in {"POST", "DELETE"}:
            return
        try:
            origin = urlsplit(request.headers.get("Origin", ""))
            same_origin = (
                origin.scheme == request.scheme and origin.netloc == request.host
                and not origin.path and not origin.query and not origin.fragment
                and not origin.username and not origin.password
            )
        except ValueError:
            same_origin = False
        supplied, expected = request.headers.get("X-CSRF-Token", ""), session.get("csrf", "")
        if (
            not same_origin or request.headers.get("Sec-Fetch-Site") not in (None, "same-origin")
            or not supplied or not expected or len(supplied) > 200 or not supplied.isascii()
            or not secrets.compare_digest(supplied, expected)
        ):
            raise AppError("csrf", "ページを再読み込みし、同じアプリ画面から操作してください。", 403)

    @app.after_request
    def headers(result):
        result.headers.update({
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "X-Frame-Options": "DENY",
            "X-Request-ID": g.request_id,
            "Content-Security-Policy": (
                f"default-src 'self'; script-src 'self' 'nonce-{g.nonce}'; "
                "style-src 'self' 'unsafe-inline'; img-src 'self'; connect-src 'self'; "
                "object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
            ),
        })
        if request.is_secure:
            result.headers["Strict-Transport-Security"] = "max-age=86400"
        return result

    @app.errorhandler(AppError)
    def known_error(error):
        app.logger.warning("code=%s request_id=%s", error.code, g.request_id)
        return response({"error": {"code": error.code, "message": error.message}}, error.status)

    @app.errorhandler(HTTPException)
    def http_error(error):
        message = "操作を完了できませんでした。入力を見直し、解決しない場合は要求IDを講師に伝えてください。"
        if error.code == 413:
            message = "送信サイズの上限を超えています。64 KiB以内のCSVを選んでください。"
        app.logger.warning("code=http_%s request_id=%s", error.code, g.request_id)
        return response({"error": {"code": f"http_{error.code}", "message": message}}, error.code or 500)

    @app.get("/")
    def index():
        return render_template("index.html", nonce=g.nonce, source=store.source)

    @app.get("/healthz")
    def health():
        return response({"status": "alive"})

    @app.get("/api/session")
    def csrf_token():
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        return response({"csrf": session["csrf"]})

    @app.get("/api/files")
    def files():
        return response({"files": [file.as_dict() for file in store.list_files()]})

    @app.post("/api/files")
    def upload():
        if set(request.files) != {"file"} or len(request.files.getlist("file")) != 1 or request.form:
            raise AppError("upload", "CSVファイルを1つ選んでください。")
        file = request.files["file"]
        filename = validate_filename(file.filename)
        content = file.stream.read(MAX_FILE_BYTES + 1)
        parse_csv(content)
        saved = store.save(filename, content)
        return response({"file": saved.as_dict(), "detail": "Blobに保存しました。このあと保存先から読み直して、表とグラフを表示します。"}, 201)

    @app.get("/api/files/<identifier>/data")
    def data(identifier):
        record, content = store.read(identifier)
        dataset = parse_csv(content)
        return response({"file": record.as_dict(), "dataset": dataset.as_dict(), "readFrom": "blob" if store.source == "azure-blob" else "test"})

    @app.get("/api/files/<identifier>/download")
    def download(identifier):
        record, content = store.read(identifier)
        parse_csv(content)
        return send_file(io.BytesIO(content), mimetype="text/csv", as_attachment=True, download_name=record.filename)

    @app.delete("/api/files/<identifier>")
    def delete(identifier):
        etag = request.headers.get("If-Match", "")
        if not etag or len(etag) > 200 or not etag.isascii():
            raise AppError("etag", "表示したファイルを再読み込みしてから削除してください。", 428)
        store.delete(identifier, etag)
        return response({"deleted": identifier})

    @app.get("/samples/<filename>")
    def sample(filename):
        allowed = {"monthly-sales.csv", "monthly-sales-updated.csv", "invalid-columns.csv"}
        if filename not in allowed:
            raise AppError("sample", "このサンプルはありません。", 404)
        path = Path(__file__).resolve().parent / "samples" / filename
        return send_file(path, mimetype="text/csv", as_attachment=True, download_name=filename)

    return app
