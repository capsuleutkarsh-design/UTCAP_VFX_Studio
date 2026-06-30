import ast
import json
import os


MAIN_NODE_TEMPLATES = [
    {"id": "gatekeeper", "label": "Gatekeeper", "group": "entry", "keywords": ["gatekeeper"]},
    {"id": "main_gui", "label": "Main Window", "group": "ui", "keywords": ["main_window", "tab_coordinator", "theme_manager", "header_builder", "qt_safety", "progress_manager"]},
    {"id": "dash_pro", "label": "Dashboard Pro", "group": "ui", "keywords": ["vfx_dashboard_pro", "dashboard_widget"]},
    {"id": "shot_review", "label": "Shot Review", "group": "ui", "keywords": ["shot_review", "comparison_viewer", "live_tech_check"]},
    {"id": "folder_creator", "label": "Folder Creator", "group": "ui", "keywords": ["folder_creator", "template_manager"]},
    {"id": "stock_browser", "label": "Stock Browser", "group": "ui", "keywords": ["stock_browser", "stock_model", "ingest_controller", "stock_"]},
    {"id": "move_scan", "label": "Move / Scan", "group": "ui", "keywords": ["move_scan", "incoming_delivery"]},
    {"id": "admin_panel", "label": "Admin Panel", "group": "ui", "keywords": ["admin_panel", "admin_widgets", "role_editor", "advanced_log_viewer", "admin_scripts", "admin_fleet", "admin_user_dialogs"]},
    {"id": "messenger", "label": "UT Messenger", "group": "messenger", "keywords": ["ut_messenger", "server/main.py", "client/gui.py"]},
    {"id": "editorial", "label": "Editorial Engine", "group": "core", "keywords": ["timeline_", "edl_exporter", "xml_exporter"]},
    {"id": "media_engine", "label": "Media Engine", "group": "core", "keywords": ["media_engines", "frame_cache", "image_loader", "video_player", "stream_engine"]},
    {"id": "sys_telemetry", "label": "Telemetry & Security", "group": "core", "keywords": ["telemetry", "audit_logger", "error_handler", "circuit_breaker", "performance_monitor"]},
    {"id": "plugins", "label": "Plugin System", "group": "core", "keywords": ["plugins/"]},
    {"id": "sweepers", "label": "Maintenance Sweepers", "group": "workers", "keywords": ["sweepers/", "sweeper_engine"]},
    {"id": "ui_widgets", "label": "UI Widgets", "group": "ui", "keywords": ["widgets/"]},
    {"id": "db_manager", "label": "Database Hub", "group": "db", "keywords": ["database_manager", "database/", "postgres_manager", "sqlite_manager", "db_worker", "db_table_"]},
    {"id": "attendance", "label": "Attendance", "group": "core", "keywords": ["attendance"]},
    {"id": "workers", "label": "Background Workers", "group": "workers", "keywords": ["workers", "asset_ingestor", "auto_pull_engine", "sequence_detector"]},
    {"id": "bridges", "label": "External Bridges", "group": "external", "keywords": ["olive_", "video_exporter", "proxy_manager", "ffmpeg"]},
    {"id": "core_infra", "label": "Core Infra", "group": "core", "keywords": ["core/infra", "library_manager", "user_manager", "server_hub", "project_manager", "metadata_engine"]},
    {"id": "updater", "label": "Auto Updater", "group": "core", "keywords": ["updater"]},
    {"id": "capsule_console", "label": "Capsule Console", "group": "tools", "keywords": ["capsule_console", "build_pipeline", "release_publisher", "test_runner"]},
    {"id": "tools_scripts", "label": "Misc Scripts", "group": "tools", "keywords": ["scripts/", "tools/"]},
    {"id": "logic_core", "label": "Logic Core", "group": "tools", "keywords": []},
]

