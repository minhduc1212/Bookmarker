import sys
import json
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QSystemTrayIcon, QMenu, QAction, QMessageBox,
    QLabel, QSizePolicy, QTabWidget, QStyle, QInputDialog
)
from PyQt5.QtGui import QIcon, QDesktopServices, QMouseEvent
from PyQt5.QtCore import QUrl, Qt, QPoint, pyqtSignal

# --- Cấu hình ---
ALL_BOOKMARKS_FILE = 'categories.json' # File JSON mới để lưu tất cả dữ liệu
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


#Main Window
class BookmarkManagerApp(QMainWindow):
    show_window_and_add_bookmark_signal = pyqtSignal()
    show_window_and_add_category_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.categories_data = {} 
        self.category_widgets = {} 

        self.load_all_bookmarks()

        self.init_ui()
        self.init_tray_icon()
        self.apply_modern_theme() # <-- HÀM apply_modern_theme() ĐƯỢC GỌI Ở ĐÂY
        self.populate_all_tables()
        
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
        
        #Add Category Button 
        self.add_category_button = QPushButton("+ Add Category")
        self.add_category_button.setObjectName("add_category_button")
        self.add_category_button.setFixedSize(120, 30)
        self.add_category_button.clicked.connect(self.prompt_new_category)
        
        add_category_btn_container = QWidget()
        add_category_btn_layout = QHBoxLayout(add_category_btn_container)
        add_category_btn_layout.setContentsMargins(0,0,0,0)
        add_category_btn_layout.addStretch()
        add_category_btn_layout.addWidget(self.add_category_button)
        
        #Add Category Button 
        main_layout.addWidget(add_category_btn_container) 

        self.setCentralWidget(main_widget)
        
        self.init_category_tabs() 

        self.show_window_and_add_bookmark_signal.connect(self.prompt_add_bookmark)
        self.show_window_and_add_category_signal.connect(self.prompt_new_category)


    def apply_modern_theme(self):
        """Áp dụng theme hiện đại (dark theme) cho toàn bộ ứng dụng."""
        self.setStyleSheet("""
            /* Global Styles */
            QMainWindow {
                background-color: #252526; /* Main background */
                border: 1px solid #3c3c3c; /* Subtle border for frameless window */
                border-radius: 8px; /* Rounded corners for the whole window */
            }
            QWidget {
                background-color: #252526;
                color: #cccccc; /* Default text color */
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
                border: 1px solid #007ACC; /* Highlight on focus */
                background-color: #444444;
            }

            /* QPushButton */
            QPushButton {
                background-color: #007ACC;
                border: none;
                border-radius: 5px;
                color: white;
                padding: 10px 18px;
                font-weight: 600; /* Semi-bold */
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
            QPushButton#delete_button { /* Áp dụng cho các nút có objectName là "delete_button" */
                background-color: #CC293D; /* Red for delete */
            }
            QPushButton#delete_button:hover {
                background-color: #A6202F;
            }
            QPushButton#delete_button:pressed {
                background-color: #801825;
            }

            /* Nút thêm Category */
            QPushButton#add_category_button {
                background-color: #4CAF50; /* Green color for add category */
                color: white;
                padding: 5px 10px;
                border-radius: 15px; /* Pill shape */
                font-size: 12px;
                font-weight: bold;
                text-transform: none; /* Không viết hoa */
                letter-spacing: normal;
                min-width: 100px;
            }
            QPushButton#add_category_button:hover {
                background-color: #45a049;
            }
            QPushButton#add_category_button:pressed {
                background-color: #3e8e41;
            }
            
            /* QTableWidget - Data Display */
            QTableWidget {
                background-color: #2D2D30; /* Slightly different background for table */
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                gridline-color: #444444;
                color: #cccccc;
                selection-background-color: #007ACC; /* Blue selection */
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
                border-bottom: 2px solid #007ACC; /* Accent border */
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
            QTabWidget::pane { /* The tab content area */
                border: 1px solid #3c3c3c;
                background-color: #252526;
                border-radius: 8px; /* Match window border radius */
                margin: 0 10px 10px 10px; /* Spacing from edges */
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                color: #cccccc;
                padding: 10px 15px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                margin-right: 2px; /* Space between tabs */
                border: none; /* Remove default tab border */
                border-bottom: 2px solid transparent; /* Placeholder for active indicator */
            }
            QTabBar::tab:hover {
                background-color: #444444;
            }
            QTabBar::tab:selected {
                background-color: #252526; /* Match pane background */
                color: #007ACC; /* Active tab color */

                border-bottom: 2px solid #007ACC; /* Active indicator */
            }
            /* Styling cho nội dung bên trong mỗi tab (padding) */
            QWidget[objectName^="category_tab_content_"] { /* Selects widgets whose name starts with category_tab_content_ */
                padding: 15px;
            }
        """)
       


    def init_category_tabs(self):

        while self.tab_widget.count() > 0:
            self.tab_widget.removeTab(0)
        self.category_widgets.clear()

        if not self.categories_data:
            self.categories_data["General"] = []
            self.save_all_bookmarks()

        for category_name in sorted(self.categories_data.keys()):
            self._create_and_add_category_tab(category_name)
        
        if self.tab_widget.count() > 0:
            self.tab_widget.setCurrentIndex(0)

    def _create_and_add_category_tab(self, category_name):

        tab_content_widget = QWidget()
        tab_content_widget.setObjectName(f"category_tab_content_{category_name.replace(' ', '_')}") 
        tab_layout = QVBoxLayout(tab_content_widget)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(10)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)
        
        title_input = QLineEdit()
        title_input.setPlaceholderText("Bookmark Title")
        url_input = QLineEdit()
        url_input.setPlaceholderText("Bookmark URL (optional, e.g., https://example.com)")
        add_button = QPushButton("ADD")
        
        add_button.clicked.connect(
            lambda checked, cat=category_name, t_input=title_input, u_input=url_input: 
            self.add_bookmark_to_category(cat, t_input, u_input)
        )

        input_layout.addWidget(title_input)
        input_layout.addWidget(url_input)
        input_layout.addWidget(add_button)
        tab_layout.addLayout(input_layout)

        bookmark_table = QTableWidget(self)
        bookmark_table.setColumnCount(2)
        bookmark_table.setHorizontalHeaderLabels(["Title", "URL"])
        bookmark_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        bookmark_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        bookmark_table.setEditTriggers(QTableWidget.NoEditTriggers) 
        bookmark_table.setSelectionBehavior(QTableWidget.SelectRows)
        bookmark_table.setSelectionMode(QTableWidget.SingleSelection)
        
        bookmark_table.doubleClicked.connect(
            lambda index, cat=category_name, table=bookmark_table: 
            self.open_selected_bookmark(cat, table)
        )
        tab_layout.addWidget(bookmark_table)

        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)

        open_button = QPushButton("OPEN SELECTED")
        open_button.clicked.connect(
            lambda checked, cat=category_name, table=bookmark_table: 
            self.open_selected_bookmark(cat, table)
        )
        delete_button = QPushButton("DELETE SELECTED")
        delete_button.setObjectName("delete_button") # <-- ĐẶT OBJECT NAME Ở ĐÂY ĐỂ CSS BIẾT
        delete_button.clicked.connect(
            lambda checked, cat=category_name, table=bookmark_table: 
            self.delete_selected_bookmark(cat, table)
        )
        action_layout.addStretch()
        action_layout.addWidget(open_button)
        action_layout.addWidget(delete_button)
        tab_layout.addLayout(action_layout)

        self.tab_widget.addTab(tab_content_widget, category_name)
        
        self.category_widgets[category_name] = {
            "tab_widget_ref": tab_content_widget,
            "title_input": title_input,
            "url_input": url_input,
            "table": bookmark_table
        }
        self.populate_category_table(category_name)

    def load_all_bookmarks(self):
        if os.path.exists(ALL_BOOKMARKS_FILE):
            try:
                with open(ALL_BOOKMARKS_FILE, 'r', encoding='utf-8') as f:
                    self.categories_data = json.load(f)
            except json.JSONDecodeError:
                self.categories_data = {}
                QMessageBox.warning(self, "Error", f"Could not load bookmarks from {ALL_BOOKMARKS_FILE}. Invalid JSON format.")
        else:
            self.categories_data = {}
            self.categories_data["General"] = []
            self.save_all_bookmarks()

    def save_all_bookmarks(self):
        """Lưu tất cả bookmark vào file JSON duy nhất."""
        with open(ALL_BOOKMARKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.categories_data, f, indent=4, ensure_ascii=False)

    def populate_all_tables(self):
        """Điền dữ liệu vào tất cả các bảng của các category."""
        for category_name in self.categories_data.keys():
            self.populate_category_table(category_name)

    def populate_category_table(self, category_name):
        """Điền dữ liệu vào bảng của một category cụ thể."""
        if category_name not in self.category_widgets:
            return

        table = self.category_widgets[category_name]["table"]
        table.setRowCount(0)

        bookmarks_for_category = self.categories_data.get(category_name, [])

        for row_idx, bookmark_item in enumerate(bookmarks_for_category):
            table.insertRow(row_idx)
            table.setItem(row_idx, 0, QTableWidgetItem(bookmark_item.get('title', 'No Title')))
            table.setItem(row_idx, 1, QTableWidgetItem(bookmark_item.get('url', ''))) 

    def add_bookmark_to_category(self, category_name, title_input_widget, url_input_widget):
        """Thêm bookmark vào category được chỉ định."""
        title = title_input_widget.text().strip()
        url = url_input_widget.text().strip()

        if not title:
            QMessageBox.warning(self, "Input Error", "Please enter a title for the bookmark.")
            return

        new_bookmark = {'title': title}
        if url:
            if not url.startswith('http://') and not url.startswith('https://'):
                url = 'https://' + url
            new_bookmark['url'] = url

        self.categories_data.setdefault(category_name, []).append(new_bookmark)
        self.save_all_bookmarks()
        self.populate_category_table(category_name)
        
        title_input_widget.clear()
        url_input_widget.clear()
        table = self.category_widgets[category_name]["table"]
        table.scrollToBottom()
        table.selectRow(len(self.categories_data[category_name]) - 1)

    def delete_selected_bookmark(self, category_name, table_widget):
        """Xóa bookmark đã chọn từ bảng của category cụ thể."""
        selected_rows = table_widget.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Selection", "Please select a bookmark to delete.")
            return

        row_index = selected_rows[0].row()
        
        bookmark_to_delete = self.categories_data[category_name][row_index]
        title_to_delete = bookmark_to_delete.get('title', 'Unnamed Bookmark')

        reply = QMessageBox.question(self, 'Delete Bookmark',
                                     f"Are you sure you want to delete '{title_to_delete}' from '{category_name}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            del self.categories_data[category_name][row_index]
            self.save_all_bookmarks()
            self.populate_category_table(category_name)
            
            if not self.categories_data[category_name]:
                reply_delete_category = QMessageBox.question(self, 'Delete Category',
                                                             f"Category '{category_name}' is now empty. Do you want to remove this category?",
                                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply_delete_category == QMessageBox.Yes:
                    self.delete_category(category_name)


    def open_selected_bookmark(self, category_name, table_widget):
        """Mở URL của bookmark đã chọn (nếu có)."""
        selected_rows = table_widget.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Selection", "Please select a bookmark to open.")
            return

        row_index = selected_rows[0].row()
        url = self.categories_data[category_name][row_index].get('url')
        if url:
            QDesktopServices.openUrl(QUrl(url))
        else:
            QMessageBox.information(self, "No URL", "Selected bookmark does not have an associated URL.")

    def prompt_new_category(self):
        """Mở hộp thoại để người dùng nhập tên category mới."""
        self.show()
        self.raise_()
        self.activateWindow()

        category_name, ok = QInputDialog.getText(self, "New Category", "Enter new category name:")
        if ok and category_name:
            category_name = category_name.strip()
            if not category_name:
                QMessageBox.warning(self, "Input Error", "Category name cannot be empty.")
                return

            if category_name in self.categories_data:
                QMessageBox.warning(self, "Category Exists", f"Category '{category_name}' already exists.")
            else:
                self.categories_data[category_name] = []
                self.save_all_bookmarks()
                self._create_and_add_category_tab(category_name)
                self.tab_widget.setCurrentIndex(self.tab_widget.indexOf(self.category_widgets[category_name]["tab_widget_ref"]))
                QMessageBox.information(self, "Category Added", f"Category '{category_name}' has been added.")

    def delete_category(self, category_name):
        """Xóa toàn bộ một category."""
        if category_name not in self.categories_data:
            return

        reply = QMessageBox.question(self, 'Delete Category',
                                     f"Are you sure you want to delete the entire category '{category_name}' and all its bookmarks?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            tab_index = self.tab_widget.indexOf(self.category_widgets[category_name]["tab_widget_ref"])
            if tab_index != -1:
                self.tab_widget.removeTab(tab_index)
            
            del self.categories_data[category_name]
            del self.category_widgets[category_name]
            
            self.save_all_bookmarks()
            QMessageBox.information(self, "Category Deleted", f"Category '{category_name}' has been deleted.")
            
            if not self.categories_data:
                self.categories_data["General"] = []
                self.save_all_bookmarks()
                self._create_and_add_category_tab("General")


    def prompt_add_bookmark(self):
        """Mở hộp thoại để người dùng thêm bookmark vào category hiện tại."""
        self.show()
        self.raise_()
        self.activateWindow()
        
        current_category_name = self.tab_widget.tabText(self.tab_widget.currentIndex())
        if current_category_name in self.category_widgets:
            self.category_widgets[current_category_name]["title_input"].setFocus()
        else:
            QMessageBox.warning(self, "No Active Category", "Please select or create a category first.")


    # --- Window Control Methods ---
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

        add_bookmark_action = QAction("Add Bookmark (Current Tab)", self)
        add_bookmark_action.triggered.connect(self.show_window_and_add_bookmark_signal.emit)
        tray_menu.addAction(add_bookmark_action)

        add_category_action = QAction("Add New Category", self)
        add_category_action.triggered.connect(self.show_window_and_add_category_signal.emit)
        tray_menu.addAction(add_category_action)

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