"""
Tab Coordinator Component.

Manages tab registration, initialization, visibility and navigation.

Extracted from main_window.py for better maintainability.
"""

from PySide6.QtWidgets import QListWidgetItem
from PySide6.QtCore import Qt, QSize, Signal, QObject
import logging


class TabCoordinator(QObject):
    """
    Coordinates tab management for the main window.
    
    Handles:
    - Tab registration and initialization
    - Tab visibility management
    - Navigation between tabs
    - Permission-based tab access
    """
    
    tab_switched = Signal(str)  # tab_name
    
    def __init__(self, parent_window, sidebar_nav, content_stack):
        """
        Initialize tab coordinator.
        
        Args:
            parent_window: Reference to main window
            sidebar_nav: QListWidget for sidebar navigation
            content_stack: QStackedWidget for tab content
        """
        super().__init__(parent_window)
        self.parent = parent_window
        self.sidebar_nav = sidebar_nav
        self.content_stack = content_stack
        self.nav_items = []  # List of {page, item} dicts
        
        # Lazy loading infrastructure (Improvement #4)
        self.tab_factories = {}  # Factory functions for each tab
        self.tab_instances = {}  # Cached instances
        self.tab_labels = []  # Ordered list of tab labels
        
        # Connect navigation signal
        self.sidebar_nav.currentRowChanged.connect(self._on_nav_changed)
    
    def register_tab(self, page_widget, label, icon="", permission_key=None, 
                     visible=True, user_role=None, allowed_tabs=None):
        """
        Register a tab for management.
        
        Args:
            page_widget: The tab widget to add
            label: Display label for the tab
            icon: Optional icon emoji/text
            permission_key: Permission key to check
            visible: Whether tab should be visible by default
            user_role: Current user's role
            allowed_tabs: List of allowed tab permissions
        
        Returns:
            bool: True if tab was added, False if filtered by permissions
        """
        if not page_widget:
            return False
        
        # Check if already added
        for entry in self.nav_items:
            if entry['page'] == page_widget:
                logging.warning(f"Tab {label} already registered")
                return False
        
        # Permission check
        if permission_key and user_role and allowed_tabs:
            is_dev = (user_role and user_role.lower() == "developer")
            has_perm = (permission_key in allowed_tabs) or ("ALL" in allowed_tabs)
            
            # DEBUG LOGGING
            logging.info(f"[SCAN] Tab Registration: '{label}'")
            logging.info(f"   Permission Key: '{permission_key}'")
            logging.info(f"   User Role: '{user_role}' | Is Developer: {is_dev}")
            logging.info(f"   Allowed Tabs: {allowed_tabs}")
            logging.info(f"   Has Permission: {has_perm}")
            
            # Skip if no permission (unless developer)
            if not (is_dev or has_perm):
                logging.warning(f"[SKIP] Tab '{label}' FILTERED - No permission")
                # Some tabs need to be added but hidden (for workflow switching)
                if not visible:
                    pass  # Continue to add but hidden
                else:
                    return False
            else:
                logging.info(f"[OK] Tab '{label}' ALLOWED")
        
        # Add to stack
        self.content_stack.addWidget(page_widget)
        
        # Add to sidebar
        is_collapsed = getattr(self, "sidebar_collapsed", False)
        
        if is_collapsed:
            display_text = f"{icon}" if icon else " "
        else:
            display_text = f"{icon}  {label}" if icon else label
            
        item = QListWidgetItem(display_text)
        item.setSizeHint(QSize(0, 50))
        
        if is_collapsed:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
        self.sidebar_nav.addItem(item)
        
        # Set visibility
        item.setHidden(not visible)
        
        # Store mapping
        self.nav_items.append({
            'page': page_widget,
            'item': item,
            'label': label,
            'permission': permission_key
        })
        
        logging.info(f"Tab registered: {label}")
        return True
    
    def set_tab_visible(self, page_widget, visible, rename_to=None):
        """
        Set visibility of a tab.
        
        Args:
            page_widget: The tab widget
            visible: True to show, False to hide
            rename_to: Optional new label text
        """
        if not page_widget:
            return
        
        for entry in self.nav_items:
            if entry['page'] == page_widget:
                entry['item'].setHidden(not visible)
                if rename_to:
                    entry['item'].setText(rename_to)
                return

    def set_sidebar_collapsed(self, collapsed: bool):
        """Update the text of sidebar items based on collapse state."""
        self.sidebar_collapsed = collapsed
        
        # We need to match the items in self.sidebar_nav with self.tab_factories 
        # to know their original icon and label.
        # The QListWidget items are in the same order as self.tab_labels
        for i in range(self.sidebar_nav.count()):
            item = self.sidebar_nav.item(i)
            if i < len(self.tab_labels):
                label = self.tab_labels[i]
                factory_data = self.tab_factories.get(label, {})
                icon = factory_data.get('icon', '')
                is_locked = factory_data.get('locked', False)
                
                # Format text
                if collapsed:
                    # Center the icon without extra spaces
                    display_text = f"{icon}" if icon else " "
                else:
                    if is_locked:
                        display_text = f"{icon}  [LOCKED] {label}" if icon else f"[LOCKED] {label}"
                    else:
                        display_text = f"{icon}  {label}" if icon else label
                
                # We need to handle setText and alignment.
                item.setText(display_text)
                if collapsed:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def select_tab(self, page_widget):
        """
        Switch to specified tab.
        
        Args:
            page_widget: The tab widget to switch to
        """
        if not page_widget:
            return
        
        for i, entry in enumerate(self.nav_items):
            if entry['page'] == page_widget:
                self.sidebar_nav.setCurrentRow(i)
                return
    
    def get_current_tab(self):
        """Return currently active tab widget."""
        return self.content_stack.currentWidget()
    
    def get_current_tab_name(self):
        """Return name of currently active tab."""
        current_widget = self.get_current_tab()
        for entry in self.nav_items:
            if entry['page'] == current_widget:
                return entry['label']
        return "Unknown"
    
    def find_tab_by_page(self, page_widget):
        """
        Find tab entry by page widget.
        
        Returns:
            dict or None: Tab entry dict if found
        """
        for entry in self.nav_items:
            if entry['page'] == page_widget:
                return entry
        return None
    
    def register_tab_factory(self, label, factory_fn, icon="", permission_key=None,
                            visible=True, user_role=None, allowed_tabs=None, tooltip=""):
        """
        Register a tab factory for lazy initialization (Improvement #4).
        
        Args:
            label: Display label for the tab
            factory_fn: Callable that creates the tab widget
            icon: Optional icon emoji/text
            permission_key: Permission key to check
            visible: Whether tab should be visible by default
            user_role: Current user's role
            allowed_tabs: List of allowed tab permissions
            tooltip: Optional tooltip shown when hovering the sidebar item
        
        Returns:
            bool: True if tab was registered
        """
        is_locked = False
        lock_tooltip = tooltip

        # Permission check
        if permission_key and user_role and allowed_tabs:
            is_dev = (user_role and user_role.lower() == "developer")
            has_perm = (permission_key in allowed_tabs) or ("ALL" in allowed_tabs)
            
            logging.info(f"[LAZY] Registering factory: '{label}'")
            logging.info(f"   Permission: '{permission_key}' | Role: '{user_role}'")
            logging.info(f"   Has Permission: {has_perm}")
            
            if not (is_dev or has_perm):
                if not visible:  # Keep hidden workflow tabs hidden.
                    logging.warning(f"[SKIP] Factory '{label}' - No permission")
                    return False
                is_locked = True
                lock_tooltip = f"Requires permission: {permission_key}"
                logging.info(f"[LOCKED] Factory '{label}' shown as locked (no permission).")
        
        # Store factory
        self.tab_factories[label] = {
            'factory': None if is_locked else factory_fn,
            'icon': icon,
            'permission': permission_key,
            'visible': visible,
            'locked': is_locked,
        }
        self.tab_labels.append(label)
        
        # Add to sidebar immediately (for navigation)
        is_collapsed = getattr(self, "sidebar_collapsed", False)
        
        if is_collapsed:
            display_text = f"{icon}" if icon else " "
        else:
            if is_locked:
                display_text = f"{icon}  [LOCKED] {label}" if icon else f"[LOCKED] {label}"
            else:
                display_text = f"{icon}  {label}" if icon else label
                
        item = QListWidgetItem(display_text)
        item.setSizeHint(QSize(0, 50))
        item.setHidden(not visible)
        
        if is_collapsed:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
        if is_locked:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled & ~Qt.ItemFlag.ItemIsSelectable)
            item.setToolTip(lock_tooltip)
        elif tooltip:
            item.setToolTip(tooltip)
        self.sidebar_nav.addItem(item)

        if self.sidebar_nav.currentRow() < 0 and not item.isHidden() and bool(item.flags() & Qt.ItemFlag.ItemIsEnabled):
            self.sidebar_nav.setCurrentRow(self.sidebar_nav.count() - 1)
        
        logging.info(f"[OK] Factory registered: {label}")
        return True

    
    def get_or_create_tab(self, index):
        """
        Lazily create tab when first accessed (Improvement #4).
        
        Args:
            index: Tab index (row number)
        
        Returns:
            QWidget or None: The tab widget
        """
        if index < 0 or index >= len(self.tab_labels):
            return None
        
        label = self.tab_labels[index]
        
        # Return cached if exists
        if label in self.tab_instances:
            logging.debug(f"[LAZY] Using cached tab: {label}")
            return self.tab_instances[label]
        
        # Create new instance
        if label not in self.tab_factories:
            logging.error(f"[LAZY] No factory for tab: {label}")
            return None
        
        factory_info = self.tab_factories[label]
        if factory_info.get("locked"):
            return None

        try:
            logging.info(f"[LAZY] Creating tab: {label}")
            factory = factory_info.get('factory')
            if factory is None:
                logging.error(f"[LAZY] Missing factory for tab: {label}")
                return None
            widget = factory()
            
            if widget:
                self.tab_instances[label] = widget
                self.content_stack.addWidget(widget)
                
                # Also add to nav_items for compatibility
                item = self.sidebar_nav.item(index)
                if item:
                    self.nav_items.append({
                        'page': widget,
                        'item': item,
                        'label': label,
                        'permission': factory_info['permission']
                    })
                
                logging.info(f"[OK] Tab created: {label}")
                return widget
            else:
                logging.error(f"[LAZY] Factory returned None for: {label}")
                return None
                
        except Exception as e:
            logging.exception(f"[LAZY] Failed to create tab '{label}': {e}", exc_info=True)
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self.parent,
                "Tab Load Error",
                f"Failed to load tab '{label}'.\n\nError: {str(e)}\n\nPlease check logs."
            )
            return None
    
    def _on_nav_changed(self, row):
        """Handle sidebar navigation change with lazy loading and fade-in."""
        if row < 0:
            return

        is_first_load = (
            row < len(self.tab_labels)
            and self.tab_labels[row] not in self.tab_instances
        )

        # Lazy load tab on demand.
        widget = self.get_or_create_tab(row)

        # Fallback for eagerly-registered/plugin tabs that are already attached.
        if not widget:
            item = self.sidebar_nav.item(row)
            for entry in self.nav_items:
                if entry.get("item") is item:
                    widget = entry.get("page")
                    break
            if not widget and 0 <= row < self.content_stack.count():
                widget = self.content_stack.widget(row)

        if not widget:
            return

        self.content_stack.setCurrentWidget(widget)

        # UX Polish: Force layout calculation to prevent "broken layout on first load" bugs.
        # PySide6 sometimes delays layout math for complex widgets added to a QStackedWidget 
        # until the user resizes the window. We explicitly force it here.
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QResizeEvent
        from PySide6.QtCore import QCoreApplication
        
        QApplication.processEvents()
        if is_first_load:
            widget.updateGeometry()
            if widget.layout():
                widget.layout().activate()
            # Post a synthetic resize event to force deep child layout recalculations
            resize_event = QResizeEvent(widget.size(), widget.size())
            QCoreApplication.postEvent(widget, resize_event)

        # Emit signal with tab name.
        try:
            item = self.sidebar_nav.item(row)
            if item:
                self.tab_switched.emit(item.text())
        except Exception as exc:
            logging.debug("Tab switch signal emit failed: %s", exc)

    
    def get_tab_count(self):
        """Return total number of registered tabs."""
        # Sidebar count includes lazy tabs (not yet created), eagerly created tabs,
        # and dynamically loaded plugins.
        return self.sidebar_nav.count()
    
    def get_visible_tab_count(self):
        """Return number of visible tabs."""
        return sum(1 for entry in self.nav_items if not entry['item'].isHidden())
