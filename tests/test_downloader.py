from contextlib import redirect_stderr, redirect_stdout
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import socket
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.parse
import urllib.request
from xml.sax.saxutils import escape

from scripts import download_model as downloader


def fixture_signed_url(location, signature="fixture-secret"):
    return location + "?" + urllib.parse.urlencode({"sig": signature})


class DownloaderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name) / "package"
        self.bodies = {
            "MAI-Code-1.1-Flash-Q2-XS.gguf": b"fixture-model-weights-not-a-real-gguf",
            "dflash-v3-lc1.gguf": b"fixture-drafter-not-a-real-gguf",
            "llama-config.json": b'{"model":"MAI-Code-1.1-Flash-Q2-XS.gguf"}',
        }
        artifacts = tuple(
            downloader.Artifact(name, len(body),
                                hashlib.sha256(body).hexdigest() if name.endswith(".gguf") else None)
            for name, body in self.bodies.items()
        )
        self.addCleanup(patch.stopall)
        patch.object(downloader, "ARTIFACTS", artifacts).start()
        patch.object(downloader.time, "sleep", lambda _: None).start()
        self.calls = []
        self.resolutions = 0
        self.behavior = None
        self.behavior_name = None
        self.behavior_used = False
        self.extra_blob = False
        self.bad_asset = False
        self.bad_sas = None
        self.catalog_repeat = False
        self.active_gets = 0
        self.max_active_gets = 0
        self.active_lock = threading.Lock()
        self.get_delay = 0
        self.fail_range_start = None
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reply(self, status, body=b"", headers=None):
                self.send_response(status)
                for name, value in (headers or {"Content-Length": str(len(body))}).items():
                    self.send_header(name, value)
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(body)

            def do_POST(self):
                fixture.calls.append(("POST", self.path, dict(self.headers)))
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if self.headers.get("x-ms-use-full-service-contracts") != "true":
                    self.reply(400)
                    return
                entries = [
                    {"assetId": downloader.ASSET_ID,
                     "annotations": {"systemCatalogData": {
                         "modelFlavor": "GGUF", "githubCopilotLocal": True}}},
                    {"assetId": "azureml://registries/azureml/models/Online/versions/1",
                     "annotations": {"systemCatalogData": {
                         "modelFlavor": "GGUF", "githubCopilotLocal": False}}},
                    {"assetId": "azureml://registries/azureml/models/Other-Local/versions/1",
                     "annotations": {"systemCatalogData": {
                         "modelFlavor": "GGUF", "githubCopilotLocal": True}}},
                ]
                index = int(body.get("continuationToken", 0))
                next_token = str(index + 1) if index < len(entries) - 1 else None
                if fixture.catalog_repeat:
                    next_token = "1"
                self.reply(200, json.dumps({"value": entries[index:index + 1],
                                           "continuationToken": next_token}).encode())

            def do_HEAD(self):
                self.do_GET()

            def do_GET(self):
                fixture.calls.append((self.command, self.path, dict(self.headers)))
                parsed = urllib.parse.urlsplit(self.path)
                query = urllib.parse.parse_qs(parsed.query)
                if parsed.path.endswith("/nonazureaccount"):
                    fixture.resolutions += 1
                    data = {
                        "modelEntity": {
                            "assetId": "different-asset" if fixture.bad_asset else downloader.ASSET_ID,
                            "isArchived": False,
                            "systemMetadata": {"modelFlavor": "GGUF", "githubCopilotLocal": True},
                        },
                        "blobSasUri": fixture.bad_sas or fixture_signed_url(
                            "https://fixture.blob.core.windows.net/container/bundle",
                            f"fixture-secret-{fixture.resolutions}"),
                    }
                    self.reply(200, json.dumps(data).encode())
                    return
                if query.get("comp") == ["list"]:
                    names = list(fixture.bodies)
                    if fixture.extra_blob:
                        names.append("../unexpected.gguf")
                    index = int(query.get("marker", ["0"])[0])
                    page = names[index:index + 2]
                    rows = "".join(
                        "<Blob><Name>" + escape("bundle/" + name)
                        + "</Name><Properties><Content-Length>"
                        + str(len(fixture.bodies.get(name, b"unexpected")))
                        + "</Content-Length></Properties></Blob>" for name in page
                    )
                    marker = str(index + 2) if index + 2 < len(names) else ""
                    self.reply(200, ("<EnumerationResults><Blobs>" + rows
                                     + "</Blobs><NextMarker>" + marker
                                     + "</NextMarker></EnumerationResults>").encode())
                    return
                name = parsed.path.rsplit("/", 1)[-1]
                if name not in fixture.bodies:
                    self.reply(404)
                    return
                body = fixture.bodies[name]
                headers = {"Content-Length": str(len(body)), "ETag": '"fixture-v1"',
                           "Accept-Ranges": "bytes"}
                if self.command == "HEAD":
                    self.reply(200, headers=headers)
                    return
                with fixture.active_lock:
                    fixture.active_gets += 1
                    fixture.max_active_gets = max(fixture.max_active_gets, fixture.active_gets)
                try:
                    threading.Event().wait(fixture.get_delay)
                    self.serve_blob(name, body, headers)
                finally:
                    with fixture.active_lock:
                        fixture.active_gets -= 1

            def serve_blob(self, name, body, headers):
                if self.headers.get("If-Match") != '"fixture-v1"':
                    self.reply(412)
                    return
                behavior = fixture.behavior if (
                    not fixture.behavior_used
                    and fixture.behavior_name in (None, name)) else None
                if behavior == "expired":
                    fixture.behavior_used = True
                    self.reply(403)
                    return
                if behavior == "unavailable":
                    self.reply(503)
                    return
                if behavior == "redirect":
                    self.reply(302, headers={"Content-Length": "0",
                                             "Location": fixture_signed_url("https://attacker.invalid/")})
                    return
                requested_range = self.headers.get("Range")
                start_text, end_text = (requested_range or "bytes=0-").split("=")[1].split("-")
                offset = int(start_text)
                end = int(end_text) if end_text else len(body) - 1
                if requested_range:
                    headers["Content-Range"] = f"bytes {offset}-{end}/{len(body)}"
                if requested_range and fixture.fail_range_start == offset:
                    threading.Event().wait(0.05)
                    self.reply(503)
                    return
                payload = body[offset:end + 1]
                headers["Content-Length"] = str(len(payload))
                if behavior == "wrong-range":
                    headers["Content-Range"] = f"bytes 0-{len(body) - 1}/{len(body)}"
                if behavior == "changed-etag":
                    headers["ETag"] = '"fixture-v2"'
                if behavior == "wrong-length":
                    headers["Content-Length"] = str(len(payload) + 1)
                if behavior == "corrupt":
                    payload = b"x" * len(payload)
                if behavior == "truncate":
                    fixture.behavior_used = True
                    self.reply(206 if requested_range else 200, payload[:7], headers)
                    self.wfile.flush()
                    self.connection.shutdown(socket.SHUT_WR)
                    return
                status = 206 if requested_range and behavior != "ignored-range" else 200
                self.reply(status, payload, headers)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        local_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                                   downloader.NoRedirect())
        origin = f"http://127.0.0.1:{self.server.server_port}"

        class FixtureOpener:
            def open(self, request, timeout):
                parsed = urllib.parse.urlsplit(request.full_url)
                local = urllib.request.Request(
                    origin + parsed.path + ("?" + parsed.query if parsed.query else ""),
                    data=request.data, headers=dict(request.header_items()),
                    method=request.get_method(),
                )
                return local_opener.open(local, timeout=timeout)

        patch.object(downloader, "OPENER", FixtureOpener()).start()

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def run_cli(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = downloader.main([*args, "--output", str(self.output)])
        return code, stdout.getvalue(), stderr.getvalue()

    def artifact_gets(self):
        return [call for call in self.calls if call[0] == "GET"
                and urllib.parse.urlsplit(call[1]).path.startswith("/container/")
                and "comp=list" not in call[1]]

    def seed_partial(self, blob, data):
        self.output.mkdir(exist_ok=True)
        artifact = blob.artifact
        (self.output / (artifact.name + ".part")).write_bytes(data)
        (self.output / (artifact.name + ".part.json")).write_text(json.dumps({
            "assetId": downloader.ASSET_ID, "name": artifact.name, "bytes": artifact.size,
            "sha256": artifact.sha256, "etag": blob.etag,
        }), encoding="utf-8")

    def test_default_and_explicit_dry_run_fetch_only_metadata(self):
        for args in ((), ("--dry-run",)):
            with self.subTest(args=args):
                code, stdout, stderr = self.run_cli(*args)
                self.assertEqual(code, 0, stderr)
                plan = json.loads(stdout)
                self.assertEqual(plan["mode"], "metadata-only")
                self.assertEqual(plan["totalBytes"], sum(map(len, self.bodies.values())))
                self.assertEqual(len(plan["files"]), 3)
                self.assertFalse(self.output.exists())
                self.assertEqual(self.artifact_gets(), [])
                self.assertNotIn("fixture-secret", stdout + stderr)

    def test_catalog_pagination_filters_out_online_models(self):
        code, stdout, stderr = self.run_cli("--list-models")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout), [
            downloader.ASSET_ID, "azureml://registries/azureml/models/Other-Local/versions/1"])
        self.assertEqual(sum(call[0] == "POST" for call in self.calls), 3)
        self.assertEqual(self.artifact_gets(), [])
        self.assertFalse(self.output.exists())

    def test_catalog_repeated_continuation_token_fails(self):
        self.catalog_repeat = True
        code, _, stderr = self.run_cli("--list-models")
        self.assertEqual(code, 1)
        self.assertIn("pagination", stderr)

    def test_streamed_download_and_receipt_contain_no_signed_urls(self):
        code, stdout, stderr = self.run_cli("--download")
        self.assertEqual(code, 0, stderr)
        receipt = json.loads(stdout)
        for name, body in self.bodies.items():
            self.assertEqual((self.output / name).read_bytes(), body)
            self.assertEqual(receipt["files"][name]["sha256"], hashlib.sha256(body).hexdigest())
            self.assertFalse((self.output / (name + ".part")).exists())
        self.assertEqual(receipt["files"]["llama-config.json"]["verification"], "https-etag-size-json")
        stored = "".join(path.read_text(errors="replace") for path in self.output.iterdir())
        self.assertNotIn("sig=", stdout + stderr + stored)
        self.assertNotIn("fixture-secret", stdout + stderr + stored)
        self.assertFalse((self.output / ".download.lock").exists())

    def test_interrupted_transfer_retries_and_resumes_with_range(self):
        self.behavior = "truncate"
        code, _, stderr = self.run_cli("--download")
        self.assertEqual(code, 0, stderr)
        gets = self.artifact_gets()
        self.assertTrue(any(call[2].get("Range") == "bytes=7-" for call in gets))
        for name, body in self.bodies.items():
            self.assertEqual((self.output / name).read_bytes(), body)

    def test_invalid_resume_responses_do_not_modify_existing_partial(self):
        blobs = downloader.resolve()
        blob = next(iter(blobs.values()))
        for behavior in ("wrong-range", "ignored-range", "changed-etag", "wrong-length"):
            with self.subTest(behavior=behavior):
                self.behavior = behavior
                self.seed_partial(blob, b"fixture")
                with self.assertRaises(downloader.DownloadError):
                    downloader.download_file(blob, self.output, lambda _: None)
                self.assertEqual((self.output / (blob.artifact.name + ".part")).read_bytes(),
                                 b"fixture")
                self.assertFalse((self.output / blob.artifact.name).exists())

    def test_expired_sas_is_resolved_again_without_leaking_credentials(self):
        self.behavior = "expired"
        code, stdout, stderr = self.run_cli("--download")
        self.assertEqual(code, 0, stderr)
        self.assertGreaterEqual(self.resolutions, 2)
        self.assertNotIn("fixture-secret", stdout + stderr)
        self.assertEqual(len(self.artifact_gets()), 4)

    def test_retry_limit_fails_without_traceback_or_signed_url(self):
        self.behavior = "unavailable"
        code, stdout, stderr = self.run_cli("--download")
        self.assertEqual(code, 1)
        self.assertEqual(len(self.artifact_gets()), downloader.MAX_ATTEMPTS)
        self.assertIn("HTTP 503", stderr)
        self.assertNotIn("Traceback", stderr)
        self.assertNotIn("fixture-secret", stdout + stderr)
        self.assertFalse((self.output / "download-manifest.json").exists())
        self.assertFalse((self.output / ".download.lock").exists())

    def test_corrupt_download_is_not_promoted_to_completed_file(self):
        self.behavior = "corrupt"
        code, _, stderr = self.run_cli("--download")
        name = next(iter(self.bodies))
        self.assertEqual(code, 1)
        self.assertIn("SHA-256 mismatch", stderr)
        self.assertFalse((self.output / name).exists())
        self.assertTrue((self.output / (name + ".part")).exists())

    def test_existing_valid_weights_are_hashed_without_redownload_and_config_is_compared(self):
        self.output.mkdir()
        for name, body in self.bodies.items():
            (self.output / name).write_bytes(body)
        code, _, stderr = self.run_cli("--download")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(len(self.artifact_gets()), 1)
        self.assertIn("/llama-config.json?", self.artifact_gets()[0][1])

    def test_existing_same_size_modified_json_config_is_not_accepted_or_overwritten(self):
        self.output.mkdir()
        for name, body in self.bodies.items():
            (self.output / name).write_bytes(body)
        config = self.output / "llama-config.json"
        modified = config.read_bytes().replace(b'"model"', b'"other"')
        config.write_bytes(modified)
        code, _, stderr = self.run_cli("--download")
        self.assertEqual(code, 1)
        self.assertIn("differs from the remote config", stderr)
        self.assertEqual(config.read_bytes(), modified)

    def test_known_config_checksum_rejects_modified_existing_json_without_a_get(self):
        config_name = "llama-config.json"
        pinned = tuple(
            downloader.Artifact(artifact.name, artifact.size,
                                hashlib.sha256(self.bodies[config_name]).hexdigest())
            if artifact.name == config_name else artifact
            for artifact in downloader.ARTIFACTS
        )
        self.output.mkdir()
        for name, body in self.bodies.items():
            (self.output / name).write_bytes(body)
        config = self.output / config_name
        modified = config.read_bytes().replace(b'"model"', b'"other"')
        config.write_bytes(modified)
        with patch.object(downloader, "ARTIFACTS", pinned):
            code, _, stderr = self.run_cli("--download")
        self.assertEqual(code, 1)
        self.assertIn("SHA-256 mismatch", stderr)
        self.assertEqual(config.read_bytes(), modified)
        self.assertEqual(self.artifact_gets(), [])

    def test_complete_partial_is_verified_and_installed_without_another_get(self):
        blob = next(iter(downloader.resolve().values()))
        self.seed_partial(blob, self.bodies[blob.artifact.name])
        downloader.download_file(blob, self.output, lambda _: None)
        self.assertEqual((self.output / blob.artifact.name).read_bytes(),
                         self.bodies[blob.artifact.name])
        self.assertEqual(self.artifact_gets(), [])

    def test_invalid_downloaded_config_is_not_installed(self):
        self.behavior = "corrupt"
        self.behavior_name = "llama-config.json"
        code, _, stderr = self.run_cli("--download")
        self.assertEqual(code, 1)
        self.assertIn("invalid JSON", stderr)
        self.assertFalse((self.output / "llama-config.json").exists())
        self.assertTrue((self.output / "llama-config.json.part").exists())
        self.assertFalse((self.output / "download-manifest.json").exists())

    def test_partial_config_without_a_reference_hash_is_refetched_not_trusted(self):
        blob = downloader.resolve()["llama-config.json"]
        modified = self.bodies["llama-config.json"].replace(b'"model"', b'"other"')
        self.seed_partial(blob, modified)
        downloader.download_file(blob, self.output, lambda _: None)
        self.assertEqual((self.output / "llama-config.json").read_bytes(),
                         self.bodies["llama-config.json"])
        self.assertEqual(len(self.artifact_gets()), 1)

    def test_low_disk_space_stops_before_artifact_requests_and_unlocks_output(self):
        with patch.object(downloader.shutil, "disk_usage",
                          return_value=SimpleNamespace(free=0)):
            code, _, stderr = self.run_cli("--download")
        self.assertEqual(code, 1)
        self.assertIn("Insufficient free disk space", stderr)
        self.assertEqual(self.artifact_gets(), [])
        self.assertFalse((self.output / ".download.lock").exists())

    def test_existing_wrong_file_and_foreign_partial_are_not_overwritten(self):
        self.output.mkdir()
        name = next(iter(self.bodies))
        target = self.output / name
        target.write_bytes(b"do-not-overwrite")
        code, _, stderr = self.run_cli("--download")
        self.assertEqual(code, 1)
        self.assertEqual(target.read_bytes(), b"do-not-overwrite")
        self.assertEqual(self.artifact_gets(), [])
        target.unlink()
        partial = self.output / (name + ".part")
        partial.write_bytes(b"foreign-partial")
        code, _, stderr = self.run_cli("--download")
        self.assertEqual(code, 1)
        self.assertIn("no identity metadata", stderr)
        self.assertEqual(partial.read_bytes(), b"foreign-partial")
        self.assertEqual(self.artifact_gets(), [])

    def test_unexpected_asset_or_files_fail_without_artifact_gets(self):
        self.bad_asset = True
        self.assertEqual(self.run_cli("--dry-run")[0], 1)
        self.bad_asset = False
        self.extra_blob = True
        self.assertEqual(self.run_cli("--dry-run")[0], 1)
        self.assertEqual(self.artifact_gets(), [])

    def test_unapproved_locations_and_redirects_are_rejected_without_leaking_urls(self):
        for location in ("http://fixture.blob.core.windows.net/container",
                         "https://attacker.invalid/container",
                         "https://fixture.blob.core.windows.net:invalid/container"):
            with self.subTest(location=location):
                self.bad_sas = fixture_signed_url(location)
                code, stdout, stderr = self.run_cli("--dry-run")
                self.assertEqual(code, 1)
                self.assertNotIn("fixture-secret", stdout + stderr)
        self.bad_sas = None
        self.behavior = "redirect"
        code, stdout, stderr = self.run_cli("--download")
        self.assertEqual(code, 1)
        self.assertIn("HTTP 302", stderr)
        self.assertNotIn("attacker.invalid", stdout + stderr)
        self.assertNotIn("fixture-secret", stdout + stderr)

    def test_changed_partial_identity_and_output_lock_prevent_transfer(self):
        blob = next(iter(downloader.resolve().values()))
        self.seed_partial(blob, b"fixture")
        state = self.output / (blob.artifact.name + ".part.json")
        state.write_text(state.read_text().replace("fixture-v1", "older-revision"))
        code, _, stderr = self.run_cli("--download")
        self.assertEqual(code, 1)
        self.assertIn("identity/ETag changed", stderr)
        lock = self.output / ".download.lock"
        lock.write_text("another-downloader")
        code, _, stderr = self.run_cli("--download")
        self.assertEqual(code, 1)
        self.assertIn("locked", stderr)
        self.assertEqual(lock.read_text(), "another-downloader")
        self.assertEqual(self.artifact_gets(), [])

    def test_parallel_range_requests_are_actually_concurrent_and_bounded(self):
        self.get_delay = 0.03
        with patch.object(downloader, "RANGE_BYTES", 8):
            code, _, stderr = self.run_cli("--download", "--parallelism", "4")
        self.assertEqual(code, 0, stderr)
        self.assertGreaterEqual(self.max_active_gets, 2)
        self.assertLessEqual(self.max_active_gets, 4)
        main_name = next(iter(self.bodies))
        ranges = [call[2]["Range"] for call in self.artifact_gets()
                  if f"/{main_name}?" in call[1]]
        self.assertIn("bytes=0-7", ranges)
        self.assertIn("bytes=8-15", ranges)
        for name, body in self.bodies.items():
            self.assertEqual((self.output / name).read_bytes(), body)
        self.assertEqual({path.name for path in self.output.iterdir()},
                         set(self.bodies) | {"download-manifest.json"})

    def test_one_worker_and_resuming_with_a_different_worker_count(self):
        self.get_delay = 0.01
        self.fail_range_start = 8
        with patch.object(downloader, "RANGE_BYTES", 8):
            code, _, stderr = self.run_cli("--download", "--parallelism", "1")
            self.assertEqual(code, 1)
            self.assertEqual(self.max_active_gets, 1)
            main_name = next(iter(self.bodies))
            state = json.loads((self.output / (main_name + ".part.json")).read_text())
            self.assertIn(0, state["completedRanges"])
            self.assertNotIn(1, state["completedRanges"])
            self.fail_range_start = None
            self.calls.clear()
            code, _, stderr = self.run_cli("--download", "--parallelism", "4")
        self.assertEqual(code, 0, stderr)
        resumed_ranges = [call[2].get("Range") for call in self.artifact_gets()
                          if f"/{main_name}?" in call[1]]
        self.assertNotIn("bytes=0-7", resumed_ranges)
        self.assertIn("bytes=8-15", resumed_ranges)
        self.assertEqual((self.output / main_name).read_bytes(), self.bodies[main_name])

    def test_parallel_failure_retains_completed_ranges_and_resumes_only_missing_ones(self):
        self.get_delay = 0.01
        self.fail_range_start = 8
        with patch.object(downloader, "RANGE_BYTES", 8):
            code, _, stderr = self.run_cli("--download")
            self.assertEqual(code, 1)
            main_name = next(iter(self.bodies))
            state_path = self.output / (main_name + ".part.json")
            state = json.loads(state_path.read_text())
            completed = set(state["completedRanges"])
            self.assertTrue(completed)
            self.assertNotIn(1, completed)
            self.assertFalse((self.output / main_name).exists())
            self.fail_range_start = None
            self.calls.clear()
            code, _, stderr = self.run_cli("--download")
        self.assertEqual(code, 0, stderr)
        for method, url, headers in self.artifact_gets():
            if f"/{main_name}?" in url:
                start = int(headers["Range"].split("=")[1].split("-")[0])
                self.assertNotIn(start // 8, completed)
        self.assertEqual((self.output / main_name).read_bytes(), self.bodies[main_name])
        self.assertFalse(state_path.exists())

    def test_parallel_hash_mismatch_or_bad_ranges_never_install_a_file(self):
        with patch.object(downloader, "RANGE_BYTES", 8):
            self.behavior = "corrupt"
            code, _, stderr = self.run_cli("--download")
            self.assertEqual(code, 1)
            self.assertIn("SHA-256 mismatch", stderr)
            main_name = next(iter(self.bodies))
            self.assertFalse((self.output / main_name).exists())
            (self.output / (main_name + ".part")).unlink()
            (self.output / (main_name + ".part.json")).unlink()
            self.behavior = "wrong-range"
            code, _, stderr = self.run_cli("--download")
            self.assertEqual(code, 1)
            self.assertIn("invalid Content-Range", stderr)
            self.assertFalse((self.output / main_name).exists())

    def test_parallel_download_can_reuse_a_contiguous_sequential_partial(self):
        blob = next(iter(downloader.resolve().values()))
        self.seed_partial(blob, self.bodies[blob.artifact.name][:16])
        with patch.object(downloader, "RANGE_BYTES", 8):
            downloader.download_file(blob, self.output, lambda _: None)
        self.assertEqual((self.output / blob.artifact.name).read_bytes(),
                         self.bodies[blob.artifact.name])
        ranges = [call[2]["Range"] for call in self.artifact_gets()]
        self.assertNotIn("bytes=0-7", ranges)
        self.assertNotIn("bytes=8-15", ranges)
        self.assertIn("bytes=16-23", ranges)

    def test_invalid_worker_count_is_rejected_before_any_network_request(self):
        for count in ("0", "17", "not-an-integer"):
            with self.subTest(count=count), self.assertRaises(SystemExit) as error:
                self.run_cli("--download", "--parallelism", count)
            self.assertEqual(error.exception.code, 2)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
