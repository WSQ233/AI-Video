import hashlib
import http.server
import json
import os
import re
import sys
import tempfile
import threading
import unittest
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import drive_fast_io as dfi  # noqa: E402


class _FakeSourceState:
    def __init__(self, payload: bytes, expected_hf_token: str = "hf_secret_test") -> None:
        self.payload = payload
        self.expected_hf_token = expected_hf_token
        self.cdn_url = ""
        self.cdn_saw_auth = False


class _FakeHFRedirectHandler(http.server.BaseHTTPRequestHandler):
    state: _FakeSourceState

    def log_message(self, format: str, *args: object) -> None:
        pass

    def _handle_redirect(self) -> None:
        auth = self.headers.get("Authorization", "")
        if auth != f"Bearer {self.state.expected_hf_token}":
            self.send_response(401)
            self.end_headers()
            return
        self.send_response(302)
        self.send_header("Location", self.state.cdn_url)
        self.end_headers()

    def do_HEAD(self) -> None:
        self._handle_redirect()

    def do_GET(self) -> None:
        self._handle_redirect()


class _FakeCDNHandler(http.server.BaseHTTPRequestHandler):
    state: _FakeSourceState

    def log_message(self, format: str, *args: object) -> None:
        pass

    def _serve(self, head_only: bool) -> None:
        # 跨域重定向到预签名 CDN 时绝不能携带 HF Authorization，否则模拟 S3 报 403
        if self.headers.get("Authorization"):
            self.state.cdn_saw_auth = True
            self.send_response(403)
            self.end_headers()
            return

        data = self.state.payload
        total = len(data)
        rng = self.headers.get("Range")
        if rng:
            m = re.match(r"bytes=(\d+)-(\d*)", rng)
            if not m:
                self.send_response(416)
                self.end_headers()
                return
            start = int(m.group(1))
            end = int(m.group(2)) if m.group(2) else total - 1
            end = min(end, total - 1)
            chunk = data[start : end + 1]
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{total}")
            self.send_header("Content-Length", str(len(chunk)))
            self.end_headers()
            if not head_only:
                self.wfile.write(chunk)
            return

        self.send_response(200)
        self.send_header("Content-Length", str(total))
        self.end_headers()
        if not head_only:
            self.wfile.write(data)

    def do_HEAD(self) -> None:
        self._serve(head_only=True)

    def do_GET(self) -> None:
        self._serve(head_only=False)


class _FakeDriveState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.token = "valid_drive_token"
        self.next_id = 1
        self.folders: dict[str, dict] = {"root": {"id": "root", "name": "MyDrive", "parent": None}}
        self.files: dict[str, dict] = {}
        self.sessions: dict[str, dict] = {}
        self.inject_upload_503_once = False
        self.inject_partial_308_once = False
        self.inject_download_429_once = False

    def new_id(self, prefix: str) -> str:
        val = f"{prefix}_{self.next_id}"
        self.next_id += 1
        return val


