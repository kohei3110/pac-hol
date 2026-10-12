from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import re
from typing import Protocol
from uuid import UUID

from azure.core import MatchConditions
from azure.core import exceptions as azure_errors
from azure.core.pipeline.transport import RequestsTransport
from azure.identity import ManagedIdentityCredential
from azure.storage.blob import BlobServiceClient, ContentSettings

from .data import AppError, FILENAME, MAX_FILE_BYTES, MAX_FILES, validate_file_id


@dataclass(frozen=True)
class Settings:
    account: str
    client_id: str
    container: str = "uploads"

    @classmethod
    def from_env(cls, env: dict) -> "Settings":
        account, client_id = env.get("AZURE_STORAGE_ACCOUNT"), env.get("AZURE_CLIENT_ID")
        if not isinstance(account, str) or not re.fullmatch(r"[a-z0-9]{3,24}", account):
            raise ValueError("AZURE_STORAGE_ACCOUNT must be a valid storage account name.")
        if not isinstance(client_id, str):
            raise ValueError("AZURE_CLIENT_ID is required for the assigned managed identity.")
        try:
            identifier = UUID(client_id)
        except ValueError:
            raise ValueError("AZURE_CLIENT_ID must be a valid managed-identity client ID.") from None
        if identifier.int == 0:
            raise ValueError("AZURE_CLIENT_ID must not be the zero UUID.")
        return cls(account, str(identifier))

    @property
    def account_url(self) -> str:
        return f"https://{self.account}.blob.core.windows.net"


@dataclass(frozen=True)
class StoredFile:
    identifier: str
    filename: str
    size: int
    etag: str
    sha256: str
    updated: str

    def as_dict(self) -> dict:
        return {
            "id": self.identifier,
            "filename": self.filename,
            "size": self.size,
            "etag": self.etag,
            "sha256": self.sha256,
            "updated": self.updated,
            "blobName": f"files/{self.identifier}.csv",
        }


class UploadStore(Protocol):
    source: str

    def save(self, filename: str, content: bytes) -> StoredFile: ...
    def list_files(self) -> list[StoredFile]: ...
    def read(self, identifier: str) -> tuple[StoredFile, bytes]: ...
    def delete(self, identifier: str, etag: str) -> None: ...


