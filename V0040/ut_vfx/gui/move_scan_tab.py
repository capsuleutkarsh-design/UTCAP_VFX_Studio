"""
Legacy compatibility wrapper for Move/Scan tab.

`MoveScanTab` now delegates to `SmartMoveScanTab` so there is only one
maintained implementation.
"""

import logging

from .tabs.smart_move_scan_tab import SmartMoveScanTab

logger = logging.getLogger(__name__)


class MoveScanTab(SmartMoveScanTab):
    """
    Backward-compatible alias for the modern Smart Move/Scan implementation.
    """

    def __init__(self, config_manager):
        logger.info("MoveScanTab is deprecated; using SmartMoveScanTab implementation.")
        super().__init__(config_manager)
