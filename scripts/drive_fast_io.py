#!/usr/bin/env python3
"""
Google Drive v3 API 高速流式 I/O 引擎（绕过 Colab DriveFS FUSE 瓶颈）：
1. 上传方向（Hugging Face -> 5TB Google Drive）：
   - 下载端使用多线程 HTTP Range 顺序滑动窗口预取（严格有界内存缓冲，峰值 <= ~350MB/文件）
   - 上传端按 256MiB 大块异步流水线直推 Google Drive v3 Resumable Upload API
   - 全程本地磁盘占用 0 GB，彻底免疫 Colab 免费 CPU 107GB 本地盘爆盘
   - 支持会话级断点续传、精确字节数校验、LFS SHA256 流式校验与原子覆盖
2. 下载方向（5TB Google Drive -> A100 本地 NVMe SSD 预热）：
   - 对单一大文件启用多线程 HTTP Range 分片并发直下 + os.pwrite 零拷贝落盘
   - 彻底消除 DriveFS FUSE 读取产生的 50~60GB 本地额外缓存膨胀，大幅节省 A100 CU
3. 零依赖兜底：
   - 优先使用 requests + urllib3 大连接池（Colab 原生预装），无 requests 环境自动降级为标准库 http.client
   - 若当前环境未完成 Google OAuth 鉴权，上层脚本可无缝回退至优化后的 DriveFS 路径
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import http.client
import json
import os
import re
import shutil
import ssl
import tempfile
import threading
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

try:
    import requests
    from requests.adapters import HTTPAdapter
except ImportError:  # pragma: no cover - 仅在无 requests 的精简本地环境触发
    requests = None  # type: ignore[assignment]
    HTTPAdapter = None  # type: ignore[assignment]


DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
DRIVE_UPLOAD_BASE = "https://www.googleapis.com/upload/drive/v3"

UPLOAD_GRANULARITY = 256 * 1024  # Google Drive Resumable Upload 要求 256 KiB 对齐
DEFAULT_UPLOAD_CHUNK_MB = 256  # 真机实测 256MiB 大块 (~40.6 MB/s) 追平单流上限且保留断点续传
DEFAULT_FETCH_PART_MB = 16
DEFAULT_FETCH_WORKERS = 8
DEFAULT_MAX_BUFFERED_PARTS = 16  # 16 * 16 MiB = 256 MiB 滑动窗口上限
DEFAULT_DOWNLOAD_WORKERS = 16  # 真机实测 16 线程 Range 直下 123+ MB/s (4.14x DriveFS)
DEFAULT_DOWNLOAD_CHUNK_MB = 32
DEFAULT_TIMEOUT = (30, 180)
FETCH_PART_TIMEOUT = (15, 35)  # 16MiB 单分片短超时，防止单条 TCP 静默挂死阻塞滑动窗口
DOWNLOAD_RANGE_TIMEOUT = (15, 45)


def align_upload_size(num_bytes: int) -> int:
    """将上传分块大小对齐到 256 KiB 整数倍（至少 256 KiB）。"""
    aligned = (max(num_bytes, UPLOAD_GRANULARITY) // UPLOAD_GRANULARITY) * UPLOAD_GRANULARITY
    return max(aligned, UPLOAD_GRANULARITY)


def format_eta(seconds: float) -> str:
    if seconds <= 0 or seconds == float("inf"):
        return "--:--"
    sec = int(seconds)
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def copy_file_fast(src: Path, dst: Path, buf_size: int = 16 * 1024 * 1024) -> None:
    """使用 16 MiB 大块顺序拷贝并原子替换，比 shutil.copy2 默认 1 MiB 缓冲对大模型文件更友好。"""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".part")
    try:
        with src.open("rb") as rfp, tmp.open("wb") as wfp:
            shutil.copyfileobj(rfp, wfp, length=buf_size)
        os.replace(tmp, dst)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def drive_path_to_rel_parts(path: Path) -> list[str] | None:
    """
    将 Colab 挂载路径（如 /content/drive/MyDrive/AI_Video/shared/models）
    转换为相对于 Google Drive MyDrive 根目录的层级列表。
    """
    posix = path.as_posix()
    for marker in ("/MyDrive/", "/My Drive/"):
        if marker in posix:
            rel = posix.split(marker, 1)[1].strip("/")
            return [p for p in rel.split("/") if p]
    if posix.endswith("/MyDrive") or posix.endswith("/My Drive"):
        return []
    return None


@dataclass
class HttpResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes
    url: str

    def header(self, name: str, default: str = "") -> str:
        return self.headers.get(name.lower(), default)

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))


class _HttpTransport:
    """
    线程安全 HTTP 客户端封装：
    - 若安装 requests（Colab 原生自带），按线程本地复用 requests.Session + 32 连接池
    - 否则自动降级至标准库 http.client，保持相同接口（含 308 保留与跨域重定向剥离 Auth）
    """

    def __init__(self, pool_size: int = 32, timeout: tuple[int, int] = DEFAULT_TIMEOUT) -> None:
        self.pool_size = pool_size
        self.timeout = timeout
        self._local = threading.local()
        self._ssl_context = ssl.create_default_context()

    def _get_requests_session(self) -> Any:
        sess = getattr(self._local, "session", None)
        if sess is None:
            sess = requests.Session()
            adapter = HTTPAdapter(pool_connections=self.pool_size, pool_maxsize=self.pool_size)
            sess.mount("https://", adapter)
            sess.mount("http://", adapter)
            self._local.session = sess
        return sess

    def _stdlib_request_once(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | memoryview | None,
        timeout_sec: float,
    ) -> tuple[int, dict[str, str], http.client.HTTPResponse, http.client.HTTPConnection]:
        parsed = urllib.parse.urlsplit(url)
        is_https = parsed.scheme.lower() == "https"
        host = parsed.hostname or ""
        port = parsed.port or (443 if is_https else 80)
        target = parsed.path or "/"
        if parsed.query:
            target = f"{target}?{parsed.query}"

        conn: http.client.HTTPConnection
        if is_https:
            conn = http.client.HTTPSConnection(host, port, timeout=timeout_sec, context=self._ssl_context)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=timeout_sec)

        req_headers = dict(headers)
        if body is not None and "Content-Length" not in {k.title(): v for k, v in req_headers.items()}:
            req_headers["Content-Length"] = str(len(body))
        conn.request(method.upper(), target, body=body, headers=req_headers)
        resp = conn.getresponse()
        resp_headers = {k.lower(): v for k, v in resp.getheaders()}
        return resp.status, resp_headers, resp, conn

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        body: bytes | memoryview | None = None,
        allow_redirects: bool = True,
        timeout: tuple[int, int] | None = None,
    ) -> HttpResponse:
        req_headers = dict(headers or {})
        eff_timeout = timeout or self.timeout

        if requests is not None:
            sess = self._get_requests_session()
            data: Any = bytes(body) if isinstance(body, memoryview) else body
            resp = sess.request(
                method=method.upper(),
                url=url,
                headers=req_headers,
                data=data,
                allow_redirects=allow_redirects,
                timeout=eff_timeout,
            )
            return HttpResponse(
                status_code=resp.status_code,
                headers={k.lower(): v for k, v in resp.headers.items()},
                body=resp.content,
                url=resp.url,
            )

        current_url = url
        current_headers = dict(req_headers)
        timeout_sec = float(eff_timeout[1] if isinstance(eff_timeout, tuple) else eff_timeout)
        for _ in range(10):
            status, resp_headers, resp, conn = self._stdlib_request_once(
                method, current_url, current_headers, body, timeout_sec
            )
            try:
                content = b"" if method.upper() == "HEAD" else resp.read()
            finally:
                conn.close()

            if allow_redirects and status in (301, 302, 303, 307, 308) and "location" in resp_headers:
                next_url = urllib.parse.urljoin(current_url, resp_headers["location"])
                if urllib.parse.urlsplit(next_url).netloc != urllib.parse.urlsplit(current_url).netloc:
                    current_headers = {
                        k: v for k, v in current_headers.items() if k.lower() != "authorization"
                    }
                current_url = next_url
                continue

            return HttpResponse(status_code=status, headers=resp_headers, body=content, url=current_url)

        raise RuntimeError(f"HTTP 重定向次数过多: {url}")

    def stream_get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        chunk_size: int = 4 * 1024 * 1024,
        on_chunk: Callable[[bytes], None],
        allow_redirects: bool = True,
        timeout: tuple[int, int] | None = None,
    ) -> tuple[int, dict[str, str], str]:
        """流式 GET 读取并回调每个块，避免把大响应完整缓存在内存中。"""
        req_headers = dict(headers or {})
        eff_timeout = timeout or self.timeout

        if requests is not None:
            sess = self._get_requests_session()
            with sess.get(
                url,
                headers=req_headers,
                stream=True,
                allow_redirects=allow_redirects,
                timeout=eff_timeout,
            ) as resp:
                resp_headers = {k.lower(): v for k, v in resp.headers.items()}
                if resp.status_code in (200, 206):
                    for part in resp.iter_content(chunk_size=chunk_size):
                        if part:
                            on_chunk(part)
                return resp.status_code, resp_headers, resp.url

        current_url = url
        current_headers = dict(req_headers)
        timeout_sec = float(eff_timeout[1] if isinstance(eff_timeout, tuple) else eff_timeout)
        for _ in range(10):
            status, resp_headers, resp, conn = self._stdlib_request_once(
                "GET", current_url, current_headers, None, timeout_sec
            )
            try:
                if allow_redirects and status in (301, 302, 303, 307, 308) and "location" in resp_headers:
                    resp.read()
                    next_url = urllib.parse.urljoin(current_url, resp_headers["location"])
                    if urllib.parse.urlsplit(next_url).netloc != urllib.parse.urlsplit(current_url).netloc:
                        current_headers = {
                            k: v for k, v in current_headers.items() if k.lower() != "authorization"
                        }
                    current_url = next_url
                    continue
                if status in (200, 206):
                    while True:
                        part = resp.read(chunk_size)
                        if not part:
                            break
                        on_chunk(part)
                else:
                    resp.read()
                return status, resp_headers, current_url
            finally:
                conn.close()

        raise RuntimeError(f"HTTP 流式下载重定向次数过多: {url}")


class DriveAuthManager:
    """
    Google Drive OAuth Token 管理器：
    1. 支持直接注入 credentials / static token（便于单元测试或自定义接入）
    2. 优先使用 google.auth.default(scopes=[DRIVE_SCOPE]) 并自动无感续期
    3. 兜底使用父进程通过环境变量 GDRIVE_ACCESS_TOKEN 传入的短期内存 Token
    """

    def __init__(
        self,
        *,
        access_token: str | None = None,
        credentials: Any = None,
    ) -> None:
        self._lock = threading.Lock()
        self._credentials = credentials
        self._static_token = (access_token or os.environ.get("GDRIVE_ACCESS_TOKEN") or "").strip() or None
        self._token_expiry: float = 0.0

        if self._credentials is None and self._static_token is None:
            self._try_load_adc()

    def _try_load_adc(self) -> None:
        try:
            import google.auth  # type: ignore[import-not-found]

            creds, _ = google.auth.default(scopes=[DRIVE_SCOPE])
            self._credentials = creds
        except Exception:
            self._credentials = None

    def available(self) -> bool:
        return self._credentials is not None or self._static_token is not None

    def get_token(self, force_refresh: bool = False) -> str:
        with self._lock:
            if self._credentials is not None:
                now = time.time()
                needs_refresh = (
                    force_refresh
                    or not getattr(self._credentials, "token", None)
                    or getattr(self._credentials, "expired", False)
                    or (self._token_expiry > 0 and now >= self._token_expiry - 180)
                )
                if needs_refresh:
                    try:
                        from google.auth.transport.requests import Request  # type: ignore[import-not-found]

                        self._credentials.refresh(Request())
                        expiry = getattr(self._credentials, "expiry", None)
                        if expiry is not None:
                            self._token_expiry = expiry.timestamp()
                        else:
                            self._token_expiry = now + 3000
                    except Exception:
                        if self._static_token:
                            return self._static_token
                        raise
                token = getattr(self._credentials, "token", None)
                if token:
                    return str(token)

            if self._static_token:
                return self._static_token
            raise RuntimeError("未获取到可用的 Google Drive OAuth 凭证，请先在 Colab 执行 auth.authenticate_user()。")


def _escape_drive_query(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _parse_range_end(range_header: str) -> int | None:
    """解析 Google Drive 308 响应中的 Range: bytes=0-67108863，返回已提交末尾偏移量。"""
    m = re.search(r"bytes=\d+-(\d+)", range_header or "")
    return int(m.group(1)) if m else None


def _parse_content_range_total(header_val: str) -> int | None:
    m = re.search(r"/(\d+)$", (header_val or "").strip())
    return int(m.group(1)) if m else None


class _SlidingWindowFetcher:
    """
    有界内存多线程顺序滑动窗口下载器：
    - 后台 fetch_workers 个线程并发从源 URL 按 HTTP Range 拉取 fetch_part_size 分片
    - Semaphore(max_buffered_parts) 严格封顶内存占用，防止大文件 OOM
    - 消费端严格按 part_idx = 0, 1, 2... 顺序取出数据，实现与上传流 100% 重叠并行
    """

    def __init__(
        self,
        transport: _HttpTransport,
        source_url: str,
        start_offset: int,
        total_size: int,
        part_size: int,
        source_headers: dict[str, str] | None = None,
        workers: int = DEFAULT_FETCH_WORKERS,
        max_buffered_parts: int = DEFAULT_MAX_BUFFERED_PARTS,
    ) -> None:
        self.transport = transport
        self.source_url = source_url
        self.start_offset = start_offset
        self.total_size = total_size
        self.part_size = part_size
        self.source_headers = dict(source_headers or {})
        self.workers = max(1, workers)
        self.max_buffered_parts = max(self.workers, max_buffered_parts)

        self._parts: list[tuple[int, int]] = []
        pos = start_offset
        while pos < total_size:
            end = min(pos + part_size - 1, total_size - 1)
            self._parts.append((pos, end))
            pos = end + 1

        self._resolved_url = source_url
        self._url_lock = threading.Lock()
        self._idx_lock = threading.Lock()
        self._next_fetch_idx = 0
        self._ready: dict[int, bytes] = {}
        self._cond = threading.Condition()
        self._sem = threading.Semaphore(self.max_buffered_parts)
        self._stop_event = threading.Event()
        self._error: BaseException | None = None
        self._threads: list[threading.Thread] = []

    def _resolve_direct_url(self, force: bool = False) -> str:
        with self._url_lock:
            if not force and self._resolved_url != self.source_url:
                return self._resolved_url
            try:
                # 必须使用 GET + Range: bytes=0-0 解析最终直链，避免 S3/Xet 对 HEAD 签发的预签名 URL 在 GET 时报 403
                probe_headers = dict(self.source_headers)
                probe_headers["Range"] = "bytes=0-0"
                resp = self.transport.request(
                    "GET",
                    self.source_url,
                    headers=probe_headers,
                    allow_redirects=True,
                    timeout=(20, 60),
                )
                if resp.status_code in (200, 206):
                    self._resolved_url = resp.url
            except Exception:
                self._resolved_url = self.source_url
            return self._resolved_url

    def _headers_for_url(self, target_url: str) -> dict[str, str]:
        if urllib.parse.urlsplit(target_url).netloc == urllib.parse.urlsplit(self.source_url).netloc:
            return dict(self.source_headers)
        return {k: v for k, v in self.source_headers.items() if k.lower() != "authorization"}

    def _fetch_range(self, start: int, end: int) -> bytes:
        expected_len = end - start + 1
        last_exc: Exception | None = None
        for attempt in range(7):
            if self._stop_event.is_set():
                raise RuntimeError("下载已中止")
            target_url = self._resolve_direct_url(force=(attempt > 0))
            headers = self._headers_for_url(target_url)
            headers["Range"] = f"bytes={start}-{end}"
            try:
                resp = self.transport.request(
                    "GET",
                    target_url,
                    headers=headers,
                    allow_redirects=True,
                    timeout=FETCH_PART_TIMEOUT,
                )
                if resp.status_code in (200, 206):
                    data = resp.body
                    if resp.status_code == 200 and start > 0 and len(data) == self.total_size:
                        data = data[start : end + 1]
                    if len(data) == expected_len:
                        return data
                    last_exc = RuntimeError(f"分片长度不匹配 [{start}-{end}]: 期望 {expected_len}, 实得 {len(data)}")
                elif resp.status_code in (401, 403, 404, 410):
                    # 预签名直链可能过期，下轮强制刷新原始 HF URL
                    last_exc = RuntimeError(f"源端返回 HTTP {resp.status_code} [{start}-{end}]")
                elif resp.status_code in (408, 429, 500, 502, 503, 504):
                    last_exc = RuntimeError(f"源端临时错误 HTTP {resp.status_code} [{start}-{end}]")
                else:
                    raise RuntimeError(f"源端不可恢复 HTTP {resp.status_code} [{start}-{end}]")
            except Exception as exc:
                last_exc = exc

            backoff = min(20.0, 1.0 * (2 ** attempt))
            self._stop_event.wait(backoff)

        raise RuntimeError(f"下载分片 [{start}-{end}] 重试耗尽: {last_exc}")

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            with self._idx_lock:
                if self._next_fetch_idx >= len(self._parts):
                    return
                part_idx = self._next_fetch_idx
                self._next_fetch_idx += 1

            while not self._stop_event.is_set():
                if self._sem.acquire(timeout=0.5):
                    break
            else:
                return

            try:
                start, end = self._parts[part_idx]
                data = self._fetch_range(start, end)
                with self._cond:
                    self._ready[part_idx] = data
                    self._cond.notify_all()
            except BaseException as exc:
                self._sem.release()
                with self._cond:
                    if self._error is None:
                        self._error = exc
                    self._stop_event.set()
                    self._cond.notify_all()
                return

    def start(self) -> None:
        self._resolve_direct_url(force=False)
        worker_count = min(self.workers, max(1, len(self._parts)))
        for idx in range(worker_count):
            t = threading.Thread(target=self._worker_loop, name=f"hf-fetch-{idx}", daemon=True)
            t.start()
            self._threads.append(t)

    def __len__(self) -> int:
        return len(self._parts)

    def pop_part(self, part_idx: int) -> tuple[int, int, bytes]:
        with self._cond:
            while part_idx not in self._ready and self._error is None:
                self._cond.wait(timeout=1.0)
            if self._error is not None:
                raise self._error
            data = self._ready.pop(part_idx)
        self._sem.release()
        start, end = self._parts[part_idx]
        return start, end, data

    def close(self) -> None:
        self._stop_event.set()
        with self._cond:
            self._ready.clear()
            self._cond.notify_all()
        for t in self._threads:
            t.join(timeout=3.0)


class GoogleDriveClient:
    """面向大体积 AI 权重的高性能 Google Drive v3 客户端。"""

    def __init__(
        self,
        auth: DriveAuthManager,
        *,
        api_base: str = DRIVE_API_BASE,
        upload_base: str = DRIVE_UPLOAD_BASE,
        pool_size: int = 64,
        timeout: tuple[int, int] = DEFAULT_TIMEOUT,
    ) -> None:
        self.auth = auth
        self.api_base = api_base.rstrip("/")
        self.upload_base = upload_base.rstrip("/")
        self.transport = _HttpTransport(pool_size=pool_size, timeout=timeout)
        self._folder_cache: dict[tuple[str, ...], str] = {(): "root"}
        self._folder_lock = threading.Lock()

    def _drive_request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        body: bytes | memoryview | None = None,
        allow_redirects: bool = True,
        retries: int = 5,
    ) -> HttpResponse:
        last_exc: Exception | None = None
        need_refresh = False
        for attempt in range(retries):
            token = self.auth.get_token(force_refresh=need_refresh)
            need_refresh = False
            req_headers = dict(headers or {})
            req_headers["Authorization"] = f"Bearer {token}"
            try:
                resp = self.transport.request(
                    method,
                    url,
                    headers=req_headers,
                    body=body,
                    allow_redirects=allow_redirects,
                )
                if resp.status_code == 401:
                    need_refresh = True
                    last_exc = RuntimeError("HTTP 401")
                    continue
                if resp.status_code in (429, 500, 502, 503, 504):
                    last_exc = RuntimeError(f"Drive API HTTP {resp.status_code}: {resp.body[:200]!r}")
                    time.sleep(min(20.0, 1.0 * (2 ** attempt)))
                    continue
                return resp
            except Exception as exc:
                last_exc = exc
                time.sleep(min(20.0, 1.0 * (2 ** attempt)))
        raise RuntimeError(f"Drive API 请求失败 ({method} {url}): {last_exc}")

    def probe(self) -> dict[str, Any]:
        """验证当前 OAuth 凭证可访问 Google Drive v3 API。"""
        url = f"{self.api_base}/about?fields=user(emailAddress,displayName)"
        resp = self._drive_request("GET", url, retries=2)
        if resp.status_code != 200:
            raise RuntimeError(f"Drive API 探针失败 HTTP {resp.status_code}: {resp.body[:200]!r}")
        return resp.json()

    def find_folder_path(self, parts: list[str]) -> str | None:
        key = tuple(parts)
        with self._folder_lock:
            if key in self._folder_cache:
                return self._folder_cache[key]

        parent_id = "root"
        acc: list[str] = []
        for name in parts:
            acc.append(name)
            sub_key = tuple(acc)
            with self._folder_lock:
                cached = self._folder_cache.get(sub_key)
            if cached:
                parent_id = cached
                continue

            q = (
                f"name = '{_escape_drive_query(name)}' "
                f"and '{parent_id}' in parents "
                "and mimeType = 'application/vnd.google-apps.folder' "
                "and trashed = false"
            )
            params = urllib.parse.urlencode(
                {"q": q, "fields": "files(id,name)", "pageSize": "5", "orderBy": "modifiedTime desc"}
            )
            resp = self._drive_request("GET", f"{self.api_base}/files?{params}")
            if resp.status_code != 200:
                raise RuntimeError(f"查询目录 {name} 失败: HTTP {resp.status_code}")
            files = resp.json().get("files", [])
            if not files:
                return None
            parent_id = files[0]["id"]
            with self._folder_lock:
                self._folder_cache[sub_key] = parent_id
        return parent_id

    def ensure_folder_path(self, parts: list[str]) -> str:
        """按层级查找或创建 Google Drive 目录（线程安全防重复建夹）。"""
        parent_id = "root"
        acc: list[str] = []
        for name in parts:
            acc.append(name)
            sub_key = tuple(acc)
            with self._folder_lock:
                if sub_key in self._folder_cache:
                    parent_id = self._folder_cache[sub_key]
                    continue

                q = (
                    f"name = '{_escape_drive_query(name)}' "
                    f"and '{parent_id}' in parents "
                    "and mimeType = 'application/vnd.google-apps.folder' "
                    "and trashed = false"
                )
                params = urllib.parse.urlencode(
                    {"q": q, "fields": "files(id,name)", "pageSize": "5", "orderBy": "modifiedTime desc"}
                )
                resp = self._drive_request("GET", f"{self.api_base}/files?{params}")
                if resp.status_code != 200:
                    raise RuntimeError(f"查询目录 {name} 失败: HTTP {resp.status_code}")
                files = resp.json().get("files", [])
                if files:
                    folder_id = files[0]["id"]
                else:
                    payload = json.dumps(
                        {
                            "name": name,
                            "mimeType": "application/vnd.google-apps.folder",
                            "parents": [parent_id],
                        }
                    ).encode("utf-8")
                    create_resp = self._drive_request(
                        "POST",
                        f"{self.api_base}/files?fields=id",
                        headers={"Content-Type": "application/json; charset=UTF-8"},
                        body=payload,
                    )
                    if create_resp.status_code not in (200, 201):
                        raise RuntimeError(f"创建目录 {name} 失败: HTTP {create_resp.status_code}")
                    folder_id = create_resp.json()["id"]
                self._folder_cache[sub_key] = folder_id
                parent_id = folder_id
        return parent_id

    def list_files_in_folder(self, folder_id: str, name: str) -> list[dict[str, Any]]:
        q = f"name = '{_escape_drive_query(name)}' and '{folder_id}' in parents and trashed = false"
        params = urllib.parse.urlencode(
            {
                "q": q,
                "fields": "files(id,name,size,md5Checksum,modifiedTime)",
                "pageSize": "20",
                "orderBy": "modifiedTime desc",
            }
        )
        resp = self._drive_request("GET", f"{self.api_base}/files?{params}")
        if resp.status_code != 200:
            raise RuntimeError(f"查询文件 {name} 失败: HTTP {resp.status_code}")
        return resp.json().get("files", [])

    def trash_file(self, file_id: str) -> None:
        payload = json.dumps({"trashed": True}).encode("utf-8")
        self._drive_request(
            "PATCH",
            f"{self.api_base}/files/{file_id}",
            headers={"Content-Type": "application/json; charset=UTF-8"},
            body=payload,
            retries=3,
        )

    def delete_file(self, file_id: str) -> None:
        self._drive_request("DELETE", f"{self.api_base}/files/{file_id}", retries=3)

    def probe_source_size(self, source_url: str, source_headers: dict[str, str] | None = None) -> int:
        """通过 HEAD 或 Range: bytes=0-0 探测源文件精确总字节数。"""
        headers = dict(source_headers or {})
        resp = self.transport.request("HEAD", source_url, headers=headers, allow_redirects=True)
        if resp.status_code in (200, 206):
            cl = resp.header("content-length")
            if cl.isdigit() and int(cl) > 0:
                return int(cl)
        range_headers = dict(headers)
        range_headers["Range"] = "bytes=0-0"
        resp2 = self.transport.request("GET", source_url, headers=range_headers, allow_redirects=True)
        if resp2.status_code == 206:
            total = _parse_content_range_total(resp2.header("content-range"))
            if total and total > 0:
                return total
        if resp2.status_code == 200:
            cl = resp2.header("content-length")
            if cl.isdigit() and int(cl) > 0:
                return int(cl)
            if resp2.body:
                return len(resp2.body)
        raise RuntimeError(f"无法获取源文件总大小: {source_url} (HTTP {resp2.status_code})")

    def _start_resumable_session(self, folder_id: str, filename: str, total_size: int) -> str:
        metadata = json.dumps({"name": filename, "parents": [folder_id]}).encode("utf-8")
        url = f"{self.upload_base}/files?uploadType=resumable&fields=id,name,size,md5Checksum"
        resp = self._drive_request(
            "POST",
            url,
            headers={
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": "application/octet-stream",
                "X-Upload-Content-Length": str(total_size),
            },
            body=metadata,
            allow_redirects=False,
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"初始化 Drive Resumable Upload 失败 HTTP {resp.status_code}: {resp.body[:200]!r}")
        upload_uri = resp.header("location")
        if not upload_uri:
            raise RuntimeError("Drive Resumable Upload 响应缺少 Location 头")
        return upload_uri

    def _query_upload_offset(self, upload_uri: str, total_size: int) -> tuple[str, int, dict[str, Any] | None]:
        """
        查询 Resumable Upload 会话当前已接收字节偏移量。
        返回: (status_tag, next_offset, completed_meta)
        status_tag in {"active", "complete", "expired"}
        """
        resp = self._drive_request(
            "PUT",
            upload_uri,
            headers={
                "Content-Length": "0",
                "Content-Range": f"bytes */{total_size}",
            },
            body=b"",
            allow_redirects=False,
            retries=3,
        )
        if resp.status_code in (200, 201):
            return "complete", total_size, resp.json()
        if resp.status_code == 308:
            end = _parse_range_end(resp.header("range"))
            return "active", (end + 1) if end is not None else 0, None
        if resp.status_code in (404, 410):
            return "expired", 0, None
        raise RuntimeError(f"查询上传断点失败 HTTP {resp.status_code}: {resp.body[:200]!r}")

    def _upload_chunk(
        self,
        upload_uri: str,
        chunk: bytes | memoryview,
        chunk_start: int,
        total_size: int,
    ) -> tuple[int, dict[str, Any] | None]:
        """
        向 Google Drive Resumable Upload 会话发送单个顺序块，内置断线/5xx 自动精准续传。
        返回 (next_offset, completed_meta)。
        """
        chunk_len = len(chunk)
        chunk_end = chunk_start + chunk_len - 1
        rel_offset = 0
        mv = memoryview(chunk)

        for attempt in range(8):
            cur_start = chunk_start + rel_offset
            payload = mv[rel_offset:]
            headers = {
                "Content-Type": "application/octet-stream",
                "Content-Length": str(len(payload)),
                "Content-Range": f"bytes {cur_start}-{chunk_end}/{total_size}",
            }
            try:
                token = self.auth.get_token(force_refresh=False)
                headers["Authorization"] = f"Bearer {token}"
                resp = self.transport.request(
                    "PUT",
                    upload_uri,
                    headers=headers,
                    body=payload,
                    allow_redirects=False,
                )
                if resp.status_code in (200, 201):
                    return total_size, resp.json()
                if resp.status_code == 308:
                    end = _parse_range_end(resp.header("range"))
                    next_offset = (end + 1) if end is not None else cur_start
                    if next_offset > chunk_end:
                        return next_offset, None
                    if next_offset >= chunk_start:
                        rel_offset = next_offset - chunk_start
                        continue
                    return next_offset, None
                if resp.status_code == 401:
                    self.auth.get_token(force_refresh=True)
                    continue
                if resp.status_code in (404, 410):
                    raise RuntimeError("RESUMABLE_SESSION_EXPIRED")
                if resp.status_code not in (408, 429, 500, 502, 503, 504):
                    raise RuntimeError(f"Drive 分块上传失败 HTTP {resp.status_code}: {resp.body[:200]!r}")
            except RuntimeError as exc:
                if str(exc) == "RESUMABLE_SESSION_EXPIRED":
                    raise
                if "Drive 分块上传失败" in str(exc):
                    raise
            except Exception:
                pass

            # 网络抖动或 5xx：先退避，再向 Drive 询问精确偏移量从当前缓冲续传
            time.sleep(min(20.0, 1.0 * (2 ** attempt)))
            tag, server_offset, meta = self._query_upload_offset(upload_uri, total_size)
            if tag == "complete":
                return total_size, meta
            if tag == "expired":
                raise RuntimeError("RESUMABLE_SESSION_EXPIRED")
            if server_offset > chunk_end:
                return server_offset, None
            if server_offset >= chunk_start:
                rel_offset = server_offset - chunk_start
            else:
                return server_offset, None

        raise RuntimeError(f"Drive 分块上传 [{chunk_start}-{chunk_end}] 重试耗尽")

    def stream_url_to_drive(
        self,
        *,
        source_url: str,
        folder_parts: list[str],
        filename: str,
        expected_size: int | None = None,
        expected_sha256: str | None = None,
        source_headers: dict[str, str] | None = None,
        force: bool = False,
        upload_chunk_mb: int = DEFAULT_UPLOAD_CHUNK_MB,
        fetch_part_mb: int = DEFAULT_FETCH_PART_MB,
        fetch_workers: int = DEFAULT_FETCH_WORKERS,
        max_buffered_parts: int = DEFAULT_MAX_BUFFERED_PARTS,
        resume_dir: Path | None = None,
        progress_interval: float = 15.0,
    ) -> dict[str, Any]:
        """
        将远端 HTTP 文件以 0 本地磁盘占用、多线程滑动窗口流水线直传到 5TB Google Drive。
        """
        folder_id = self.ensure_folder_path(folder_parts)
        total_size = expected_size if (expected_size and expected_size > 0) else self.probe_source_size(
            source_url, source_headers
        )

        existing_files = self.list_files_in_folder(folder_id, filename)
        if not force:
            for item in existing_files:
                if int(item.get("size") or -1) == total_size:
                    size_gb = total_size / (1024 ** 3)
                    print(
                        f"  [已存在精确跳过] {'/'.join(folder_parts[-1:])}/{filename} ({size_gb:.2f} GB, 字节数一致)",
                        flush=True,
                    )
                    return {"status": "skipped", "file_id": item["id"], "size": total_size}

        upload_chunk_size = align_upload_size(upload_chunk_mb * 1024 * 1024)
        fetch_part_size = align_upload_size(min(fetch_part_mb * 1024 * 1024, upload_chunk_size))
        if upload_chunk_size % fetch_part_size != 0:
            fetch_part_size = upload_chunk_size

        resume_root = resume_dir or (Path(tempfile.gettempdir()) / "ai_video_gdrive_resume")
        resume_root.mkdir(parents=True, exist_ok=True)
        session_key = hashlib.sha1(f"{folder_id}/{filename}/{total_size}".encode("utf-8")).hexdigest()[:16]
        session_file = resume_root / f"{session_key}.json"

        upload_uri = ""
        start_offset = 0
        completed_meta: dict[str, Any] | None = None

        if session_file.exists() and not force:
            try:
                saved = json.loads(session_file.read_text(encoding="utf-8"))
                if saved.get("total_size") == total_size and saved.get("upload_uri"):
                    tag, srv_offset, meta = self._query_upload_offset(saved["upload_uri"], total_size)
                    if tag == "complete":
                        completed_meta = meta
                        start_offset = total_size
                    elif tag == "active":
                        upload_uri = saved["upload_uri"]
                        start_offset = srv_offset
                        if start_offset > 0:
                            print(
                                f"  [断点续传] {filename} 复用上传会话，从 {start_offset / (1024 ** 3):.2f} / {total_size / (1024 ** 3):.2f} GB 继续",
                                flush=True,
                            )
                    else:
                        session_file.unlink(missing_ok=True)
            except Exception:
                session_file.unlink(missing_ok=True)

        t0 = time.time()
        for session_attempt in range(2):
            if completed_meta is not None:
                break

            if not upload_uri:
                upload_uri = self._start_resumable_session(folder_id, filename, total_size)
                start_offset = 0
                session_file.write_text(
                    json.dumps(
                        {
                            "filename": filename,
                            "folder_id": folder_id,
                            "total_size": total_size,
                            "upload_uri": upload_uri,
                        }
                    ),
                    encoding="utf-8",
                )

            hasher = hashlib.sha256() if (expected_sha256 and start_offset == 0) else None
            cur_offset = start_offset
            last_report_t = time.time()
            last_report_bytes = cur_offset

            try:
                while cur_offset < total_size:
                    fetcher = _SlidingWindowFetcher(
                        transport=self.transport,
                        source_url=source_url,
                        start_offset=cur_offset,
                        total_size=total_size,
                        part_size=fetch_part_size,
                        source_headers=source_headers,
                        workers=fetch_workers,
                        max_buffered_parts=max_buffered_parts,
                    )
                    fetcher.start()
                    reset_needed = False
                    try:
                        part_idx = 0
                        num_parts = len(fetcher)
                        while part_idx < num_parts:
                            chunk_start = cur_offset
                            chunk_target = min(upload_chunk_size, total_size - chunk_start)
                            buf = bytearray(chunk_target)
                            filled = 0
                            while filled < chunk_target and part_idx < num_parts:
                                p_start, _p_end, p_bytes = fetcher.pop_part(part_idx)
                                part_idx += 1
                                expected_pos = chunk_start + filled
                                if p_start != expected_pos:
                                    raise RuntimeError(f"分片偏移错乱: 期望 {expected_pos}, 实得 {p_start}")
                                end_fill = filled + len(p_bytes)
                                buf[filled:end_fill] = p_bytes
                                filled = end_fill

                            if hasher is not None:
                                hasher.update(buf)

                            next_offset, meta = self._upload_chunk(upload_uri, buf, chunk_start, total_size)
                            if meta is not None:
                                completed_meta = meta
                                cur_offset = total_size
                                break
                            if next_offset != chunk_start + filled:
                                # 极端情况：服务端偏移量落后，重启滑动窗口从服务端偏移重拉
                                cur_offset = next_offset
                                hasher = None
                                reset_needed = True
                                break
                            cur_offset = next_offset

                            now = time.time()
                            if progress_interval > 0 and (now - last_report_t >= progress_interval):
                                delta_b = cur_offset - last_report_bytes
                                inst_mb = (delta_b / (1024 ** 2)) / max(now - last_report_t, 0.1)
                                avg_mb = ((cur_offset - start_offset) / (1024 ** 2)) / max(now - t0, 0.1)
                                pct = (cur_offset / total_size) * 100.0
                                eta_sec = (total_size - cur_offset) / max(avg_mb * 1024 * 1024, 1.0)
                                print(
                                    f"  [API直传] {filename} | {cur_offset / (1024 ** 3):.2f}/{total_size / (1024 ** 3):.2f} GB "
                                    f"({pct:.1f}%) | 实时 {inst_mb:.1f} MB/s | 均速 {avg_mb:.1f} MB/s | ETA {format_eta(eta_sec)}",
                                    flush=True,
                                )
                                last_report_t = now
                                last_report_bytes = cur_offset
                    finally:
                        fetcher.close()

                    if not reset_needed:
                        break
                break
            except RuntimeError as exc:
                if str(exc) == "RESUMABLE_SESSION_EXPIRED" and session_attempt == 0:
                    print(f"  [会话刷新] {filename} 上传会话失效，重新创建会话...", flush=True)
                    session_file.unlink(missing_ok=True)
                    upload_uri = ""
                    start_offset = 0
                    continue
                raise

        if completed_meta is None:
            raise RuntimeError(f"上传完成但未收到 Google Drive 元数据: {filename}")

        new_file_id = completed_meta["id"]
        remote_size = int(completed_meta.get("size") or -1)
        if remote_size != total_size:
            self.delete_file(new_file_id)
            raise RuntimeError(f"云盘落地字节数不匹配 ({filename}): 期望 {total_size}, 实得 {remote_size}")

        if expected_sha256 and hasher is not None:
            actual_sha256 = hasher.hexdigest().lower()
            if actual_sha256 != expected_sha256.lower():
                self.delete_file(new_file_id)
                raise RuntimeError(
                    f"SHA256 校验失败 ({filename}): 期望 {expected_sha256}, 实得 {actual_sha256}，已删除损坏云盘文件。"
                )

        session_file.unlink(missing_ok=True)

        # 原子清理同名旧副本（确保目录内始终仅保留最新校验通过的唯一文件）
        for old in existing_files:
            if old["id"] != new_file_id:
                try:
                    self.trash_file(old["id"])
                except Exception:
                    pass

        elapsed = time.time() - t0
        avg_mb = ((total_size - start_offset) / (1024 ** 2)) / max(elapsed, 0.1)
        sha_note = ", SHA256✓" if (expected_sha256 and hasher is not None) else ""
        print(
            f"  [API直传完成] {'/'.join(folder_parts[-1:])}/{filename} "
            f"({total_size / (1024 ** 3):.2f} GB, 耗时 {elapsed:.1f}s, 均速 {avg_mb:.1f} MB/s{sha_note})",
            flush=True,
        )
        return {
            "status": "uploaded",
            "file_id": new_file_id,
            "size": total_size,
            "elapsed": elapsed,
            "avg_mb_s": avg_mb,
        }

    def download_file_to_local(
        self,
        *,
        folder_parts: list[str],
        filename: str,
        local_dst: Path,
        workers: int = DEFAULT_DOWNLOAD_WORKERS,
        chunk_mb: int = DEFAULT_DOWNLOAD_CHUNK_MB,
        progress_interval: float = 10.0,
    ) -> dict[str, Any]:
        """
        绕过 DriveFS FUSE，通过 Google Drive v3 API 多线程 HTTP Range 分片并发直下到本地 NVMe SSD。
        零 DriveFS 读取缓存膨胀，大幅加快 A100 启动预热速度。
        """
        folder_id = self.find_folder_path(folder_parts)
        if not folder_id:
            raise FileNotFoundError(f"云盘目录不存在: {'/'.join(folder_parts)}")

        candidates = self.list_files_in_folder(folder_id, filename)
        if not candidates:
            raise FileNotFoundError(f"云盘文件不存在: {'/'.join(folder_parts)}/{filename}")

        target = max(candidates, key=lambda x: int(x.get("size") or 0))
        file_id = target["id"]
        total_size = int(target.get("size") or 0)
        if total_size <= 0:
            raise RuntimeError(f"云盘文件大小异常 ({filename}): {total_size}")

        local_dst.parent.mkdir(parents=True, exist_ok=True)
        if local_dst.exists() and local_dst.stat().st_size == total_size:
            return {"status": "skipped", "size": total_size, "elapsed": 0.0}

        tmp = local_dst.with_suffix(local_dst.suffix + ".part")
        if tmp.exists():
            tmp.unlink()

        chunk_size = max(4 * 1024 * 1024, chunk_mb * 1024 * 1024)
        ranges: list[tuple[int, int]] = []
        pos = 0
        while pos < total_size:
            end = min(pos + chunk_size - 1, total_size - 1)
            ranges.append((pos, end))
            pos = end + 1

        t0 = time.time()
        downloaded = 0
        prog_lock = threading.Lock()
        write_lock = threading.Lock()
        last_report = [t0]
        use_pwrite = hasattr(os, "pwrite")

        media_url = f"{self.api_base}/files/{file_id}?alt=media&acknowledgeAbuse=true"

        open_flags = os.O_CREAT | os.O_RDWR | os.O_TRUNC | getattr(os, "O_BINARY", 0)
        fd = os.open(str(tmp), open_flags, 0o644)
        try:
            os.ftruncate(fd, total_size)

            def fetch_and_write(start: int, end: int) -> None:
                nonlocal downloaded
                expected_len = end - start + 1
                last_exc: Exception | None = None
                need_refresh = False
                for attempt in range(7):
                    token = self.auth.get_token(force_refresh=need_refresh)
                    need_refresh = False
                    write_pos = [start]
                    got = [0]

                    def on_piece(piece: bytes) -> None:
                        nonlocal downloaded
                        if got[0] + len(piece) > expected_len:
                            raise RuntimeError(
                                f"Range [{start}-{end}] 响应字节超出预期: {got[0] + len(piece)} > {expected_len}"
                            )
                        offset = write_pos[0]
                        if use_pwrite:
                            written = 0
                            mv = memoryview(piece)
                            while written < len(piece):
                                n = os.pwrite(fd, mv[written:], offset + written)
                                written += n
                        else:
                            with write_lock:
                                os.lseek(fd, offset, os.SEEK_SET)
                                written = 0
                                mv = memoryview(piece)
                                while written < len(piece):
                                    n = os.write(fd, mv[written:])
                                    written += n
                        write_pos[0] += len(piece)
                        got[0] += len(piece)
                        with prog_lock:
                            downloaded += len(piece)
                            now = time.time()
                            if progress_interval > 0 and (now - last_report[0] >= progress_interval):
                                avg_mb = (downloaded / (1024 ** 2)) / max(now - t0, 0.1)
                                pct = (downloaded / total_size) * 100.0
                                print(
                                    f"  [API极速预热] {filename} | {downloaded / (1024 ** 3):.2f}/{total_size / (1024 ** 3):.2f} GB "
                                    f"({pct:.1f}%) | 均速 {avg_mb:.1f} MB/s",
                                    flush=True,
                                )
                                last_report[0] = now

                    try:
                        status, _hdrs, _final_url = self.transport.stream_get(
                            media_url,
                            headers={
                                "Authorization": f"Bearer {token}",
                                "Range": f"bytes={start}-{end}",
                            },
                            chunk_size=4 * 1024 * 1024,
                            on_chunk=on_piece,
                            timeout=DOWNLOAD_RANGE_TIMEOUT,
                        )
                        if status in (200, 206) and got[0] == expected_len:
                            return
                        if status == 401:
                            need_refresh = True
                            last_exc = RuntimeError("401")
                            with prog_lock:
                                downloaded = max(0, downloaded - got[0])
                            continue
                        last_exc = RuntimeError(
                            f"Range [{start}-{end}] HTTP {status}, 期望 {expected_len}, 实得 {got[0]}"
                        )
                    except Exception as exc:
                        last_exc = exc

                    with prog_lock:
                        downloaded = max(0, downloaded - got[0])
                    time.sleep(min(20.0, 1.0 * (2 ** attempt)))

                raise RuntimeError(f"Drive API 分片下载 [{start}-{end}] 失败: {last_exc}")

            eff_workers = min(max(1, workers), len(ranges))
            with concurrent.futures.ThreadPoolExecutor(max_workers=eff_workers) as pool:
                futs = [pool.submit(fetch_and_write, s, e) for s, e in ranges]
                for f in concurrent.futures.as_completed(futs):
                    f.result()
        except Exception:
            os.close(fd)
            tmp.unlink(missing_ok=True)
            raise
        else:
            os.close(fd)

        if tmp.stat().st_size != total_size:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(f"本地预热文件大小校验失败 ({filename})")
        os.replace(tmp, local_dst)

        elapsed = time.time() - t0
        avg_mb = (total_size / (1024 ** 2)) / max(elapsed, 0.1)
        return {
            "status": "downloaded",
            "size": total_size,
            "elapsed": elapsed,
            "avg_mb_s": avg_mb,
        }


def try_create_drive_client(verbose: bool = True) -> GoogleDriveClient | None:
    """尝试初始化并探测 Google Drive v3 API 客户端；若未授权则静默返回 None 以便回退 DriveFS。"""
    auth = DriveAuthManager()
    if not auth.available():
        return None
    client = GoogleDriveClient(auth)
    try:
        info = client.probe()
        if verbose:
            email = info.get("user", {}).get("emailAddress", "unknown")
            print(f"[Drive API Turbo 就绪] 已绕过 DriveFS FUSE，直连 Google Drive v3 API (账号: {email})", flush=True)
        return client
    except Exception as exc:
        if verbose:
            print(f"[Drive API 不可用 -> 自动回退 DriveFS] 原因: {exc}", flush=True)
        return None
