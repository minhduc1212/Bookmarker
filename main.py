import sys
import json
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QSystemTrayIcon, QMenu, QAction, QMessageBox,
    QLabel, QSizePolicy, QTabWidget, QStyle
)
from PyQt5.QtGui import QIcon, QDesktopServices, QMouseEvent, QFont, QFontDatabase
from PyQt5.QtCore import QUrl, Qt, QPoint, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect

# --- Cấu hình ---
BOOKMARKS_FILE = 'bookmarks.json'
NON_URL_BOOKMARKS_FILE = 'non_url_bookmarks.json'
APP_ICON_PATH = 'assets/icon.png'
MINIMIZE_ICON_PATH = 'assets/minimize_icon.png'
MAXIMIZE_ICON_PATH = 'assets/maximize_icon.png'
RESTORE_ICON_PATH = 'assets/restore_icon.png'
CLOSE_ICON_PATH = 'assets/close_icon.png'


# --- Custom Title Bar Widget ---
class CustomTitleBar(QWidget):
    minimize_requested = pyqtSignal()
    maximize_restore_requested = pyqtSignal()
    close_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setFixedHeight(40)
        self.dragging = False
        self.offset = QPoint()

        self.setup_ui()
        self.setup_connections()
        self.apply_styles()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if os.path.exists(APP_ICON_PATH):
            self.app_icon_label = QLabel()
            self.app_icon_label.setPixmap(QIcon(APP_ICON_PATH).pixmap(24, 24))
            self.app_icon_label.setContentsMargins(10, 0, 0, 0)
            layout.addWidget(self.app_icon_label)
        else:
            self.app_icon_label = None

        self.title_label = QLabel("Bookmark Manager")
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        if self.app_icon_label is None:
            self.title_label.setContentsMargins(10, 0, 0, 0)
        else:
            self.title_label.setContentsMargins(5, 0, 0, 0)
        
        layout.addWidget(self.title_label)
        layout.addStretch()

        self.min_btn = QPushButton()
        self.max_res_btn = QPushButton()
        self.close_btn = QPushButton()

        self.min_btn.setFixedSize(40, 40)
        self.max_res_btn.setFixedSize(40, 40)
        self.close_btn.setFixedSize(40, 40)

        self._set_button_icon(self.min_btn, MINIMIZE_ICON_PATH, QStyle.SP_TitleBarMinButton)
        self._set_button_icon(self.close_btn, CLOSE_ICON_PATH, QStyle.SP_TitleBarCloseButton)
        
        layout.addWidget(self.min_btn)
        layout.addWidget(self.max_res_btn)
        layout.addWidget(self.close_btn)

    def _set_button_icon(self, button, custom_path, fallback_standard_pixmap):
        if os.path.exists(custom_path):
            button.setIcon(QIcon(custom_path))
        else:
            button.setIcon(self.style().standardIcon(fallback_standard_pixmap))

    def setup_connections(self):
        self.min_btn.clicked.connect(self.minimize_requested.emit)
        self.max_res_btn.clicked.connect(self.maximize_restore_requested.emit)
        self.close_btn.clicked.connect(self.close_requested.emit)

    def apply_styles(self):
        self.setStyleSheet("""
            CustomTitleBar {
                background-color: #1e1e1e;
                border-bottom: 1px solid #333333;
            }
            CustomTitleBar QLabel {
                color: #f0f0f0;
                font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
                font-size: 16px;
                font-weight: 500;
            }
            CustomTitleBar QPushButton {
                background-color: transparent;
                border: none;
                color: #f0f0f0;
                font-size: 18px;
            }
            CustomTitleBar QPushButton:hover {
                background-color: #333333;
            }
            CustomTitleBar QPushButton#close_btn:hover {
                background-color: #e81123;
            }
            CustomTitleBar QPushButton:pressed {
                background-color: #007acc;
            }
            CustomTitleBar QPushButton#close_btn:pressed {
                background-color: #8c0000;
            }
        """)
        self.min_btn.setObjectName("min_btn")
        self.max_res_btn.setObjectName("max_res_btn")
        self.close_btn.setObjectName("close_btn")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging:
            self.parent_window.move(event.globalPos() - self.offset)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.dragging = False
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.maximize_restore_requested.emit()
            event.accept()

    def update_max_restore_icon(self, is_maximized):
        if is_maximized:
            self._set_button_icon(self.max_res_btn, RESTORE_ICON_PATH, QStyle.SP_TitleBarMaxButton)
        else:
            self._set_button_icon(self.max_res_btn, MAXIMIZE_ICON_PATH, QStyle.SP_TitleBarMaxButton)


