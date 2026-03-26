#!/usr/bin/env python3
import sys
import os
import json
import logging
import time
import subprocess
import webbrowser
from pathlib import Path
from functools import partial
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

import requests

try:
    import winreg
except ImportError:
    winreg = None  # Allow running on non-Windows for development/testing

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton,
    QMessageBox, QLabel, QSpacerItem, QSizePolicy, QScrollArea, QProgressBar,
    QLineEdit
)
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QImage, QPainterPath
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QSize

# --- Constants ---
ICON_DISPLAY_SIZE = 24
ICON_LOAD_SIZE = 64
ICON_CORNER_RADIUS = 8
DOWNLOAD_BLOCK_SIZE = 65536  # 64KB chunks for faster downloads
DOWNLOAD_TIMEOUT = 15
IMAGE_LOAD_TIMEOUT = 5
WHITE_BORDER_THRESHOLD = 240
MAX_CONCURRENT_IMAGE_LOADERS = 6
WINDOW_TITLE = "Applications Installer"
WINDOW_GEOMETRY = (700, 200, 800, 600)
SCROLL_COLUMN_WIDTH = 230

# --- Logging Configuration ---
logging.basicConfig(
    filename='app_installer.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Resource Path (PyInstaller compatibility) ---
def resource_path(relative_path: str) -> Path:
    """Get the absolute path to a resource, works for dev and PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).parent / relative_path

# --- Stylesheet ---
STYLE_SHEET = """
QWidget {
    background-color: #0D1117;
    color: #C9D1D9;
    font-family: 'Segoe UI', sans-serif;
}

QLabel[objectName^="title"] {
    font-size: 16px;
    font-weight: 600;
    color: #58A6FF;
    padding: 15px 0;
    border-bottom: 2px solid #30363D;
}

QCheckBox {
    spacing: 10px;
    padding: 6px;
    background: #161B22;
    border-radius: 6px;
    margin: 2px 0;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #30363D;
    border-radius: 4px;
}
QCheckBox::indicator:checked {
    background: qradialgradient(cx: 0.5, cy: 0.5, radius: 0.6,
                                fx: 0.5, fy: 0.5,
                                stop: 0 #3FBA58,
                                stop: 1 #238636);
    border: 2px solid #2EA043;
}

QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #238636, stop:1 #2EA043);
    border: 1px solid #2EA043;
    border-radius: 6px;
    padding: 10px 25px;
    color: white;
    font-weight: 600;
    min-width: 120px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #2EA043, stop:1 #3FBA58);
}
QPushButton:pressed {
    background: #238636;
}
QPushButton:disabled {
    background: #484F58;
    border-color: #6E7681;
}

QProgressBar {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 8px;
    height: 24px;
    text-align: center;
    font-weight: 500;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #2EA043, stop:1 #3FBA58);
    border-radius: 7px;
    margin: 2px;
}

QScrollArea {
    border: 3px solid #30363D;
    border-radius: 5px;
    background: transparent;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: transparent;
    width: 7px;
    margin: 0;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #30363D;
    min-height: 20px;
    border-radius: 6px;
}

QLabel#infoLabel {
    font-size: 13px;
    color: #8B949E;
    padding: 6px 10px;
    background: #161B22;
    border-radius: 4px;
}

QLineEdit {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 6px;
    padding: 8px 12px;
    color: #C9D1D9;
    font-size: 14px;
}
QLineEdit:focus {
    border-color: #58A6FF;
}

QMessageBox {
    background: #0D1117;
    border: 1px solid #30363D;
}
QMessageBox QLabel {
    color: #C9D1D9;
    font-size: 14px;
}
QMessageBox QPushButton {
    min-width: 80px;
    padding: 8px 16px;
}

