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
import requests
import winreg

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton,
    QMessageBox, QLabel, QSpacerItem, QSizePolicy, QScrollArea, QProgressBar
)
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QImage, QPainterPath
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QSize
from PyQt5.QtSvg import QSvgRenderer

# Configuration du logging
logging.basicConfig(
    filename='app_installer.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ------------------- CONSTANTES & FEUILLE DE STYLE -------------------
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

# ------------------- FONCTIONS UTILITAIRES -------------------
def store_url(productid: str) -> str:
    """Génère une URL pour le Microsoft Store."""
    return f"ms-windows-store://pdp?hl=fr-fr&gl=fr&productid={productid}&mode=mini"

def extension_url(id: str) -> str:
    """Génère une URL pour une extension Chrome."""
    return f"https://chromewebstore.google.com/detail/{id}"

def get_url(app_details: dict) -> str:
    """Retourne l'URL appropriée selon le type d'application."""
    app_type = app_details.get('type')
    if app_type == 'microsoft':
        return store_url(app_details['productid'])
    elif app_type == 'extension':
        return extension_url(app_details['id'])
    return app_details.get('url', '')

def remove_white_border(pixmap: QPixmap, threshold: int = 240) -> QPixmap:
    """Supprime les bordures blanches connectées aux bords d'une image."""
    image = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
    width, height = image.width(), image.height()
    visited = set()
    stack = []

    def is_white(x: int, y: int) -> bool:
        color = image.pixelColor(x, y)
        return all(c >= threshold for c in (color.red(), color.green(), color.blue()))

    # Ajouter les pixels des bordures à la pile
    for x in range(width):
        if is_white(x, 0): stack.append((x, 0)); visited.add((x, 0))
        if is_white(x, height - 1): stack.append((x, height - 1)); visited.add((x, height - 1))
    for y in range(height):
        if is_white(0, y): stack.append((0, y)); visited.add((0, y))
        if is_white(width - 1, y): stack.append((width - 1, y)); visited.add((width - 1, y))

    # Algorithme de remplissage par inondation
    while stack:
        x, y = stack.pop()
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited and is_white(nx, ny):
                stack.append((nx, ny))
                visited.add((nx, ny))

    # Rendre les pixels blancs transparents
    for x, y in visited:
        color = image.pixelColor(x, y)
        color.setAlpha(0)
        image.setPixelColor(x, y, color)

    return QPixmap.fromImage(image)

def round_pixmap(pixmap: QPixmap, radius: int = 10) -> QPixmap:
    """Applique des coins arrondis à un QPixmap."""
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

def load_svg_logo(url: str, size: QSize) -> QPixmap:
    """Charge un logo SVG et le convertit en QPixmap."""
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        renderer = QSvgRenderer(response.content)
        pixmap = QPixmap(size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return pixmap
    except requests.RequestException as e:
        logging.error(f"Erreur lors du chargement du logo SVG depuis {url}: {e}")
        return None

# ------------------- WIDGET PERSONNALISÉ -------------------
class ClickableCheckBox(QCheckBox):
    """Case à cocher cliquable avec support du clic et des touches."""
    def hitButton(self, pos):
        return self.rect().contains(pos)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.toggle()
            event.accept()
        else:
            super().keyPressEvent(event)

# ------------------- TÉLÉCHARGEMENT & INSTALLATION -------------------
class DownloadThread(QThread):
    """Thread pour télécharger un fichier en arrière-plan."""
    progress_signal = pyqtSignal(int, float, float, float, float)  # Pourcentage, taille totale, téléchargé, vitesse, ETA
    finished_signal = pyqtSignal(str)  # Chemin du fichier ou vide si échec

    def __init__(self, url: str, file_path: str):
        super().__init__()
        self.url = url
        self.file_path = file_path
        self.is_cancelled = False
        self.start_time = None

    def run(self):
        try:
            with requests.get(self.url, stream=True, timeout=10) as response:
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
                        downloaded += f.write(data)
                        if total_size:
                            percent = downloaded * 100 // total_size
                            downloaded_mb = downloaded / (1024 * 1024)
                            elapsed_time = time.time() - self.start_time
                            speed = downloaded_mb / elapsed_time if elapsed_time > 0 else 0
                            eta = (total_size - downloaded) / (speed * 1024 * 1024) if speed > 0 else 0
                            self.progress_signal.emit(percent, total_size_mb, downloaded_mb, speed, eta)
            self.finished_signal.emit(self.file_path)
        except requests.RequestException as e:
            logging.error(f"Échec du téléchargement de {self.url}: {e}")
            self.finished_signal.emit("")

    def cancel(self):
        """Annule le téléchargement en cours."""
        self.is_cancelled = True

class InstallationManager(QObject):
    """Gestionnaire de la file d'attente des installations."""
    installation_complete = pyqtSignal()
    installation_started = pyqtSignal(str)
    installation_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.queue = []
        self.current_thread = None
        self.current_app = ""

    def add_to_queue(self, app: str, details: dict, downloads_path: Path):
        """Ajoute une application à la file d'attente."""
        self.queue.append((app, details, downloads_path))
        if not self.current_thread:
            self.process_next()

    def process_next(self):
        """Traite la prochaine application dans la file."""
        while self.queue:
            app, details, downloads_path = self.queue.pop(0)
            self.current_app = app
            url = get_url(details)
            app_type = details.get("type", "")
            if "(manual)" in app:
                webbrowser.open(url)
                QMessageBox.information(None, "Information", f"Please install {app} manually.")
                continue
            else:
                file_ext = ".msi" if url.endswith('.msi') else ".exe"
                file_path = downloads_path / f"{app}{file_ext}"
                self.current_thread = DownloadThread(url, str(file_path))
                self.current_thread.progress_signal.connect(self.parent().update_progress)
                self.current_thread.finished_signal.connect(partial(self.install_application, app=app))
                self.installation_started.emit(app)
                self.current_thread.start()
                break
        else:
            self.installation_finished.emit()
            self.installation_complete.emit()
        self.parent().update_button_states()

    def install_application(self, file_path: str, app: str):
        """Lance l'installation d'une application téléchargée."""
        if file_path:
            if file_path.endswith('.msi'):
                subprocess.Popen(["msiexec", "/i", file_path], shell=True)
            else:
                subprocess.Popen([file_path], shell=True)
            logging.info(f"Installation démarrée pour {app}")
        else:
            logging.error(f"Échec du téléchargement de {app}")
            QMessageBox.critical(None, "Erreur", f"Échec du téléchargement de {app}")
        self.current_thread = None
        self.current_app = ""
        self.process_next()

    def cancel_current_installation(self):
        """Annule l'installation en cours."""
        if self.current_thread:
            self.current_thread.cancel()
            self.current_thread = None
            self.current_app = ""
            self.process_next()

# ------------------- APPLICATION PRINCIPALE -------------------
class AppInstaller(QWidget):
    """Fenêtre principale de l'installeur d'applications."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Applications Installer")
        self.setGeometry(700, 200, 800, 600)
        self.setStyleSheet(STYLE_SHEET)
        self.checkboxes = {}
        self.column_checkboxes = []
        self.select_buttons = {}
        self.load_applications()
        self.setup_ui()
        self.installation_manager = InstallationManager(self)
        self.installation_manager.installation_complete.connect(self.on_installation_complete)
        self.installation_manager.installation_started.connect(self.on_installation_started)
        self.installation_manager.installation_finished.connect(self.on_installation_finished)

    def load_applications(self):
        """Charge les applications depuis un fichier JSON ou utilise les valeurs par défaut."""
        script_dir = Path(__file__).parent
        json_path = script_dir / 'applications.json'
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                self.applications = json.load(f)
        except FileNotFoundError:
            logging.error(f"applications.json non trouvé à {json_path}. Utilisation des valeurs par défaut.")
            self.applications = self.get_default_applications()

    def get_default_applications(self) -> dict:
        """Retourne une liste d'applications par défaut."""
        return {
            "Brave": {"url": "https://laptop-updates.brave.com/latest/winx64", "logo": "https://img.icons8.com/?size=100&id=cM42lftaD9Z3&format=png&color=000000"},
            "Discord": {"url": "https://discord.com/api/downloads/distributions/app/installers/latest?channel=stable&platform=win&arch=x64", "logo": "https://img.icons8.com/color/2x/discord"},
            "HWINFO (manual)": {"url": "https://www.hwinfo.com/download/", "logo": "https://www.hwinfo.com/wp-content/themes/hwinfo/img/logo-sm.png"},
            "NVIDIA App (manual)": {"url": "https://fr.download.nvidia.com/nvapp/client/10.0.0.535/NVIDIA_app_beta_v10.0.0.535.exe", "logo": "https://img.icons8.com/color/512/nvidia.png"},
            "Dark Reader": {"url": extension_url("dark-reader/eimadpbcbfnmbkopoojfekhnkhdbieeh"), "type": "extension", "logo": "logos/dark_reader.png"},
            "Google Traduction": {"url": extension_url("google-translate/aapbdbdomjkkjkaonfhkkikfgjllcleb"), "type": "extension", "logo": "logos/google_translate.png"},
        }

    def setup_ui(self):
        """Configure l'interface utilisateur."""
        main_layout = QVBoxLayout(self)

        # Titres des colonnes
        title_layout = QHBoxLayout()
        titles = ["Applications", "Chrome Extensions", "Microsoft Store Applications"]
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        for text in titles:
            label = QLabel(text)
            label.setFont(title_font)
            label.setObjectName("title")
            title_layout.addWidget(label, alignment=Qt.AlignCenter)
        main_layout.addLayout(title_layout)

        # Boutons "Select All"
        select_all_layout = QHBoxLayout()
        main_layout.addLayout(select_all_layout)

        # Colonnes de cases à cocher
        columns_layout = QHBoxLayout()
        for idx in range(len(titles)):
            column = QVBoxLayout()
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            content = QWidget()
            col_layout = QVBoxLayout(content)
            scroll.setWidget(content)
            scroll.setFixedWidth(230)
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

        # Ajout des applications
        for app, details in self.applications.items():
            app_type = self.get_application_type(details)
            if "(manual)" in app:
                app_type = "manual"
            checkbox = ClickableCheckBox(app)
            checkbox.setProperty("type", app_type)

            # Chargement du logo
            logo_link = details.get("logo")
            if not logo_link and (app_url := details.get("url")):
                domain = urlparse(app_url).netloc
                if domain:
                    logo_link = f"https://logo.clearbit.com/{domain}"
            if logo_link and logo_link.lower().startswith("http"):
                pixmap = load_svg_logo(logo_link, QSize(24, 24)) if logo_link.lower().endswith(".svg") else None
                if not pixmap:
                    try:
                        response = requests.get(logo_link, timeout=5)
                        response.raise_for_status()
                        pixmap = QPixmap()
                        pixmap.loadFromData(response.content)
                    except requests.RequestException as e:
                        logging.error(f"Échec du chargement de l'image pour {app}: {e}")
                        pixmap = None
                if pixmap:
                    pixmap = remove_white_border(pixmap)
                    pixmap = round_pixmap(pixmap, radius=10)
                    checkbox.setIcon(QIcon(pixmap))
                    checkbox.setIconSize(QSize(24, 24))

            col_idx = self.get_column_index_for_app_type(app_type)
            checkbox.toggled.connect(partial(self.update_select_all_button, column_index=col_idx))
            self.column_checkboxes[col_idx].addWidget(checkbox)
            self.checkboxes[app] = checkbox

        # Boutons d'action
        btn_layout = QHBoxLayout()
        self.install_button = QPushButton("Install")
        self.install_button.clicked.connect(self.start_installation)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_installation)
        self.cancel_button.setEnabled(False)
        btn_layout.addWidget(self.install_button)
        btn_layout.addWidget(self.cancel_button)
        main_layout.addLayout(btn_layout)

        # Barre de progression
        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)

        # Informations de téléchargement
        info_layout = QHBoxLayout()
        self.current_app_label = QLabel()
        self.file_size_label = QLabel()
        self.speed_label = QLabel()
        self.eta_label = QLabel()
        for widget in (self.current_app_label, self.file_size_label, self.speed_label, self.eta_label):
            info_layout.addWidget(widget)
        main_layout.addLayout(info_layout)

    def toggle_select_column(self, column_index: int):
        """Active ou désactive toutes les cases d'une colonne."""
        layout = self.column_checkboxes[column_index]
        any_checked = any(layout.itemAt(i).widget().isChecked() for i in range(layout.count()))
        for i in range(layout.count()):
            layout.itemAt(i).widget().setChecked(not any_checked)
        self.update_select_all_button(column_index)

    def update_select_all_button(self, column_index: int):
        """Met à jour le texte du bouton Select All/Deselect All."""
        layout = self.column_checkboxes[column_index]
        any_checked = any(layout.itemAt(i).widget().isChecked() for i in range(layout.count()))
        self.select_buttons[column_index].setText("Deselect All" if any_checked else "Select All")

    def get_column_index_for_app_type(self, app_type: str) -> int:
        """Retourne l'index de la colonne selon le type d'application."""
        return {'extension': 1, 'microsoft': 2}.get(app_type, 0)

    def get_application_type(self, app_details: dict) -> str:
        """Détermine le type d'application."""
        return app_details.get("type", "")

    def start_installation(self):
        """Démarre l'installation des applications sélectionnées."""
        if self.installation_manager.current_thread:
            QMessageBox.warning(self, "Attention", "Une installation est en cours. Veuillez patienter.")
            return
        applications_to_install = [app for app, cb in self.checkboxes.items() if cb.isChecked()]
        if not applications_to_install:
            QMessageBox.information(self, "Information", "No application selected!")
            return
        downloads_path = self.get_downloads_path()
        for app in applications_to_install:
            self.installation_manager.add_to_queue(app, self.applications[app], downloads_path)
        self.update_button_states()

    def update_progress(self, percent: int, total_size_mb: float, downloaded_mb: float, speed: float, eta: float):
        """Met à jour la barre de progression et les informations."""
        self.progress_bar.setValue(percent)
        self.file_size_label.setText(f"Total size: {downloaded_mb:.2f}/{total_size_mb:.2f}MB")
        self.speed_label.setText(f"Speed: {speed:.2f}MB/s")
        self.eta_label.setText(f"ETA: {eta:.0f}s")

    def update_button_states(self):
        """Met à jour l'état des boutons."""
        self.install_button.setEnabled(not self.installation_manager.current_thread)
        self.cancel_button.setEnabled(bool(self.installation_manager.current_thread))

    def cancel_installation(self):
        """Annule l'installation en cours."""
        self.installation_manager.cancel_current_installation()
        self.progress_bar.setValue(0)

    def on_installation_complete(self):
        self.close()

    def on_installation_started(self, app):
        self.current_app_label.setText(f"Installing: {app}")
        self.file_size_label.setText("Total size: -")
        self.speed_label.setText("Speed: -")
        self.eta_label.setText("ETA: -")
        self.update_button_states()

    def on_installation_finished(self):
        """Réinitialise l'interface après une installation."""
        self.progress_bar.setValue(0)
        self.current_app_label.setText("")
        self.file_size_label.setText("")
        self.speed_label.setText("")
        self.eta_label.setText("")
        self.update_button_states()

    def on_installation_complete(self):
        """Ferme l'application quand tout est terminé."""
        self.close()

    def get_downloads_path(self) -> Path:
        """Récupère le chemin du dossier Téléchargements."""
        sub_key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        downloads_guid = "{374DE290-123F-4565-9164-39C4925E467B}"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                value, _ = winreg.QueryValueEx(key, downloads_guid)
                return Path(os.path.expandvars(value))
        except FileNotFoundError:
            return Path.home() / "Downloads"

# ------------------- POINT D'ENTRÉE -------------------
if __name__ == '__main__':
    app = QApplication(sys.argv)
    installer = AppInstaller()
    installer.show()
    sys.exit(app.exec_())