class _FakeDriveHandler(http.server.BaseHTTPRequestHandler):
    state: _FakeDriveState
    base_url: str

    def log_message(self, format: str, *args: object) -> None:
        pass

    def _check_auth(self) -> bool:
        if self.headers.get("Authorization") != f"Bearer {self.state.token}":
            self.send_response(401)
            self.end_headers()
            return False
        return True

    def _send_json(self, status: int, obj: dict, extra_headers: dict[str, str] | None = None) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if not self._check_auth():
            return
        parsed = urllib.parse.urlsplit(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/drive/v3/about":
            self._send_json(200, {"user": {"emailAddress": "tester@example.com"}})
            return

        if parsed.path == "/drive/v3/files":
            q = qs.get("q", [""])[0]
            name_m = re.search(r"name = '([^']+)'", q)
            parent_m = re.search(r"'([^']+)' in parents", q)
            want_folder = "application/vnd.google-apps.folder" in q
            name = name_m.group(1) if name_m else ""
            parent = parent_m.group(1) if parent_m else ""

            with self.state.lock:
                if want_folder:
                    matches = [
                        {"id": f["id"], "name": f["name"]}
                        for f in self.state.folders.values()
                        if f["name"] == name and f["parent"] == parent
                    ]
                else:
                    matches = [
                        {
                            "id": f["id"],
                            "name": f["name"],
                            "size": str(len(f["data"])),
                            "md5Checksum": hashlib.md5(f["data"]).hexdigest(),
                            "modifiedTime": f["modifiedTime"],
                        }
                        for f in self.state.files.values()
                        if f["name"] == name and f["parent"] == parent and not f["trashed"]
                    ]
            self._send_json(200, {"files": matches})
            return

        m = re.match(r"^/drive/v3/files/([^/]+)$", parsed.path)
        if m and qs.get("alt", [""])[0] == "media":
            fid = m.group(1)
            with self.state.lock:
                if self.state.inject_download_429_once:
                    self.state.inject_download_429_once = False
                    self.send_response(429)
                    self.end_headers()
                    return
                fobj = self.state.files.get(fid)
            if not fobj or fobj["trashed"]:
                self.send_response(404)
                self.end_headers()
                return

            data = fobj["data"]
            total = len(data)
            rng = self.headers.get("Range")
            if rng:
                rm = re.match(r"bytes=(\d+)-(\d+)", rng)
                start, end = int(rm.group(1)), min(int(rm.group(2)), total - 1)
                part = data[start : end + 1]
                self.send_response(206)
                self.send_header("Content-Range", f"bytes {start}-{end}/{total}")
                self.send_header("Content-Length", str(len(part)))
                self.end_headers()
                self.wfile.write(part)
                return

            self.send_response(200)
            self.send_header("Content-Length", str(total))
            self.end_headers()
            self.wfile.write(data)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:
        if not self._check_auth():
            return
        parsed = urllib.parse.urlsplit(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b""
        meta = json.loads(body.decode("utf-8")) if body else {}

        if parsed.path == "/drive/v3/files":
            with self.state.lock:
                fid = self.state.new_id("dir")
                self.state.folders[fid] = {
                    "id": fid,
                    "name": meta["name"],
                    "parent": meta["parents"][0],
                }
            self._send_json(200, {"id": fid})
            return

        if parsed.path == "/upload/drive/v3/files":
            total_size = int(self.headers.get("X-Upload-Content-Length", "0"))
            with self.state.lock:
                sid = self.state.new_id("sess")
                self.state.sessions[sid] = {
                    "name": meta["name"],
                    "parent": meta["parents"][0],
                    "total_size": total_size,
                    "buf": bytearray(),
                    "completed_file_id": None,
                }
            upload_uri = f"{self.base_url}/upload/session/{sid}"
            self.send_response(200)
            self.send_header("Location", upload_uri)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        self.send_response(404)
        self.end_headers()

    def do_PUT(self) -> None:
        if not self._check_auth():
            return
        m = re.match(r"^/upload/session/([^/]+)$", self.path)
        if not m:
            self.send_response(404)
            self.end_headers()
            return
        sid = m.group(1)
        length = int(self.headers.get("Content-Length", "0"))
        chunk = self.rfile.read(length) if length else b""
        cr = self.headers.get("Content-Range", "")

        with self.state.lock:
            sess = self.state.sessions.get(sid)
            if not sess:
                self.send_response(404)
                self.end_headers()
                return

            # 探针查询: bytes */total
            if cr.startswith("bytes */"):
                if sess["completed_file_id"]:
                    fobj = self.state.files[sess["completed_file_id"]]
                    self._send_json(200, {"id": fobj["id"], "name": fobj["name"], "size": str(len(fobj["data"]))})
                    return
                self.send_response(308)
                if len(sess["buf"]) > 0:
                    self.send_header("Range", f"bytes=0-{len(sess['buf']) - 1}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            rm = re.match(r"bytes (\d+)-(\d+)/(\d+)", cr)
            if not rm:
                self.send_response(400)
                self.end_headers()
                return
            start, end, total = int(rm.group(1)), int(rm.group(2)), int(rm.group(3))

            if self.state.inject_upload_503_once and start > 0:
                self.state.inject_upload_503_once = False
                self.send_response(503)
                self.end_headers()
                return

            # Google Drive 协议校验：非最后一块必须是 256 KiB 整数倍
            if end < total - 1 and (len(chunk) % dfi.UPLOAD_GRANULARITY != 0):
                self.send_response(400)
                self.end_headers()
                return

            if start != len(sess["buf"]):
                self.send_response(308)
                if len(sess["buf"]) > 0:
                    self.send_header("Range", f"bytes=0-{len(sess['buf']) - 1}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            if self.state.inject_partial_308_once and start > 0 and len(chunk) >= 512 * 1024:
                self.state.inject_partial_308_once = False
                half = 256 * 1024
                sess["buf"].extend(chunk[:half])
                self.send_response(308)
                self.send_header("Range", f"bytes=0-{len(sess['buf']) - 1}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            sess["buf"].extend(chunk)
            if len(sess["buf"]) >= total:
                fid = self.state.new_id("file")
                data = bytes(sess["buf"])
                self.state.files[fid] = {
                    "id": fid,
                    "name": sess["name"],
                    "parent": sess["parent"],
                    "data": data,
                    "trashed": False,
                    "modifiedTime": f"2026-11-26T16:00:{self.state.next_id:02d}Z",
                }
                sess["completed_file_id"] = fid
                self._send_json(200, {"id": fid, "name": sess["name"], "size": str(len(data))})
                return

            self.send_response(308)
            self.send_header("Range", f"bytes=0-{len(sess['buf']) - 1}")
            self.send_header("Content-Length", "0")
            self.end_headers()

    def do_PATCH(self) -> None:
        if not self._check_auth():
            return
        m = re.match(r"^/drive/v3/files/([^/]+)$", self.path)
        if not m:
            self.send_response(404)
            self.end_headers()
            return
        fid = m.group(1)
        length = int(self.headers.get("Content-Length", "0"))
        meta = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        with self.state.lock:
            if fid in self.state.files and meta.get("trashed"):
                self.state.files[fid]["trashed"] = True
        self._send_json(200, {"id": fid, "trashed": True})

    def do_DELETE(self) -> None:
        if not self._check_auth():
            return
        m = re.match(r"^/drive/v3/files/([^/]+)$", self.path)
        if not m:
            self.send_response(404)
            self.end_headers()
            return
        fid = m.group(1)
        with self.state.lock:
            self.state.files.pop(fid, None)
        self.send_response(204)
        self.end_headers()


def _start_server(handler_cls: type[http.server.BaseHTTPRequestHandler]) -> tuple[http.server.ThreadingHTTPServer, str]:
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, f"http://127.0.0.1:{port}"


def _stop_server(srv: http.server.ThreadingHTTPServer) -> None:
    srv.shutdown()
    srv.server_close()


class DriveFastIOTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_ctx = tempfile.TemporaryDirectory(prefix="drive_fast_io_test_")
        self.addCleanup(self.tmp_ctx.cleanup)
        self.tmp_dir = Path(self.tmp_ctx.name)

        # 3.3 MiB 随机二进制（特意非 256 KiB 对齐，用于覆盖末尾尾块逻辑）
        self.payload = os.urandom(3 * 1024 * 1024 + 333_333)
        self.payload_sha256 = hashlib.sha256(self.payload).hexdigest()

        self.src_state = _FakeSourceState(self.payload)
        self.drive_state = _FakeDriveState()

        cdn_handler = type("CDNHandler", (_FakeCDNHandler,), {"state": self.src_state})
        self.cdn_srv, cdn_base = _start_server(cdn_handler)
        self.addCleanup(_stop_server, self.cdn_srv)
        self.src_state.cdn_url = f"{cdn_base}/cas/blob_123"

        hf_handler = type("HFHandler", (_FakeHFRedirectHandler,), {"state": self.src_state})
        self.hf_srv, self.hf_base = _start_server(hf_handler)
        self.addCleanup(_stop_server, self.hf_srv)

        drive_handler = type("DriveHandler", (_FakeDriveHandler,), {"state": self.drive_state})
        self.drive_srv, drive_base = _start_server(drive_handler)
        drive_handler.base_url = drive_base
        self.addCleanup(_stop_server, self.drive_srv)

        auth = dfi.DriveAuthManager(access_token=self.drive_state.token)
        self.client = dfi.GoogleDriveClient(
            auth,
            api_base=f"{drive_base}/drive/v3",
            upload_base=f"{drive_base}/upload/drive/v3",
        )

    def test_stream_upload_cross_domain_redirect_sha256_skip_and_force_overwrite(self) -> None:
        info = self.client.probe()
        self.assertEqual(info["user"]["emailAddress"], "tester@example.com")

        res = self.client.stream_url_to_drive(
            source_url=f"{self.hf_base}/resolve/main/model.safetensors",
            folder_parts=["AI_Video", "shared", "models", "diffusion_models"],
            filename="model.safetensors",
            expected_size=len(self.payload),
            expected_sha256=self.payload_sha256,
            source_headers={"Authorization": f"Bearer {self.src_state.expected_hf_token}"},
            upload_chunk_mb=1,
            fetch_part_mb=1,
            fetch_workers=4,
            max_buffered_parts=6,
            resume_dir=self.tmp_dir / "resume",
            progress_interval=0,
        )
        self.assertEqual(res["status"], "uploaded")
        self.assertFalse(self.src_state.cdn_saw_auth, "跨域重定向到预签名 CDN 时不应泄露 HF Authorization")
        first_id = res["file_id"]
        self.assertEqual(self.drive_state.files[first_id]["data"], self.payload)

        # 再次同步同大小文件应当精确跳过
        res_skip = self.client.stream_url_to_drive(
            source_url=f"{self.hf_base}/resolve/main/model.safetensors",
            folder_parts=["AI_Video", "shared", "models", "diffusion_models"],
            filename="model.safetensors",
            expected_size=len(self.payload),
            source_headers={"Authorization": f"Bearer {self.src_state.expected_hf_token}"},
            upload_chunk_mb=1,
            fetch_part_mb=1,
            resume_dir=self.tmp_dir / "resume",
            progress_interval=0,
        )
        self.assertEqual(res_skip["status"], "skipped")
        self.assertEqual(res_skip["file_id"], first_id)

        # force=True 应当上传新副本并把旧文件移入回收站
        res_force = self.client.stream_url_to_drive(
            source_url=f"{self.hf_base}/resolve/main/model.safetensors",
            folder_parts=["AI_Video", "shared", "models", "diffusion_models"],
            filename="model.safetensors",
            expected_size=len(self.payload),
            expected_sha256=self.payload_sha256,
            source_headers={"Authorization": f"Bearer {self.src_state.expected_hf_token}"},
            force=True,
            upload_chunk_mb=1,
            fetch_part_mb=1,
            resume_dir=self.tmp_dir / "resume",
            progress_interval=0,
        )
        self.assertEqual(res_force["status"], "uploaded")
        self.assertNotEqual(res_force["file_id"], first_id)
        self.assertTrue(self.drive_state.files[first_id]["trashed"])
        self.assertFalse(self.drive_state.files[res_force["file_id"]]["trashed"])

    def test_upload_recovers_from_503_and_partial_308(self) -> None:
        self.drive_state.inject_upload_503_once = True
        self.drive_state.inject_partial_308_once = True

        res = self.client.stream_url_to_drive(
            source_url=f"{self.hf_base}/resolve/main/model.safetensors",
            folder_parts=["AI_Video", "shared", "models", "diffusion_models"],
            filename="retry_model.safetensors",
            expected_sha256=self.payload_sha256,
            source_headers={"Authorization": f"Bearer {self.src_state.expected_hf_token}"},
            upload_chunk_mb=1,
            fetch_part_mb=1,
            fetch_workers=4,
            resume_dir=self.tmp_dir / "resume",
            progress_interval=0,
        )
        self.assertEqual(res["status"], "uploaded")
        self.assertEqual(self.drive_state.files[res["file_id"]]["data"], self.payload)

    def test_session_resume_from_halfway_offset(self) -> None:
        folder_id = self.client.ensure_folder_path(["AI_Video", "shared", "models", "vae"])
        total = len(self.payload)
        half_offset = 1024 * 1024  # 1 MiB (256 KiB 对齐)

        # 预先建立已完成 1 MiB 的未完成会话
        upload_uri = self.client._start_resumable_session(folder_id, "resumed.safetensors", total)
        next_off, meta = self.client._upload_chunk(upload_uri, self.payload[:half_offset], 0, total)
        self.assertEqual(next_off, half_offset)
        self.assertIsNone(meta)

        resume_dir = self.tmp_dir / "resume_half"
        resume_dir.mkdir(parents=True, exist_ok=True)
        session_key = hashlib.sha1(f"{folder_id}/resumed.safetensors/{total}".encode("utf-8")).hexdigest()[:16]
        (resume_dir / f"{session_key}.json").write_text(
            json.dumps(
                {
                    "filename": "resumed.safetensors",
                    "folder_id": folder_id,
                    "total_size": total,
                    "upload_uri": upload_uri,
                }
            ),
            encoding="utf-8",
        )

        res = self.client.stream_url_to_drive(
            source_url=f"{self.hf_base}/resolve/main/model.safetensors",
            folder_parts=["AI_Video", "shared", "models", "vae"],
            filename="resumed.safetensors",
            expected_size=total,
            expected_sha256=self.payload_sha256,
            source_headers={"Authorization": f"Bearer {self.src_state.expected_hf_token}"},
            upload_chunk_mb=1,
            fetch_part_mb=1,
            resume_dir=resume_dir,
            progress_interval=0,
        )
        self.assertEqual(res["status"], "uploaded")
        self.assertEqual(self.drive_state.files[res["file_id"]]["data"], self.payload)
        self.assertFalse((resume_dir / f"{session_key}.json").exists())

    def test_sha256_mismatch_deletes_corrupt_file(self) -> None:
        with self.assertRaises(RuntimeError):
            self.client.stream_url_to_drive(
                source_url=f"{self.hf_base}/resolve/main/model.safetensors",
                folder_parts=["AI_Video", "shared", "models", "diffusion_models"],
                filename="bad_sha.safetensors",
                expected_size=len(self.payload),
                expected_sha256="0" * 64,
                source_headers={"Authorization": f"Bearer {self.src_state.expected_hf_token}"},
                upload_chunk_mb=1,
                fetch_part_mb=1,
                resume_dir=self.tmp_dir / "resume_bad",
                progress_interval=0,
            )
        # 损坏文件应已被自动删除
        folder_id = self.client.find_folder_path(["AI_Video", "shared", "models", "diffusion_models"])
        self.assertIsNotNone(folder_id)
        self.assertEqual(self.client.list_files_in_folder(folder_id, "bad_sha.safetensors"), [])

    def test_multithreaded_range_download_to_local_with_429_retry(self) -> None:
        # 9.5 MiB 随机大文件（chunk_size=4MiB -> 3 个并发 Range 分片）
        big_data = os.urandom(9 * 1024 * 1024 + 512_345)
        folder_id = self.client.ensure_folder_path(["AI_Video", "shared", "models", "diffusion_models"])
        fid = self.drive_state.new_id("file")
        self.drive_state.files[fid] = {
            "id": fid,
            "name": "big_weight.safetensors",
            "parent": folder_id,
            "data": big_data,
            "trashed": False,
            "modifiedTime": "2026-11-26T16:10:00Z",
        }
        self.drive_state.inject_download_429_once = True

        local_dst = self.tmp_dir / "local_ssd" / "big_weight.safetensors"
        res = self.client.download_file_to_local(
            folder_parts=["AI_Video", "shared", "models", "diffusion_models"],
            filename="big_weight.safetensors",
            local_dst=local_dst,
            workers=4,
            chunk_mb=4,
            progress_interval=0,
        )
        self.assertEqual(res["status"], "downloaded")
        self.assertEqual(local_dst.read_bytes(), big_data)
        self.assertFalse(local_dst.with_suffix(".safetensors.part").exists())

        # 二次预热应跳过
        res2 = self.client.download_file_to_local(
            folder_parts=["AI_Video", "shared", "models", "diffusion_models"],
            filename="big_weight.safetensors",
            local_dst=local_dst,
            workers=4,
            chunk_mb=4,
            progress_interval=0,
        )
        self.assertEqual(res2["status"], "skipped")

    def test_path_mapping_and_copy_file_fast(self) -> None:
        self.assertEqual(
            dfi.drive_path_to_rel_parts(Path("/content/drive/MyDrive/AI_Video/shared/models")),
            ["AI_Video", "shared", "models"],
        )
        self.assertEqual(
            dfi.drive_path_to_rel_parts(Path("/content/drive/My Drive/AI_Video")),
            ["AI_Video"],
        )
        self.assertIsNone(dfi.drive_path_to_rel_parts(Path("/tmp/local_dir")))

        src = self.tmp_dir / "src.bin"
        dst = self.tmp_dir / "dst.bin"
        src.write_bytes(self.payload)
        dfi.copy_file_fast(src, dst, buf_size=512 * 1024)
        self.assertEqual(dst.read_bytes(), self.payload)
        self.assertFalse(dst.with_suffix(".bin.part").exists())


if __name__ == "__main__":
    unittest.main()
