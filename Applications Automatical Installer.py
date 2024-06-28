import sys
import os
import json
import logging
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

# Set up logging
logging.basicConfig(filename='app_installer.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class DownloadThread(QThread):
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str)

    def __init__(self, url, file_path):
        QThread.__init__(self)
        self.url = url
        self.file_path = file_path

    def run(self):
        try:
            response = requests.get(self.url, stream=True)
            response.raise_for_status()  # This will raise an exception for HTTP errors
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024
            with open(self.file_path, "wb") as f:
                for data in response.iter_content(block_size):
                    f.write(data)
                    if total_size:
                        self.progress_signal.emit(f.tell() * 100 // total_size)
            self.finished_signal.emit(self.file_path)
        except Exception as e:
            logging.error(f"Download failed: {str(e)}")
            self.finished_signal.emit("")

class InstallationManager(QObject):
    installation_complete = pyqtSignal()
    installation_started = pyqtSignal()
    installation_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.queue = []
        self.current_thread = None

    def add_to_queue(self, app, details, downloads_path):
        self.queue.append((app, details, downloads_path))
        if not self.current_thread:
            self.installation_started.emit()
            self.process_next()

    def process_next(self):
        if self.queue:
            app, details, downloads_path = self.queue.pop(0)
            url = details["url"]
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
                self.current_thread.start()
        else:
            self.installation_finished.emit()
            self.installation_complete.emit()

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
        self.process_next()

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

class AppInstaller(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Applications Installer")
        self.setGeometry(700, 200, 800, 600)
        self.load_applications()
        self.setup_ui()
        self.installation_manager = InstallationManager(self)
        self.installation_manager.installation_complete.connect(self.on_installation_complete)
        self.installation_manager.installation_started.connect(self.on_installation_started)
        self.installation_manager.installation_finished.connect(self.on_installation_finished)

    def load_applications(self):
        try:
            with open('applications.json', 'r') as f:
                self.applications = json.load(f)
            # Generate URLs for Microsoft Store apps and Chrome extensions
            for app, details in self.applications.items():
                if 'type' in details:
                    details['url'] = get_url(details)
        except FileNotFoundError:
            logging.error("applications.json not found. Using default applications.")
            self.applications = self.get_default_applications()

    def get_default_applications(self):
        def Store_url(productid):
            return f"ms-windows-store://pdp?hl=fr-fr&gl=fr&referrer=storeforweb&source=https%3A%2F%2Fwww.google.com%2F&productid={productid}&mode=mini&pos=7%2C2%2C1922%2C922"
        def extension_url(id):
            return f"https://chromewebstore.google.com/detail/{id}"
        return {
            "Brave": {"url": "https://laptop-updates.brave.com/latest/winx64"},
            "Discord": {"url": "https://discord.com/api/downloads/distributions/app/installers/latest?channel=stable&platform=win&arch=x64"},
            "Google Drive": {"url": "https://dl.google.com/drive-file-stream/GoogleDriveSetup.exe"},
            "Epic Games": {"url": "https://launcher-public-service-prod06.ol.epicgames.com/launcher/api/installer/download/EpicGamesLauncherInstaller.msi"},
            "Git": {"url": "https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/Git-2.44.0-64-bit.exe"},
            "Steam ": {"url": "https://cdn.akamai.steamstatic.com/client/installer/SteamSetup.exe"},
            "Winrar": {"url": "https://www.win-rar.com/fileadmin/winrar-versions/winrar/winrar-x64-700fr.exe"},
            "HWINFO (manual)": {"url": "https://www.hwinfo.com/download/"},
            "NVIDIA App (manual)": {"url": "https://fr.download.nvidia.com/nvapp/client/10.0.0.535/NVIDIA_app_beta_v10.0.0.535.exe"},
            "Dark Reader": {"url": extension_url("dark-reader/eimadpbcbfnmbkopoojfekhnkhdbieeh"), "type": "extension"},
            "Google Traduction": {"url": extension_url("google-translate/aapbdbdomjkkjkaonfhkkikfgjllcleb"), "type": "extension"},
            "Hower Zoom+": {"url": extension_url("hover-zoom%2B/pccckmaobkjjboncdfnnofkonhgpceea"), "type": "extension"},
            "Return YouTube Dislike": {"url": extension_url("return-youtube-dislike/gebbhagfogifgggkldgodflihgfeippi"), "type": "extension"},
            "SponsorBlock": {"url": extension_url("sponsorblock-for-youtube/mnjggcdmjocbbbhaepdhchncahnbgone"), "type": "extension"},
            "Visual Studio Code": {"url": Store_url("xp9khm4bk9fz7q"), "type": "microsoft"},
            "Office": {"url": Store_url("9wzdncrd29v9"), "type": "microsoft"},
        }

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
            checkbox = QCheckBox(app)
            color = self.get_color_for_app_type(app_type, app)
            checkbox.setStyleSheet(f"color: {color}")
            
            column_idx = self.get_column_index_for_app_type(app_type)
            self.column_checkboxes[column_idx].addWidget(checkbox)
            self.checkboxes[app] = checkbox

        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)

        self.create_and_add_button("Install", self.install_applications, button_layout)
        self.create_and_add_button("Quit", self.close, button_layout)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.install_button = QPushButton("Install")
        self.install_button.clicked.connect(self.install_applications)
    
    def create_select_all_button(self, column_index):
        button = QPushButton("Select All")
        button.clicked.connect(lambda: self.select_all_column(self.column_checkboxes[column_index]))
        return button

    def get_color_for_app_type(self, app_type, app_name):
        if "manual" in app_name:
            return 'purple'
        if app_type == 'extension':
            return 'green'
        if app_type == 'microsoft':
            return 'blue'

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

    def select_all_column(self, column_checkboxes):
        check_state = not column_checkboxes.itemAt(0).widget().isChecked()
        for i in range(column_checkboxes.count()):
            checkbox = column_checkboxes.itemAt(i).widget()
            checkbox.setChecked(check_state)

    def get_application_type(self, app_details):
        return app_details.get("type", "")

    def install_applications(self):
        applications_to_install = [app for app, checkbox in self.checkboxes.items() if checkbox.isChecked()]
        if not applications_to_install:
            QMessageBox.information(self, "Information", "No application selected!")
            return

        downloads_path = self.get_downloads_path()
        for app in applications_to_install:
            details = self.applications[app]
            self.installation_manager.add_to_queue(app, details, downloads_path)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def on_installation_complete(self):
        self.close()

    def on_installation_started(self):
        self.install_button.setEnabled(False)
        self.install_button.setText("Installation in progress...")

    def on_installation_finished(self):
        self.install_button.setEnabled(True)
        self.install_button.setText("Install")
        self.progress_bar.setValue(0)

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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    installer = AppInstaller()
    installer.show()
    sys.exit(app.exec_())