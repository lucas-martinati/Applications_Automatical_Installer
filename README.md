# 🖥️ Applications Automatical Installer

A Windows tool to automatically install a list of selected applications.

## 🔽 Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/<your-username>/Applications_Automatical_Installer.git
   cd Applications_Automatical_Installer
   ```

2. **Install Python and dependencies**:

   Run the `Install_dependency.bat` script. It will install Python (if not already installed) and the required packages.
   Re-run the script after execution to ensure all packages are properly installed.

## 🚀 Usage

### Run directly with Python

```bash
python Applications_Automatical_Installer.py
```

### Compile to `.exe`

To generate a standalone executable, run the following commands in PowerShell:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
venv\Scripts\activate
pyinstaller --onefile --windowed --add-data "applications.json;." Applications_Automatical_Installer.py
```

The executable will be generated in the `dist/` folder.

> **Note:** Make sure `pyinstaller` is installed (`pip install pyinstaller`).

## 🤔 How It Works

This repository enables the automatic installation of selected applications from an easily extendable list. Each application is installed with administrator privileges to prevent conflicts, and the installation files are saved in the Windows `Downloads` folder.

Some applications like **Nvidia App** or **Davinci Resolve** require an active internet connection during installation and cannot be installed automatically. The script will redirect you to the official website for manual installation. These applications are labeled as "(Manual)" and displayed in purple. A list of extensions is also provided with links to their respective sites.

## 📱 Applications

- Brave
- Discord
- Epic Games
- Git
- GOG Galaxy
- Google Drive
- Java
- Logitech G HUB
- Modrinth
- Oculus
- Parsec
- ProtonVPN
- Rockstar Games
- Steam
- Stremio
- Streamlabs
- Ubisoft Connect
- Wemod
- Winrar
- Rectify11 (manual)
- Davinci Resolve (manual)
- HWINFO (manual)
- NVIDIA App (manual)
- NVIDIA GeForce NOW (manual)
- Voicemod (manual)

## 🧩 Chrome Extensions

- Authenticator
- Buster - Captcha Solver
- Dark Reader
- Google Traduction
- Hover Zoom+
- Return YouTube Dislike
- SponsorBlock
- Steam Inventory Helper
- Twitch Live
- Volume Master

## 🏪 Microsoft Store Applications

- Bitwarden
- Visual Studio Code
- Microsoft PowerToys
- Xbox Accessories
- Pichon
- Wintoys
- Office

## 📸 Preview

![image](https://github.com/user-attachments/assets/84e37193-f74a-4178-ba29-e74090392ba0)
