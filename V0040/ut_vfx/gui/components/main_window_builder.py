import os
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QSplitter, QStackedWidget, QListWidget, QSystemTrayIcon, QMenu, QStatusBar
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont, QColor


class MainWindowBuilderMixin:
    """
    Mixin for VFXFolderCreatorApp that handles the initial UI construction.
    """

    def init_ui(self):
            """Initialize the user interface components."""
            from ... import __version__ as APP_VERSION
            from .tab_coordinator import TabCoordinator
            from ..tabs.home_tab import HomeTab
            from ..tabs.folder_creator_tab import FolderCreatorTab
            from ..tabs.smart_move_scan_tab import SmartMoveScanTab
            from ..cap_rename_tab import CapRenameTab 
            from ..tabs.stock_browser_tab import StockBrowserTab
            from ..tabs.vfx_review_dual_mode_tab import VFXReviewDualModeTab
            from ..tabs.vfx_dashboard_pro.ui.dashboard_widget import DashboardWidget
            from ..tabs.settings_tab import SettingsTab
            from ..admin_panel import AdminPanelTab
            from ..tester_panel import TesterPanel
            from ..attendance_tab import AttendanceTab
            from ..tabs.incoming_delivery_tab import IncomingDeliveryTab

            central_widget = QWidget()
            self.setCentralWidget(central_widget)

            main_layout = QVBoxLayout(central_widget)
            main_layout.setContentsMargins(15, 15, 15, 2)  # Minimal bottom margin for max editor space
            main_layout.setSpacing(15)

            # A. Toolbar Removed (Moved to Header)
            # self.create_toolbar()

            # B. Header
            self.header_widget = self.create_header()
            main_layout.addWidget(self.header_widget)

            # C. Main Content Area (Sidebar + Stack)
            content_container = QWidget()
            content_layout = QHBoxLayout(content_container)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(0)

            # 1. Sidebar (Left Rail) with Collapse Container
            self.sidebar_container = QWidget()
            self.sidebar_container.setObjectName("SidebarContainer")
            self.sidebar_container.setStyleSheet("background: transparent;")

            sidebar_layout = QVBoxLayout(self.sidebar_container)
            sidebar_layout.setContentsMargins(0, 0, 0, 0)
            sidebar_layout.setSpacing(0)

            self.sidebar_nav = QListWidget()
            self.sidebar_nav.setObjectName("MainSidebar")
            self.sidebar_nav.setFocusPolicy(Qt.NoFocus)
            self.sidebar_nav.setTextElideMode(Qt.TextElideMode.ElideNone)

            self.sidebar_toggle_btn = QPushButton("⮜")
            self.sidebar_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.sidebar_toggle_btn.setFixedHeight(40)
            self.sidebar_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #555;
                    border: none;
                    border-top: 1px solid #222;
                    font-size: 16px;
                    text-align: right;
                    padding-right: 20px;
                }
                QPushButton:hover {
                    color: #38BDF8;
                    background-color: rgba(56, 189, 248, 0.05);
                }
            """)
            self.sidebar_toggle_btn.clicked.connect(self.toggle_sidebar)

            sidebar_layout.addWidget(self.sidebar_nav)
            sidebar_layout.addWidget(self.sidebar_toggle_btn)

            # 2. Content Stack (Right Panel)
            self.content_stack = QStackedWidget()

            content_layout.addWidget(self.sidebar_container)
            content_layout.addWidget(self.content_stack)
            self.sidebar_collapsed = False

            main_layout.addWidget(content_container, 1)

            # Initialize Tab Coordinator (EXTRACTED COMPONENT)
            self.tab_coordinator = TabCoordinator(self, self.sidebar_nav, self.content_stack)
            self.tab_coordinator.tab_switched.connect(self._on_tab_switched)
            self.tab_coordinator.sidebar_collapsed = True

            # Make sidebar collapsed by default on startup without triggering animations yet
            self.sidebar_collapsed = True
            self.sidebar_container.setFixedWidth(64)

            self.sidebar_toggle_btn.setText("⮞")
            self.sidebar_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #555;
                    border: none;
                    border-top: 1px solid #222;
                    font-size: 16px;
                    text-align: center;
                    padding: 0;
                }
                QPushButton:hover { color: #38BDF8; background-color: rgba(56, 189, 248, 0.05); }
            """)

            self.sidebar_nav.setStyleSheet("""
                QListWidget { background: transparent; border: none; outline: none; padding: 2px; }
                QListWidget::item { 
                    color: #E0E0E0;
                    padding: 12px 0px; 
                    border-radius: 6px;
                    margin: 2px 4px;
                    font-size: 32px;
                }
                QListWidget::item:hover {
                    background-color: rgba(255, 255, 255, 0.05);
                }
                QListWidget::item:selected {
                    background-color: rgba(0, 180, 216, 0.15);
                    color: #00B4D8;
                    border-left: 3px solid #00B4D8;
                    border-radius: 4px;
                }
            """)

            # === LAZY TAB LOADING (Improvement #4) ===
            # Register tab factories instead of creating instances
            # Tabs will be created on-demand when first accessed

            logging.info("[LAZY] Registering tab factories...")

            # Home Tab (Cinematic Hub)
            self.tab_coordinator.register_tab_factory(
                "Home",
                lambda: HomeTab(
                    user_data=self.user_data,
                    app_context=self.app_context,
                    main_window=self
                ),
                icon="🏠",
                permission_key=None,  # Always allowed
                user_role=self.user_role,
                allowed_tabs=self.allowed_tabs,
                tooltip="Cinematic Dashboard Hub & Quick Actions"
            )

            def create_folder_creator():
                tab = FolderCreatorTab(self.config_manager)
                if hasattr(tab, "template_changed"):
                    tab.template_changed.connect(lambda *_: self.on_templates_refreshed())
                return tab

            # Folder Creator
            self.tab_coordinator.register_tab_factory(
                "Folder Creator",
                create_folder_creator,
                icon="📁",
                permission_key="Folder Creator",
                user_role=self.user_role,
                allowed_tabs=self.allowed_tabs
            ,
                tooltip="Build VFX project structures from Excel templates or Auto-Scan mode"
            )

            # Scan Manager
            self.tab_coordinator.register_tab_factory(
                "Scan Manager",
                lambda: SmartMoveScanTab(self.config_manager),
                icon="🚀",
                permission_key="Move/Scan",
                user_role=self.user_role,
                allowed_tabs=self.allowed_tabs
            ,
                tooltip="Move and ingest media using Smart Scan intelligence with Excel mapping"
            )


            # CAP Rename
            self.tab_coordinator.register_tab_factory(
                "CAP Rename",
                lambda: CapRenameTab(self.config_manager),
                icon="🏷️",
                permission_key="Rename Tool",
                user_role=self.user_role,
                allowed_tabs=self.allowed_tabs
            ,
                tooltip="Batch-rename VFX deliverables using smart pattern matching"
            )

            # Stock Viewer
            self.tab_coordinator.register_tab_factory(
                "Stock Viewer",
                lambda: StockBrowserTab(
                    self.library_manager,
                    user_roles=self.user_roles,
                    user_role=self.user_role,
                ),
                icon="🎞️",
                permission_key="Stock Browser",
                user_role=self.user_role,
                allowed_tabs=self.allowed_tabs
            ,
                tooltip="Browse, preview and manage your stock asset library"
            )



            # Shot Review (VFX Supervisor Review Tool - Dual Mode)
            self.tab_coordinator.register_tab_factory(
                "Shot Review",
                lambda: VFXReviewDualModeTab(self.config_manager, self.user_data),
                icon="🎬",
                permission_key="Shot Review",
                user_role=self.user_role,
                allowed_tabs=self.allowed_tabs
            ,
                tooltip="VFX Supervisor review tool - dual-mode comparison and annotation"
            )

            # VFX Dashboard Pro
            self.tab_coordinator.register_tab_factory(
                "VFX Dashboard",
                lambda: DashboardWidget(
                    user_data={**(self.user_data or {}), "inherit_app_theme": True},
                    user_manager=self.app_context.user_manager(),
                    app_context=self.app_context,
                ),
                icon="📊",
                permission_key="Dashboard",
                user_role=self.user_role,
                allowed_tabs=self.allowed_tabs
            ,
                tooltip="Live project dashboard with shot tracking and production metrics"
            )



            # Settings
            def create_settings():
                settings = SettingsTab(self.config_manager)
                settings.templates_refresh_requested.connect(self.on_templates_refreshed)
                settings.global_settings_updated.connect(self.on_global_settings_updated)
                return settings

            self.tab_coordinator.register_tab_factory(
                "Settings",
                create_settings,
                icon="⚙️",
                permission_key="Settings",
                user_role=self.user_role,
                allowed_tabs=self.allowed_tabs
            ,
                tooltip="Configure application paths, templates and global preferences"
            )

            # Admin Panel
            self.tab_coordinator.register_tab_factory(
                "Admin Panel",
                lambda: (
                    self._build_sync_disabled_tab(
                        "Admin Panel Unavailable",
                        "Admin fleet monitoring and remote controls are unavailable in LOCAL MODE.",
                    )
                    if self._is_sqlite_fallback_mode()
                    else AdminPanelTab(
                        current_username=(self.user_data or {}).get(
                            "user_id",
                            (self.user_data or {}).get("username", "Unknown"),
                        ),
                        app_context=self.app_context,
                    )
                ),
                icon="🛡️",
                permission_key="Admin Panel",
                user_role=self.user_role,
                allowed_tabs=self.allowed_tabs
            ,
                tooltip=(
                    "User management, live workstation monitoring and fleet reports"
                    if not self._is_sqlite_fallback_mode()
                    else "Unavailable in LOCAL MODE (requires central PostgreSQL)."
                )
            )

            # Tester Panel
            self.tab_coordinator.register_tab_factory(
                "Tester Panel",
                lambda: TesterPanel(
                    user_manager=self.app_context.user_manager(),
                    app_context=self.app_context,
                ),
                icon="🧪",
                permission_key="Tester Panel",
                user_role=self.user_role,
                allowed_tabs=self.allowed_tabs
            ,
                tooltip="Generate test data and validate workflows - developer/QA tool"
            )



            # Attendance
            self.tab_coordinator.register_tab_factory(
                "Attendance",
                lambda: AttendanceTab(
                    self.user_data,
                    attendance=self.app_context.attendance(),
                    user_manager=self.app_context.user_manager(),
                    app_context=self.app_context,
                    sync_enabled=not self._is_sqlite_fallback_mode(),
                ),
                icon="⏱️",
                user_role=self.user_role,
                allowed_tabs=self.allowed_tabs
            ,
                tooltip=(
                    "Track team attendance, hours and export timesheets"
                    if not self._is_sqlite_fallback_mode()
                    else "LOCAL MODE. Team sync/export actions are limited."
                )
            )

            # Incoming Delivery (Final - Smart Ingest) - hidden by default.
            # Shown only when Workflow Mode 2 is selected via WorkflowManager.
            self.tab_coordinator.register_tab_factory(
                "Incoming Delivery",
                lambda: IncomingDeliveryTab(self.config_manager),
                icon="\U0001F4E5",
                permission_key="Move/Scan",
                user_role=self.user_role,
                allowed_tabs=self.allowed_tabs,
                visible=False
            )


            # Store nav_items reference for backward compatibility
            self.nav_items = self.tab_coordinator.nav_items

            # --- DYNAMIC PLUGIN LOADER ---
            self.load_plugins()

            # Guarantee that all dynamically loaded tabs have their text stripped on boot
            if hasattr(self, 'tab_coordinator'):
                self.tab_coordinator.set_sidebar_collapsed(True)

            # main_layout.addWidget(self.tab_widget, 1) # Removed

            # D. Footer / Status Bar
            footer_widget = self.create_footer()
            main_layout.addWidget(footer_widget)

            self.status_bar = QStatusBar()
            self.setStatusBar(self.status_bar)
            self.status_bar.showMessage(f"Ready - UT_VFX Production v{APP_VERSION}", 5000)

            # E. Global Task Progress (Status Bar)
            try:
                from PySide6.QtWidgets import QProgressBar
                self.global_progress = QProgressBar()
                self.global_progress.setMaximumWidth(200)
                self.global_progress.setFixedHeight(14)
                self.global_progress.setTextVisible(False)
                self.global_progress.setVisible(False)
                self.status_bar.addPermanentWidget(self.global_progress)
                
                from .task_manager_dock import task_registry
                
                def update_global_progress(task_id):
                    # Find highest progress among running tasks, or just show active
                    active_tasks = [t for t in task_registry.get_all_tasks() if t.status.lower() in ("running", "pending", "paused")]
                    if not active_tasks:
                        self.global_progress.setVisible(False)
                        return
                    
                    self.global_progress.setVisible(True)
                    # Use the progress of the most recently updated active task
                    task = active_tasks[-1]
                    self.global_progress.setValue(task.progress)
                    self.global_progress.setToolTip(f"{task.name}: {task.progress}%")
                
                def on_task_added(task): update_global_progress(task.task_id)
                def on_task_removed(task_id): update_global_progress(task_id)
                def on_task_updated(task_id): update_global_progress(task_id)
                
                task_registry.task_added.connect(on_task_added)
                task_registry.task_removed.connect(on_task_removed)
                task_registry.task_updated.connect(on_task_updated)
                
            except Exception as e:
                logging.error(f"Failed to load Global Progress Bar: {e}")

    def create_toolbar(self):
            """Create application toolbar with workflow switching."""
            # --- ARTIST CHECK: HIDE TOOLBAR ---
            if self.user_role.lower() == "artist":  # Case-insensitive
                return

    def create_header(self):
            """
            Create the application header.

            DELEGATED to HeaderBuilder component for better maintainability.
            Kept as wrapper method for backward compatibility.
            """
            # Delegate to header builder component
            header_widget = self.header_builder.create_header()


            # Get mode selector and connect it to workflow change
            self.mode_selector = self.header_builder.get_mode_selector()
            if self.mode_selector:
                self.mode_selector.currentIndexChanged.connect(self.workflow_manager.change_workflow_mode)

            # Connect help button (stored in header_builder during creation)
            if hasattr(self.header_builder, 'help_button'):
                self.header_builder.help_button.clicked.connect(self.show_help_dialog)
            if hasattr(self.header_builder, 'logout_button') and self.header_builder.logout_button:
                self.header_builder.logout_button.clicked.connect(self.logout_user)
            if hasattr(self.header_builder, "health_label") and self.header_builder.health_label:
                try:
                    self.header_builder.health_label.clicked.connect(self.show_runtime_diagnostics)
                except Exception as exc:
                    logging.debug("Health label click bind skipped: %s", exc)

            return header_widget

    def create_footer(self):
            footer = QWidget()
            footer.setObjectName("footer")
            footer_layout = QVBoxLayout(footer)
            footer_layout.setContentsMargins(0, 0, 0, 0)
            team_layout = QHBoxLayout()
            team_layout.setContentsMargins(10, 2, 10, 5)

            team_label = QLabel("TEAM \u2764\uFE0F UT_VFX")
            team_label.setFont(QFont("Segoe UI", 8))
            team_label.setStyleSheet("color: #666;")

            license_label = QLabel("Copyright (c) 2026 Utkarsh Tripathi | Licensed under GPLv3")
            license_label.setFont(QFont("Segoe UI", 8))
            license_label.setStyleSheet("color: #666;")

            team_layout.addWidget(team_label)
            team_layout.addStretch()
            team_layout.addWidget(license_label)
            footer_layout.addLayout(team_layout)
            return footer

    def init_variables(self):
            # Initialize database connection asynchronously to avoid blocking UI
            try:
                from ut_vfx.core.infra.db_worker import run_db_async
                db = self.app_context.db_manager()
                if self._db_init_worker and hasattr(self._db_init_worker, "cancel"):
                    self._db_init_worker.cancel()
                    self._db_init_worker = None
                self._db_init_worker = run_db_async(
                    lambda: db.execute_query("SELECT 1"),
                    on_success=lambda r: logging.info("Database initialized successfully (async)"),
                    on_error=lambda e: logging.warning(f"Initial DB check failed (User might work offline): {e}"),
                    owner=self,
                )
            except Exception as e:
                logging.warning(f"DB init setup failed: {e}")

            self.is_processing = False
            self._omnibar_recent_entries = []
            self._omnibar_recent_shots = []
            self._load_omnibar_state()
