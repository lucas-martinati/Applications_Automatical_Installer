## 🔽 Installation
**Note:** Installation is only necessary if you intend to modify the source code.

1. **Install Python and Required Packages**:

   -Run the `install_python_and_packages.bat` file. This script will install Python (if not already installed) and the necessary packages.
   -After execution, restart the script to ensure all packages are properly installed.

## 🚀 Usage

- **Standard Usage on Windows**:

   Simply execute the provided `Applications_Automatical_Installer.exe` file to launch the application.

- **Modifying the Python Code**:

   If you wish to modify the source code, run the corresponding `Install_dependency.bat` script to set up the development environment.

- **Recompiling the Python Script into an Executable**:

   After making changes to the code, use the following command to generate a new executable:
    ```
    Code\venv\Scripts\activate
    cd Code
    pyinstaller --onefile --windowed --add-data "applications.json;." Applications_Automatical_Installer.py
    ```
    This command creates a standalone executable from your Python script, including the necessary `applications.json` file.

## 🤔 Explanation

This repository facilitates the automatic installation of selected applications from an easily extendable list. Each application is installed with administrative privileges to prevent conflicts, and the installation files are saved in the Windows 'Downloads' folder.

Please note that certain applications, such as "Nvidia App" or "Davinci Resolve," require an active internet connection during installation and cannot be installed automatically. For these, the script will redirect you to the official website for manual installation. These applications are labeled as “(Manual)” and highlighted in purpe. Additionally, a list of extensions is provided, directing you to their respective sites.

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
- Streamlabs
- Wemod
- Winrar

## 📱 Chrome extensions

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

## 📱 Microsoft Store applications

- Visual Studio Code
- Microsoft PowerToys
- Pichon
- Wintoys
- Office

![image](https://github.com/LucasM548/Applications-Automatical-Intaller/assets/127530926/4e0c1313-4f27-4b6d-8383-41f4d7bf29d6)