SUBNODE_TEMPLATES = {
    "tools_scripts": [
        {"id": "ts_debug", "label": "Dev Debug", "group": "sub_tools", "keywords": ["dev_debug/", "verify_db.py", "read_log.py"]},
        {"id": "ts_patches", "label": "Dev Patches", "group": "sub_tools", "keywords": ["dev_patches/"]},
        {"id": "ts_launchers", "label": "Launchers", "group": "sub_tools", "keywords": ["launchers/"]},
        {"id": "ts_tools", "label": "Tooling Scripts", "group": "sub_tools", "keywords": ["tools/"]},
        {"id": "ts_misc", "label": "General Scripts", "group": "sub_tools", "keywords": ["scripts/"]},
    ],
    "capsule_console": [
        {"id": "cap_build", "label": "Build & Release", "group": "sub_ui", "keywords": ["build_pipeline.py", "release_publisher.py", "bump_version.py"]},
        {"id": "cap_test", "label": "Test Runner", "group": "sub_ui", "keywords": ["test_runner", "test_runner_gui.py"]},
        {"id": "cap_runtime", "label": "Console Runtime", "group": "sub_core", "keywords": ["capsule_console/main.py", "build_tab.py", "test_tab.py", "process_runner.py"]},
    ],
    "admin_panel": [
        {"id": "adm_live", "label": "Live Dash", "group": "sub_ui", "keywords": ["admin_widgets.py", "admin_panel.py"]},
        {"id": "adm_logs", "label": "Audit Logs", "group": "sub_ui", "keywords": ["advanced_log_viewer.py"]},
        {"id": "adm_roles", "label": "Roles & Users", "group": "sub_ui", "keywords": ["role_editor.py", "admin_user_dialogs.py"]},
        {"id": "adm_fleet", "label": "Fleet Report", "group": "sub_workers", "keywords": ["admin_fleet_report_service.py", "admin_fleet_export.py"]},
        {"id": "adm_diag", "label": "Diagnostics", "group": "sub_core", "keywords": ["checkup.py", "crash_diagnostics.py", "pg_config_tool.py"]},
    ],
    "db_manager": [
        {"id": "db_postgres", "label": "Postgres", "group": "sub_db", "keywords": ["postgres_manager.py"]},
        {"id": "db_sqlite", "label": "SQLite", "group": "sub_db", "keywords": ["sqlite_manager.py", "sqlite_handler.py"]},
        {"id": "db_worker", "label": "Async Worker", "group": "sub_workers", "keywords": ["db_worker.py"]},
        {"id": "db_sync", "label": "Consistency", "group": "sub_core", "keywords": ["consistency_protocol.py"]},
        {"id": "db_ops", "label": "DB Scripts & Tables", "group": "sub_core", "keywords": ["db_table_", "apply_indexes.py", "apply_indexes_fast.py", "check_if_working.py", "check_index_status.py", "direct_check.py", "emergency_check.py", "database_manager.py"]},
    ],
    "media_engine": [
        {"id": "me_stream", "label": "Stream", "group": "sub_core", "keywords": ["stream_engine.py"]},
        {"id": "me_seq", "label": "Sequence", "group": "sub_core", "keywords": ["sequence_engine.py", "image_engine.py"]},
        {"id": "me_cache", "label": "RAM Cache", "group": "sub_workers", "keywords": ["frame_cache.py", "async_image_loader.py", "image_loader.py", "base_engine.py"]},
    ],
    "dash_pro": [
        {"id": "dash_kanban", "label": "Kanban", "group": "sub_ui", "keywords": ["kanban_board.py"]},
        {"id": "dash_excel", "label": "Excel", "group": "sub_core", "keywords": ["excel_handler.py", "sqlite_handler.py", "migrate_excel_to_db.py", "history.py"]},
        {"id": "dash_sheets", "label": "Sheets Sync", "group": "sub_external", "keywords": ["sheets_sync.py"]},
        {"id": "dash_sync_svc", "label": "Sync Service", "group": "sub_core", "keywords": ["dashboard_sync_service.py", "project_manager.py", "poll_worker.py", "file_lock.py"]},
        {"id": "dash_ui", "label": "Dashboard UI", "group": "sub_ui", "keywords": ["dashboard_widget.py", "dashboard_layout_builder.py", "stats_widget.py", "shot_detail.py", "add_project_dialog.py", "edit_project_dialog.py", "login_dialog.py", "history_dialog.py", "concept_layout.py", "dashboard_avatar_service.py", "sync_dialog.py"]},
        {"id": "dash_models", "label": "Dashboard Models", "group": "sub_core", "keywords": ["project_model.py", "shot_model.py", "shot_table_model.py", "delegates.py", "header_filter_view.py", "qss_generator.py", "thumbnail.py", "__init__.py"]},
    ],
    "shot_review": [
        {"id": "sr_compare", "label": "Viewer", "group": "sub_ui", "keywords": ["comparison_viewer.py", "image_viewer.py", "annotation_overlay.py", "timeline_graphics.py", "video_player_widget.py"]},
        {"id": "sr_tech", "label": "Tech Check", "group": "sub_ui", "keywords": ["live_tech_check.py", "continuity_checker.py", "tech_check_dialog.py", "render_selector_dialog.py"]},
        {"id": "sr_olive", "label": "Olive XML", "group": "sub_external", "keywords": ["olive_bridge.py"]},
        {"id": "sr_ffmpeg", "label": "FFmpeg", "group": "sub_workers", "keywords": ["video_exporter.py"]},
        {"id": "sr_orch", "label": "Review Orchestration", "group": "sub_core", "keywords": ["shot_review_batch_service.py", "shot_review_layout_builder.py", "shot_review_project_service.py", "shot_review_tab.py", "workers.py", "export_dialog.py", "lineup_editor_mode.py", "__init__.py"]},
    ],
    "messenger": [
        {"id": "msg_client", "label": "Client GUI", "group": "sub_ui", "keywords": ["client/gui.py", "client/components.py", "client/dialogs.py", "chat_panel.py", "contacts_panel.py", "home_panel.py", "sidebar_panel.py", "app_controller.py", "api_client.py", "theme.py", "state.py", "models.py", "launcher.py", "logic.py", "workers.py", "utils.py", "gui.py"]},
        {"id": "msg_server", "label": "WS Server", "group": "sub_core", "keywords": ["server/main.py", "server/websockets_manager.py", "server/endpoints.py", "server/v2_endpoints.py", "server/security.py", "server/telemetry.py", "run_chat_server.py", "schemas.py"]},
        {"id": "msg_db", "label": "V2 Store", "group": "sub_db", "keywords": ["server/v2_store.py", "server/database.py", "database.py"]},
        {"id": "msg_runtime", "label": "Runtime & Entry", "group": "sub_core", "keywords": ["__main__.py", "scratch_script.py", "update_theme_script.py", "__init__.py"]},
    ],
    "ui_widgets": [
        {"id": "wid_speed", "label": "Speed Indicators", "group": "sub_ui", "keywords": ["db_speed_indicator"]},
        {"id": "wid_nuke", "label": "Nuke Slider", "group": "sub_ui", "keywords": ["nuke_slider.py"]},
        {"id": "wid_buttons", "label": "UI Buttons", "group": "sub_ui", "keywords": ["styled_buttons.py", "py_toggle.py"]},
        {"id": "wid_misc", "label": "Widget Toolkit", "group": "sub_ui", "keywords": ["advanced_player.py", "quick_look.py", "tag_edit_dialog.py", "users_list_widget.py", "kanban_board.py", "__init__.py"]},
    ],
    "sweepers": [
        {"id": "swp_proxy", "label": "Proxy Sweep", "group": "sub_workers", "keywords": ["proxy_sweeper.py", "sweeper_engine.py"]},
        {"id": "swp_temp", "label": "Temp Sweep", "group": "sub_workers", "keywords": ["temp_sweeper.py"]},
    ],
    "main_gui": [
        {"id": "mg_core", "label": "Main UI Core", "group": "sub_ui", "keywords": ["main_window.py", "theme_manager.py", "header_builder.py", "progress_manager.py", "qt_safety.py", "tab_coordinator.py", "_fix_main_window.py"]},
    ],
    "core_infra": [
        {"id": "infra_users", "label": "User & Project Infra", "group": "sub_core", "keywords": ["user_manager.py", "project_repository.py", "library_manager.py", "metadata_engine.py"]},
        {"id": "infra_config", "label": "Config & Style Infra", "group": "sub_core", "keywords": ["config_manager.py", "global_config.py", "performance_config.py", "design_tokens.py", "style_builder.py"]},
        {"id": "infra_runtime", "label": "Runtime Infra", "group": "sub_core", "keywords": ["server_hub.py", "network_manager.py", "retry_strategy.py", "file_operations.py", "shared_json_write_coordinator.py", "app_context.py"]},
        {"id": "infra_logging", "label": "Logging & Health", "group": "sub_core", "keywords": ["central_logger.py", "logging_config.py", "logging_utils.py", "idle_monitor.py", "consistency_protocol.py", "__init__.py"]},
    ],
    "workers": [
        {"id": "wrk_ingest", "label": "Ingest Workers", "group": "sub_workers", "keywords": ["asset_ingestor.py", "analysis.py", "library.py", "reporting.py", "structure.py", "validation_service.py", "adaptation_engine.py"]},
        {"id": "wrk_pull", "label": "Auto Pull Workers", "group": "sub_workers", "keywords": ["auto_pull_engine.py", "auto_pull_worker.py", "smart_scan_worker.py", "beta_smart_worker.py"]},
        {"id": "wrk_io", "label": "IO Workers", "group": "sub_workers", "keywords": ["file_io.py", "file_ops.py", "excel_loader.py", "db_monitor.py", "admin_workers.py"]},
        {"id": "wrk_seq", "label": "Sequence Workers", "group": "sub_workers", "keywords": ["sequence_detector.py", "sequence.py", "__init__.py"]},
    ],
    "stock_browser": [
        {"id": "sb_data", "label": "Stock Data", "group": "sub_core", "keywords": ["stock_repository.py", "stock_model.py", "migrate_stock_data.py", "debug_stock_db.py", "check_stock_count.py", "db_table_stock_library"]},
        {"id": "sb_ui", "label": "Stock UI", "group": "sub_ui", "keywords": ["stock_browser_tab.py", "ingest_controller.py", "widgets.py", "gallery.py", "inspector.py", "sidebar.py", "__init__.py"]},
    ],
    "attendance": [
        {"id": "att_core", "label": "Attendance Core", "group": "sub_core", "keywords": ["attendance_manager.py", "central_attendance.py", "attendance_cleanup.py"]},
        {"id": "att_ui", "label": "Attendance UI", "group": "sub_ui", "keywords": ["attendance_tab.py", "attendance_metrics.py", "attendance_export_worker.py"]},
    ],
    "logic_core": [
        {"id": "lc_shell", "label": "App Shell", "group": "sub_core", "keywords": ["launcher.py", "help_content.py", "debug_hw.py", "__init__.py", "startup_manager.py", "single_instance.py", "refactor_styles.py", "worker_threads.py", "hardware_info.py"]},
        {"id": "lc_review", "label": "Review Logic", "group": "sub_core", "keywords": ["continuity_checker.py", "dashboard_sync.py", "enhanced_notes.py", "live_reporter.py", "notification_manager.py", "review_shot.py"]},
        {"id": "lc_utils", "label": "Core Utilities", "group": "sub_core", "keywords": ["asset_tracker.py", "backup_recovery.py", "resource_manager.py", "safe_json.py", "security.py", "text_utils.py", "validators.py", "media_capabilities.py", "sequence_utils.py", "analyzer.py", "reporter.py", "sequence.py", "validation_service.py", "adaptation_engine.py", "reporting.py"]},
        {"id": "lc_gui", "label": "GUI Utility Logic", "group": "sub_ui", "keywords": ["database_explorer.py", "help_dialog.py", "login_dialog.py", "notification_overlay.py", "tester_panel.py", "cap_rename_tab.py", "vfx_review_dual_mode_tab.py", "dashboard_tab.py", "settings_tab.py", "custom_template_dialog.py", "update_available_dialog.py", "visual_diff_dialog.py", "network_handler.py", "progress_overlay.py", "queued_worker_controller.py", "web_bridge.py", "workflow_manager.py"]},
    ],
    "gatekeeper": [
        {"id": "gk_entry", "label": "Gatekeeper Runtime", "group": "sub_core", "keywords": ["gatekeeper_main.py", "gatekeeper_window.py", "fix_gatekeeper.py"]},
    ],
    "folder_creator": [
        {"id": "fc_templates", "label": "Template Flow", "group": "sub_core", "keywords": ["template_manager.py", "path_template_manager.py", "folder_creator_tab.py"]},
    ],
    "move_scan": [
        {"id": "ms_flow", "label": "Move/Scan Flow", "group": "sub_core", "keywords": ["move_scan_tab.py", "incoming_delivery_tab.py", "smart_move_scan_tab.py"]},
    ],
    "editorial": [
        {"id": "ed_timeline", "label": "Timeline Core", "group": "sub_core", "keywords": ["timeline_manager.py", "timeline_model.py"]},
        {"id": "ed_export", "label": "Editorial Exports", "group": "sub_external", "keywords": ["edl_exporter.py", "xml_exporter.py"]},
    ],
    "bridges": [
        {"id": "br_olive", "label": "Olive Bridge", "group": "sub_external", "keywords": ["olive_wrapper.py", "olive_bridge.py"]},
        {"id": "br_media", "label": "Media Bridge", "group": "sub_external", "keywords": ["video_exporter.py", "ffmpeg"]},
        {"id": "br_proxy", "label": "Proxy Bridge", "group": "sub_external", "keywords": ["proxy_manager.py"]},
    ],
    "sys_telemetry": [
        {"id": "tel_runtime", "label": "Telemetry Runtime", "group": "sub_core", "keywords": ["telemetry_report.py", "telemetry.py", "performance_monitor.py"]},
        {"id": "tel_security", "label": "Security & Audit", "group": "sub_core", "keywords": ["audit_logger.py", "error_handler.py", "circuit_breaker.py"]},
    ],
    "plugins": [
        {"id": "pl_runtime", "label": "Plugin Runtime", "group": "sub_core", "keywords": ["plugin_interface.py", "workspace_info_plugin.py", "validate_naming.py", "__init__.py"]},
    ],
    "updater": [
        {"id": "up_core", "label": "Updater Core", "group": "sub_core", "keywords": ["sidecar_engine.py", "updater_script.py", "update_checker.py", "__init__.py"]},
    ],
}


def _new_info():
    return {
        "filepath": "",
        "doc": "",
        "files": [],
        "classes": [],
        "funcs": [],
        "used_by": [],
        "feeds_to": [],
        "complexity": 0,
        "churn": 0,
        "circular_count": 0,
        "orphan_count": 0,
        "entry_count": 0,
        "risk_score": 0,
        "lint_count": 0,
        "coverage_sum": 0.0,
        "clones": 0,
        "coverage": 0.0,
        "todos": [],
        "sql_tables": [],
    }


def _as_bool(raw):
    return str(raw).strip().lower() == "true"


def _dedupe_keep_order(items):
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _dedupe_node_refs(items):
    """Dedupe a list of {label, group} dicts by label."""
    seen = set()
    out = []
    for item in items:
        key = item["label"] if isinstance(item, dict) else item
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _make_node(template, is_main=False, parent=None):
    return {
        "id": template["id"],
        "label": template["label"],
        "group": template["group"],
        "keywords": [k.lower() for k in template.get("keywords", [])],
        "is_main": is_main,
        "parent": parent,
        "info": _new_info(),
    }


