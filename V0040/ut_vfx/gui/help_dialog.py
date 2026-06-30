# -*- coding: utf-8 -*-
"""
Help Dialog - Interactive documentation system for UT_VFX.

Provides tabbed, searchable help content with rich formatting and emoji support.
"""

import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTextBrowser, QLineEdit, QPushButton, QLabel,
    QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..core.help_content import HELP_CONTENT, get_all_tabs, search_help


class HelpDialog(QDialog):
    """
    Main help dialog featuring tabbed documentation with search.
    """
    
    def __init__(self, parent=None, initial_tab="getting_started"):
        super().__init__(parent)
        self.setWindowTitle("📚 UT_VFX Help")
        self.setMinimumSize(1000, 800)
        self.resize(1200, 850)
        
        self.setup_ui()
        self.load_content()
        self.set_active_tab(initial_tab)
        
        # Apply polished dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
                color: #e8e8e8;
            }
            QTabWidget::pane {
                border: 1px solid #2a2a2a;
                background: #1e1e1e;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: #252525;
                color: #999;
                padding: 12px 24px;
                border: 1px solid #2a2a2a;
                border-bottom: none;
                margin-right: 3px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background: #2a2a2a;
                color: #ffffff;
                border-bottom: 3px solid #00B4D8;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background: #2d2d2d;
                color: #ddd;
            }
            QTextBrowser {
                background: #1e1e1e;
                color: #e8e8e8;
                border: 1px solid #2a2a2a;
                border-radius: 6px;
                padding: 20px;
                font-size: 14px;
                line-height: 1.6;
            }
            QLineEdit {
                background: #252525;
                color: #e8e8e8;
                border: 2px solid #333;
                border-radius: 6px;
                padding: 10px 14px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #00B4D8;
                background: #2a2a2a;
            }
            QPushButton {
                background: #2d2d2d;
                color: #e8e8e8;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #3a3a3a;
                border: 1px solid #00B4D8;
            }
            QPushButton:pressed {
                background: #252525;
            }
        """)
    
    def setup_ui(self):
        """Create the main UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header with search
        header = self.create_header()
        layout.addWidget(header)
        
        # Tab widget for different help sections
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        layout.addWidget(self.tab_widget)
        
        # Footer with buttons
        footer = self.create_footer()
        layout.addWidget(footer)
    
    def create_header(self):
        """Create header with title and search."""
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background: #252525;
                border-bottom: 1px solid #00B4D8;
            }
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(24, 16, 24, 16)
        h_layout.setSpacing(20)
        
        # Title - Clean text only
        title = QLabel("UT_VFX Help")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #00B4D8; border: none;")
        h_layout.addWidget(title)
        
        h_layout.addStretch()
        
        # Search container with integrated clear button
        search_container = QWidget()
        search_container.setStyleSheet("background: transparent; border: none;")
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(0)
        
        # Search box with icon
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍  Search documentation...")
        self.search_box.setFixedWidth(320)
        self.search_box.setFixedHeight(36)
        self.search_box.setStyleSheet("""
            QLineEdit {
                background: #2a2a2a;
                color: #e8e8e8;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 8px 40px 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #00B4D8;
                background: #2d2d2d;
            }
        """)
        self.search_box.textChanged.connect(self.on_search)
        search_layout.addWidget(self.search_box)
        
        # Clear button (icon style, overlaid on search box)
        clear_btn = QPushButton("×")
        clear_btn.setFixedSize(28, 28)
        clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #666;
                border: none;
                border-radius: 14px;
                font-size: 20px;
                font-weight: bold;
                margin-right: 4px;
            }
            QPushButton:hover {
                background: #3a3a3a;
                color: #00B4D8;
            }
            QPushButton:pressed {
                background: #404040;
            }
        """)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(lambda: self.search_box.clear())
        
        # Position clear button over search box (right side)
        search_layout.addWidget(clear_btn)
        search_layout.setAlignment(clear_btn, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        clear_btn.move(-32, 0)  # Overlay on search box
        
        h_layout.addWidget(search_container)
        
        return header
    
    def create_footer(self):
        """Create footer with action buttons."""
        footer = QWidget()
        footer.setStyleSheet("""
            QWidget {
                background: #252525;
                border-top: 1px solid #333;
            }
        """)
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(24, 14, 24, 14)
        
        # Info label
        info = QLabel("💡 Press <b>F1</b> anytime to open help")
        info.setStyleSheet("color: #888; font-size: 12px; border: none;")
        f_layout.addWidget(info)
        
        f_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.setFixedHeight(34)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #00B4D8;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: 600;
                font-size: 13px;
                color: #fff;
            }
            QPushButton:hover {
                background: #00A5C8;
            }
            QPushButton:pressed {
                background: #0095B8;
            }
        """)
        close_btn.clicked.connect(self.accept)
        f_layout.addWidget(close_btn)
        
        return footer
    
    def load_content(self):
        """Load all help content into tabs."""
        try:
            tabs_data = get_all_tabs()
            
            if not tabs_data:
                logging.error("No help tabs found - HELP_CONTENT may be empty")
                self._show_error_tab("No Help Content", 
                    "Help system is not available. The help content database is empty.")
                return
                
            for tab_data in tabs_data:
                tab_id = tab_data["id"]
                tab_title = tab_data["title"]
                
                # Create text browser for this tab
                browser = QTextBrowser()
                browser.setOpenExternalLinks(True)
                browser.setObjectName(tab_id)
                
                # Load HTML content
                try:
                    content_data = HELP_CONTENT[tab_id]
                    html_content = self.format_html(content_data.get("content", ""))
                    browser.setHtml(html_content)
                except Exception as e:
                    logging.exception(f"Error loading content for tab {tab_id}")
                    browser.setHtml(self.format_html(f"<h2>Error Loading Content</h2><p>{str(e)}</p>"))
                
                # Add tab
                self.tab_widget.addTab(browser, tab_title)
                
        except ImportError as e:
            logging.exception("Failed to import help_content module")
            self._show_error_tab("Import Error", 
                f"Failed to load help system: {str(e)}<br><br>Please contact IT support.")
        except Exception as e:
            logging.exception("Error loading help content")
            self._show_error_tab("System Error", 
                f"An error occurred while loading help: {str(e)}")
    
    def _show_error_tab(self, title, message):
        """Display error message in help dialog"""
        error_html = self.format_html(f"""
            <h1 style="color: #ff5555;">&#9888; {title}</h1>
            <p style="font-size: 14px;">{message}</p>
            <hr style="border: 1px solid #444; margin: 20px 0;">
            <p style="color: #888;">If this problem persists, please contact your supervisor or IT team for support.</p>
        """)
        browser = QTextBrowser()
        browser.setHtml(error_html)
        self.tab_widget.addTab(browser, f"Warning: {title}")
    
    def format_html(self, content):
        """Wrap content in HTML template with styling."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    font-size: 13px;
                    line-height: 1.6;
                    color: #e0e0e0;
                    margin: 0;
                    padding: 0;
                }}
                h1 {{
                    color: #00B4D8;
                    border-bottom: 2px solid #00B4D8;
                    padding-bottom: 10px;
                    margin-top: 0;
                }}
                h2 {{
                    color: #4CAF50;
                    border-bottom: 1px solid #444;
                    padding-bottom: 5px;
                    margin-top: 25px;
                }}
                h3 {{
                    color: #FFA726;
                    margin-top: 20px;
                }}
                code {{
                    background: #1a1a1a;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: 'Consolas', monospace;
                    color: #4CAF50;
                }}
                pre {{
                    background: #1a1a1a;
                    padding: 15px;
                    border-radius: 5px;
                    border-left: 3px solid #00B4D8;
                    overflow-x: auto;
                    font-family: 'Consolas', monospace;
                    font-size: 12px;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 15px 0;
                }}
                th {{
                    background: #3a3a3a;
                    color: #00B4D8;
                    font-weight: bold;
                    text-align: left;
                    padding: 10px;
                    border: 1px solid #555;
                }}
                td {{
                    padding: 8px;
                    border: 1px solid #444;
                }}
                tr:nth-child(even) {{
                    background: #2a2a2a;
                }}
                ul, ol {{
                    margin: 10px 0;
                    padding-left: 25px;
                }}
                li {{
                    margin: 5px 0;
                }}
                a {{
                    color: #00B4D8;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
                p {{
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            {content}
        </body>
        </html>
        """
    
    def set_active_tab(self, tab_id):
        """Set active tab by ID."""
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if widget.objectName() == tab_id:
                self.tab_widget.setCurrentIndex(i)
                break
    
    def on_search(self, query):
        """Handle search query."""
        if not query.strip():
            # Reset to normal content
            self.load_content()
            return
        
        # Perform search
        results = search_help(query)
        
        if not results:
            # No results - show message
            no_results_html = self.format_html(f"""
                <h2>🔍 No Results Found</h2>
                <p>No help content matches your search for <b>"{query}"</b></p>
                <p>Try different keywords or check spelling.</p>
            """)
            current_browser = self.tab_widget.currentWidget()
            if isinstance(current_browser, QTextBrowser):
                current_browser.setHtml(no_results_html)
        else:
            # Show results in current tab
            results_html = "<h2>🔍 Search Results</h2>"
            results_html += f"<p>Found <b>{len(results)}</b> result(s) for <b>\"{query}\"</b></p>"
            
            for tab_id, title, snippet in results:
                results_html += f"""
                    <div style="background: #2a2a2a; padding: 10px; margin: 10px 0; border-left: 3px solid #00B4D8; border-radius: 3px;">
                        <h3>{title}</h3>
                        <p>{snippet}</p>
                    </div>
                """
            
            results_html += """
                <p style="margin-top: 20px; color: #888; font-size: 11px;">
                💡 Tip: Clear search to return to full documentation
                </p>
            """
            
            current_browser = self.tab_widget.currentWidget()
            if isinstance(current_browser, QTextBrowser):
                current_browser.setHtml(self.format_html(results_html))
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key.Key_Escape:
            self.accept()
        else:
            super().keyPressEvent(event)


def show_help(parent=None, tab_id="getting_started"):
    """
    Show help dialog.
    
    Args:
        parent: Parent widget
        tab_id: ID of tab to show (default: getting_started)
    """
    dialog = HelpDialog(parent, initial_tab=tab_id)
    dialog.exec()
