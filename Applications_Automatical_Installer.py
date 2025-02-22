import sys
import os
import json
import logging
import time
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QCheckBox, QPushButton, QMessageBox, QLabel,
                             QSpacerItem, QSizePolicy, QScrollArea, QProgressBar)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
import requests
import winreg
import subprocess
import webbrowser

logging.basicConfig(filename='app_installer.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def store_url(productid):
    return f"ms-windows-store://pdp?hl=fr-fr&gl=fr&referrer=storeforweb&source=https%3A%2F%2Fwww.google.com%2F&productid={productid}&mode=mini&pos=7%2C2%2C1922%2C922"

def extension_url(id):
    return f"https://chromewebstore.google.com/detail/{id}"

def get_url(app_details):
    if 'type' in app_details:
        if app_details['type'] == 'microsoft':
            return store_url(app_details['productid'])
        elif app_details['type'] == 'extension':
            return extension_url(app_details['id'])
    return app_details['url']

class ClickableCheckBox(QCheckBox):
    def hitButton(self, pos):
        return self.rect().contains(pos)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.toggle()
            event.accept()
        else:
            super().keyPressEvent(event)
#=================== DOWNLOAD STATS ===================
class DownloadThread(QThread):
    progress_signal = pyqtSignal(int, float, float, float, float)
    finished_signal = pyqtSignal(str)

    def __init__(self, url, file_path):
        QThread.__init__(self)
        self.url = url
        self.file_path = file_path
        self.is_cancelled = False
        self.start_time = None

    def run(self):
        try:
            response = requests.get(self.url, stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            total_size_mb = total_size / (1024 * 1024)
            block_size = 8192
            downloaded = 0
            self.start_time = time.time()

            with open(self.file_path, "wb") as f:
                for data in response.iter_content(block_size):
                    if self.is_cancelled:
                        f.close()
                        os.remove(self.file_path)
                        return

                    size = f.write(data)
                    downloaded += size

                    if total_size:
                        percent = downloaded * 100 // total_size
                        downloaded_mb = downloaded / (1024 * 1024)
                        elapsed_time = time.time() - self.start_time
                        speed = downloaded / (1024 * 1024 * elapsed_time) if elapsed_time > 0 else 0
                        eta = (total_size - downloaded) / (speed * 1024 * 1024) if speed > 0 else 0

                        self.progress_signal.emit(percent, total_size_mb, downloaded_mb, speed, eta)

            self.finished_signal.emit(self.file_path)
        except Exception as e:
            logging.error(f"Download failed: {str(e)}")
            self.finished_signal.emit("")

    def cancel(self):
        self.is_cancelled = True
#=================== END OF DOWNLOAD STATS ===================

#=================== INSTALL APPLICATIONS ===================
class InstallationManager(QObject):
    installation_complete = pyqtSignal()
    installation_started = pyqtSignal(str)
    installation_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.queue = []
        self.current_thread = None
        self.current_app = ""

    def add_to_queue(self, app, details, downloads_path):
        self.queue.append((app, details, downloads_path))
        if not self.current_thread:
            self.process_next()

    def process_next(self):
        if self.queue:
            app, details, downloads_path = self.queue.pop(0)
            self.current_app = app
            url = get_url(details)
            app_type = details.get("type", "")

            if app_type in ['extension', 'microsoft'] or "(manual)" in app:
                webbrowser.open(url)
                QMessageBox.information(None, "Information", f"Please manually install {app} from the opened web page.")
                self.process_next()
            else:
                file_path = downloads_path / (f"{app}.msi" if url.endswith('.msi') else f"{app}.exe")
                self.current_thread = DownloadThread(url, str(file_path))
                self.current_thread.progress_signal.connect(self.parent().update_progress)
                self.current_thread.finished_signal.connect(lambda fp, a=app: self.install_application(fp, a))
                self.installation_started.emit(app)
                self.current_thread.start()
        else:
            self.installation_finished.emit()
            self.installation_complete.emit()

        self.parent().update_button_states()

    def install_application(self, file_path, app):
        if file_path:
            if file_path.endswith('.msi'):
                subprocess.Popen(["msiexec", "/i", file_path], shell=True)
            else:
                subprocess.Popen([file_path], shell=True)
            logging.info(f"Started installation of {app}")
        else:
            logging.error(f"Failed to download {app}")
            QMessageBox.critical(None, "Error", f"Failed to download {app}")

        self.current_thread = None
        self.current_app = ""
        self.process_next()

    def cancel_current_installation(self):
        if self.current_thread:
            self.current_thread.cancel()
            self.current_thread = None
            self.current_app = ""
            self.process_next()
#=================== END OF INSTALL APPLICATIONS ===================

class AppInstaller(QWidget):
    #=================== LOAD APPLICATIONS ===================
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
        QWidget {
            background-color: #0D1117;
            color: #C9D1D9;
            font-family: 'Segoe UI', sans-serif;
        }

        /* Titres */
        QLabel[objectName^="title"] {
            font-size: 16px;
            font-weight: 600;
            color: #58A6FF;
            padding: 15px 0;
            border-bottom: 2px solid #30363D;
        }

        /* Cases à cocher */
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
            border-radius: 4px;
        }

        /* Boutons */
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

        /* Barre de progression */
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

        /* Zones de défilement */
        QScrollArea {
            border: 3px solid #30363D;
            border-radius: 5px;
            background: transparent;
        }
        QScrollBar:vertical {
            background: transparent;
            width: 7px;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background: #30363D;
            min-height: 20px;
            border-radius: 6px;
        }

        QScrollBar:horizontal {
            background: transparent;
            width: 7px;
            margin: 0;
        }
        QScrollBar::handle:horizontal {
            background: #30363D;
            min-height: 20px;
            border-radius: 6px;
        }

        /* Étiquettes d'information */
        QLabel#infoLabel {
            font-size: 13px;
            color: #8B949E;
            padding: 6px 10px;
            background: #161B22;
            border-radius: 4px;
        }

        /* Fenêtres de message */
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

        /* Couleurs spécifiques aux types */
        QCheckBox[type="extension"] { color: #58A6FF; }
        QCheckBox[type="microsoft"] { color: #DB61A2; }
        QCheckBox[type="manual"] { color: #D29922; }
    """)
        self.setWindowTitle("Applications Installer")
        self.setGeometry(700, 200, 800, 600)
        self.load_applications()
        self.setup_ui()
        self.installation_manager = InstallationManager(self)
        self.installation_manager.installation_complete.connect(self.on_installation_complete)
        self.installation_manager.installation_started.connect(self.on_installation_started)
        self.installation_manager.installation_finished.connect(self.on_installation_finished)

    def load_applications(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(script_dir, 'applications.json')

        try:
            with open(json_path, 'r') as f:
                self.applications = json.load(f)
        except FileNotFoundError:
            logging.error(f"applications.json not found at {json_path}. Using default applications.")
            self.applications = self.get_default_applications()

    def get_default_applications(self):
        return {
            "Brave": {"url": "https://laptop-updates.brave.com/latest/winx64"},
            "Discord": {"url": "https://discord.com/api/downloads/distributions/app/installers/latest?channel=stable&platform=win&arch=x64"},
            "HWINFO (manual)": {"url": "https://www.hwinfo.com/download/"},
            "NVIDIA App (manual)": {"url": "https://fr.download.nvidia.com/nvapp/client/10.0.0.535/NVIDIA_app_beta_v10.0.0.535.exe"},
            "Dark Reader": {"url": extension_url("dark-reader/eimadpbcbfnmbkopoojfekhnkhdbieeh"), "type": "extension"},
            "Google Traduction": {"url": extension_url("google-translate/aapbdbdomjkkjkaonfhkkikfgjllcleb"), "type": "extension"},
        }
    #=================== LOAD APPLICATIONS ===================

    #=================== UI ===================
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)

        titles = ["Applications", "Chrome Extensions", "Microsoft Store Applications"]
        title_layout = QHBoxLayout()
        for title_text in titles:
            title_label = QLabel(title_text)
            title_label.setFont(title_font)
            title_layout.addWidget(title_label, alignment=Qt.AlignCenter)
        layout.addLayout(title_layout)

        select_all_layout = QHBoxLayout()
        layout.addLayout(select_all_layout)

        columns_layout = QHBoxLayout()
        layout.addLayout(columns_layout)

        self.checkboxes = {}
        self.column_checkboxes = [[], [], []]

        for idx, title in enumerate(titles):
            column_layout = QVBoxLayout()
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_content = QWidget()
            scroll_layout = QVBoxLayout(scroll_content)
            scroll_area.setWidget(scroll_content)
            scroll_area.setFixedWidth(230)
            column_layout.addWidget(scroll_area)

            select_all_button = self.create_select_all_button(idx)
            select_all_layout.addWidget(select_all_button)

            columns_layout.addLayout(column_layout)
            if idx < len(titles) - 1:
                columns_layout.addItem(QSpacerItem(40, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

            self.column_checkboxes[idx] = scroll_layout

        for app, details in self.applications.items():
            app_type = self.get_application_type(details)
            checkbox = ClickableCheckBox(app)
            if "(manual)" in app:
                app_type = "manual"
            checkbox.setProperty("type", app_type)
            column_idx = self.get_column_index_for_app_type(app_type)
            # Connexion pour mettre à jour le texte du bouton quand la checkbox change
            checkbox.toggled.connect(lambda checked, col=column_idx: self.update_select_all_button(col))
            self.column_checkboxes[column_idx].addWidget(checkbox)
            self.checkboxes[app] = checkbox


        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)

        self.install_button = QPushButton("Install")
        self.install_button.clicked.connect(self.install_informations)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_installation)
        self.cancel_button.setEnabled(False)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.install_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # Labels - informations de téléchargement
        self.current_app_label = QLabel()
        self.file_size_label = QLabel()
        self.speed_label = QLabel()
        self.eta_label = QLabel()

        info_layout = QHBoxLayout()
        info_layout.addWidget(self.current_app_label)
        info_layout.addWidget(self.file_size_label)
        info_layout.addWidget(self.speed_label)
        info_layout.addWidget(self.eta_label)

        layout.addLayout(info_layout)

    def create_select_all_button(self, column_index):
        button = QPushButton("Select All")
        button.clicked.connect(lambda _, col=column_index: self.toggle_select_column(col))
        if not hasattr(self, 'select_buttons'):
            self.select_buttons = {}
        self.select_buttons[column_index] = button
        return button

    def toggle_select_column(self, column_index):
        layout = self.column_checkboxes[column_index]
        any_checked = any(layout.itemAt(i).widget().isChecked() for i in range(layout.count()))
        new_state = False if any_checked else True
        for i in range(layout.count()):
            checkbox = layout.itemAt(i).widget()
            checkbox.setChecked(new_state)
        self.update_select_all_button(column_index)

    def update_select_all_button(self, column_index):
        layout = self.column_checkboxes[column_index]
        any_checked = any(layout.itemAt(i).widget().isChecked() for i in range(layout.count()))
        button = self.select_buttons[column_index]
        if any_checked:
            button.setText("Deselect All")
        else:
            button.setText("Select All")


    def get_column_index_for_app_type(self, app_type):
        if app_type == 'extension':
            return 1
        elif app_type == 'microsoft':
            return 2
        return 0

    def create_and_add_button(self, text, slot, layout):
        button = QPushButton(text)
        button.clicked.connect(slot)
        layout.addWidget(button)
    #================ END OF UI ================

    #================================= INSTALL APPLICATIONS ================================
    def get_application_type(self, app_details):
        if "(manual)" in app_details.get("url", ""):
            return "manual"
        return app_details.get("type", "")

    def install_informations(self):
        if self.installation_manager.current_thread:
            QMessageBox.warning(self, "Warning", "An installation is already in progress. Please wait for it to finish.")
            return

        applications_to_install = [app for app, checkbox in self.checkboxes.items() if checkbox.isChecked()]
        if not applications_to_install:
            QMessageBox.information(self, "Information", "No application selected!")
            return

        downloads_path = self.get_downloads_path()
        for app in applications_to_install:
            details = self.applications[app]
            self.installation_manager.add_to_queue(app, details, downloads_path)
        self.update_button_states()

    def update_progress(self, percent, total_size_mb, downloaded_mb, speed, eta):
        self.progress_bar.setValue(percent)
        self.file_size_label.setText(f"Total size: {downloaded_mb:.2f}/{total_size_mb:.2f}MB")
        self.speed_label.setText(f"Speed: {speed:.2f}MB/s")
        self.eta_label.setText(f"ETA: {eta:.0f}s")

    def update_button_states(self):
        self.install_button.setEnabled(False)
        self.cancel_button.setEnabled(True)

    def cancel_installation(self):
        self.installation_manager.cancel_current_installation()
        self.progress_bar.setValue(0)

    def on_installation_complete(self):
        self.close()

    def on_installation_started(self, app):
        self.update_button_states()
        self.current_app_label.setText(f"Installing: {app}")
        self.file_size_label.setText("Total size: -")
        self.speed_label.setText("Speed: -")
        self.eta_label.setText("ETA: -")

    def on_installation_finished(self):
        self.update_button_states()
        self.progress_bar.setValue(0)
        self.current_app_label.setText("")
        self.file_size_label.setText("")
        self.speed_label.setText("")
        self.eta_label.setText("")
    #============================= END OF INSTALL APPLICATIONS ==============================

    #================================= DOWNLOAD PATH ================================
    def get_downloads_path(self):
        sub_key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        downloads_guid = "{374DE290-123F-4565-9164-39C4925E467B}"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                value, _ = winreg.QueryValueEx(key, downloads_guid)
                downloads_path = os.path.expandvars(value)
                return Path(downloads_path)
        except FileNotFoundError:
            return Path.home() / "Downloads"
    #============================= END OF DOWNLOAD PATH ==============================

if __name__ == '__main__':
    app = QApplication(sys.argv)
    installer = AppInstaller()
    installer.show()
    sys.exit(app.exec_())