import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import requests
import subprocess
import os
import ctypes
import shutil
from pathlib import Path
import winreg
import webbrowser
from tqdm import tqdm

applications = {
    "Brave": "https://laptop-updates.brave.com/latest/winx64",
    "Discord": "https://discord.com/api/download?platform=win",
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
    "Davinci Resolve (site)": "https://www.blackmagicdesign.com/fr/products/davinciresolve", # Impossible d'installer auto
    "HWINFO (site)": "https://www.hwinfo.com/download/", # Impossible d'installer auto
    "NVIDIA App (site)": "https://fr.download.nvidia.com/nvapp/client/10.0.0.535/NVIDIA_app_beta_v10.0.0.535.exe", # Impossible d'installer auto
    "NVIDIA GeForce NOW (site)": "https://download.nvidia.com/gfnpc/GeForceNOW-release.exe", # Impossible d'installer auto
    "Voicemod (site)": "https://www.voicemod.net/", # Impossible d'installer auto
}

#================================= CHEMIN DE TELECHARGEMENT ================================
def get_telechargements_path():
    sub_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
        value = winreg.QueryValueEx(key, '{374DE290-123F-4565-9164-39C4925E467B}')[0]
        return Path(value)

telechargements_path = get_telechargements_path()
#============================= END OF CHEMIN DE TELECHARGEMENT ==============================

#================================= INSTALLATION DES APPLICATIONS ================================
def download_applications():
    applications_installed = [app for app, installed in variables_applications.items() if installed.get()]
    if not applications_installed:
        messagebox.showinfo("Information", "Aucune application sélectionnée!")
        return

    for app, installed in variables_applications.items():
        if installed.get():
            url = applications[app]
            if "(site)" in app:
                webbrowser.open(url)
            else:
                try:
                    #======== .MSI =========
                    if url.endswith('.msi'):
                        files_path = telechargements_path / (app + ".msi")
                        with open(files_path, "wb") as f:
                            response = requests.get(url, stream=True)
                            total_size = int(response.headers.get('content-length', 0))
                            with tqdm(total=total_size, unit='B', unit_scale=True, desc=f'Téléchargement de {app}', unit_divisor=1024) as pbar:
                                for data in response.iter_content(chunk_size=1024):
                                    f.write(data)
                                    pbar.update(len(data))

                        # Exécution de msiexec pour installer le fichier MSI
                        subprocess.call(["msiexec", "/i", str(files_path)])
                    
                    #======== .EXE =========
                    else:
                        files_path = telechargements_path / (app + ".exe")
                        with open(files_path, "wb") as f:
                            response = requests.get(url, stream=True)
                            total_size = int(response.headers.get('content-length', 0))
                            with tqdm(total=total_size, unit='B', unit_scale=True, desc=f'Téléchargement de {app}', unit_divisor=1024) as pbar:
                                for data in response.iter_content(chunk_size=1024):
                                    f.write(data)
                                    pbar.update(len(data))

                    # Exécution du fichier d'installation avec les droits administrateur
                    ctypes.windll.shell32.ShellExecuteW(None, "runas", str(files_path), None, None, 1)

                except Exception as e:
                    messagebox.showerror("Erreur", f"Impossible d'installer {app} : {str(e)}")
    root.destroy() # Fermeture après l'installation des apps
#============================= END OF INSTALLATION DES APPLICATIONS ==============================

#================================= FENETRE TINKER ================================
root = tk.Tk()
root.title("Installateur d'applications")

#======== CASE A COCHER =========
variables_applications = {}
frame = tk.Frame(root)
frame.pack()

# définition de la disposition
max_per_column = 11
column = 0
row = 0

# création des cases a cocher
for app in applications:
    variables_applications[app] = tk.BooleanVar(value=False)
    checkbox = tk.Checkbutton(frame, text=app, variable=variables_applications[app], font=('Helvetica', 12))
    checkbox.grid(row=row, column=column, sticky='w', padx=10, pady=1)
    row += 1
    if row >= max_per_column:
        row = 0
        column += 1

#Bouton d'installation et quitter
install_button = tk.Button(root, text="Installer", command=download_applications, width=20, bg="blue", fg="white", relief="raised", font=('Helvetica', 12, 'bold'))
install_button.pack(pady=10)

quit_button = tk.Button(root, text="Quitter", command=root.destroy, width=20, bg="red", fg="white", relief="raised", font=('Helvetica', 12, 'bold'))
quit_button.pack(pady=10)
#============================= END OF FENETRE TINKER ==============================

# Lancement de la boucle principale
root.mainloop()