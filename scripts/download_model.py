"""Resolve or download the pinned MAI on-device package using only the standard library."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass, field
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


ASSET_ID = "azureml://registries/azureml/models/MAI-Code-1.1-Flash-On-Device/versions/2"
CATALOG = "https://api.catalog.azureml.ms"
ROOT = Path(__file__).resolve().parents[1]
CHUNK_BYTES = 1024 * 1024
RANGE_BYTES = 64 * 1024 * 1024
METADATA_LIMIT = 4 * 1024 * 1024
MAX_ATTEMPTS = 3


@dataclass(frozen=True)
class Artifact:
    name: str
    size: int
    sha256: str | None


# GGUF digests were observed in the retained run manifests, not supplied by the catalog.
ARTIFACTS = (
    Artifact("MAI-Code-1.1-Flash-Q2-XS.gguf", 56307620832,
             "048788de4848e92c7a543feb1c5e0c9144515ac8a3fec1508d5857d25b0e556e"),
    Artifact("dflash-v3-lc1.gguf", 381214016,
             "7052df547898b46fab3ff23f8c1085547003116899506099467f948debb75b15"),
    Artifact("llama-config.json", 504, None),
)


@dataclass(frozen=True)
class Blob:
    artifact: Artifact
    url: str = field(repr=False)
    etag: str


class DownloadError(Exception):
    pass


class RemoteError(DownloadError):
    def __init__(self, status=None):
        self.status = status
        self.retryable = status is None or status in (403, 408, 429, 500, 502, 503, 504)
        super().__init__(f"Remote request failed (HTTP {status})." if status else
                         "Remote connection interrupted or timed out.")


def require(condition, message):
    if not condition:
        raise DownloadError(message)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(NoRedirect())


def https_location(url, *, blob_only=False):
    try:
        parsed = urllib.parse.urlsplit(url)
        port = parsed.port
    except (ValueError, TypeError):
        raise DownloadError("Remote location is not a valid HTTPS URL.") from None
    require(parsed.scheme == "https" and port in (None, 443)
            and not parsed.username and not parsed.password and not parsed.fragment
            and ((not blob_only and parsed.hostname == "api.catalog.azureml.ms")
                 or (parsed.hostname or "").endswith(".blob.core.windows.net")),
            "Refusing a URL outside the HTTPS catalog/Azure Blob allowlist.")
    return parsed


def request(url, *, method="GET", headers=None, data=None):
    https_location(url)
    combined = {"User-Agent": "MAI-on-device-downloader/1.0", "Accept-Encoding": "identity"}
    combined.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=combined, method=method)
    try:
        return OPENER.open(req, timeout=60)
    except urllib.error.HTTPError as error:
        status = error.code
        error.close()
        raise RemoteError(status) from None
    except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException):
        raise RemoteError() from None


def metadata(url, *, data=None, headers=None):
    with request(url, method="POST" if data is not None else "GET",
                 data=data, headers=headers) as response:
        require(response.status == 200, "Unexpected metadata response status.")
        try:
            body = response.read(METADATA_LIMIT + 1)
        except (OSError, http.client.HTTPException):
            raise RemoteError() from None
    require(len(body) <= METADATA_LIMIT, "Metadata response exceeds the size limit.")
    return body


def json_metadata(url, **kwargs):
    try:
        return json.loads(metadata(url, **kwargs))
    except (ValueError, UnicodeError):
        raise DownloadError("Catalog returned invalid JSON metadata.") from None


def list_models():
    """List all latest public GGUF entries explicitly marked for Copilot local use."""
    body = {
        "filters": [
            {"field": key, "operator": "eq", "values": [value]}
            for key, value in (
                ("type", "models"), ("kind", "Versioned"), ("labels", "latest"),
                ("annotations/systemCatalogData/modelFlavor", "GGUF"),
            )
        ],
        "pageSize": 100,
    }
    models = set()
    seen = set()
    for _ in range(100):
        page = json_metadata(CATALOG + "/asset-gallery/v1.0/models",
                             data=json.dumps(body).encode("utf-8"),
                             headers={"Content-Type": "application/json",
                                      "x-ms-use-full-service-contracts": "true"})
        require(isinstance(page, dict) and isinstance(page.get("value"), list),
                "Catalog search response has an unexpected shape.")
        for row in page["value"]:
            require(isinstance(row, dict), "Catalog search contains an invalid entry.")
            annotations = row.get("annotations") or {}
            require(isinstance(annotations, dict), "Catalog annotations are invalid.")
            info = annotations.get("systemCatalogData") or {}
            require(isinstance(info, dict), "Catalog local-model metadata is invalid.")
            if (info.get("modelFlavor") == "GGUF" and info.get("githubCopilotLocal") is True
                    and not annotations.get("archived") and not annotations.get("isArchived")):
                asset = row.get("assetId")
                require(isinstance(asset, str), "Catalog asset identity is missing.")
                if re.fullmatch(r"azureml://registries/azureml/models/[A-Za-z0-9._-]+"
                                r"/versions/[A-Za-z0-9._-]+", asset):
                    models.add(asset)
        token = page.get("continuationToken")
        if token is None or token == "":
            return sorted(models)
        require(isinstance(token, str) and token not in seen,
                "Catalog pagination token is invalid or repeated.")
        seen.add(token)
        body["continuationToken"] = token
    raise DownloadError("Catalog pagination exceeds the page limit.")


def resolve():
    result = json_metadata(CATALOG + "/modelregistry/v1.0/registry/models/nonazureaccount?"
                           + urllib.parse.urlencode({"assetId": ASSET_ID}))
    require(isinstance(result, dict), "Resolver response has an unexpected shape.")
    entity = result.get("modelEntity")
    require(isinstance(entity, dict) and entity.get("assetId") == ASSET_ID
            and entity.get("isArchived") is False, "Resolver returned a different or archived asset.")
    info = entity.get("systemMetadata") or {}
    require(isinstance(info, dict) and info.get("modelFlavor") == "GGUF"
            and info.get("githubCopilotLocal") is True,
            "Asset is not marked as an on-device GGUF model.")
    sas = result.get("blobSasUri")
    require(isinstance(sas, str), "Resolver did not supply a Blob download location.")
    parsed = https_location(sas, blob_only=True)
    require(bool(parsed.query), "Resolver supplied an unsigned Azure Blob location.")
    segments = parsed.path.strip("/").split("/")
    require(all(segment and urllib.parse.unquote(segment) not in (".", "..")
                for segment in segments), "Resolver supplied an invalid Blob prefix.")
    container = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "/" + segments[0], "", ""))
    prefix = urllib.parse.unquote("/".join(segments[1:])).rstrip("/")
    prefix = prefix + "/" if prefix else ""
    sizes = {}
    marker = ""
    seen = set()
    for _ in range(100):
        query = {"restype": "container", "comp": "list", "maxresults": 100,
                 "prefix": prefix, "marker": marker}
        raw = metadata(container + "?" + parsed.query + "&" + urllib.parse.urlencode(query))
        require(b"<!DOCTYPE" not in raw.upper() and b"<!ENTITY" not in raw.upper(),
                "Blob listing contains unsupported XML declarations.")
        try:
            listing = ET.fromstring(raw)
        except ET.ParseError:
            raise DownloadError("Blob listing contains invalid XML.") from None
        require(listing.tag == "EnumerationResults", "Blob listing has an unexpected shape.")
        for blob in listing.findall("./Blobs/Blob"):
            name = blob.findtext("Name")
            size = blob.findtext("./Properties/Content-Length", "")
            require(name not in sizes and size.isdecimal(), "Blob listing has invalid file entries.")
            sizes[name] = int(size)
        marker = listing.findtext("NextMarker") or ""
        if not marker:
            break
        require(marker not in seen, "Blob listing repeats a pagination marker.")
        seen.add(marker)
    else:
        raise DownloadError("Blob listing exceeds the page limit.")
    expected = {prefix + artifact.name: artifact.size for artifact in ARTIFACTS}
    require(sizes == expected, "Asset files or sizes differ from the pinned version-2 package.")
    blobs = {}
    for artifact in ARTIFACTS:
        url = container + "/" + urllib.parse.quote(prefix + artifact.name, safe="/") + "?" + parsed.query
        with request(url, method="HEAD") as response:
            require(response.status == 200
                    and response.headers.get("Content-Length") == str(artifact.size),
                    f"{artifact.name}: HEAD size does not match the pinned package.")
            etag = response.headers.get("ETag", "")
            require(re.fullmatch(r'"[A-Za-z0-9._:-]+"', etag) is not None,
                    f"{artifact.name}: a strong ETag is required.")
            require(response.headers.get("Content-Encoding", "identity") == "identity",
                    f"{artifact.name}: compressed transfers are not supported.")
        blobs[artifact.name] = Blob(artifact, url, etag)
    return blobs


def atomic_json(path, value):
    require(not path.is_symlink(), "Refusing a symbolic-link metadata file.")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".download-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def hash_file(path):
    digest = hashlib.sha256()
    if path.exists():
        with path.open("rb") as stream:
            while chunk := stream.read(CHUNK_BYTES):
                digest.update(chunk)
    return digest


def allocated_bytes(path):
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        get_size = ctypes.WinDLL("kernel32", use_last_error=True).GetCompressedFileSizeW
        get_size.argtypes = (wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD))
        get_size.restype = wintypes.DWORD
        high = wintypes.DWORD()
        ctypes.set_last_error(0)
        low = get_size(str(path.resolve()), ctypes.byref(high))
        if low == 0xFFFFFFFF and ctypes.get_last_error():
            raise ctypes.WinError(ctypes.get_last_error())
        return (high.value << 32) | low
    info = path.stat()
    require(hasattr(info, "st_blocks"), "Cannot determine partial-file disk allocation on this platform.")
    return info.st_blocks * 512


def validate_file(path, artifact, digest):
    require(path.stat().st_size == artifact.size, f"{artifact.name}: file size mismatch.")
    require(artifact.sha256 is None or digest == artifact.sha256,
            f"{artifact.name}: SHA-256 mismatch; file retained, not installed.")
    if artifact.name == "llama-config.json":
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError):
            raise DownloadError("llama-config.json: invalid JSON; file retained, not installed.") from None
        require(isinstance(config, dict), "llama-config.json must contain a JSON object.")
    return {"bytes": artifact.size, "sha256": digest,
            "verification": "archived-sha256" if artifact.sha256 else "https-etag-size-json"}


@contextmanager
def transfer_response(blob, offset=0, end=None):
    artifact = blob.artifact
    headers = {"If-Match": blob.etag}
    ranged = bool(offset) or end is not None
    if ranged:
        headers["Range"] = f"bytes={offset}-" + (str(end) if end is not None else "")
    last_byte = artifact.size - 1 if end is None else end
    with request(blob.url, headers=headers) as response:
        require(response.status == (206 if ranged else 200),
                f"{artifact.name}: server did not honor the requested transfer range.")
        require(response.headers.get("ETag") == blob.etag,
                f"{artifact.name}: response ETag changed.")
        require(response.headers.get("Content-Length") == str(last_byte - offset + 1)
                and response.headers.get("Content-Encoding", "identity") == "identity",
                f"{artifact.name}: response size/encoding is invalid.")
        if ranged:
            require(response.headers.get("Content-Range")
                    == f"bytes {offset}-{last_byte}/{artifact.size}",
                    f"{artifact.name}: invalid Content-Range; partial file is unchanged.")
        yield response


def partial_identity(blob):
    artifact = blob.artifact
    return {"assetId": ASSET_ID, "name": artifact.name, "bytes": artifact.size,
            "sha256": artifact.sha256, "etag": blob.etag}


def read_partial_state(path, name):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError):
        raise DownloadError(f"{name}: partial-download metadata is invalid.") from None


def download_ranges(blob, target, partial, state_path, emit, parallelism):
    artifact = blob.artifact
    identity = partial_identity(blob)
    count = (artifact.size + RANGE_BYTES - 1) // RANGE_BYTES
    existing_size = partial.stat().st_size if partial.exists() else 0
    require(existing_size <= artifact.size, f"{artifact.name}: partial file exceeds expected size.")
    if state_path.exists():
        saved = read_partial_state(state_path, artifact.name)
        if saved == identity:
            # A former sequential partial is a contiguous prefix; only whole ranges are reusable.
            completed = set(range(existing_size // RANGE_BYTES))
            if existing_size == artifact.size:
                completed = set(range(count))
        else:
            require(isinstance(saved, dict)
                    and all(saved.get(key) == value for key, value in identity.items())
                    and saved.get("mode") == "parallel-ranges-v1"
                    and saved.get("rangeBytes") == RANGE_BYTES,
                    f"{artifact.name}: partial identity/ETag or range layout changed.")
            entries = saved.get("completedRanges")
            require(isinstance(entries, list)
                    and all(type(index) is int and 0 <= index < count for index in entries)
                    and len(set(entries)) == len(entries),
                    f"{artifact.name}: invalid completed-range journal.")
            completed = set(entries)
            require(all(existing_size >= min((index + 1) * RANGE_BYTES, artifact.size)
                        for index in completed),
                    f"{artifact.name}: journal references missing partial bytes.")
    else:
        require(not partial.exists(), f"{artifact.name}: partial file has no identity metadata.")
        completed = set()
    if not partial.exists():
        partial.open("xb").close()
    state = {**identity, "mode": "parallel-ranges-v1", "rangeBytes": RANGE_BYTES,
             "completedRanges": sorted(completed)}
    atomic_json(state_path, state)
    state_lock = threading.Lock()
    stop = threading.Event()
    last_progress = time.monotonic()

    def fetch_range(index):
        nonlocal last_progress
        if stop.is_set():
            raise DownloadError("Parallel transfer cancelled; incomplete ranges remain resumable.")
        start = index * RANGE_BYTES
        end = min(start + RANGE_BYTES, artifact.size) - 1
        position = start
        with transfer_response(blob, start, end) as response, partial.open("r+b") as stream:
            stream.seek(start)
            while position <= end:
                if stop.is_set():
                    raise DownloadError("Parallel transfer cancelled; incomplete ranges remain resumable.")
                try:
                    chunk = response.read(min(CHUNK_BYTES, end - position + 1))
                except (OSError, http.client.HTTPException):
                    raise RemoteError() from None
                if not chunk:
                    raise RemoteError()
                stream.write(chunk)
                position += len(chunk)
            stream.flush()
            os.fsync(stream.fileno())
        with state_lock:
            completed.add(index)
            state["completedRanges"] = sorted(completed)
            atomic_json(state_path, state)
            if time.monotonic() - last_progress >= 5 or len(completed) == count:
                total = sum(min(RANGE_BYTES, artifact.size - item * RANGE_BYTES)
                            for item in completed)
                emit(f"{artifact.name}: {total}/{artifact.size} bytes in completed ranges "
                     f"({total / artifact.size:.1%}).")
                last_progress = time.monotonic()

    pending = [index for index in range(count) if index not in completed]
    emit(f"{artifact.name}: {len(completed)}/{count} ranges already complete; "
         f"using up to {parallelism} parallel connections.")
    with ThreadPoolExecutor(max_workers=parallelism) as pool:
        futures = []
        try:
            futures = [pool.submit(fetch_range, index) for index in pending]
            for future in as_completed(futures):
                future.result()
        finally:
            stop.set()
            for future in futures:
                future.cancel()
    require(len(completed) == count, f"{artifact.name}: not all ranges completed.")
    emit(f"{artifact.name}: verifying full-file SHA-256 before installation.")
    result = validate_file(partial, artifact, hash_file(partial).hexdigest())
    require(not target.exists(), f"{artifact.name}: destination appeared during transfer; not overwritten.")
    os.replace(partial, target)
    state_path.unlink()
    emit(f"{artifact.name}: complete.")
    return result


def download_file(blob, directory, emit, parallelism=4):
    artifact = blob.artifact
    target = directory / artifact.name
    partial = directory / (artifact.name + ".part")
    state_path = directory / (artifact.name + ".part.json")
    for path in (target, partial, state_path):
        require(not path.is_symlink(), f"{artifact.name}: refusing a symbolic-link file.")
    if target.exists():
        require(not partial.exists(), f"{artifact.name}: both complete and partial files exist.")
        require(target.is_file() and target.stat().st_size == artifact.size,
                f"{artifact.name}: existing file has the wrong size; it will not be overwritten.")
        emit(f"{artifact.name}: checking existing file.")
        result = validate_file(target, artifact, hash_file(target).hexdigest())
        if artifact.sha256 is None:
            # There is no pinned config digest: compare existing bytes with the current remote blob.
            with transfer_response(blob) as response:
                try:
                    current = response.read(artifact.size + 1)
                except (OSError, http.client.HTTPException):
                    raise RemoteError() from None
            require(len(current) == artifact.size
                    and hashlib.sha256(current).hexdigest() == result["sha256"],
                    f"{artifact.name}: existing file differs from the remote config; not overwritten.")
        return result
    if artifact.sha256 is not None and artifact.size > RANGE_BYTES:
        return download_ranges(blob, target, partial, state_path, emit, parallelism)
    identity = partial_identity(blob)
    if state_path.exists():
        saved = read_partial_state(state_path, artifact.name)
        require(saved == identity,
                f"{artifact.name}: partial identity/ETag changed; refusing to combine different revisions.")
    else:
        require(not partial.exists(), f"{artifact.name}: partial file has no identity metadata.")
        atomic_json(state_path, identity)
    offset = partial.stat().st_size if partial.exists() else 0
    require(offset <= artifact.size, f"{artifact.name}: partial file exceeds the expected size.")
    if offset and artifact.sha256 is None:
        # The tiny config has no reference digest; re-fetch it rather than trust a saved prefix.
        partial.unlink()
        offset = 0
    emit(f"{artifact.name}: hashing {offset} existing bytes before transfer.")
    digest = hash_file(partial)
    if offset < artifact.size:
        with transfer_response(blob, offset) as response:
            last_progress = time.monotonic()
            with partial.open("ab") as stream:
                while offset < artifact.size:
                    try:
                        chunk = response.read(min(CHUNK_BYTES, artifact.size - offset))
                    except (OSError, http.client.HTTPException):
                        raise RemoteError() from None
                    if not chunk:
                        raise RemoteError()
                    stream.write(chunk)
                    digest.update(chunk)
                    offset += len(chunk)
                    if time.monotonic() - last_progress >= 5:
                        emit(f"{artifact.name}: {offset}/{artifact.size} bytes ({offset / artifact.size:.1%}).")
                        last_progress = time.monotonic()
                stream.flush()
                os.fsync(stream.fileno())
    result = validate_file(partial, artifact, digest.hexdigest())
    require(not target.exists(), f"{artifact.name}: destination appeared during transfer; not overwritten.")
    os.replace(partial, target)
    state_path.unlink()
    emit(f"{artifact.name}: complete.")
    return result


@contextmanager
def output_lock(directory):
    lock = directory / ".download.lock"
    try:
        stream = lock.open("x", encoding="ascii")
    except FileExistsError:
        raise DownloadError("Output directory is locked. If no downloader is running, remove .download.lock.") from None
    try:
        with stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        lock.unlink()


def download(blobs, directory, emit, parallelism=4):
    directory.mkdir(parents=True, exist_ok=True)
    with output_lock(directory):
        remaining = 0
        for artifact in ARTIFACTS:
            target = directory / artifact.name
            partial = directory / (artifact.name + ".part")
            require(not target.is_symlink() and not partial.is_symlink(),
                    f"{artifact.name}: refusing a symbolic-link file.")
            if target.is_file():
                available = target.stat().st_size
            elif partial.is_file():
                # Logical length includes unwritten holes in random-access partial files.
                available = min(artifact.size, allocated_bytes(partial))
            else:
                available = 0
            remaining += max(0, artifact.size - available)
        require(shutil.disk_usage(directory).free >= remaining + 64 * 1024 * 1024,
                "Insufficient free disk space for the remaining downloads plus a 64 MiB margin.")
        completed = {}
        for artifact in ARTIFACTS:
            for attempt in range(MAX_ATTEMPTS):
                try:
                    if attempt:
                        blobs = resolve()
                    completed[artifact.name] = download_file(blobs[artifact.name], directory, emit,
                                                             parallelism)
                    break
                except RemoteError as error:
                    if not error.retryable or attempt == MAX_ATTEMPTS - 1:
                        raise
                    emit(f"{artifact.name}: transient request failure; refreshing metadata and retrying "
                         f"({attempt + 2}/{MAX_ATTEMPTS}). Partial bytes are retained.")
                    time.sleep(2 ** attempt)
        receipt = {"assetId": ASSET_ID, "files": completed}
        atomic_json(directory / "download-manifest.json", receipt)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--list-models", action="store_true", help="List on-device GGUF catalog assets; no downloads.")
    mode.add_argument("--dry-run", action="store_true", help="Resolve/list/HEAD metadata only (the default).")
    mode.add_argument("--download", action="store_true", help="Explicitly download the three version-2 artifacts.")
    parser.add_argument("--output", type=Path, default=ROOT / "models" / "MAI-Code-1.1-Flash-On-Device",
                        help="Destination directory; only created with --download.")
    parser.add_argument("--parallelism", type=int, choices=range(1, 17), default=4, metavar="1..16",
                        help="Concurrent byte-range requests per large GGUF (default: 4; 1 disables parallelism).")
    args = parser.parse_args(argv)
    try:
        if args.list_models:
            print(json.dumps(list_models(), indent=2))
            return 0
        blobs = resolve()
        if args.download:
            receipt = download(blobs, args.output, lambda line: print(line, file=sys.stderr, flush=True),
                               args.parallelism)
            print(json.dumps(receipt, indent=2))
        else:
            print(json.dumps({
                "mode": "metadata-only",
                "assetId": ASSET_ID,
                "totalBytes": sum(artifact.size for artifact in ARTIFACTS),
                "parallelism": args.parallelism,
                "files": [{"name": artifact.name, "bytes": artifact.size,
                           "archivedSha256": artifact.sha256} for artifact in ARTIFACTS],
                "note": "No artifact bodies fetched. Use --download to transfer files.",
            }, indent=2))
        return 0
    except DownloadError as error:
        print(f"Downloader failed: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"Downloader failed: local I/O error (errno {error.errno}).", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted. Partial downloads are retained; rerun --download to resume.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