class AzureBlobStore:
    source = "azure-blob"

    def __init__(self, settings: Settings, *, container_client=None):
        self.settings = settings
        self.credential = None
        self.service = None
        if container_client is not None:
            self.container = container_client
            return
        self.credential = ManagedIdentityCredential(
            client_id=settings.client_id, connection_timeout=3, read_timeout=5, retry_total=0
        )
        self.service = BlobServiceClient(
            settings.account_url,
            credential=self.credential,
            retry_total=2,
            redirect_max=0,
            transport=RequestsTransport(connection_timeout=3, read_timeout=10, use_env_settings=False),
        )
        self.container = self.service.get_container_client(settings.container)

    def close(self):
        if self.service is not None:
            self.service.close()
        if self.credential is not None:
            self.credential.close()

    @contextmanager
    def _azure(self, *, file_operation=False):
        try:
            yield
        except azure_errors.ResourceExistsError:
            raise
        except azure_errors.ResourceModifiedError:
            raise AppError("changed", "保存されたファイルが変更されています。再読み込みしてください。", 409) from None
        except azure_errors.ClientAuthenticationError:
            raise AppError("identity", "アプリのマネージドIDで接続できません。講師に連絡してください。", 503) from None
        except azure_errors.ResourceNotFoundError:
            raise AppError(
                "not_found" if file_operation else "storage_missing",
                "このファイルは見つかりません。" if file_operation else "保存先のコンテナーが見つかりません。講師に連絡してください。",
                404 if file_operation else 503,
            ) from None
        except azure_errors.HttpResponseError as error:
            if error.status_code in (401, 403):
                raise AppError("storage_forbidden", "保存先へのアクセスが拒否されました。権限と接続経路の確認が必要なので、講師に連絡してください。", 503) from None
            raise AppError("storage_response", "Storageがエラーを返しました。要求IDを講師へ伝えてください。", 503) from None
        except (azure_errors.ServiceRequestError, azure_errors.ServiceResponseError):
            raise AppError("storage_network", "保存先につながりません。DNSやネットワークの確認が必要なので、講師に連絡してください。", 503) from None

    @staticmethod
    def _path(identifier: str) -> str:
        return f"files/{validate_file_id(identifier)}.csv"

    @staticmethod
    def _record(identifier: str, properties) -> StoredFile:
        metadata = properties.metadata
        if not isinstance(metadata, dict):
            raise AppError("blob_metadata", "Blobの学習用メタデータがありません。", 502)
        name, digest = metadata.get("filename"), metadata.get("sha256")
        if (
            metadata.get("schema") != "hol04-v1"
            or not isinstance(name, str) or not FILENAME.fullmatch(name) or ".." in name
            or not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest)
            or not isinstance(properties.size, int) or not 0 < properties.size <= MAX_FILE_BYTES
            or not isinstance(properties.etag, str) or not properties.etag
            or not isinstance(properties.last_modified, datetime)
        ):
            raise AppError("blob_metadata", "保存されたBlobが、このアプリで読み取れる形式になっていません。", 502)
        return StoredFile(identifier, name, properties.size, properties.etag, digest,
                          properties.last_modified.astimezone(timezone.utc).isoformat())

    def save(self, filename: str, content: bytes) -> StoredFile:
        digest = hashlib.sha256(content).hexdigest()
        # Fixed slots and If-None-Match enforce the limit across simultaneous replicas.
        for number in range(1, MAX_FILES + 1):
            identifier = f"file-{number:02}"
            blob = self.container.get_blob_client(self._path(identifier))
            try:
                with self._azure():
                    blob.upload_blob(
                        content, overwrite=False, max_concurrency=1,
                        content_settings=ContentSettings(content_type="text/csv; charset=utf-8"),
                        metadata={"schema": "hol04-v1", "filename": filename, "sha256": digest},
                    )
                    return self._record(identifier, blob.get_blob_properties())
            except azure_errors.ResourceExistsError:
                continue
        raise AppError("file_limit", "10件まで保存できます。今回保存した不要なファイルを削除してから、もう一度試してください。", 409)

    def list_files(self) -> list[StoredFile]:
        result = []
        with self._azure():
            for blob in self.container.list_blobs(name_starts_with="files/", include=["metadata"]):
                match = re.fullmatch(r"files/(file-(?:0[1-9]|10))\.csv", blob.name)
                if not match:
                    raise AppError("unknown_blob", "アプリが管理しないBlobがfiles/内にあります。講師へ連絡してください。", 409)
                result.append(self._record(match[1], blob))
        return sorted(result, key=lambda file: (file.updated, file.identifier), reverse=True)

    def read(self, identifier: str) -> tuple[StoredFile, bytes]:
        blob = self.container.get_blob_client(self._path(identifier))
        with self._azure(file_operation=True):
            properties = blob.get_blob_properties()
            record = self._record(identifier, properties)
            content = blob.download_blob(
                offset=0, length=record.size, max_concurrency=1,
                etag=record.etag, match_condition=MatchConditions.IfNotModified,
            ).readall()
        if len(content) != record.size or hashlib.sha256(content).hexdigest() != record.sha256:
            raise AppError("blob_integrity", "Blobの内容と保存時のチェックサムが一致しません。", 502)
        return record, content

    def delete(self, identifier: str, etag: str) -> None:
        blob = self.container.get_blob_client(self._path(identifier))
        with self._azure(file_operation=True):
            blob.delete_blob(etag=etag, match_condition=MatchConditions.IfNotModified)
