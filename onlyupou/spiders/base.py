"""Base spider utilities."""

from __future__ import annotations

from typing import Any, Optional, Tuple

import scrapy


class DorisTargetMixin:
    """Mixin that allows spiders to declare Doris synchronization metadata."""

    #: Name of the Doris database the spider writes to by default.
    doris_database: Optional[str] = None
    #: Name of the Doris table the spider writes to by default.
    doris_table: Optional[str] = None

    def get_doris_target(self, item: Any) -> Tuple[Optional[str], Optional[str]]:
        """Return the Doris database and table for the given item.

        Spiders can override this method to dynamically choose the target table
        depending on the item that is being processed. By default it simply
        returns the values stored in :attr:`doris_database` and
        :attr:`doris_table`.
        """

        return self.doris_database, self.doris_table


class DorisSpider(DorisTargetMixin, scrapy.Spider):
    """Convenience base class that integrates :class:`DorisTargetMixin`."""

    pass