def _parse_context_md(md_filepath):
    file_data = {}
    current = None

    with open(md_filepath, "r", encoding="utf-8") as handle:
        lines = handle.readlines()

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("## `"):
            current = line.replace("## `", "", 1).replace("`", "").strip()
            file_data[current] = {
                "id": current,
                "label": os.path.basename(current),
                "filepath": "",
                "doc": "",
                "complexity": 0,
                "is_orphan": False,
                "is_entry": False,
                "is_circular": False,
                "churn": 0,
                "true_deps": [],
                "classes": [],
                "funcs": [],
                "lint_count": 0,
                "coverage": 0.0,
                "clones": 0,
                "todos": [],
                "sql_tables": [],
            }
            continue

        if not current:
            continue

        node = file_data[current]
        if line.startswith("FilePath:"):
            node["filepath"] = line.split("FilePath:", 1)[1].strip()
        elif line.startswith("ModDoc:"):
            raw_doc = line.split("ModDoc:", 1)[1].strip()
            try:
                node["doc"] += ast.literal_eval(raw_doc)
            except Exception:
                node["doc"] += raw_doc
        elif line.startswith("Complexity:"):
            try:
                node["complexity"] = int(line.split(":", 1)[1].strip())
            except Exception:
                node["complexity"] = 0
        elif line.startswith("IsOrphan:"):
            node["is_orphan"] = _as_bool(line.split(":", 1)[1])
        elif line.startswith("IsEntry:"):
            node["is_entry"] = _as_bool(line.split(":", 1)[1])
        elif line.startswith("IsCircular:"):
            node["is_circular"] = _as_bool(line.split(":", 1)[1])
        elif line.startswith("ChurnCount:"):
            try:
                node["churn"] = int(line.split(":", 1)[1].strip())
            except Exception:
                node["churn"] = 0
        elif line.startswith("LintCount:"):
            try:
                node["lint_count"] = int(line.split(":", 1)[1].strip())
            except Exception:
                node["lint_count"] = 0
        elif line.startswith("Coverage:"):
            try:
                node["coverage"] = float(line.split(":", 1)[1].strip())
            except Exception:
                node["coverage"] = 0.0
        elif line.startswith("Clones:"):
            try:
                node["clones"] = int(line.split(":", 1)[1].strip())
            except Exception:
                node["clones"] = 0
        elif line.startswith("Todos:"):
            try:
                node["todos"] = json.loads(line.split("Todos:", 1)[1].strip())
            except Exception:
                pass
        elif line.startswith("SqlTables:"):
            tables = line.split("SqlTables:", 1)[1].strip().split(",")
            node["sql_tables"] = [t.strip() for t in tables if t.strip()]
        elif line.startswith("TrueDeps: `"):
            dep_text = line.replace("TrueDeps: `", "", 1).replace("`", "").strip()
            node["true_deps"] = [d.strip() for d in dep_text.split(",") if d.strip()]
        elif line.startswith("Class `"):
            try:
                class_name = line.replace("Class `", "", 1).split("|||DOC|||", 1)[0].strip()
            except Exception:
                class_name = line
            node["classes"].append(class_name)
        elif line.startswith("Func `"):
            try:
                func_name = line.replace("Func `", "", 1).split("|||DOC|||", 1)[0].strip()
            except Exception:
                func_name = line
            node["funcs"].append(func_name)

    return file_data


def _resolve_parent(path_lower, main_nodes):
    for node in main_nodes:
        if any(keyword in path_lower for keyword in node.get("keywords", [])):
            return node["id"]
    return "logic_core"


def _resolve_subnode(path_lower, parent_id, sub_nodes_dict):
    for sub in sub_nodes_dict.get(parent_id, []):
        if any(keyword in path_lower for keyword in sub.get("keywords", [])):
            return sub["id"]
    return None


def _get_or_create_other_subnode(parent_id, sub_nodes_dict, all_nodes_map):
    sid = f"{parent_id}_other"
    if sid in all_nodes_map:
        return sid

    parent_group = all_nodes_map[parent_id]["group"]
    group = "sub_tools"
    if parent_group == "ui":
        group = "sub_ui"
    elif parent_group == "db":
        group = "sub_db"
    elif parent_group == "workers":
        group = "sub_workers"
    elif parent_group == "external":
        group = "sub_external"
    elif parent_group in {"core", "entry", "messenger"}:
        group = "sub_core"

    node = {
        "id": sid,
        "label": "Other Modules",
        "group": group,
        "keywords": [],
        "is_main": False,
        "parent": parent_id,
        "info": _new_info(),
    }
    sub_nodes_dict.setdefault(parent_id, []).append(node)
    all_nodes_map[sid] = node
    return sid


def _finalize_info(info):
    info["files"] = _dedupe_keep_order(info["files"])
    info["classes"] = _dedupe_keep_order(info["classes"])
    info["funcs"] = _dedupe_keep_order(info["funcs"])
    info["used_by"] = _dedupe_node_refs(info["used_by"])
    info["feeds_to"] = _dedupe_node_refs(info["feeds_to"])
    
    # Accurate orphan status for high-level main nodes
    info["orphan"] = (len(info["used_by"]) == 0) and (info.get("entry_count", 0) == 0)
    
    info["risk_score"] = round(
        (info["complexity"] / 220.0)
        + (info["churn"] * 3.5)
        + (info["circular_count"] * 20)
        + (info.get("orphan_count", 0) * 2.0),
        2,
    )


def _export_node(node):
    return {
        "id": node["id"],
        "label": node["label"],
        "group": node["group"],
        "is_main": node["is_main"],
        "parent": node["parent"],
        "info": node["info"],
    }


