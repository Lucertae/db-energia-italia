"""Classe base Source: HTTP con cache, rate limit, retry."""
from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from loguru import logger

import config
from models import Company


class RateLimiter:
    def __init__(self, min_delay: float = config.MIN_DELAY_SECONDS) -> None:
        self.min_delay = min_delay
        self._last: dict[str, float] = {}

    def wait(self, url: str) -> None:
        host = urlparse(url).netloc.lower()
        now = time.monotonic()
        last = self._last.get(host, 0.0)
        delta = now - last
        if delta < self.min_delay:
            time.sleep(self.min_delay - delta)
        self._last[host] = time.monotonic()


_RATE_LIMITER = RateLimiter()


class Source(ABC):
    name: str = "base"
    expected_min_results: int = 0

    def __init__(self, use_cache: bool = True) -> None:
        self.use_cache = use_cache
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": config.USER_AGENT,
                "Accept": "text/html,application/json,*/*",
                "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
            }
        )

    @abstractmethod
    def fetch(self) -> list[Company]:
        raise NotImplementedError

    def run(self) -> list[Company]:
        try:
            results = self.fetch()
        except Exception as exc:  # noqa: BLE001 — isolation per modulo
            logger.exception("Fonte {} fallita: {}", self.name, exc)
            return []
        if self.expected_min_results > 0 and len(results) == 0:
            logger.error(
                "Fonte {}: 0 risultati (attesi >{}). "
                "Probabile cambio layout/API — aggiornare selettori/endpoint.",
                self.name,
                self.expected_min_results,
            )
        else:
            logger.info("Fonte {}: {} record", self.name, len(results))
        return results

    def _cache_path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return config.CACHE_DIR / digest

    def get_cached_text(self, url: str, **kwargs: Any) -> str:
        method = str(kwargs.pop("method", "GET")).upper()
        json_body = kwargs.pop("json", None)
        data = kwargs.pop("data", None)
        cache_key = f"{method}:{url}:{json.dumps(json_body, sort_keys=True, default=str)}:{data}"
        path = self._cache_path(cache_key)
        meta_path = path.with_suffix(".meta.json")

        if self.use_cache and path.exists():
            return path.read_text(encoding="utf-8", errors="replace")

        _RATE_LIMITER.wait(url)
        last_err: Exception | None = None
        for attempt in range(config.MAX_RETRIES):
            try:
                resp = self.session.request(
                    method,
                    url,
                    timeout=config.REQUEST_TIMEOUT,
                    json=json_body,
                    data=data,
                    **kwargs,
                )
                if resp.status_code in {429, 500, 502, 503, 504}:
                    raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
                resp.raise_for_status()
                text = resp.text
                if self.use_cache:
                    path.write_text(text, encoding="utf-8")
                    meta_path.write_text(
                        json.dumps(
                            {
                                "url": url,
                                "method": method,
                                "status": resp.status_code,
                                "cached_at": time.time(),
                            },
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                return text
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                sleep_s = min(60.0, (2**attempt) * config.MIN_DELAY_SECONDS)
                # honor Retry-After if present
                retry_after = None
                if isinstance(exc, requests.HTTPError) and exc.response is not None:
                    ra = exc.response.headers.get("Retry-After")
                    if ra:
                        try:
                            retry_after = float(ra)
                        except ValueError:
                            try:
                                dt = parsedate_to_datetime(ra)
                                retry_after = max(0.0, dt.timestamp() - time.time())
                            except Exception:  # noqa: BLE001
                                retry_after = None
                logger.warning(
                    "{} {} tentativo {}/{} fallito: {} — retry in {:.1f}s",
                    method,
                    url,
                    attempt + 1,
                    config.MAX_RETRIES,
                    exc,
                    retry_after or sleep_s,
                )
                time.sleep(retry_after or sleep_s)
        raise RuntimeError(f"Request fallita dopo retry: {url}") from last_err

    def get_cached_json(self, url: str, **kwargs: Any) -> Any:
        text = self.get_cached_text(url, **kwargs)
        return json.loads(text)
