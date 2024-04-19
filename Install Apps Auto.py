from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton, QMessageBox, QLabel, QSpacerItem, QSizePolicy
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from pathlib import Path
from tqdm import tqdm
import webbrowser
import subprocess
import requests
import winreg
import sys
import os

class AppInstaller(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Installateur d'applications")
        self.applications = {
            "Brave": "https://laptop-updates.brave.com/latest/winx64",
            "Discord": "https://discord.com/api/downloads/distributions/app/installers/latest?channel=stable&platform=win&arch=x64",
            "Epic Games": "https://launcher-public-service-prod06.ol.epicgames.com/launcher/api/installer/download/EpicGamesLauncherInstaller.msi",
            "Git": "https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/Git-2.44.0-64-bit.exe",
            "GOG Galaxy": "https://webinstallers.gog-statics.com/download/GOG_Galaxy_2.0.exe?payload=aKB7F3BHw5NoN2YWknDMijQCYnKgHNmiuE-ZQH5qOFwqEprfTG4XR9vIgNeGZ1bBFQ2v7owOBlberSmn-yntUfS_14Aeqz3fwP2gAmbadgMcI9zO000XgA_7rXdfrzBTmnAGSLkOp9726xxtCKf8-OgkjdudGNIO_Rmgcjb5YEV2HwJV7kTft9jrTFD2haCI6Py8Sht6AiAMQKwcKU-pItTuypAjuSihxff5IcpeAqDeRyKQDF1cJlpe_D5hrDC5SLGykrIaXdP6ZjWTG9U0YDWYacADIeObsaiuTUbKEQU32bvfz0-p1v3JJYS20PFYSxccdCsavCo2K6E_eVAgKT1EsSVc96l_uxM4Sl2jxoYo4_5py65cKpSsv2osfCvu31LKZ6TvkRFZ8rm6MYeJx0OX5ASiiRAqmBCl2LYr6eFqnbmdyFb5mFNHVTvSTPHY5jt1HG3je2IOXdgtWMP8G7q7Gv-22JUF0q1QCjqPOxz-KClk-UDCKkgKZQVT4m0RB26q3McGHzUYUpHQThP1vA8A555MhyUevz5UHTinjzib8rtGHKn3_J1geGrYobhpy0yTOJ_UHE_pnUP-bxMYPRyJpKf-DNZbdvo99q_C47Jp38WD5fg4wgmJvjoWhI3KU04CabrE4Pl9VuXDFu4R5p8xLNSzp28QrG-G6nb6ZQ3YNZdrId4sOqlS-kNUhscX0eQzRRJoLc6ih5c3v24uoMks8OFhhhJzw2NgRlijgrR2cxgjsYXFYbu3OfMNXywyA3Ds",
            "Java": "https://javadl.oracle.com/webapps/download/AutoDL?BundleId=249553_4d245f941845490c91360409ecffb3b4",
            "Logitech G HUB": "https://download01.logi.com/web/ftp/pub/techsupport/gaming/lghub_installer.exe",
            "Modrinth": "https://launcher-files.modrinth.com/versions/0.6.3/windows/Modrinth%20App_0.6.3_x64_en-US.msi",
            "Oculus": "https://www.oculus.com/download_app/?id=1582076955407037",
            "Parsec": "https://s3.amazonaws.com/parsec-build/package/parsec-windows.exe",
            "ProtonVPN": "https://protonvpn.com/download/ProtonVPN_v3.2.10.exe",
            "Rockstar Games": "https://gamedownloads.rockstargames.com/public/installer/Rockstar-Games-Launcher.exe",
            "Steam": "https://cdn.akamai.steamstatic.com/client/installer/SteamSetup.exe",
            "Streamlabs": "https://streamlabs.com/streamlabs-desktop/download?sdb=0",
            "Wemod": "https://www.wemod.com/download/direct",
            "Winrar": "https://www.win-rar.com/fileadmin/winrar-versions/winrar/winrar-x64-700fr.exe",
            "Davinci Resolve (manuel)": "https://www.blackmagicdesign.com/fr/products/davinciresolve", # Install manuel
            "HWINFO (manuel)": "https://www.hwinfo.com/download/", # Install manuel
            "NVIDIA App (manuel)": "https://fr.download.nvidia.com/nvapp/client/10.0.0.535/NVIDIA_app_beta_v10.0.0.535.exe", # Install manuel
            "NVIDIA GeForce NOW (manuel)": "https://download.nvidia.com/gfnpc/GeForceNOW-release.exe", # Install manuel
            "Voicemod (manuel)": "https://www.voicemod.net/", # Install manuel
            "Authentificator (Extension)": "https://chrome.google.com/webstore/detail/authenticator/bhghoamapcdpbohphigoooaddinpkbai", # Extension
            "Buster - Captcha Solver (Extension)": "https://chrome.google.com/webstore/detail/buster-captcha-solver-for/mpbjkejclgfgadiemmefgebjfooflfhl/related", # Extension
            "Dark Reader (Extension)": "https://chrome.google.com/webstore/detail/dark-reader/eimadpbcbfnmbkopoojfekhnkhdbieeh", # Extension
            "Google Traduction (Extension)": "https://chrome.google.com/webstore/detail/google-translate/aapbdbdomjkkjkaonfhkkikfgjllcleb", # Extension
            "Hower Zoom+ (Extension)": "https://chrome.google.com/webstore/detail/hover-zoom%2B/pccckmaobkjjboncdfnnofkonhgpceea", # Extension
            "Return YouTube Dislike (Extension)": "https://chrome.google.com/webstore/detail/return-youtube-dislike/gebbhagfogifgggkldgodflihgfeippi", # Extension
            "SponsorBlock (Extension)": "https://chrome.google.com/webstore/detail/sponsorblock-for-youtube/mnjggcdmjocbbbhaepdhchncahnbgone", # Extension
            "Steam Inventory Helper (Extension)": "https://chrome.google.com/webstore/detail/steam-inventory-helper/cmeakgjggjdlcpncigglobpjbkabhmjl", # Extension
            "Twitch Live (Extension)": "https://chrome.google.com/webstore/detail/twitch-live-extension/nlnfdlcbnpafokhpjfffmoobbejpedgj", # Extension
            "Volume Booster (Extension)": "https://chromewebstore.google.com/detail/buster-captcha-solver-for/mpbjkejclgfgadiemmefgebjfooflfhl", # Extension
            "Visual Studio Code (Microsoft)": "ms-windows-store://pdp?hl=en-us&gl=us&productid=xp9khm4bk9fz7q&referrer=storeforweb&source=https%3A%2F%2Fwww.google.com%2F&mode=mini&pos=7%2C2%2C1922%2C922", # Micosoft
            "Microsoft PowerToys (Microsoft)": "ms-windows-store://pdp?hl=fr-fr&gl=fr&productid=xp89dcgq3k6vld&referrer=storeforweb&source=https%3A%2F%2Fwww.google.com%2F&mode=mini&pos=7%2C2%2C1922%2C922", # Micosoft
            "Pichon (Microsoft)": "ms-windows-store://pdp?hl=fr-fr&gl=fr&referrer=storeforweb&source=https%3A%2F%2Fwww.google.com%2F&productid=9nk8t1kshffr&mode=mini&pos=7%2C2%2C1922%2C922", # Micosoft
            "Wintoys (Microsoft)": "ms-windows-store://pdp?hl=fr-fr&gl=fr&referrer=storeforweb&source=https%3A%2F%2Fwww.google.com%2F&productid=9p8ltpgcbzxd&mode=mini&pos=7%2C2%2C1922%2C922", # Micosoft
            "Office (Microsoft)": "ms-windows-store://pdp?hl=fr-fr&gl=fr&referrer=storeforweb&source=https%3A%2F%2Fwww.google.com%2F&productid=9wzdncrd29v9&mode=mini&pos=7%2C2%2C1922%2C922", # Micosoft
        }
        self.setup_ui()

    #=================== UI ===================
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)

        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Applications", font=title_font), alignment=Qt.AlignCenter)
        title_layout.addWidget(QLabel("Extensions Brave", font=title_font), alignment=Qt.AlignCenter)
        title_layout.addWidget(QLabel("Applications Microsoft Store", font=title_font), alignment=Qt.AlignCenter)
        layout.addLayout(title_layout)

        select_all_layout = QHBoxLayout()
        layout.addLayout(select_all_layout)

        column1 = QVBoxLayout()
        column2 = QVBoxLayout()
        column3 = QVBoxLayout()
        
        select_all_column1_button = QPushButton("Tout sélectionner")
        select_all_column1_button.clicked.connect(lambda: self.select_all_column(self.column1_checkboxes))
        select_all_layout.addWidget(select_all_column1_button)

        select_all_column2_button = QPushButton("Tout sélectionner")
        select_all_column2_button.clicked.connect(lambda: self.select_all_column(self.column2_checkboxes))
        select_all_layout.addWidget(select_all_column2_button)

        select_all_column3_button = QPushButton("Tout sélectionner")
        select_all_column3_button.clicked.connect(lambda: self.select_all_column(self.column3_checkboxes))
        select_all_layout.addWidget(select_all_column3_button)

        columns_layout = QHBoxLayout()
        layout.addLayout(columns_layout)

        columns_layout.addLayout(column1)
        columns_layout.addItem(QSpacerItem(40, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        columns_layout.addLayout(column2)
        columns_layout.addItem(QSpacerItem(40, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        columns_layout.addLayout(column3)
        columns_layout.addItem(QSpacerItem(40, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.checkboxes = {}
        self.column1_checkboxes = []
        self.column2_checkboxes = []
        self.column3_checkboxes = []

        for app in self.applications:
            checkbox = QCheckBox(app)
            if "(manuel)" in app:
                checkbox.setStyleSheet("color: purple")
                column1.addWidget(checkbox)
                self.column1_checkboxes.append(checkbox)
            elif "(Extension)" in app:
                checkbox.setStyleSheet("color: green")
                column2.addWidget(checkbox)
                self.column2_checkboxes.append(checkbox)
            elif "(Microsoft)" in app:
                checkbox.setStyleSheet("color: blue")
                column3.addWidget(checkbox)
                self.column3_checkboxes.append(checkbox)
            else:
                column1.addWidget(checkbox)
                self.column1_checkboxes.append(checkbox)

            self.checkboxes[app] = checkbox

        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)

        install_button = QPushButton("Installer")
        install_button.clicked.connect(self.install_applications)
        button_layout.addWidget(install_button)

        quit_button = QPushButton("Quitter")
        quit_button.clicked.connect(self.close)
        button_layout.addWidget(quit_button)
    #================ END OF UI ================
    def select_all_column(self, column_checkboxes):
        if column_checkboxes[0].isChecked():
            for checkbox in column_checkboxes:
                checkbox.setChecked(False)
        else:
            for checkbox in column_checkboxes:
                checkbox.setChecked(True)

    #================================= INSTALLATION DES APPLICATIONS ================================
    def install_applications(self):
        applications_installed = [app for app, checkbox in self.checkboxes.items() if checkbox.isChecked()]
        if not applications_installed:
            QMessageBox.information(self, "Information", "Aucune application sélectionnée!")
            return

        downloads_path = self.get_downloads_path()
        for app in applications_installed:
            url = self.applications[app]
            try:
                if "(manuel)" in app or "(Extension)" in app or "(Microsoft)" in app:
                    if "(Microsoft)" in app:
                        QMessageBox.information(self, "Information", f"Veuillez installer manuellement l'application {app} depuis le Microsoft Store.")
                    webbrowser.open(url)
                else:
                    file_name = f"{app}.msi" if url.endswith('.msi') else f"{app}.exe"
                    file_path = downloads_path / file_name

                    response = requests.get(url, stream=True)
                    total_size = int(response.headers.get('content-length', 0))
                    with open(file_path, "wb") as f, tqdm(total=total_size, unit='B', unit_scale=True, desc=f'Téléchargement de {app}', unit_divisor=1024) as pbar:
                        for data in response.iter_content(chunk_size=1024):
                            f.write(data)
                            pbar.update(len(data))

                    if url.endswith('.msi'):
                        subprocess.Popen(["msiexec", "/i", str(file_path)], shell=True)
                    else:
                        subprocess.Popen([str(file_path)], shell=True)

            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Impossible d'installer {app} : {str(e)}")
        self.close()
    #============================= END OF INSTALLATION DES APPLICATIONS ==============================

    #================================= CHEMIN DE TELECHARGEMENT ================================
    def get_downloads_path(self):
        try:
            sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                downloads_path = winreg.QueryValueEx(key, '{374DE290-123F-4565-9164-39C4925E467B}')[[1]]
        except Exception as e:
            print(f"Erreur lors de la récupération du dossier Downloads: {e}")
            # Retourner le dossier Downloads par défaut si la lecture du registre échoue
            downloads_path = os.path.join(os.getenv('USERPROFILE'), 'Downloads')
            
        # Expanding environment variables in case the registry contains a reference like %USERPROFILE%
        return Path(os.path.expandvars(downloads_path))
    #============================= END OF CHEMIN DE TELECHARGEMENT ==============================

if __name__ == '__main__':
    app = QApplication(sys.argv)
    installer = AppInstaller()
    installer.show()
    sys.exit(app.exec_())