def generate_expanding_html_from_md(md_filepath, html_filepath):
    print("-> [2/2] Compiling V32 Dashboard Engine...")
    if not os.path.exists(md_filepath):
        print(f"   [!] Error: {md_filepath} not found.")
        return

    file_data = _parse_context_md(md_filepath)

    main_nodes = [_make_node(t, is_main=True) for t in MAIN_NODE_TEMPLATES]
    sub_nodes_dict = {node["id"]: [] for node in main_nodes}
    all_nodes_map = {node["id"]: node for node in main_nodes}

    for parent_id, templates in SUBNODE_TEMPLATES.items():
        if parent_id not in sub_nodes_dict:
            continue
        for template in templates:
            sub = _make_node(template, is_main=False, parent=parent_id)
            sub_nodes_dict[parent_id].append(sub)
            all_nodes_map[sub["id"]] = sub

    file_to_parent = {}
    file_to_node = {}

    for file_id, fdata in file_data.items():
        path_lower = file_id.lower().replace("\\", "/")
        parent_id = _resolve_parent(path_lower, main_nodes)
        child_id = _resolve_subnode(path_lower, parent_id, sub_nodes_dict)
        if child_id is None:
            child_id = _get_or_create_other_subnode(parent_id, sub_nodes_dict, all_nodes_map)

        file_to_parent[file_id] = parent_id
        file_to_node[file_id] = child_id

        child_node = all_nodes_map[child_id]
        parent_node = all_nodes_map[parent_id]

        for target_node in (child_node, parent_node):
            info = target_node["info"]
            # Keep relative paths for source viewer deep-linking.
            file_ref = file_id if file_id.lower().endswith(".py") else fdata["label"]
            info["files"].append(file_ref)
            info["classes"].extend(fdata["classes"])
            info["funcs"].extend(fdata["funcs"])
            info["complexity"] += fdata["complexity"]
            info["churn"] += fdata["churn"]
            info["lint_count"] += fdata["lint_count"]
            info["coverage_sum"] += fdata["coverage"]
            info["clones"] += fdata["clones"]
            info["todos"].extend(fdata.get("todos", []))
            for t in fdata.get("sql_tables", []):
                if t not in info["sql_tables"]:
                    info["sql_tables"].append(t)
            if fdata["is_orphan"]:
                info["orphan_count"] += 1
            if fdata["is_entry"]:
                info["entry_count"] += 1
            if fdata["is_circular"]:
                info["circular_count"] += 1
            if not info["filepath"] and fdata["filepath"]:
                info["filepath"] = fdata["filepath"]
            if fdata["doc"] and fdata["doc"] != "No module docstring provided." and not info["doc"]:
                info["doc"] = fdata["doc"]

    main_edges = set()
    trace_edges = set()

    for src_file, fdata in file_data.items():
        src_node_id = file_to_node.get(src_file)
        src_parent_id = file_to_parent.get(src_file)
        if not src_node_id or not src_parent_id:
            continue

        for dep in fdata.get("true_deps", []):
            if dep not in file_to_node:
                continue

            tgt_node_id = file_to_node[dep]
            tgt_parent_id = file_to_parent[dep]

            if src_node_id != tgt_node_id:
                trace_edges.add((src_node_id, tgt_node_id))
                src_n = all_nodes_map[src_node_id]
                tgt_n = all_nodes_map[tgt_node_id]
                tgt_n["info"]["used_by"].append({"label": src_n["label"], "group": src_n["group"]})
                src_n["info"]["feeds_to"].append({"label": tgt_n["label"], "group": tgt_n["group"]})

            if src_parent_id != tgt_parent_id:
                main_edges.add((src_parent_id, tgt_parent_id))
                src_p = all_nodes_map[src_parent_id]
                tgt_p = all_nodes_map[tgt_parent_id]
                tgt_p["info"]["used_by"].append({"label": src_p["label"], "group": src_p["group"]})
                src_p["info"]["feeds_to"].append({"label": tgt_p["label"], "group": tgt_p["group"]})

    # Build SQL Heatmap edges
    for src_file, fdata in file_data.items():
        src_parent_id = file_to_parent.get(src_file)
        if not src_parent_id: continue
        for table in fdata.get("sql_tables", []):
            tgt_parent_id = f"db_table_{table}"
            if tgt_parent_id in all_nodes_map:
                main_edges.add((src_parent_id, tgt_parent_id))
                src_p = all_nodes_map[src_parent_id]
                tgt_p = all_nodes_map[tgt_parent_id]
                tgt_p["info"]["used_by"].append({"label": src_p["label"], "group": src_p["group"]})
                src_p["info"]["feeds_to"].append({"label": tgt_p["label"], "group": tgt_p["group"]})

    for node in all_nodes_map.values():
        if node["info"]["files"]:
            node["info"]["coverage"] = node["info"]["coverage_sum"] / len(node["info"]["files"])
        _finalize_info(node["info"])

    filtered_sub_nodes = {}
    for parent_id, children in sub_nodes_dict.items():
        filtered_sub_nodes[parent_id] = [
            _export_node(child) for child in children if child["info"]["files"]
        ]

    exported_main_nodes = [_export_node(node) for node in main_nodes]
    exported_main_edges = [
        {"id": f"main_{src}_{dst}", "from": src, "to": dst}
        for src, dst in sorted(main_edges)
    ]
    exported_trace_edges = [
        {"id": f"dep_{src}_{dst}", "from": src, "to": dst}
        for src, dst in sorted(trace_edges)
    ]

    total_files = sum(len(f.get("files", [])) for f in all_nodes_map.values() if "info" in f)
    
    safe_data = {
        "main_nodes": exported_main_nodes,
        "main_edges": exported_main_edges,
        "sub_nodes_dict": filtered_sub_nodes,
        "trace_edges": exported_trace_edges,
        "total_files": total_files
    }
    json_payload = json.dumps(safe_data).replace("</", "<\\/")

    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UTCAP System Brain V32</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@300;400;600;800;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/vs2015.min.css">
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <style>
        :root {
            --bg-base: #060609;
            --bg-panel: rgba(10,12,18,0.7);
            --bg-surface: rgba(15,18,25,0.6);
            --border-subtle: rgba(255,255,255,0.06);
            --border-glow: rgba(0,243,255,0.3);
            --text-main: #f8fafc;
            --text-muted: #64748b;
            --text-dim: #94a3b8;
            --accent: #3b82f6;
            --accent-cyan: #00f3ff;
            --accent-purple: #a78bfa;
            --danger: #ff3366;
            --warning: #fbbf24;
            --success: #00ff66;
            --sidebar-w: 320px;
            --font-display: 'Inter', sans-serif;
            --font-ui: 'Inter', sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
            --text-2xs: 10px;
            --text-xs: 11px;
            --text-sm: 12px;
            --space-1: 6px;
            --space-2: 10px;
            --space-3: 14px;
            --space-4: 18px;
            --space-5: 24px;
        }
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        html, body { width: 100%; height: 100%; overflow: hidden; }
        body { 
            font-family: var(--font-ui); background: var(--bg-base); color: var(--text-main); display: flex; flex-direction: column;
            line-height: 1.35;
            background-image: 
                linear-gradient(rgba(0, 243, 255, 0.02) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 243, 255, 0.02) 1px, transparent 1px);
            background-size: 50px 50px;
        }

        #pcv { position: fixed; inset: 0; z-index: 0; pointer-events: none; }

        #hud {
            position: fixed; top: 0; left: 0; right: 0; height: 56px;
            background: rgba(5,7,16,0.88); backdrop-filter: blur(24px);
            border-bottom: 1px solid var(--border-subtle);
            display: flex; align-items: center; padding: 0 var(--space-4); gap: var(--space-3);
            z-index: 100;
        }
        .hud-brand { font-size: var(--text-xs); font-weight: 900; letter-spacing: 1.8px; white-space: nowrap; text-transform: uppercase; }
        .hud-brand span { background: linear-gradient(90deg,#3b82f6,#a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
        
        #breadcrumb { font-family: var(--font-mono); font-size: var(--text-2xs); color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
        #breadcrumb b { color: var(--accent-cyan); font-weight: 700; opacity: 0.8; }

        .hud-stats { display: flex; align-items: center; gap: 0; }
        .hud-stat { display: flex; flex-direction: column; align-items: center; padding: 0 11px; }
        .hud-val { font-family: var(--font-mono); font-size: 14px; font-weight: 700; color: var(--accent-cyan); line-height: 1; }
        .hud-lbl { font-size: 7px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1.2px; margin-top: 3px; }
        .hud-sep { width: 1px; height: 24px; background: var(--border-subtle); }

        .hud-ctrls { display: flex; gap: 8px; margin-left: 10px; }
        .hbtn { background: rgba(255,255,255,0.04); border: 1px solid var(--border-subtle); color: var(--text-dim); padding: 4px 10px; border-radius: 4px; font-size: 9px; font-weight: 700; cursor: pointer; transition: all 0.15s; }
        .hbtn:hover { background: rgba(59,130,246,0.15); border-color: var(--accent); color: #fff; }

        #layout { display: flex; flex: 1; margin-top: 56px; height: calc(100vh - 56px); position: relative; z-index: 1; }

        #sidebar {
            width: var(--sidebar-w); min-width: var(--sidebar-w);
            background: linear-gradient(180deg, rgba(10,12,18,0.9), rgba(10,12,18,0.78));
            border-right: 1px solid var(--border-subtle);
            display: flex; flex-direction: column; z-index: 10; overflow-y: auto;
            transition: transform 0.3s ease;
        }
        #sidebar.collapsed { transform: translateX(-100%); width: 0; min-width: 0; }
        #sbtoggle {
            position: absolute; top: 50%; left: var(--sidebar-w); transform: translateY(-50%);
            width: 16px; height: 50px; background: var(--bg-surface);
            border: 1px solid var(--border-subtle); border-left: none;
            color: var(--text-muted); cursor: pointer; font-size: 8px;
            display: flex; align-items: center; justify-content: center;
            z-index: 50; border-radius: 0 4px 4px 0; transition: left 0.3s ease;
        }
        #sidebar.collapsed + #sbtoggle { left: 0; }

        .dock-hdr { padding: var(--space-4); border-bottom: 1px solid var(--border-subtle); }
        .dock-hdr h1 {
            font-family: var(--font-display);
            font-size: 13px;
            font-weight: 900;
            letter-spacing: 1.3px;
            text-transform: uppercase;
        }
        .dock-sub { font-size: 8px; color: var(--text-muted); text-transform: uppercase; margin-top: var(--space-1); letter-spacing: 1.2px; }
        
        .dock-sec { padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--border-subtle); }
        .dock-sec--end { border-bottom: none; }
        .sec-ttl { font-size: 9px; font-weight: 800; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1.4px; margin-bottom: var(--space-2); }

        #searchBar {
            width: 100%; padding: 9px 11px; border: 1px solid var(--border-subtle);
            border-radius: 8px; background: rgba(0,0,0,0.3); color: var(--text-main); font-size: var(--text-xs); outline: none;
            transition: border-color 0.18s ease, box-shadow 0.18s ease;
        }
        #searchBar:focus { border-color: rgba(59,130,246,0.55); box-shadow: 0 0 0 3px rgba(59,130,246,0.12); }

        .btn-grp { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-1); }
        .btn-grp--stack { grid-template-columns: 1fr; }
        .btn {
            width: 100%; min-height: 34px; padding: 8px 11px; background: rgba(255,255,255,0.01);
            border: 1px solid var(--border-subtle); color: var(--text-dim);
            border-radius: 8px; cursor: pointer; font-size: var(--text-2xs); font-weight: 750;
            transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease, transform 0.1s ease;
            text-align: left; letter-spacing: 0.25px;
        }
        .btn:hover { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.18); color: #fff; }
        .btn:active { transform: translateY(1px); }
        .btn.active { background: rgba(59,130,246,0.15); border-color: var(--accent); color: #fff; box-shadow: 0 0 10px rgba(59,130,246,0.1); }
        .btn--row { display:flex; align-items:center; justify-content:space-between; }
        .btn__meta { font-family: var(--font-mono); font-size: 9px; letter-spacing: 0.3px; opacity: 0.9; }
        .btn--warn { color: var(--warning); border-color: rgba(245,158,11,0.45); }
        .btn--danger { color: var(--danger); border-color: rgba(239,68,68,0.45); }
        .ctrl-select {
            width:100%;
            min-height: 34px;
            padding: 8px 10px;
            background: rgba(255,255,255,0.02);
            color: var(--text-dim);
            border:1px solid var(--border-subtle);
            border-radius:8px;
            font-size: var(--text-2xs);
            font-weight:750;
            outline:none;
            font-family:var(--font-ui);
            cursor:pointer;
        }
        .ctrl-select:focus { border-color: rgba(59,130,246,0.55); box-shadow: 0 0 0 3px rgba(59,130,246,0.12); }
        .hint { font-size: 8px; color: var(--text-muted); margin-top: var(--space-1); line-height: 1.45; }

        .f-chips { display: flex; flex-wrap: wrap; gap: 4px; }
        .f-chip { padding: 3px 8px; border-radius: 12px; font-size: 8px; font-weight: 800; border: 1px solid var(--border-subtle); cursor: pointer; transition: all 0.15s; opacity: 0.6; }
        .f-chip:hover { opacity: 1; }
        .f-chip.active { opacity: 1; box-shadow: 0 0 8px currentColor; }

        .legend-list { display: flex; flex-direction: column; gap: 5px; }
        .lg-item { display: flex; align-items: center; gap: 8px; font-size: 9px; color: var(--text-dim); }
        .lg-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
        .lg-bar { width: 12px; height: 4px; border-radius: 2px; flex-shrink: 0; }

        #netbox { flex-grow: 1; position: relative; }
        #netmap { width: 100%; height: 100%; outline: none; }

        #inspector {
            position: fixed; top: 0; right: -420px; width: 400px;
            height: 100vh; background: var(--bg-panel);
            backdrop-filter: blur(40px) saturate(150%); border-left: 1px solid var(--border-subtle);
            transition: right 0.35s cubic-bezier(0.2, 0.8, 0.2, 1);
            z-index: 200; display: flex; flex-direction: column;
        }
        #inspector.open { right: 0; }
        /* Inspector styles same as before... */
        .ins-hdr { padding: var(--space-4); border-bottom: 1px solid var(--border-subtle); flex-shrink: 0; position: relative; }
        .ins-close { position: absolute; right: 15px; top: 15px; cursor: pointer; color: var(--text-muted); background: none; border: none; font-size: 18px; }
        .ins-title { font-family: var(--font-display); font-size: 18px; font-weight: 850; margin-bottom: 8px; letter-spacing: 0.2px; }
        .ins-path-wrap { display:flex; align-items:flex-start; gap:var(--space-1); margin-bottom:var(--space-3); }
        #i_path { font-family:var(--font-mono); font-size:10px; color:var(--text-muted); word-break:break-all; flex:1; }
        .copy-btn { background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.16); color:#fff; cursor:pointer; padding:6px 9px; font-size:10px; border-radius:8px; font-family:var(--font-ui); white-space:nowrap; font-weight: 700; }
        .copy-btn:hover { background:rgba(59,130,246,0.2); border-color:var(--accent); }

        .flow-head { display:flex; justify-content:space-between; margin-bottom:8px; align-items:center; }
        .metric-chip { color:#061016; font-size:10px; font-weight:800; opacity:0.95; }
        .metric-chip--out { background: var(--accent-cyan); }
        .metric-chip--in { background: var(--accent-purple); }
        .tag { background: rgba(255,255,255,0.05); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 3px 8px; font-size: 10px; font-family: var(--font-mono); color: var(--text-dim); cursor: pointer; transition: all 0.15s; margin-right: 4px; margin-bottom: 4px; display: inline-block; }
        .tag:hover { background: rgba(59,130,246,0.15); border-color: var(--accent); color: #fff; }
        .ins-body { padding: var(--space-4); overflow-y: auto; flex-grow: 1; }
        .doc-box { background: rgba(0,0,0,0.2); border: 1px solid var(--border-subtle); padding: 11px 12px; border-radius: 8px; font-size: var(--text-xs); color: var(--text-dim); margin-bottom: var(--space-3); white-space: pre-wrap; line-height: 1.55; }
        .cpx-bar { margin-bottom: var(--space-3); }
        .cpx-hdr { display: flex; justify-content: space-between; font-size: 9px; font-weight: 700; color: var(--text-muted); margin-bottom: 6px; letter-spacing: 0.5px; text-transform: uppercase; }
        .cpx-track { height: 5px; background: rgba(255,255,255,0.06); border-radius: 3px; overflow: hidden; }
        .cpx-fill { height: 100%; border-radius: 3px; background: linear-gradient(90deg,var(--accent),var(--accent-purple)); transition: width 0.8s; }
        details { background: rgba(0,0,0,0.15); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 8px 10px; margin-bottom: var(--space-2); }
        summary { font-size: var(--text-2xs); font-weight: 800; color: var(--text-dim); cursor: pointer; list-style: none; display: flex; justify-content: space-between; letter-spacing: 0.35px; text-transform: uppercase; }
        summary::after { content: '+'; color: var(--text-muted); }
        details[open] summary::after { content: '-'; }
        .tag-list { margin-top: 8px; }

        /* MODAL */
        #code-viewer { position: fixed; inset: 0; background: rgba(0,0,0,0.85); backdrop-filter: blur(8px); z-index: 1000; display: none; align-items: center; justify-content: center; padding: 40px; }
        #code-viewer.open { display: flex; }
        .modal { width: 100%; max-width: 1100px; height: 85vh; background: #1e1e1e; border-radius: 12px; border: 1px solid var(--border-glow); display: flex; flex-direction: column; overflow: hidden; }
        .modal-hdr { padding: 12px 20px; background: #252526; border-bottom: 1px solid #333; display: flex; justify-content: space-between; align-items: center; }
        .modal-path { font-family: var(--font-mono); font-size: 12px; color: #9ca3af; }
        .icon-btn { background: none; border: none; color: #888; cursor: pointer; font-size: 18px; }
        .count-muted { color: var(--text-muted); }
        .modal-body { flex: 1; overflow: auto; padding: 0; }
        .modal-body pre { margin:0; }
        .modal-body code { font-family:'JetBrains Mono'; font-size: 13px; padding: 25px !important; }

        #boot_screen {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: var(--bg-base); z-index: 10000;
            display: flex; flex-direction: column; justify-content: center; align-items: center;
            font-family: 'JetBrains Mono', monospace; color: var(--accent-cyan);
            background-image: 
                linear-gradient(rgba(0, 243, 255, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 243, 255, 0.03) 1px, transparent 1px);
            background-size: 40px 40px;
        }
        #boot_btn {
            padding: 15px 30px; background: transparent; border: 2px solid var(--accent-cyan); color: var(--accent-cyan);
            font-family: 'JetBrains Mono', monospace; font-size: 20px; cursor: pointer; text-transform: uppercase;
            border-radius: 4px; transition: 0.3s; margin-top: 20px;
        }
        #boot_btn:hover { background: var(--accent-cyan); color: #000; box-shadow: 0 0 20px rgba(0, 243, 255, 0.4); }

        @media (max-width: 980px) {
            :root { --sidebar-w: 280px; }
            #hud { height: 48px; padding: 0 10px; gap: 8px; }
            #layout { margin-top: 48px; height: calc(100vh - 48px); }
            .hud-stats { display: none; }
            .hud-brand { font-size: 10px; letter-spacing: 1px; }
            #breadcrumb { font-size: 8px; }
            #sbtoggle { top: 10px; transform: none; height: 32px; width: 20px; }
            #inspector { width: 100%; right: -100%; }
        }
    </style>
</head>
<body>
<div id="boot_screen">
    <h1 style="font-size: 45px; margin-bottom: 10px; font-family: 'Inter', sans-serif; font-weight: 800;">UTCAP SYSTEM V32</h1>
    <p id="boot_log" style="margin-bottom: 40px; min-height: 20px; color: #8b949e;"></p>
    <button id="boot_btn">Initialize Workspace</button>
</div>
<canvas id="pcv"></canvas>
<div id="hud">
    <div class="hud-brand"><span>UTCAP SYSTEM BRAIN</span></div>
    <div id="breadcrumb">Project <b>/</b> Overview</div>
    <div class="hud-stats">
        <div class="hud-stat"><div id="h_mod" class="hud-val">0</div><div class="hud-lbl">Modules</div></div><div class="hud-sep"></div>
        <div class="hud-stat"><div id="h_files" class="hud-val">0</div><div class="hud-lbl">Files</div></div><div class="hud-sep"></div>
        <div class="hud-stat"><div id="h_orp" class="hud-val">0</div><div class="hud-lbl">Orphans</div></div><div class="hud-sep"></div>
        <div class="hud-stat"><div id="h_circ" class="hud-val">0</div><div class="hud-lbl">Cycles</div></div><div class="hud-sep"></div>
        <div class="hud-stat"><div id="h_cls" class="hud-val">0</div><div class="hud-lbl">Classes</div></div><div class="hud-sep"></div>
        <div class="hud-stat"><div id="h_fn" class="hud-val">0</div><div class="hud-lbl">Funcs</div></div>
    </div>
</div>

<div id="layout">
    <div id="sidebar">
        <div class="dock-hdr"><h1>ARCH-PILOT</h1><div class="dock-sub">Comprehensive Analysis V32</div></div>
        
        <div class="dock-sec">
            <div class="btn-grp">
                <button class="btn" onclick="net.fit()">Fit View</button>
                <button class="btn" onclick="resetView()">Reset Map</button>
            </div>
        </div>
        
        <div class="dock-sec"><input type="text" id="searchBar" placeholder="Search modules, files, classes..."></div>
        <div class="dock-sec">
            <div class="hint">Shortcuts: / search | Esc close | Left/Right next node</div>
        </div>
        
        <div class="dock-sec">
            <div class="sec-ttl">Deep Dive Controls</div>
            <div class="btn-grp">
                <button class="btn btn--warn" onclick="expandAll()">Expand All</button>
                <button class="btn btn--danger" onclick="collapseAll()">Collapse</button>
            </div>
            <div class="hint">Double-click a node to expand its Python files.</div>
        </div>

        <div class="dock-sec">
            <div class="sec-ttl">Interaction Mode</div>
            <div class="btn-grp btn-grp--stack">
                <button class="btn btn--row active" id="tm_ins" onclick="setTrace('ins')"><span>Inspector Info</span><span class="btn__meta">I</span></button>
                <button class="btn btn--row" id="tm_path" onclick="setTrace('path')"><span>Pathfinder (Upstream)</span><span class="btn__meta">U</span></button>
                <button class="btn btn--row" id="tm_blast" onclick="setTrace('blast')"><span>Blast Radius (Downstream)</span><span class="btn__meta">D</span></button>
            </div>
        </div>

        <div class="dock-sec">
            <div class="sec-ttl">Visual Overlays</div>
            <div class="btn-grp btn-grp--stack" style="margin-bottom: 8px;">
                <select id="heatDrop" class="ctrl-select" onchange="setHeat(this.value)">
                    <option value="norm">Standard Colors</option>
                    <option value="cpx">Complexity Heatmap</option>
                    <option value="risk">Risk / Churn Hotspots</option>
                </select>
            </div>
            <div class="btn-grp btn-grp--stack">
                <button class="btn btn--row" id="vo_live_data" onclick="toggleLiveData()"><span>Live Data Streams</span><span class="btn__meta">ON</span></button>
                <button class="btn btn--row" id="hm_circ" onclick="setHeat('circ')"><span>Scan for Cycles</span><span class="btn__meta">C</span></button>
                <button class="btn btn--row" id="vo_force" onclick="toggleForcefields()"><span>Blueprint Forcefields</span><span class="btn__meta">F</span></button>
            </div>
        </div>

        <div class="dock-sec">
            <div class="sec-ttl">Filter by Layer</div>
            <div class="f-chips" id="fchips"></div>
        </div>

        <div class="dock-sec dock-sec--end">
            <div class="sec-ttl">Legend</div>
            <div class="legend-list" id="legend"></div>
        </div>
    </div>
    <button id="sbtoggle" onclick="toggleSidebar()">&#9664;</button>
    <div id="netbox"><div id="netmap"></div></div>
</div>

<div id="code-viewer">
    <div class="modal">
        <div class="modal-hdr"><span id="m_path" class="modal-path"></span><button class="icon-btn" onclick="closeCode()">&#x2715;</button></div>
        <div class="modal-body"><pre><code id="m_code" class="language-python"></code></pre></div>
    </div>
</div>

<div id="inspector">
    <div class="ins-hdr"><button class="ins-close" onclick="closeIns()">&#10005;</button><div class="ins-title" id="i_title">Module Name</div><div id="i_group" class="tag">GROUP</div></div>
    <div class="ins-body">
        <div class="ins-path-wrap">
            <div id="i_path"></div>
            <button id="copy_path_btn" class="copy-btn" onclick="copyPath()">Copy Path</button>
        </div>
        
        <div style="display:flex; justify-content:space-between; margin-bottom: 15px;">
            <div style="flex:1; background:rgba(0,0,0,0.2); border:1px solid var(--border-subtle); padding:10px; border-radius:8px; margin-right:8px; text-align:center;">
                <div style="font-size:10px; color:var(--text-muted); font-weight:700; text-transform:uppercase;">Lint Smells</div>
                <div id="i_lint_v" style="font-size:18px; color:var(--warning); font-family:var(--font-mono); font-weight:800;">0</div>
            </div>
            <div style="flex:1; background:rgba(0,0,0,0.2); border:1px solid var(--border-subtle); padding:10px; border-radius:8px; margin-right:8px; text-align:center;">
                <div style="font-size:10px; color:var(--text-muted); font-weight:700; text-transform:uppercase;">Coverage</div>
                <div id="i_cov_v" style="font-size:18px; color:var(--success); font-family:var(--font-mono); font-weight:800;">0%</div>
            </div>
            <div style="flex:1; background:rgba(0,0,0,0.2); border:1px solid var(--border-subtle); padding:10px; border-radius:8px; text-align:center;">
                <div style="font-size:10px; color:var(--text-muted); font-weight:700; text-transform:uppercase;">Clones</div>
                <div id="i_clone_v" style="font-size:18px; color:var(--danger); font-family:var(--font-mono); font-weight:800;">0</div>
            </div>
        </div>
        
        <div id="i_doc" class="doc-box"></div>
        
        <div id="i_todos" style="margin-bottom:15px;"></div>
        
        <div class="cpx-bar"><div class="cpx-hdr"><span>Architectural Complexity</span><span id="i_cpx_v">0</span></div><div class="cpx-track"><div id="i_cpx_f" class="cpx-fill" style="width:0%"></div></div></div>
        
        <div id="i_feeds_out_sec" style="margin-bottom:20px; display:none;">
             <div class="sec-ttl flow-head"><span>DATA FEEDS TO</span><span class="f-chip metric-chip metric-chip--out" id="i_out_c">0</span></div>
             <div id="i_feeds_out" style="display:flex; flex-wrap:wrap; gap:6px;"></div>
        </div>
        <div id="i_feeds_in_sec" style="margin-bottom:20px; display:none;">
             <div class="sec-ttl flow-head"><span>DATA COMES FROM</span><span class="f-chip metric-chip metric-chip--in" id="i_in_c">0</span></div>
             <div id="i_feeds_in" style="display:flex; flex-wrap:wrap; gap:6px;"></div>
        </div>

        <details open><summary><span>Source Files</span><span id="i_f_c" class="count-muted">0</span></summary><div id="i_files" class="tag-list"></div></details>
        <details><summary><span>Internal Classes</span><span id="i_c_c" class="count-muted">0</span></summary><div id="i_classes" class="tag-list"></div></details>
        <details><summary><span>Internal Functions</span><span id="i_fn_c" class="count-muted">0</span></summary><div id="i_funcs" class="tag-list"></div></details>
    </div>
</div>

<script type="application/json" id="gd">__JSON_PAYLOAD__</script>
<script>
// --- AUDIO ENGINE ---
let audioCtx;
function initAudio() { audioCtx = new (window.AudioContext || window.webkitAudioContext)(); }

function playSfx(type) {
    if (!audioCtx) return;
    if (audioCtx.state === 'suspended') audioCtx.resume();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain); gain.connect(audioCtx.destination);
    
    const now = audioCtx.currentTime;
    if (type === 'hover') {
        osc.type = 'sine'; osc.frequency.setValueAtTime(1000, now); osc.frequency.exponentialRampToValueAtTime(600, now + 0.03);
        gain.gain.setValueAtTime(0.02, now); gain.gain.exponentialRampToValueAtTime(0.001, now + 0.03);
        osc.start(now); osc.stop(now + 0.03);
    } else if (type === 'click') {
        osc.type = 'square'; osc.frequency.setValueAtTime(300, now); osc.frequency.exponentialRampToValueAtTime(100, now + 0.08);
        gain.gain.setValueAtTime(0.05, now); gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08);
        osc.start(now); osc.stop(now + 0.08);
    } else if (type === 'expand') {
        osc.type = 'triangle'; osc.frequency.setValueAtTime(150, now); osc.frequency.exponentialRampToValueAtTime(400, now + 0.15);
        gain.gain.setValueAtTime(0.05, now); gain.gain.linearRampToValueAtTime(0, now + 0.15);
        osc.start(now); osc.stop(now + 0.15);
    }
}

// --- BOOT SEQUENCE ---
document.getElementById('boot_btn').addEventListener('click', function() {
    initAudio(); playSfx('expand');
    const btn = this; const log = document.getElementById('boot_log');
    btn.style.display = 'none';
    
    const msgs = ["> COMPILING AST DATA...", "> CALCULATING ORBITAL PHYSICS...", "> SYSTEM ONLINE."];
    let i = 0;
    const interval = setInterval(() => {
        if(i < msgs.length) { log.innerText = msgs[i]; playSfx('hover'); i++; } 
        else { 
            clearInterval(interval);
            document.getElementById('boot_screen').style.opacity = '0';
            document.getElementById('boot_screen').style.pointerEvents = 'none';
            setTimeout(() => document.getElementById('boot_screen').remove(), 500);
        }
    }, 200);
});

// --- DATA ---
const RAW = JSON.parse(document.getElementById('gd').textContent);
const MAIN = RAW.main_nodes, SUBS = RAW.sub_nodes_dict, EDGES = RAW.main_edges;

const GCOL = { entry:'#ef4444', ui:'#3b82f6', core:'#10b981', db:'#8b5cf6', messenger:'#a855f7', workers:'#f59e0b', external:'#eab308', tools:'#a78bfa' };
const GICO = { entry:'EN', ui:'UI', core:'CO', db:'DB', messenger:'MS', workers:'WK', tools:'TL' };

// Preserve raw node data separately (vis-network DataSet strips custom props)
const nodeRawMap = {};
MAIN.forEach(n => { nodeRawMap[n.id] = n; });

let traceMode = 'ins', heatMode = 'norm', hiddenGroups = new Set(), searchQuery = '';

function getContextIcon(raw) {
    const id = raw.id.toLowerCase(); const lbl = raw.label.toLowerCase();
    if (id.includes('postgres') || lbl.includes('postgres')) return 'PG';
    if (id.includes('sqlite') || lbl.includes('sqlite')) return 'SQ';
    if (id.includes('test') || lbl.includes('test')) return 'TS';
    if (id.includes('ui') || id.includes('gui')) return 'UI';
    if (id.includes('db_table')) return 'DB';
    if (id.includes('messenger')) return 'MS';
    if (id.includes('build') || lbl.includes('build')) return 'BL';
    if (id.includes('ffmpeg') || id.includes('video')) return 'VD';
    return GICO[raw.group] || 'ND';
}

function sNode(raw, isM) {
    const i = raw.info || {}, base = GCOL[raw.group] || '#3b82f6', c = i.complexity || 0;
    let bdr = base;
    let isWarning = false;
    
    if (heatMode === 'cpx') { 
        bdr = c > 1000 ? '#ef4444' : c > 500 ? '#f59e0b' : '#10b981'; 
        if (c > 1000) isWarning = true;
    }
    if (heatMode === 'risk') { 
        bdr = (i.risk_score||0) > 80 ? '#ef4444' : (i.risk_score||0) > 40 ? '#f59e0b' : '#10b981';
        if ((i.risk_score||0) > 80) isWarning = true;
    }
    if (heatMode === 'circ') {
        bdr = (i.circular_count||0) > 0 ? '#ef4444' : base;
        if ((i.circular_count||0) > 0) isWarning = true;
    }

    return {
        id: raw.id,
        label: getContextIcon(raw) + ' ' + raw.label.replace(/[\\u{1F300}-\\u{1F9FF}\\u{2600}-\\u{26FF}\\u{2700}-\\u{27BF}\\u{1F100}-\\u{1F1FF}]/gu, '').trim(),
        shape: 'box',
        color: { background: isWarning ? 'rgba(30, 10, 15, 0.95)' : 'rgba(5, 7, 15, 0.95)', border: bdr, highlight: { background: 'rgba(15, 20, 30, 0.95)', border: '#fff' } },
        font: { color: isWarning ? '#fca5a5' : '#e2e8f0', size: isM ? 10 : 8, face: 'Inter', bold: "10px Inter #ffffff" },
        borderWidth: 2,
        shadow: { enabled: true, color: bdr, size: isM ? (isWarning ? 30 : 15) : 8, x: 0, y: 0 }
    };
}

// --- NETWORK ---
const nodesDS = new vis.DataSet(MAIN.map(n => sNode(n, true)));
const edgesDS = new vis.DataSet(EDGES.map(e => ({
    id: e.id, from: e.from, to: e.to, arrows: 'to',
    color: { color:'rgba(0, 243, 255, 0.25)', highlight: '#00f3ff' }, dashes: false,
    smooth: { type:'curvedCW', roundness:0.2 }
})));

const expandedNodes = {};

const net = new vis.Network(document.getElementById('netmap'), { nodes:nodesDS, edges:edgesDS }, {
    physics: { 
        solver:'forceAtlas2Based', 
        forceAtlas2Based: { 
            gravitationalConstant: -400,
            centralGravity: 0.015,
            springLength: 350,
            springConstant: 0.04,
            damping: 0.85 
        },
        maxVelocity: 15,
        minVelocity: 0.1,
        stabilization: { iterations: 150 }
    },
    interaction: { hover:true, hoverConnectedEdges:true, selectConnectedEdges:true }
});

// --- ANIMATED EDGES ---
let offset = 0;
function animateEdges() {
    offset = (offset + 1) % 100;
    edgesDS.update(edgesDS.get().map(e => ({ id:e.id, dashOffset:-offset })));
    requestAnimationFrame(animateEdges);
}
animateEdges();

// --- TRACE & HEAT CONTROLS ---
function setTrace(m) {
    traceMode = m;
    try {
        document.querySelectorAll('[id^=tm_]').forEach(b => b.classList.remove('active'));
        if(document.getElementById('tm_' + m)) document.getElementById('tm_' + m).classList.add('active');
        
        const selected = net.getSelectedNodes();
        if (selected.length > 0) {
            if (m === 'ins') { resetView(); showIns(nodeRawMap[selected[0]]); }
            else if (m === 'path') runTrace(selected[0], 'up');
            else if (m === 'blast') runTrace(selected[0], 'down');
        } else {
            if (m === 'ins') resetView();
        }
    } catch(e) {}
}

function setHeat(m) {
    heatMode = m;
    try {
        if(m==='circ') { document.getElementById('hm_circ').classList.add('active'); document.getElementById('heatDrop').value = 'norm'; }
        else { document.getElementById('hm_circ').classList.remove('active'); document.getElementById('heatDrop').value = m; }
    } catch(e) {}
    nodesDS.update(nodesDS.get().map(n => sNode(nodeRawMap[n.id], !n.id.includes('__'))));
}

// --- INSPECTOR ---
function showIns(raw) {
    const i = raw.info || {};
    document.getElementById('i_title').innerText = raw.label;

    // Data-Feeds Topolgy
    const connectedEdgesIds = net.getConnectedEdges(raw.id);
    let outs = [], ins = [];
    connectedEdgesIds.forEach(eid => {
        const edge = edgesDS.get(eid);
        if (!edge) return;
        if (edge.from === raw.id) outs.push(edge.to);
        if (edge.to === raw.id) ins.push(edge.from);
    });
    
    if (outs.length > 0) {
        document.getElementById('i_feeds_out_sec').style.display = 'block';
        document.getElementById('i_out_c').innerText = outs.length;
        document.getElementById('i_feeds_out').innerHTML = outs.map(id => {
            const n = nodeRawMap[id] || {label: id, group: 'unknown'};
            return `<div class="btn" style="border-color:var(--accent-cyan); width:auto; text-align:center;" onclick="net.selectNodes(['${id}']); net.emit('click', {nodes:['${id}']})">${getContextIcon(n)} ${n.label}</div>`;
        }).join('');
    } else document.getElementById('i_feeds_out_sec').style.display = 'none';

    if (ins.length > 0) {
        document.getElementById('i_feeds_in_sec').style.display = 'block';
        document.getElementById('i_in_c').innerText = ins.length;
        document.getElementById('i_feeds_in').innerHTML = ins.map(id => {
            const n = nodeRawMap[id] || {label: id, group: 'unknown'};
            return `<div class="btn" style="border-color:var(--accent-purple); width:auto; text-align:center;" onclick="net.selectNodes(['${id}']); net.emit('click', {nodes:['${id}']})">${getContextIcon(n)} ${n.label}</div>`;
        }).join('');
    } else document.getElementById('i_feeds_in_sec').style.display = 'none';

    document.getElementById('i_group').innerText = raw.group.toUpperCase();
    document.getElementById('i_path').innerText = i.filepath || (i.files && i.files[0]) || 'Path unavailable';
    document.getElementById('copy_path_btn').innerText = 'Copy Path';
    document.getElementById('i_lint_v').innerText = i.lint_count || 0;
    document.getElementById('i_cov_v').innerText = (i.coverage || 0).toFixed(1) + '%';
    document.getElementById('i_clone_v').innerText = i.clones || 0;
    document.getElementById('i_doc').innerText = i.doc || 'No documentation.';
    
    // Render Todos
    const todoBox = document.getElementById('i_todos');
    if (i.todos && i.todos.length > 0) {
        let html = '<div style="font-size:12px; font-weight:bold; color:var(--text-muted); margin-bottom:8px;">TECH DEBT (' + i.todos.length + ')</div>';
        i.todos.forEach(t => {
            let color = t.type === 'TODO' ? 'var(--primary)' : (t.type === 'FIXME' ? 'var(--danger)' : 'var(--warning)');
            html += `<div style="background:rgba(0,0,0,0.3); border-left:3px solid ${color}; padding:8px; margin-bottom:5px; border-radius:4px; font-size:12px;">`;
            html += `<span style="color:${color}; font-weight:bold; margin-right:5px;">${t.type}</span>`;
            html += `<span style="color:var(--text-muted);">Line ${t.line}:</span> ${t.message}`;
            html += `</div>`;
        });
        todoBox.innerHTML = html;
        todoBox.style.display = 'block';
    } else {
        todoBox.style.display = 'none';
        todoBox.innerHTML = '';
    }
    
    document.getElementById('i_cpx_v').innerText = i.complexity || 0;
    document.getElementById('i_cpx_f').style.width = Math.min(100, ((i.complexity||0) / 1500) * 100) + '%';
    document.getElementById('breadcrumb').innerHTML = `Project <b>/</b> ${raw.group.toUpperCase()} <b>/</b> ${raw.label}`;
    renderTags('i_files', i.files || [], true);
    renderTags('i_classes', i.classes || []);
    renderTags('i_funcs', i.funcs || []);
    document.getElementById('i_f_c').innerText = (i.files||[]).length;
    document.getElementById('i_c_c').innerText = (i.classes||[]).length;
    document.getElementById('i_fn_c').innerText = (i.funcs||[]).length;
    if (traceMode === 'ins') document.getElementById('inspector').classList.add('open');
    if (traceMode === 'path') runTrace(raw.id, 'up');
    if (traceMode === 'blast') runTrace(raw.id, 'down');
}

function copyPath() {
    const btn = document.getElementById('copy_path_btn');
    const pathText = (document.getElementById('i_path').innerText || '').trim();
    if (!pathText || pathText === 'Path unavailable') return;
    navigator.clipboard.writeText(pathText).then(() => {
        btn.innerText = 'Copied';
        setTimeout(() => { btn.innerText = 'Copy Path'; }, 1200);
    }).catch(() => {});
}

function runTrace(nodeId, dir) {
    const traceSet = new Set([nodeId]);
    const queue = [nodeId];
    while (queue.length) {
        const curr = queue.shift();
        const neighbors = dir === 'up' ? net.getConnectedNodes(curr, 'to') : net.getConnectedNodes(curr, 'from');
        neighbors.forEach(n => { if (!traceSet.has(n)) { traceSet.add(n); queue.push(n); } });
    }
    nodesDS.update(nodesDS.get().map(n => ({ id:n.id, opacity: traceSet.has(n.id) ? 1 : 0.08 })));
}

function resetView() {
    nodesDS.update(nodesDS.get().map(n => ({ id:n.id, opacity:1 })));
    document.getElementById('inspector').classList.remove('open');
    net.fit();
}

function renderTags(id, items, link=false) {
    const box = document.getElementById(id);
    box.innerHTML = '';
    if (!items || items.length === 0) {
        box.innerHTML = '<span style="color:var(--text-muted);font-size:10px">None</span>';
        return;
    }
    items.forEach(v => {
        const tag = document.createElement('div');
        tag.className = 'tag';
        tag.innerText = v;
        if (link) tag.onclick = () => viewSource(v);
        box.appendChild(tag);
    });
}

// --- SOURCE VIEWER ---
async function viewSource(p) {
    const m = document.getElementById('code-viewer'), c = document.getElementById('m_code');
    document.getElementById('m_path').innerText = p;
    c.innerText = 'Loading...';
    m.classList.add('open');
    try {
        const resp = await fetch(`/api/file?path=${encodeURIComponent(p)}`);
        const d = await resp.json();
        if (d.error) throw new Error(d.error);
        c.innerText = d.content;
        hljs.highlightElement(c);
    } catch(e) { c.innerText = 'Error: ' + e.message; }
}

function closeCode() { document.getElementById('code-viewer').classList.remove('open'); }
function closeIns() {
    document.getElementById('inspector').classList.remove('open');
    nodesDS.update(nodesDS.get().map(n => ({ id:n.id, opacity:1 })));
}
function toggleSidebar() { document.getElementById('sidebar').classList.toggle('collapsed'); }

// --- LAYER FILTERS & LEGEND ---
const fbox = document.getElementById('fchips'), lbox = document.getElementById('legend');
Object.keys(GCOL).forEach(g => {
    fbox.innerHTML += `<div class="f-chip active" style="color:${GCOL[g]};border-color:${GCOL[g]}40" onclick="toggleLayer('${g}', this)">${g.toUpperCase()}</div>`;
    lbox.innerHTML += `<div class="lg-item"><div class="lg-bar" style="background:${GCOL[g]};box-shadow:0 0 5px ${GCOL[g]}"></div><span>${g.charAt(0).toUpperCase()+g.slice(1)}</span></div>`;
});

function toggleLayer(g, el) {
    el.classList.toggle('active');
    if (hiddenGroups.has(g)) hiddenGroups.delete(g); else hiddenGroups.add(g);
    applyNodeFilters();
}

function applyNodeFilters() {
    nodesDS.update(nodesDS.get().map(n => {
        const raw = nodeRawMap[n.id];
        const groupHidden = hiddenGroups.has(raw ? raw.group : '');
        let match = true;
        if (searchQuery) {
            if (raw) {
                const q = searchQuery;
                match = raw.label.toLowerCase().includes(q) ||
                        (raw.info?.files || []).some(f => f.toLowerCase().includes(q)) ||
                        (raw.info?.classes || []).some(c => c.toLowerCase().includes(q));
            } else {
                match = n.label.toLowerCase().includes(searchQuery);
            }
        }
        return { id: n.id, hidden: groupHidden || !match };
    }));
}

// --- CLICK & SEARCH HANDLERS ---
document.getElementById('searchBar').addEventListener('input', e => {
    searchQuery = e.target.value.toLowerCase().trim();
    applyNodeFilters();
});

function _isTypingContext(el) {
    if (!el) return false;
    const tag = (el.tagName || '').toUpperCase();
    return tag === 'INPUT' || tag === 'TEXTAREA' || !!el.isContentEditable;
}

function _selectNodeByStep(step) {
    const visible = nodesDS.get().filter(n => !n.hidden);
    if (!visible.length) return;

    const ordered = visible
        .map(n => ({ id: n.id, label: (nodeRawMap[n.id]?.label || n.label || '').toLowerCase() }))
        .sort((a, b) => a.label.localeCompare(b.label));

    const selectedId = (net.getSelectedNodes() || [])[0];
    let idx = ordered.findIndex(n => n.id === selectedId);
    if (idx < 0) idx = step > 0 ? -1 : 0;

    const nextIdx = (idx + step + ordered.length) % ordered.length;
    const targetId = ordered[nextIdx].id;
    const raw = nodeRawMap[targetId];
    if (!raw) return;

    net.selectNodes([targetId]);
    net.focus(targetId, { scale: 1, animation: { duration: 220, easingFunction: 'easeInOutQuad' } });
    showIns(raw);
}

document.addEventListener('keydown', (e) => {
    if (e.defaultPrevented) return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;

    const active = document.activeElement;

    if (e.key === '/' && !_isTypingContext(active)) {
        e.preventDefault();
        const search = document.getElementById('searchBar');
        search.focus();
        search.select();
        return;
    }

    if (e.key === 'Escape') {
        e.preventDefault();
        const codeOpen = document.getElementById('code-viewer').classList.contains('open');
        if (codeOpen) {
            closeCode();
            return;
        }
        const inspectorOpen = document.getElementById('inspector').classList.contains('open');
        if (inspectorOpen) {
            closeIns();
            return;
        }
        const search = document.getElementById('searchBar');
        if ((search.value || '').trim()) {
            search.value = '';
            searchQuery = '';
            applyNodeFilters();
        }
        return;
    }

    if (_isTypingContext(active)) return;
    if (e.key === 'ArrowRight') {
        e.preventDefault();
        _selectNodeByStep(1);
        return;
    }
    if (e.key === 'ArrowLeft') {
        e.preventDefault();
        _selectNodeByStep(-1);
    }
});

net.on('click', params => {
    if (params.nodes.length > 0) {
        playSfx('click');
        const raw = nodeRawMap[params.nodes[0]];
        if (raw) showIns(raw);
    } else {
        resetView();
    }
});

net.on('doubleClick', params => {
    if (params.nodes.length > 0) {
        playSfx('expand');
        const pid = params.nodes[0];
        if (SUBS[pid]) {
            if (expandedNodes[pid]) {
                SUBS[pid].forEach(s => {
                    try { edgesDS.remove("edge_" + pid + "_" + s.id); } catch(e) {}
                    try { nodesDS.remove(s.id); } catch(e) {}
                });
                expandedNodes[pid] = false;
            } else {
                let newNodes = []; let newEdges = [];
                SUBS[pid].forEach(s => {
                    nodeRawMap[s.id] = s;
                    if (!nodesDS.get(s.id)) newNodes.push(sNode(s, false));
                    const eid = "edge_" + pid + "_" + s.id;
                    if (!edgesDS.get(eid)) {
                        newEdges.push({ 
                            id: eid, 
                            from: pid, 
                            to: s.id, 
                            dashes: [5,5], 
                            color: { color: '#00f3ff'}, 
                            width: 2,
                            length: 120 
                        });
                    }
                });
                nodesDS.update(newNodes); edgesDS.update(newEdges);
                expandedNodes[pid] = true;
                applyNodeFilters();
            }
        }
    }
});

let lastHovered = null;
net.on("hoverNode", function(params) { 
    if(lastHovered !== params.node) { playSfx('hover'); lastHovered = params.node; }
    net.canvas.body.container.style.cursor = 'pointer'; 
});
net.on("blurNode", function() { lastHovered = null; net.canvas.body.container.style.cursor = 'default'; });

// --- DEEP DIVE CONTROLS ---
function expandAll() {
    playSfx('expand');
    let newNodes = []; let newEdges = [];
    MAIN.forEach(m => {
        const pid = m.id;
        if (SUBS[pid] && !expandedNodes[pid]) {
            SUBS[pid].forEach(s => {
                nodeRawMap[s.id] = s;
                if (!nodesDS.get(s.id)) newNodes.push(sNode(s, false));
                const eid = "edge_" + pid + "_" + s.id;
                if (!edgesDS.get(eid)) {
                    newEdges.push({ 
                        id: eid, from: pid, to: s.id, 
                        color: { color: 'rgba(0,243,255,0.4)' }, dashes: false, width: 1, length: 80 
                    });
                }
            });
            expandedNodes[pid] = true;
        }
    });
    nodesDS.update(newNodes); edgesDS.update(newEdges);
}

function collapseAll() {
    playSfx('click');
    let removeNodes = []; let removeEdges = [];
    MAIN.forEach(m => {
        const pid = m.id;
        if (SUBS[pid] && expandedNodes[pid]) {
            SUBS[pid].forEach(s => {
                removeEdges.push("edge_" + pid + "_" + s.id);
                removeNodes.push(s.id);
            });
            expandedNodes[pid] = false;
        }
    });
    edgesDS.remove(removeEdges); nodesDS.remove(removeNodes);
}

let isLiveDataEnabled = false;
function toggleLiveData() {
    isLiveDataEnabled = !isLiveDataEnabled;
    const btn = document.getElementById('vo_live_data');
    if (isLiveDataEnabled) btn.classList.add('active');
    else btn.classList.remove('active');
}

let isForcefieldsEnabled = false;
function toggleForcefields() {
    isForcefieldsEnabled = !isForcefieldsEnabled;
    const btn = document.getElementById('vo_force');
    if (isForcefieldsEnabled) btn.classList.add('active');
    else btn.classList.remove('active');
    net.redraw();
}

// --- HUD STATS ---
let orp = 0, circ = 0, cls = 0, fns = 0;
MAIN.forEach(n => {
    if (n.info?.orphan) orp++;
    if (n.info?.circular_count) circ++;
    cls += n.info?.classes?.length || 0;
    fns += n.info?.funcs?.length || 0;
});
document.getElementById('h_mod').innerText = MAIN.length;
document.getElementById('h_files').innerText = MAIN.reduce((a,n) => a + (n.info?.files?.length||0), 0);
document.getElementById('h_orp').innerText = orp;
document.getElementById('h_circ').innerText = circ;
document.getElementById('h_cls').innerText = cls;
document.getElementById('h_fn').innerText = fns;

// --- PARTICLES & EDGE STREAMS ---
const edgeMap = new Map();
let currentTrace = null;

// Live Server Setup
if (window.EventSource) {
    const source = new EventSource('/stream');
    source.onmessage = function(event) {
        if (event.data === 'reload') {
            console.log('Server requested reload (Code changed!)');
            // Slight delay to ensure file write is fully completed
            setTimeout(() => location.reload(), 200);
        }
    };
}
const canvas = document.getElementById('pcv'), ctx = canvas.getContext('2d');
let pts = [];
function initPts() {
    canvas.width = window.innerWidth; canvas.height = window.innerHeight;
    pts = [];
    for (let i = 0; i < 60; i++) pts.push({
        x: Math.random()*canvas.width, y: Math.random()*canvas.height,
        vx: (Math.random()-0.5)*0.5, vy: (Math.random()-0.5)*0.5, s: Math.random()*2+0.5
    });
}
function drawPts() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = 'rgba(0, 243, 255, 0.1)';
    pts.forEach(p => {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.s, 0, Math.PI*2); ctx.fill();
    });
    requestAnimationFrame(drawPts);
}
window.addEventListener('resize', initPts);
initPts();
drawPts();

