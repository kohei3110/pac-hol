import hashlib
import ipaddress
import json
import os
import re
import socket
from urllib.parse import urlsplit

from .data import parse_csv, validate_file_id
from .storage import AzureBlobStore, Settings


def main():
    settings = Settings.from_env(dict(os.environ))
    identifier = validate_file_id(os.environ["VERIFY_FILE_ID"])
    expected = os.environ["VERIFY_EXPECTED_SHA256"]
    if not re.fullmatch(r"[a-f0-9]{64}", expected):
        raise ValueError("VERIFY_EXPECTED_SHA256 must be the source-file SHA-256.")
    addresses = socket.getaddrinfo(urlsplit(settings.account_url).hostname, 443, type=socket.SOCK_STREAM)
    private_dns = bool(addresses) and all(ipaddress.ip_address(item[4][0]).is_private for item in addresses)
    store = AzureBlobStore(settings)
    try:
        record, content = store.read(identifier)
        digest = hashlib.sha256(content).hexdigest()
        if digest != expected or not private_dns:
            raise RuntimeError("Independent Blob checksum or private DNS validation failed.")
        dataset = parse_csv(content)
        print(json.dumps({
            "verified": True,
            "source": "independent-azure-blob-read",
            "sha256": digest, "size": len(content), "etagPresent": bool(record.etag),
            "privateDnsResolved": private_dns,
            "rowCount": len(dataset.rows), "total": sum(row.value for row in dataset.rows),
        }), flush=True)
    finally:
        store.close()


if __name__ == "__main__":
    main()
