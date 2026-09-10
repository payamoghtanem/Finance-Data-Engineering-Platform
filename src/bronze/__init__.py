"""Bronze layer: loads one raw object into a queryable table with full lineage.

Implements EPIC-03 (US-03-002, US-03-003). See
docs/technical/technical-design-document.md §2a for the storage shape.
"""

from src.bronze.writer import BronzeRecord, BronzeWriter

__all__ = ["BronzeRecord", "BronzeWriter"]
