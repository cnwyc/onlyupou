"""Item pipelines used by the Scrapy project."""

from __future__ import annotations

import base64
import json
import logging
import uuid
from typing import Dict, Iterable, List, Optional, Tuple
from urllib import error as urlerror
from urllib import request as urlrequest

from itemadapter import ItemAdapter
from scrapy import Spider
from scrapy.crawler import Crawler
from scrapy.exceptions import NotConfigured


class DorisStreamLoader:
    """Simple HTTP client for pushing data into Apache Doris via stream load."""

    def __init__(
        self,
        host: str,
        *,
        user: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30,
        label_prefix: str = "scrapy",
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.host = host.rstrip("/")
        self.user = user or ""
        self.password = password or ""
        self.timeout = timeout
        self.label_prefix = label_prefix
        self.extra_headers = extra_headers or {}

    def load(self, database: str, table: str, records: Iterable[Dict]) -> None:
        payload = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
        data = payload.encode("utf-8")
        url = f"{self.host}/api/{database}/{table}/_stream_load"
        request = urlrequest.Request(url, data=data, method="PUT")
        request.add_header("Content-Type", "application/json; charset=UTF-8")
        request.add_header("format", "json")
        request.add_header("strip_outer_array", "true")
        request.add_header("label", self._generate_label())

        if self.user:
            token = base64.b64encode(f"{self.user}:{self.password}".encode("utf-8")).decode("ascii")
            request.add_header("Authorization", f"Basic {token}")

        for header, value in self.extra_headers.items():
            request.add_header(header, value)

        try:
            with urlrequest.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8", errors="ignore")
                self.logger.debug(
                    "Stream load to Doris succeeded for %s.%s: %s", database, table, body
                )
        except urlerror.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore") if exc.fp else ""
            self.logger.error(
                "HTTP error during stream load to %s.%s: %s %s", database, table, exc.code, body
            )
            raise
        except urlerror.URLError as exc:
            self.logger.error("Network error during stream load to %s.%s: %s", database, table, exc)
            raise

    def _generate_label(self) -> str:
        return f"{self.label_prefix}-{uuid.uuid4()}"


class DorisPipeline:
    """Scrapy pipeline that loads items into Apache Doris."""

    def __init__(
        self,
        loader: DorisStreamLoader,
        *,
        default_database: str,
        default_table: str,
        batch_size: int = 50,
    ) -> None:
        self.loader = loader
        self.default_database = default_database
        self.default_table = default_table
        self.batch_size = batch_size
        self.buffers: Dict[Tuple[str, str], List[Dict]] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> "DorisPipeline":
        if not crawler.settings.getbool("DORIS_ENABLED", False):
            raise NotConfigured("Doris pipeline is disabled")

        host = crawler.settings.get("DORIS_HOST")
        if not host:
            raise NotConfigured("DORIS_HOST must be configured to enable DorisPipeline")

        loader = DorisStreamLoader(
            host,
            user=crawler.settings.get("DORIS_USER"),
            password=crawler.settings.get("DORIS_PASSWORD"),
            timeout=crawler.settings.getint("DORIS_TIMEOUT", 30),
            label_prefix=crawler.settings.get("DORIS_LABEL_PREFIX", "scrapy"),
            extra_headers=crawler.settings.getdict("DORIS_STREAM_LOAD_HEADERS", {}),
        )

        default_database = crawler.settings.get("DORIS_DEFAULT_DATABASE")
        default_table = crawler.settings.get("DORIS_DEFAULT_TABLE")
        if not default_database or not default_table:
            raise NotConfigured(
                "Both DORIS_DEFAULT_DATABASE and DORIS_DEFAULT_TABLE must be set to enable DorisPipeline"
            )

        batch_size = crawler.settings.getint("DORIS_BATCH_SIZE", 50)
        return cls(
            loader,
            default_database=default_database,
            default_table=default_table,
            batch_size=batch_size,
        )

    def open_spider(self, spider: Spider) -> None:  # type: ignore[override]
        self.logger.info(
            "Opened Doris pipeline for spider %s with default target %s.%s",
            spider.name,
            self.default_database,
            self.default_table,
        )

    def close_spider(self, spider: Spider) -> None:  # type: ignore[override]
        for (database, table), buffer in list(self.buffers.items()):
            if buffer:
                self._flush(database, table, buffer)
        self.logger.info("Closed Doris pipeline for spider %s", spider.name)

    def process_item(self, item, spider: Spider):  # type: ignore[override]
        database, table = self._resolve_target(spider, item)
        key = (database, table)
        buffer = self.buffers.setdefault(key, [])
        buffer.append(ItemAdapter(item).asdict())
        if len(buffer) >= self.batch_size:
            self._flush(database, table, buffer)
        return item

    def _resolve_target(self, spider: Spider, item) -> Tuple[str, str]:
        database = self.default_database
        table = self.default_table

        getter = getattr(spider, "get_doris_target", None)
        if callable(getter):
            resolved = getter(item)
            if resolved:
                database, table = resolved

        database = getattr(spider, "doris_database", database)
        table = getattr(spider, "doris_table", table)

        if not database or not table:
            raise ValueError(
                "Doris target could not be resolved. Provide doris_database and doris_table on the spider."
            )

        return database, table

    def _flush(self, database: str, table: str, buffer: List[Dict]) -> None:
        if not buffer:
            return

        self.logger.debug(
            "Flushing %d item(s) to Doris table %s.%s", len(buffer), database, table
        )
        self.loader.load(database, table, buffer)
        buffer.clear()