net.on('beforeDrawing', function(nCtx) {
    if (!isForcefieldsEnabled) return;
    const groups = {};
    nodesDS.get().forEach(n => {
        if (n.hidden) return;
        const raw = nodeRawMap[n.id];
        if (!raw || !raw.group) return;
        if (!groups[raw.group]) groups[raw.group] = [];
        const pos = net.getPosition(n.id);
        groups[raw.group].push(pos);
    });
    
    Object.keys(groups).forEach(g => {
        const pts = groups[g];
        if (pts.length === 0) return;
        let cx = 0, cy = 0;
        pts.forEach(p => { cx += p.x; cy += p.y; });
        cx /= pts.length; cy /= pts.length;
        let maxR = 0;
        pts.forEach(p => { const d = Math.sqrt(Math.pow(p.x-cx,2)+Math.pow(p.y-cy,2)); if(d>maxR) maxR=d; });
        
        nCtx.beginPath();
        nCtx.arc(cx, cy, maxR + 80, 0, 2*Math.PI);
        const col = GCOL[g] || '#ffffff';
        nCtx.fillStyle = col + '15'; 
        nCtx.fill();
        nCtx.lineWidth = 1;
        nCtx.strokeStyle = col + '40'; 
        nCtx.stroke();
    });
});

let streamT = 0;
net.on('afterDrawing', function(nCtx) {
    if (!isLiveDataEnabled) return;
    
    // Neural-Net Continuous Global Edge Flow
    streamT += 0.008;
    nCtx.lineWidth = 2;
    
    let hoveredEdges = new Set();
    if (lastHovered) {
        const connectedIds = net.getConnectedEdges(lastHovered);
        connectedIds.forEach(id => hoveredEdges.add(id));
    }
    
    edgesDS.get().forEach(edge => {
        const fromNode = net.getPosition(edge.from);
        const toNode = net.getPosition(edge.to);
        const dist = Math.sqrt(Math.pow(toNode.x - fromNode.x, 2) + Math.pow(toNode.y - fromNode.y, 2));
        const numParticles = Math.max(1, Math.floor(dist / 45));
        
        const isHovered = hoveredEdges.has(edge.id);
        
        nCtx.fillStyle = isHovered ? '#00ff66' : 'rgba(0, 243, 255, 0.4)';
        nCtx.shadowBlur = isHovered ? 20 : 5;
        nCtx.shadowColor = isHovered ? '#00ff66' : '#00f3ff';
        
        for (let i = 0; i < numParticles; i++) {
            let progress = (streamT + (i / numParticles)) % 1;
            progress = progress * progress * (3 - 2 * progress); // Ease in out
            const x = fromNode.x + (toNode.x - fromNode.x) * progress;
            const y = fromNode.y + (toNode.y - fromNode.y) * progress;
            nCtx.beginPath(); nCtx.arc(x, y, isHovered ? 3.5 : 1.5, 0, 2 * Math.PI, false); nCtx.fill();
        }
    });
    nCtx.shadowBlur = 0;
});

// Redraw only when optional animated overlays are enabled.
setInterval(() => {
    if (isLiveDataEnabled || isForcefieldsEnabled) net.redraw();
}, 1000/30);
</script>
</body>
</html>"""

    html_content = html_template.replace("__JSON_PAYLOAD__", json_payload)
    with open(html_filepath, "w", encoding="utf-8") as handle:
        handle.write(html_content)

