"""Scrapy settings for the onlyupou project."""

from __future__ import annotations

import os
from typing import Dict

BOT_NAME = "onlyupou"

SPIDER_MODULES = ["onlyupou.spiders"]
NEWSPIDER_MODULE = "onlyupou.spiders"

# Respect robots.txt can be enabled if desired.
ROBOTSTXT_OBEY = False

# Downloader middlewares -----------------------------------------------------------------
DOWNLOADER_MIDDLEWARES = {
    "onlyupou.middlewares.RedisProxyMiddleware": 350,
}

# Item pipelines -------------------------------------------------------------------------
ITEM_PIPELINES = {
    "onlyupou.pipelines.DorisPipeline": 300,
}

# Redis proxy configuration --------------------------------------------------------------
REDIS_PROXY_URL = os.getenv("REDIS_PROXY_URL", "redis://localhost:6379/0")
REDIS_PROXY_KEY = os.getenv("REDIS_PROXY_KEY", "scrapy:proxies")
REDIS_PROXY_ENCODING = os.getenv("REDIS_PROXY_ENCODING", "utf-8")
REDIS_PROXY_FALLBACK = os.getenv("REDIS_PROXY_FALLBACK")

# Doris configuration --------------------------------------------------------------------
DORIS_ENABLED = os.getenv("DORIS_ENABLED", "0").lower() in {"1", "true", "yes", "on"}
DORIS_HOST = os.getenv("DORIS_HOST", "")
DORIS_USER = os.getenv("DORIS_USER", "root")
DORIS_PASSWORD = os.getenv("DORIS_PASSWORD", "")
DORIS_TIMEOUT = int(os.getenv("DORIS_TIMEOUT", "30"))
DORIS_LABEL_PREFIX = os.getenv("DORIS_LABEL_PREFIX", "scrapy")
DORIS_DEFAULT_DATABASE = os.getenv("DORIS_DEFAULT_DATABASE", "demo")
DORIS_DEFAULT_TABLE = os.getenv("DORIS_DEFAULT_TABLE", "items")
DORIS_BATCH_SIZE = int(os.getenv("DORIS_BATCH_SIZE", "50"))
DORIS_STREAM_LOAD_HEADERS: Dict[str, str] = {}

# User agent rotation / concurrency settings can be configured below as needed.
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en",
}

LOG_LEVEL = os.getenv("SCRAPY_LOG_LEVEL", "INFO")
