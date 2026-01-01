from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QSystemTrayIcon, QMenu, QAction, QMessageBox,
    QLabel, QSizePolicy, QTabWidget, QStyle, QInputDialog
)
from PyQt5.QtGui import QIcon, QDesktopServices, QMouseEvent
from PyQt5.QtCore import QUrl, Qt, QPoint, pyqtSignal
import sys
import json
import os