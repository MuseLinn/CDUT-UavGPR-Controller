; Inno Setup 安装脚本
; 用于生成 GPR DAQ GUI 的 EXE 安装包

#define AppName "CDUT GPR DAQ GUI"
; 定义应用版本，优先使用命令行参数，否则使用默认值
#define AppVersion GetEnv('AppVersion') != '' ? GetEnv('AppVersion') : "1.0.0"
; 新增：定义输出文件名，优先使用命令行参数
#define OutputFilename GetEnv('OutputFilename') != '' ? GetEnv('OutputFilename') : "gpr_daq_gui_installer"

[Setup]
; 基本配置
AppName=CDUT GPR DAQ GUI
AppVersion={#AppVersion}
AppPublisher=CDUT
AppPublisherURL=https://github.com/MuseLinn/CDUT-UavGPR-Controller
AppSupportURL=https://github.com/MuseLinn/CDUT-UavGPR-Controller/issues
AppUpdatesURL=https://github.com/MuseLinn/CDUT-UavGPR-Controller/releases
DefaultDirName={autopf}\CDUT-GPR-DAQ-GUI
DefaultGroupName=CDUT GPR DAQ GUI
AllowNoIcons=yes
LicenseFile=
InfoBeforeFile=
InfoAfterFile=
; 安装程序图标
SetupIconFile=lib\app_logo.ico

OutputDir=.
; 使用自定义参数作为输出文件名（带版本号）
OutputBaseFilename={#OutputFilename}
Compression=lzma
SolidCompression=yes
; 允许用户在安装时选择语言
ShowLanguageDialog=yes

[Languages]
; 使用默认英文语言，移除中文语言包依赖
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 0,6.1

[Files]
; 递归添加所有文件和子目录 - 使用正确的相对路径
source: "dist\gpr_daq_gui\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{cm:ProgramOnTheWeb,CDUT GPR DAQ GUI}"; Filename: "https://github.com/MuseLinn/CDUT-UavGPR-Controller"
Name: "{group}\{cm:UninstallProgram,CDUT GPR DAQ GUI}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\gpr_daq_gui.exe"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppName}"; Filename: "{app}\gpr_daq_gui.exe"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\gpr_daq_gui.exe"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"