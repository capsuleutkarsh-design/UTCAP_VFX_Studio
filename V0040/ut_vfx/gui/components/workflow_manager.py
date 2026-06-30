"""
Workflow Mode Manager Component.

Handles switching between different workflow modes:
- Standard (Excel Structure)
- Auto-Scan (Auto-Build & Move)
- Incoming Delivery (Smart Ingest)

Extracted from main_window.py for better maintainability.
"""

from PySide6.QtCore import QObject, Signal
import logging


class WorkflowManager(QObject):
    """
    Manages workflow mode switching and tab visibility.
    
    Coordinates which tabs are visible based on the selected workflow mode.
    """
    
    mode_changed = Signal(int, str)  # index, mode_name
    
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent = parent_window
        self.current_mode_index = 0
        self.mode_names = [
            "Standard (Excel Structure)",
            "Auto-Scan (Auto-Build & Move)",
            "Incoming Delivery (Smart Ingest)"
        ]
    
    def change_workflow_mode(self, index):
        """
        Switch the application layout based on selected workflow.
        Works with lazy-loaded tabs via TabCoordinator.
        
        Args:
            index (int): Workflow mode index (0=Excel, 1=Scan, 2=Delivery)
        """
        tc = self.parent.tab_coordinator
        
        # Helper to get tab widget by label (for lazy-loaded tabs)
        def get_tab_by_label(label):
            """Get tab instance by label, creating if needed"""
            for i, tab_label in enumerate(tc.tab_labels):
                if tab_label == label:
                    return tc.get_or_create_tab(i)
            return None
        
        # Helper to set tab visibility by label
        def set_visible_by_label(label, visible: bool, rename_to=None):
            """Set visibility of a tab by label"""
            for i, tab_label in enumerate(tc.tab_labels):
                if tab_label == label:
                    item = self.parent.sidebar_nav.item(i)
                    if item:
                        item.setHidden(not visible)
                        if rename_to:
                            if getattr(tc, 'sidebar_collapsed', False):
                                # Extract just the icon if collapsed (assumes format "ICON  Label")
                                item.setText(rename_to.split("  ")[0].strip())
                            else:
                                item.setText(rename_to)
                    return
        
        # Helper to select tab by label
        def select_by_label(label):
            """Switch to tab by label"""
            if getattr(self.parent, '_startup_complete', False) is False:
                # Don't hijack the active tab during startup (Home should be first)
                return
            for i, tab_label in enumerate(tc.tab_labels):
                if tab_label == label:
                    self.parent.sidebar_nav.setCurrentRow(i)
                    return
        
        # Helper to conditionally select tab
        def select_fallback_tab(fallback_label):
            """Switch to fallback tab ONLY if current tab is hidden."""
            if getattr(self.parent, '_startup_complete', False) is False:
                return
            current_row = self.parent.sidebar_nav.currentRow()
            current_item = self.parent.sidebar_nav.item(current_row) if current_row >= 0 else None
            
            # Only force tab switch if current tab is hidden or none selected
            if current_item is None or current_item.isHidden():
                select_by_label(fallback_label)
        
        # Mode 0: Excel Mode (Standard)
        if index == 0:
            set_visible_by_label("Incoming Delivery", False)
            set_visible_by_label("Folder Creator", True, "📁  Folder Creator")
            set_visible_by_label("Scan Manager", True)
            
            # Configure folder creator if it exists
            folder_creator = get_tab_by_label("Folder Creator")
            if folder_creator and hasattr(folder_creator, 'set_mode'):
                folder_creator.set_mode("excel")
            
            # Configure scan manager if it exists
            scan_manager = get_tab_by_label("Scan Manager")
            if scan_manager and hasattr(scan_manager, 'mode_combo'):
                scan_manager.mode_combo.setCurrentIndex(0)
            
            select_fallback_tab("Folder Creator")
            self.parent.status_bar.showMessage("Switched to Standard Excel Mode")
            mode_name = "Standard Excel Mode"
        
        # Mode 1: Scan Mode (Auto-Scan)
        elif index == 1:
            set_visible_by_label("Incoming Delivery", False)
            set_visible_by_label("Folder Creator", True, "⚡  Auto-Build & Move")
            set_visible_by_label("Scan Manager", False)  # Hide manual scan
            
            # Configure folder creator
            folder_creator = get_tab_by_label("Folder Creator")
            if folder_creator and hasattr(folder_creator, 'set_mode'):
                folder_creator.set_mode("scan")
                
            select_fallback_tab("Folder Creator")
            self.parent.status_bar.showMessage("Switched to Auto-Scan Mode")
            mode_name = "Auto-Scan Mode"
        
        # Mode 2: Incoming Delivery Mode
        elif index == 2:
            set_visible_by_label("Folder Creator", False)
            set_visible_by_label("Scan Manager", False)
            set_visible_by_label("Incoming Delivery", True)
            
            select_fallback_tab("Incoming Delivery")
            self.parent.status_bar.showMessage("Switched to Incoming Delivery Mode (Unified)")
            mode_name = "Incoming Delivery Mode"
        else:
            logging.warning(f"Unknown workflow mode index: {index}")
            return
        
        self.current_mode_index = index
        self.mode_changed.emit(index, mode_name)
        
        logging.info(f"Workflow mode changed to: {mode_name} (index {index})")
    
    def get_current_mode(self):
        """Return current workflow mode index."""
        return self.current_mode_index
    
    def get_current_mode_name(self):
        """Return current workflow mode name."""
        if 0 <= self.current_mode_index < len(self.mode_names):
            return self.mode_names[self.current_mode_index]
        return "Unknown"
