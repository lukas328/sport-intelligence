"""Partner adapters (addendum 01 section 7): interfaces with first implementations and stubs.

Concrete partner connections follow once partnerships exist. Every adapter is plain Python without
database access; services call them and store the results. See docs/integrations.md.
"""

from handball_api.integrations.base import AdapterError, NotConfiguredError
from handball_api.integrations.registry import ADAPTERS, adapter

__all__ = ["ADAPTERS", "AdapterError", "NotConfiguredError", "adapter"]
