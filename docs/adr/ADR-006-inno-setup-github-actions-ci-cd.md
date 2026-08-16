# ADR 006: Automated Packaging via Inno Setup and GitHub Actions

## Status
Accepted

## Context
Distributing raw Python scripts or standalone single-file `.exe` binaries from PyInstaller triggers frequent Windows Defender / SmartScreen false-positive warnings and lacks basic desktop integration (Start Menu shortcuts, uninstaller).

## Decision
We automate the compilation pipeline using **GitHub Actions**. PyInstaller builds the application in `--onedir` mode, and **Inno Setup** packages the resulting distribution into a signed or clean `INF03_AI_Tutor_Setup.exe` installer published automatically to **GitHub Releases**.

## Consequences
### Positive
* Clean desktop installation and uninstallation registered in Windows Settings.
* Drastic reduction in antivirus false-positive alerts.
* Automated release workflow triggered by version tags (`git tag vX.Y.Z`).