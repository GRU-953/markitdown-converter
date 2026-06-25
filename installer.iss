[Setup]
AppName=MarkItDown Converter
AppVersion=4.2.2
AppPublisher=GRU-953
AppPublisherURL=https://github.com/GRU-953/markitdown-converter
AppSupportURL=https://github.com/GRU-953/markitdown-converter/issues
AppUpdatesURL=https://github.com/GRU-953/markitdown-converter/releases
DefaultDirName={autopf}\MarkItDownConverter
DefaultGroupName=MarkItDown Converter
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=dist
OutputBaseFilename=MarkItDownConverter-Setup
SetupIconFile=assets\app_icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\MarkItDownConverter.exe
VersionInfoVersion=4.2.2
VersionInfoDescription=MarkItDown Converter Setup
VersionInfoCopyright=Copyright (C) 2024-2026 GRU-953

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "dist\MarkItDownConverter.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\MarkItDown Converter"; Filename: "{app}\MarkItDownConverter.exe"
Name: "{group}\Uninstall MarkItDown Converter"; Filename: "{uninstallexe}"
Name: "{autodesktop}\MarkItDown Converter"; Filename: "{app}\MarkItDownConverter.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MarkItDownConverter.exe"; Description: "Launch MarkItDown Converter"; Flags: nowait postinstall skipifsilent