# --- Main Application Window ---
class BookmarkManagerApp(QMainWindow):
    add_bookmark_from_tray_signal = pyqtSignal()
    add_non_url_bookmark_from_tray_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.bookmarks = []
        self.non_url_bookmarks = []

        self.load_bookmarks(BOOKMARKS_FILE, self.bookmarks)
        self.load_bookmarks(NON_URL_BOOKMARKS_FILE, self.non_url_bookmarks)

        self.init_ui()
        self.init_tray_icon()
        self.apply_modern_theme()
        self.populate_tables()
        
        self.title_bar.update_max_restore_icon(self.isMaximized()) 


    def init_ui(self):
        self.setWindowTitle('Bookmark Manager')
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowSystemMenuHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.setGeometry(100, 100, 900, 700)

        if os.path.exists(APP_ICON_PATH):
            self.setWindowIcon(QIcon(APP_ICON_PATH))

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(1, 1, 1, 1) 
        main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self)
        self.title_bar.minimize_requested.connect(self.showMinimized)
        self.title_bar.maximize_restore_requested.connect(self.toggle_maximize_restore)
        self.title_bar.close_requested.connect(self.close)
        main_layout.addWidget(self.title_bar)

        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("bookmark_tab_widget")
        main_layout.addWidget(self.tab_widget)

        # --- URL Bookmarks Tab ---
        self.url_tab = QWidget()
        self.url_tab.setObjectName("url_tab")
        self.url_tab_layout = QVBoxLayout(self.url_tab)
        self.tab_widget.addTab(self.url_tab, "Web Links")

        url_input_layout = QHBoxLayout()
        url_input_layout.setSpacing(10)
        self.title_input = QLineEdit(self)
        self.title_input.setPlaceholderText("Bookmark Title")
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("Bookmark URL (e.g., https://example.com)")
        self.add_url_button = QPushButton("ADD LINK")
        self.add_url_button.clicked.connect(self.add_url_bookmark)

        url_input_layout.addWidget(self.title_input)
        url_input_layout.addWidget(self.url_input)
        url_input_layout.addWidget(self.add_url_button)
        self.url_tab_layout.addLayout(url_input_layout)

        self.url_bookmark_table = QTableWidget(self)
        self.url_bookmark_table.setColumnCount(2)
        self.url_bookmark_table.setHorizontalHeaderLabels(["Title", "URL"])
        self.url_bookmark_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.url_bookmark_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.url_bookmark_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.url_bookmark_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.url_bookmark_table.setSelectionMode(QTableWidget.SingleSelection)
        self.url_bookmark_table.doubleClicked.connect(self.open_selected_url_bookmark)
        
        self.url_tab_layout.addWidget(self.url_bookmark_table)

        url_action_layout = QHBoxLayout()
        url_action_layout.setSpacing(10)
        self.open_url_button = QPushButton("OPEN SELECTED")
        self.open_url_button.clicked.connect(self.open_selected_url_bookmark)
        self.delete_url_button = QPushButton("DELETE SELECTED")
        self.delete_url_button.setObjectName("delete_url_button")
        self.delete_url_button.clicked.connect(self.delete_selected_url_bookmark)
        url_action_layout.addStretch()
        url_action_layout.addWidget(self.open_url_button)
        url_action_layout.addWidget(self.delete_url_button)
        self.url_tab_layout.addLayout(url_action_layout)

        # --- Non-URL Bookmarks Tab ---
        self.non_url_tab = QWidget()
        self.non_url_tab.setObjectName("non_url_tab")
        self.non_url_tab_layout = QVBoxLayout(self.non_url_tab)
        self.tab_widget.addTab(self.non_url_tab, "Names/Notes")

        non_url_input_layout = QHBoxLayout()
        non_url_input_layout.setSpacing(10)
        self.name_input = QLineEdit(self)
        self.name_input.setPlaceholderText("Name (e.g., Cyberpunk 2077, Dune)")
        self.add_name_button = QPushButton("ADD NAME")
        self.add_name_button.clicked.connect(self.add_non_url_bookmark)

        non_url_input_layout.addWidget(self.name_input)
        non_url_input_layout.addWidget(self.add_name_button)
        self.non_url_tab_layout.addLayout(non_url_input_layout)

        self.non_url_bookmark_table = QTableWidget(self)
        self.non_url_bookmark_table.setColumnCount(1)
        self.non_url_bookmark_table.setHorizontalHeaderLabels(["Name / Note"])
        self.non_url_bookmark_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.non_url_bookmark_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.non_url_bookmark_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.non_url_bookmark_table.setSelectionMode(QTableWidget.SingleSelection)

        self.non_url_tab_layout.addWidget(self.non_url_bookmark_table)

        non_url_action_layout = QHBoxLayout()
        non_url_action_layout.setSpacing(10)
        self.delete_name_button = QPushButton("DELETE SELECTED")
        self.delete_name_button.setObjectName("delete_name_button")
        self.delete_name_button.clicked.connect(self.delete_selected_non_url_bookmark)
        non_url_action_layout.addStretch()
        non_url_action_layout.addWidget(self.delete_name_button)
        self.non_url_tab_layout.addLayout(non_url_action_layout)

        self.setCentralWidget(main_widget)
        
        self.add_bookmark_from_tray_signal.connect(self.focus_url_input)
        self.add_non_url_bookmark_from_tray_signal.connect(self.focus_non_url_input)

    def apply_modern_theme(self):
        self.setStyleSheet("""
            /* Global Styles */
            QMainWindow {
                background-color: #252526;
                border: 1px solid #3c3c3c;
                border-radius: 8px;
            }
            QWidget {
                background-color: #252526;
                color: #cccccc;
                font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
                font-size: 14px;
            }

            /* QLineEdit - Input Fields */
            QLineEdit {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 10px;
                color: #f0f0f0;
                selection-background-color: #007ACC;
            }
            QLineEdit:focus {
                border: 1px solid #007ACC;
                background-color: #444444;
            }

            /* QPushButton - Buttons */
            QPushButton {
                background-color: #007ACC;
                border: none;
                border-radius: 5px;
                color: white;
                padding: 10px 18px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: #006BB8;
            }
            QPushButton:pressed {
                background-color: #005A99;
            }
            /* Specific delete button style */
            QPushButton#delete_url_button, QPushButton#delete_name_button {
                background-color: #CC293D;
            }
            QPushButton#delete_url_button:hover, QPushButton#delete_name_button:hover {
                background-color: #A6202F;
            }
            QPushButton#delete_url_button:pressed, QPushButton#delete_name_button:pressed {
                background-color: #801825;
            }
            
            /* QTableWidget - Data Display */
            QTableWidget {
                background-color: #2D2D30;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                gridline-color: #444444;
                color: #cccccc;
                selection-background-color: #007ACC;
                selection-color: white;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #007ACC;
                color: white;
            }
            QTableWidget QHeaderView::section {
                background-color: #3C3C3C;
                color: #f0f0f0;
                padding: 8px;
                border: 1px solid #333333;
                border-bottom: 2px solid #007ACC;
                font-weight: 600;
            }
            QTableWidget QTableCornerButton::section {
                background-color: #3C3C3C;
                border: 1px solid #333333;
            }
            /* Scroll bars */
            QScrollBar:vertical, QScrollBar:horizontal {
                border: none;
                background: #3c3c3c;
                width: 12px;
                margin: 0px 0px 0px 0px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #555555;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
                background: #666666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }

            /* QTabWidget */
            QTabWidget::pane {
                border: 1px solid #3c3c3c;
                background-color: #252526;
                border-radius: 8px;
                margin: 0 10px 10px 10px; 
            }
            
            QTabWidget QTabBar {
                margin-left: 25px; /* Giữ nguyên giá trị này để căn chỉnh khởi đầu tab */
            }

            QTabBar::tab {
                background-color: #3c3c3c;
                color: #cccccc;
                /* ĐIỂM CHÍNH ĐỂ SỬA LỖI: Tăng padding ngang để chữ không bị cắt */
                padding: 10px 20px; /* Tăng từ 15px lên 20px (thử nghiệm) */
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                margin-right: 2px;
                border: none; /* Bỏ viền mặc định cho tab */
            }
            QTabBar::tab:hover {
                background-color: #444444;
            }
            QTabBar::tab:selected {
                background-color: #252526; 
                color: #007ACC; 
                border-bottom: 2px solid #007ACC; 
                border-bottom-left-radius: 0; 
                border-bottom-right-radius: 0;
            }
            QTabWidget QWidget#url_tab, QTabWidget QWidget#non_url_tab {
                padding: 15px; /* Giữ nguyên padding này cho nội dung bên trong tab */
            }
        """)

    def load_bookmarks(self, file_path, data_list):
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data_list.clear()
                    data_list.extend(json.load(f))
            except json.JSONDecodeError:
                data_list.clear()
                QMessageBox.warning(self, "Error", f"Could not load bookmarks from {file_path}. Invalid JSON format.")
        else:
            data_list.clear()

    def save_bookmarks(self, file_path, data_list):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data_list, f, indent=4, ensure_ascii=False)

    def populate_tables(self):
        self.populate_url_table()
        self.populate_non_url_table()

    def populate_url_table(self):
        self.url_bookmark_table.setRowCount(0)
        for row_idx, bookmark in enumerate(self.bookmarks):
            self.url_bookmark_table.insertRow(row_idx)
            self.url_bookmark_table.setItem(row_idx, 0, QTableWidgetItem(bookmark.get('title', 'No Title')))
            self.url_bookmark_table.setItem(row_idx, 1, QTableWidgetItem(bookmark.get('url', 'No URL')))

    def add_url_bookmark(self):
        title = self.title_input.text().strip()
        url = self.url_input.text().strip()

        if not title or not url:
            QMessageBox.warning(self, "Input Error", "Please enter both title and URL for Web Links.")
            return

        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url

        new_bookmark = {'title': title, 'url': url}
        self.bookmarks.append(new_bookmark)
        self.save_bookmarks(BOOKMARKS_FILE, self.bookmarks)
        self.populate_url_table()
        
        self.title_input.clear()
        self.url_input.clear()
        self.url_bookmark_table.scrollToBottom()
        self.url_bookmark_table.selectRow(len(self.bookmarks) - 1)


    def delete_selected_url_bookmark(self):
        selected_rows = self.url_bookmark_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Selection", "Please select a bookmark to delete.")
            return

        row_index = selected_rows[0].row()
        reply = QMessageBox.question(self, 'Delete Bookmark',
                                     f"Are you sure you want to delete '{self.bookmarks[row_index]['title']}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            del self.bookmarks[row_index]
            self.save_bookmarks(BOOKMARKS_FILE, self.bookmarks)
            self.populate_url_table()

    def open_selected_url_bookmark(self):
        selected_rows = self.url_bookmark_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Selection", "Please select a bookmark to open.")
            return

        row_index = selected_rows[0].row()
        url = self.bookmarks[row_index].get('url')
        if url:
            QDesktopServices.openUrl(QUrl(url))
        else:
            QMessageBox.warning(self, "Error", "Selected bookmark has no URL.")
    
    def populate_non_url_table(self):
        self.non_url_bookmark_table.setRowCount(0)
        for row_idx, bookmark in enumerate(self.non_url_bookmarks):
            self.non_url_bookmark_table.insertRow(row_idx)
            self.non_url_bookmark_table.setItem(row_idx, 0, QTableWidgetItem(bookmark.get('name', 'No Name')))

    def add_non_url_bookmark(self):
        name = self.name_input.text().strip()

        if not name:
            QMessageBox.warning(self, "Input Error", "Please enter a name for the bookmark.")
            return

        new_bookmark = {'name': name}
        self.non_url_bookmarks.append(new_bookmark)
        self.save_bookmarks(NON_URL_BOOKMARKS_FILE, self.non_url_bookmarks)
        self.populate_non_url_table()
        
        self.name_input.clear()
        self.non_url_bookmark_table.scrollToBottom()
        self.non_url_bookmark_table.selectRow(len(self.non_url_bookmarks) - 1)

    def delete_selected_non_url_bookmark(self):
        selected_rows = self.non_url_bookmark_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Selection", "Please select a bookmark to delete.")
            return

        row_index = selected_rows[0].row()
        reply = QMessageBox.question(self, 'Delete Bookmark',
                                     f"Are you sure you want to delete '{self.non_url_bookmarks[row_index]['name']}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            del self.non_url_bookmarks[row_index]
            self.save_bookmarks(NON_URL_BOOKMARKS_FILE, self.non_url_bookmarks)
            self.populate_non_url_table()

    def toggle_maximize_restore(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self.title_bar.update_max_restore_icon(self.isMaximized()) 

    def init_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists(APP_ICON_PATH):
            self.tray_icon.setIcon(QIcon(APP_ICON_PATH))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon)) 
        
        self.tray_icon.setToolTip('Modern Bookmark Manager')

        tray_menu = QMenu()

        show_hide_action = QAction("Show/Hide Window", self)
        show_hide_action.triggered.connect(self.toggle_window_visibility)
        tray_menu.addAction(show_hide_action)

        add_url_action = QAction("Add Web Link", self)
        add_url_action.triggered.connect(self.add_bookmark_from_tray_signal.emit)
        tray_menu.addAction(add_url_action)

        add_name_action = QAction("Add Name/Note", self)
        add_name_action.triggered.connect(self.add_non_url_bookmark_from_tray_signal.emit)
        tray_menu.addAction(add_name_action)

        tray_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.tray_icon_activated)

    def toggle_window_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.toggle_window_visibility()

    def focus_url_input(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self.tab_widget.setCurrentWidget(self.url_tab)
        self.title_input.setFocus()

    def focus_non_url_input(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self.tab_widget.setCurrentWidget(self.non_url_tab)
        self.name_input.setFocus()

    def closeEvent(self, event):
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()
            self.tray_icon.showMessage(
                "Bookmark Manager",
                "Application minimized to tray. Click icon to restore.",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Tray Icon Error", "System tray not available.")
        sys.exit(1)

    app.setQuitOnLastWindowClosed(False)

    window = BookmarkManagerApp()
    window.show()
    sys.exit(app.exec_())