QCheckBox[type="extension"] { color: #58A6FF; }
QCheckBox[type="microsoft"] { color: #DB61A2; }
QCheckBox[type="manual"] { color: #D29922; }
"""

# --- HTTP Headers ---
REQUEST_HEADERS = {
    "User-Agent": "ApplicationsInstaller/1.0"
}

# --- Utility Functions ---
def store_url(productid: str) -> str:
    """Generate a Microsoft Store URL."""
    return f"ms-windows-store://pdp?hl=en-us&gl=us&productid={productid}&mode=mini"

def extension_url(ext_id: str) -> str:
    """Generate a Chrome Web Store extension URL."""
    return f"https://chromewebstore.google.com/detail/{ext_id}"

def get_url(app_details: dict) -> str:
    """Return the appropriate URL based on application type."""
    app_type = app_details.get('type')
    if app_type == 'microsoft':
        return store_url(app_details['productid'])
    elif app_type == 'extension':
        return extension_url(app_details['id'])
    return app_details.get('url', '')

def remove_white_border(pixmap: QPixmap, threshold: int = WHITE_BORDER_THRESHOLD) -> QPixmap:
    """Remove white borders connected to the edges of an image using flood fill."""
    image = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
    width, height = image.width(), image.height()

    if width == 0 or height == 0:
        return pixmap

    visited = set()
    stack = []

    def is_white(x: int, y: int) -> bool:
        color = image.pixelColor(x, y)
        return all(c >= threshold for c in (color.red(), color.green(), color.blue()))

    # Add border pixels to the stack
    for x in range(width):
        for y_pos in (0, height - 1):
            if is_white(x, y_pos) and (x, y_pos) not in visited:
                stack.append((x, y_pos))
                visited.add((x, y_pos))
    for y in range(height):
        for x_pos in (0, width - 1):
            if is_white(x_pos, y) and (x_pos, y) not in visited:
                stack.append((x_pos, y))
                visited.add((x_pos, y))

    # Flood fill algorithm
    while stack:
        x, y = stack.pop()
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited and is_white(nx, ny):
                stack.append((nx, ny))
                visited.add((nx, ny))

    # Make visited white pixels transparent
    for x, y in visited:
        color = image.pixelColor(x, y)
        color.setAlpha(0)
        image.setPixelColor(x, y, color)

    return QPixmap.fromImage(image)

def round_pixmap(pixmap: QPixmap, radius: int = ICON_CORNER_RADIUS) -> QPixmap:
    """Apply rounded corners to a QPixmap."""
    size = pixmap.size()
    rounded = QPixmap(size)
    rounded.fill(Qt.transparent)
    painter = QPainter(rounded)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(0, 0, size.width(), size.height(), radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()
    return rounded

# --- Custom Widget ---
class ClickableCheckBox(QCheckBox):
    """Checkbox with proper click and keyboard support."""
    def hitButton(self, pos):
        return self.rect().contains(pos)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.toggle()
            event.accept()
        else:
            super().keyPressEvent(event)

# --- Download & Installation ---
class DownloadThread(QThread):
    """Thread for downloading a file in the background."""
    progress_signal = pyqtSignal(int, float, float, float, float)  # percent, total_mb, downloaded_mb, speed, eta
    finished_signal = pyqtSignal(str)  # file path or empty on failure

    def __init__(self, url: str, file_path: str):
        super().__init__()
        self.url = url
        self.file_path = file_path
        self.is_cancelled = False
        self.start_time = None

    def run(self):
        try:
            with requests.get(self.url, stream=True, timeout=DOWNLOAD_TIMEOUT, headers=REQUEST_HEADERS) as response:
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                total_size_mb = total_size / (1024 * 1024)
                downloaded = 0
                self.start_time = time.time()

                with open(self.file_path, "wb") as f:
                    for data in response.iter_content(DOWNLOAD_BLOCK_SIZE):
                        if self.is_cancelled:
                            break
                        downloaded += f.write(data)
                        if total_size:
                            percent = downloaded * 100 // total_size
                            downloaded_mb = downloaded / (1024 * 1024)
                            elapsed_time = time.time() - self.start_time
                            speed = downloaded_mb / elapsed_time if elapsed_time > 0 else 0
                            eta = (total_size - downloaded) / (speed * 1024 * 1024) if speed > 0 else 0
                            self.progress_signal.emit(percent, total_size_mb, downloaded_mb, speed, eta)

            if self.is_cancelled:
                self._cleanup_file()
                return

            self.finished_signal.emit(self.file_path)
        except requests.RequestException as e:
            logging.error(f"Download failed for {self.url}: {e}")
            self._cleanup_file()
            self.finished_signal.emit("")

    def _cleanup_file(self):
        """Safely remove the partially downloaded file."""
        try:
            if os.path.exists(self.file_path):
                os.remove(self.file_path)
        except OSError as e:
            logging.warning(f"Failed to clean up file {self.file_path}: {e}")

    def cancel(self):
        """Cancel the ongoing download."""
        self.is_cancelled = True


class InstallationManager(QObject):
    """Manages the installation queue."""
    installation_complete = pyqtSignal()
    installation_started = pyqtSignal(str, int, int)  # app_name, current_index, total_count
    installation_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.queue = []
        self.current_thread = None
        self.current_app = ""
        self.total_count = 0
        self.current_index = 0

    def add_to_queue(self, app: str, details: dict, downloads_path: Path):
        """Add an application to the installation queue."""
        self.queue.append((app, details, downloads_path))
        self.total_count = len(self.queue) + self.current_index
        if not self.current_thread:
            self.process_next()

    def process_next(self):
        """Process the next application in the queue."""
        while self.queue:
            app, details, downloads_path = self.queue.pop(0)
            self.current_app = app
            self.current_index += 1
            url = get_url(details)
            app_type = details.get("type", "")

            if "(manual)" in app.lower():
                webbrowser.open(url)
                QMessageBox.information(None, "Information", f"Please install {app} manually from the opened page.")
                continue
            elif app_type in ('extension', 'microsoft'):
                webbrowser.open(url)
                continue
            else:
                file_ext = ".msi" if url.endswith('.msi') else ".exe"
                file_path = downloads_path / f"{app}{file_ext}"
                self.current_thread = DownloadThread(url, str(file_path))
                self.current_thread.progress_signal.connect(self.parent().update_progress)
                self.current_thread.finished_signal.connect(partial(self.install_application, app=app))
                self.installation_started.emit(app, self.current_index, self.total_count)
                self.current_thread.start()
                break
        else:
            self._reset()
            self.installation_finished.emit()
            self.installation_complete.emit()
        self.parent().update_button_states()

    def install_application(self, file_path: str, app: str):
        """Launch the installer for a downloaded application."""
        if file_path:
            try:
                if file_path.endswith('.msi'):
                    subprocess.Popen(["msiexec", "/i", file_path])
                else:
                    subprocess.Popen([file_path])
                logging.info(f"Installation started for {app}")
            except OSError as e:
                logging.error(f"Failed to launch installer for {app}: {e}")
                QMessageBox.critical(None, "Error", f"Failed to launch installer for {app}:\n{e}")
        else:
            logging.error(f"Download failed for {app}")
            QMessageBox.critical(None, "Error", f"Download failed for {app}")

        self.current_thread = None
        self.current_app = ""
        self.process_next()

    def cancel_current_installation(self):
        """Cancel the current installation."""
        if self.current_thread:
            self.current_thread.cancel()
            self.current_thread = None
            self.current_app = ""
        self.queue.clear()
        self._reset()
        self.installation_finished.emit()

    def _reset(self):
        """Reset counters."""
        self.total_count = 0
        self.current_index = 0


# --- Async Image Loader ---
class ImageLoader(QThread):
    """Thread for loading and processing application logos asynchronously."""
    image_loaded = pyqtSignal(str, QPixmap)

    def __init__(self, app_name: str, logo_url: str):
        super().__init__()
        self.app_name = app_name
        self.logo_url = logo_url

    def run(self):
        try:
            response = requests.get(self.logo_url, timeout=IMAGE_LOAD_TIMEOUT, headers=REQUEST_HEADERS)
            response.raise_for_status()
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)

            if pixmap.isNull():
                logging.warning(f"Failed to decode image for {self.app_name}")
                return

            # Resize first for performance
            pixmap = pixmap.scaled(ICON_LOAD_SIZE, ICON_LOAD_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            pixmap = remove_white_border(pixmap)
            pixmap = round_pixmap(pixmap)

            self.image_loaded.emit(self.app_name, pixmap)
        except requests.RequestException as e:
            logging.warning(f"Failed to load image for {self.app_name}: {e}")


# --- Main Application ---
class AppInstaller(QWidget):
    """Main application installer window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setGeometry(*WINDOW_GEOMETRY)
        self.setStyleSheet(STYLE_SHEET)
        self.checkboxes = {}
        self.column_checkboxes = []
        self.select_buttons = {}
        self.image_loaders = []
        self._image_loader_pool = []  # Track active loaders for throttling
        self._pending_image_loads = []  # Queue for pending image loads

        self.load_applications()
        self.setup_ui()

        self.installation_manager = InstallationManager(self)
        self.installation_manager.installation_complete.connect(self.on_installation_complete)
        self.installation_manager.installation_started.connect(self.on_installation_started)
        self.installation_manager.installation_finished.connect(self.on_installation_finished)

    def load_applications(self):
        """Load applications from the JSON file."""
        json_path = resource_path('applications.json')
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                self.applications = json.load(f)
        except FileNotFoundError:
            logging.error(f"applications.json not found at {json_path}. Using defaults.")
            self.applications = self.get_default_applications()
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in applications.json: {e}. Using defaults.")
            self.applications = self.get_default_applications()

    def get_default_applications(self) -> dict:
        """Return a minimal default application list."""
        return {
            "Brave": {"url": "https://laptop-updates.brave.com/latest/winx64"},
            "Discord": {
                "url": "https://discord.com/api/downloads/distributions/app/installers/latest?channel=stable&platform=win&arch=x64",
                "logo": "https://img.icons8.com/color/2x/discord"
            },
        }

    def setup_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)

        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍  Search applications...")
        self.search_bar.textChanged.connect(self.filter_applications)
        main_layout.addWidget(self.search_bar)

        # Column titles
        title_layout = QHBoxLayout()
        titles = ["Applications", "Chrome Extensions", "Microsoft Store"]
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        for text in titles:
            label = QLabel(text)
            label.setFont(title_font)
            label.setObjectName("title")
            title_layout.addWidget(label, alignment=Qt.AlignCenter)
        main_layout.addLayout(title_layout)

        # Select All buttons
        select_all_layout = QHBoxLayout()
        main_layout.addLayout(select_all_layout)

        # Checkbox columns
        columns_layout = QHBoxLayout()
        for idx in range(len(titles)):
            column = QVBoxLayout()
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            content = QWidget()
            col_layout = QVBoxLayout(content)
            scroll.setWidget(content)
            scroll.setFixedWidth(SCROLL_COLUMN_WIDTH)
            column.addWidget(scroll)
            button = QPushButton("Select All")
            button.clicked.connect(partial(self.toggle_select_column, column_index=idx))
            select_all_layout.addWidget(button)
            self.select_buttons[idx] = button
            self.column_checkboxes.append(col_layout)
            columns_layout.addLayout(column)
            if idx < len(titles) - 1:
                columns_layout.addItem(QSpacerItem(40, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        main_layout.addLayout(columns_layout)

        # Add applications with async logo loading
        for app, details in self.applications.items():
            app_type = self.get_application_type(details)
            if "(manual)" in app.lower():
                app_type = "manual"
            checkbox = ClickableCheckBox(app)
            checkbox.setProperty("type", app_type)

            # Queue async logo loading
            logo_link = details.get("logo")
            if not logo_link and (app_url := details.get("url")):
                domain = urlparse(app_url).netloc
                if domain:
                    logo_link = f"https://logo.clearbit.com/{domain}"
            if logo_link and logo_link.lower().startswith("http"):
                self._pending_image_loads.append((app, logo_link))

            col_idx = self.get_column_index_for_app_type(app_type)
            checkbox.toggled.connect(partial(self.update_select_all_button, column_index=col_idx))
            self.column_checkboxes[col_idx].addWidget(checkbox)
            self.checkboxes[app] = checkbox

        # Start loading images with throttling
        self._start_image_loading()

        # Action buttons
        btn_layout = QHBoxLayout()
        self.install_button = QPushButton("Install")
        self.install_button.clicked.connect(self.start_installation)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_installation)
        self.cancel_button.setEnabled(False)
        btn_layout.addWidget(self.install_button)
        btn_layout.addWidget(self.cancel_button)
        main_layout.addLayout(btn_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)

        # Download info labels
        info_layout = QHBoxLayout()
        self.current_app_label = QLabel()
        self.queue_label = QLabel()
        self.file_size_label = QLabel()
        self.speed_label = QLabel()
        self.eta_label = QLabel()
        for widget in (self.current_app_label, self.queue_label, self.file_size_label, self.speed_label, self.eta_label):
            info_layout.addWidget(widget)
        main_layout.addLayout(info_layout)

        # Status label (shown when all installations complete)
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #3FBA58; font-size: 14px; font-weight: 600; padding: 8px;")
        self.status_label.hide()
        main_layout.addWidget(self.status_label)

    def _start_image_loading(self):
        """Start loading images with a concurrency limit."""
        while self._pending_image_loads and len(self._image_loader_pool) < MAX_CONCURRENT_IMAGE_LOADERS:
            app_name, logo_url = self._pending_image_loads.pop(0)
            loader = ImageLoader(app_name, logo_url)
            loader.image_loaded.connect(self.update_checkbox_icon)
            loader.finished.connect(partial(self._on_image_loader_finished, loader))
            self._image_loader_pool.append(loader)
            self.image_loaders.append(loader)
            loader.start()

    def _on_image_loader_finished(self, loader):
        """Called when an image loader finishes — start the next one."""
        if loader in self._image_loader_pool:
            self._image_loader_pool.remove(loader)
        self._start_image_loading()

    def filter_applications(self, text: str):
        """Filter visible checkboxes based on search text."""
        search = text.lower().strip()
        for app_name, checkbox in self.checkboxes.items():
            checkbox.setVisible(search == "" or search in app_name.lower())

    def update_checkbox_icon(self, app_name: str, pixmap: QPixmap):
        """Update the checkbox icon with the loaded image."""
        if app_name in self.checkboxes:
            self.checkboxes[app_name].setIcon(QIcon(pixmap))
            self.checkboxes[app_name].setIconSize(QSize(ICON_DISPLAY_SIZE, ICON_DISPLAY_SIZE))

    def toggle_select_column(self, column_index: int):
        """Toggle all checkboxes in a column."""
        layout = self.column_checkboxes[column_index]
        visible_widgets = [
            layout.itemAt(i).widget() for i in range(layout.count())
            if layout.itemAt(i).widget() and layout.itemAt(i).widget().isVisible()
        ]
        any_checked = any(w.isChecked() for w in visible_widgets)
        for w in visible_widgets:
            w.setChecked(not any_checked)
        self.update_select_all_button(column_index)

    def update_select_all_button(self, column_index: int):
        """Update the Select All/Deselect All button text."""
        layout = self.column_checkboxes[column_index]
        any_checked = any(
            layout.itemAt(i).widget().isChecked()
            for i in range(layout.count())
            if layout.itemAt(i).widget()
        )
        self.select_buttons[column_index].setText("Deselect All" if any_checked else "Select All")

    def get_column_index_for_app_type(self, app_type: str) -> int:
        """Return the column index for a given application type."""
        return {'extension': 1, 'microsoft': 2}.get(app_type, 0)

    def get_application_type(self, app_details: dict) -> str:
        """Determine the application type."""
        return app_details.get("type", "")

    def start_installation(self):
        """Start installing selected applications."""
        if self.installation_manager.current_thread:
            QMessageBox.warning(self, "Warning", "An installation is already in progress. Please wait.")
            return

        applications_to_install = [app for app, cb in self.checkboxes.items() if cb.isChecked()]
        if not applications_to_install:
            QMessageBox.information(self, "Information", "No application selected!")
            return

        self.status_label.hide()
        downloads_path = self.get_downloads_path()
        for app in applications_to_install:
            self.installation_manager.add_to_queue(app, self.applications[app], downloads_path)
        self.update_button_states()

    def update_progress(self, percent: int, total_size_mb: float, downloaded_mb: float, speed: float, eta: float):
        """Update the progress bar and download info."""
        self.progress_bar.setValue(percent)
        self.file_size_label.setText(f"Size: {downloaded_mb:.1f}/{total_size_mb:.1f} MB")
        self.speed_label.setText(f"Speed: {speed:.1f} MB/s")
        minutes, seconds = divmod(int(eta), 60)
        self.eta_label.setText(f"ETA: {minutes}m {seconds}s" if minutes else f"ETA: {seconds}s")

    def update_button_states(self):
        """Update button enabled/disabled states."""
        is_installing = bool(self.installation_manager.current_thread)
        self.install_button.setEnabled(not is_installing)
        self.cancel_button.setEnabled(is_installing)

    def cancel_installation(self):
        """Cancel the current installation and clear the queue."""
        self.installation_manager.cancel_current_installation()
        self.progress_bar.setValue(0)
        self.status_label.setText("⚠️  Installation cancelled.")
        self.status_label.setStyleSheet("color: #D29922; font-size: 14px; font-weight: 600; padding: 8px;")
        self.status_label.show()

    def on_installation_started(self, app: str, current: int, total: int):
        """Update UI when an installation starts."""
        self.current_app_label.setText(f"Installing: {app}")
        self.queue_label.setText(f"({current}/{total})")
        self.file_size_label.setText("Size: —")
        self.speed_label.setText("Speed: —")
        self.eta_label.setText("ETA: —")
        self.update_button_states()

    def on_installation_finished(self):
        """Reset UI after all installations are done."""
        self.progress_bar.setValue(0)
        self.current_app_label.setText("")
        self.queue_label.setText("")
        self.file_size_label.setText("")
        self.speed_label.setText("")
        self.eta_label.setText("")
        self.update_button_states()

    def on_installation_complete(self):
        """Show completion message instead of closing."""
        self.status_label.setText("✅  All installations completed successfully!")
        self.status_label.setStyleSheet("color: #3FBA58; font-size: 14px; font-weight: 600; padding: 8px;")
        self.status_label.show()

    def get_downloads_path(self) -> Path:
        """Get the Windows Downloads folder path."""
        if winreg is None:
            return Path.home() / "Downloads"
        sub_key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        downloads_guid = "{374DE290-123F-4565-9164-39C4925E467B}"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                value, _ = winreg.QueryValueEx(key, downloads_guid)
                return Path(os.path.expandvars(value))
        except (FileNotFoundError, OSError):
            return Path.home() / "Downloads"

    def closeEvent(self, event):
        """Wait for image loader threads to finish before closing."""
        for loader in self.image_loaders:
            if loader.isRunning():
                loader.quit()
                loader.wait(2000)  # Wait up to 2 seconds per thread
        event.accept()


# --- Entry Point ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    installer = AppInstaller()
    installer.show()
    sys.exit(app.exec_())