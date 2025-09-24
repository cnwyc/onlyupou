"""Item definitions for the project."""

import scrapy


class ExampleItem(scrapy.Item):
    """A minimal example item for demonstration purposes."""

    title = scrapy.Field()
    url = scrapy.Field()
    description = scrapy.Field()
