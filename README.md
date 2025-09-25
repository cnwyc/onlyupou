# onlyupou Scrapy Project

This repository contains a basic Scrapy project that demonstrates how to:

* Fetch proxy information from Redis and apply it to outgoing requests.
* Deliver scraped data into [Apache Doris](https://doris.apache.org/) using the HTTP stream load API.
* Allow each spider to define (or override) the Doris database/table that receives its data.

The project ships with an example spider (`onlyupou.spiders.example`) that crawls
[`quotes.toscrape.com`](https://quotes.toscrape.com/) and shows how to route
items into different Doris tables based on their content.

## Project structure

```
.
├── onlyupou/
│   ├── items.py                # Scrapy items used by the project
│   ├── middlewares.py          # Redis backed proxy middleware
│   ├── pipelines.py            # Doris stream load pipeline
│   ├── settings.py             # Scrapy configuration
│   └── spiders/
│       ├── base.py             # Base classes with Doris helpers
│       └── example.py          # Sample spider
└── scrapy.cfg
```

## Requirements

* Python 3.9+
* [Scrapy](https://scrapy.org/)
* [`redis`](https://pypi.org/project/redis/) (Python client library)

The `requests` library is **not** required because the Doris pipeline relies on
Python's standard library for HTTP requests.

Install dependencies via `pip`:

```bash
pip install scrapy redis
```

## Configuration

### Redis proxy storage

Configure Redis via environment variables (defaults shown below):

* `REDIS_PROXY_URL`: connection string (default `redis://localhost:6379/0`).
* `REDIS_PROXY_KEY`: key that stores proxies (`scrapy:proxies`).
* `REDIS_PROXY_ENCODING`: proxy string encoding (`utf-8`).
* `REDIS_PROXY_FALLBACK`: optional static proxy used when Redis does not
  return one.

Proxies should be stored in a Redis set or list where each element contains the
full proxy URI, for example: `http://user:pass@10.0.0.2:8080`.

### Doris sink

The pipeline is disabled by default. Enable it and configure the target Doris
instance through environment variables:

* `DORIS_ENABLED`: set to `1`, `true`, `yes` or `on` to activate the pipeline.
* `DORIS_HOST`: Doris FE address, e.g. `http://doris-host:8030`.
* `DORIS_USER` / `DORIS_PASSWORD`: credentials for stream loading.
* `DORIS_DEFAULT_DATABASE` and `DORIS_DEFAULT_TABLE`: default target for items.
* `DORIS_BATCH_SIZE`: how many items to buffer before streaming (default `50`).
* `DORIS_LABEL_PREFIX`: optional label prefix for stream load operations.

Additional headers for stream load requests can be added by editing
`DORIS_STREAM_LOAD_HEADERS` in `settings.py` if you need to set options such as
`column_separator`.

## Spider specific Doris targets

Every spider can control where its items go by setting the `doris_database` and
`doris_table` attributes, or by overriding `get_doris_target(self, item)` for
fine-grained routing. The included `QuotesSpider` routes items with an author to
`demo.quotes`, while anonymous quotes are sent to `demo.quotes_unknown_author`.

To create a new spider, inherit from `onlyupou.spiders.base.DorisSpider` (or mix
in `DorisTargetMixin`) and define the desired Doris target.

## Running the example spider

Make sure Redis and Doris are available and configured via environment
variables. Then run:

```bash
scrapy crawl example
```

Scraped items will be sent to the configured Doris database/table using stream
load requests. The spider logs will report when batches are flushed.

## Development tips

* Use `scrapy shell <url>` to experiment with selectors.
* Adjust concurrency settings and retry policies in `settings.py` depending on
  the target website.
* Extend `RedisProxyMiddleware` if your proxy provider stores additional
  metadata that must be parsed.
