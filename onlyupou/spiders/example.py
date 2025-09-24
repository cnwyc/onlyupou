"""Example spider demonstrating Doris synchronisation and Redis proxy usage."""

from __future__ import annotations

from typing import Any, Tuple

from itemadapter import ItemAdapter

from onlyupou.items import ExampleItem
from onlyupou.spiders.base import DorisSpider


class QuotesSpider(DorisSpider):
    name = "example"
    start_urls = ["http://quotes.toscrape.com/"]

    # Default Doris target for the spider. These values can be overridden via
    # environment variables or by custom spider logic.
    doris_database = "demo"
    doris_table = "quotes"

    def parse(self, response, **kwargs):  # type: ignore[override]
        for quote in response.css("div.quote"):
            item = ExampleItem()
            item["title"] = quote.css("span.text::text").get()
            item["url"] = response.url
            item["description"] = quote.css("small.author::text").get()
            yield item

        next_page = response.css("li.next a::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def get_doris_target(self, item: Any) -> Tuple[str, str]:
        adapter = ItemAdapter(item)
        author = adapter.get("description")
        if author:
            return self.doris_database or "demo", self.doris_table or "quotes"
        return self.doris_database or "demo", "quotes_unknown_author"
