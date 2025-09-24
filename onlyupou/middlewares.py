"""Custom middlewares for the Scrapy project."""

from __future__ import annotations

import logging
from typing import Optional

from scrapy.crawler import Crawler
from scrapy.exceptions import NotConfigured
from scrapy.http import Request

try:  # pragma: no cover - optional dependency
    import redis
except ImportError:  # pragma: no cover - handled at runtime
    redis = None


class RedisProxyMiddleware:
    """Downloader middleware that fetches proxy information from Redis.

    The middleware expects a Redis instance to hold a collection with proxy
    definitions. Proxies are read using :func:`srandmember`, so the Redis key can
    refer to either a set or a list. The proxy values should be provided either
    as bytes or strings containing a full proxy URI (e.g. ``http://user:pass@ip``).
    """

    def __init__(
        self,
        redis_url: str,
        proxy_key: str,
        *,
        encoding: str = "utf-8",
        fallback_proxy: Optional[str] = None,
    ) -> None:
        if redis is None:
            raise NotConfigured(
                "redis package is required for RedisProxyMiddleware but is not installed"
            )

        self.logger = logging.getLogger(self.__class__.__name__)
        self.redis_url = redis_url
        self.proxy_key = proxy_key
        self.encoding = encoding
        self.fallback_proxy = fallback_proxy

        try:
            self.client = redis.from_url(redis_url)
        except Exception as exc:  # pragma: no cover - connection errors occur at runtime
            raise NotConfigured(f"Unable to connect to Redis using URL {redis_url!r}: {exc}") from exc

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> "RedisProxyMiddleware":
        redis_url = crawler.settings.get("REDIS_PROXY_URL")
        proxy_key = crawler.settings.get("REDIS_PROXY_KEY")
        if not redis_url or not proxy_key:
            raise NotConfigured("Redis proxy middleware is not configured")

        encoding = crawler.settings.get("REDIS_PROXY_ENCODING", "utf-8")
        fallback_proxy = crawler.settings.get("REDIS_PROXY_FALLBACK")

        return cls(redis_url, proxy_key, encoding=encoding, fallback_proxy=fallback_proxy)

    def process_request(self, request: Request, spider) -> None:  # type: ignore[override]
        if request.meta.get("proxy"):
            return

        proxy = self._get_proxy()
        if proxy:
            request.meta["proxy"] = proxy
            return

        if self.fallback_proxy:
            self.logger.debug("Using fallback proxy %s", self.fallback_proxy)
            request.meta["proxy"] = self.fallback_proxy

    def _get_proxy(self) -> Optional[str]:
        if self.client is None:
            return None

        try:
            proxy = self.client.srandmember(self.proxy_key)
        except Exception as exc:  # pragma: no cover - runtime connectivity issue
            self.logger.error("Failed to fetch proxy from Redis: %s", exc)
            return None

        if proxy is None:
            self.logger.debug("No proxy available in Redis key %s", self.proxy_key)
            return None

        if isinstance(proxy, bytes):
            return proxy.decode(self.encoding, errors="ignore")
        return proxy
