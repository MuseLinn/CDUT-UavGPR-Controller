; Inno Setup 安装脚本
; 用于生成 GPR DAQ GUI 的 EXE 安装包

#define AppName "CDUT GPR DAQ GUI"

[Setup]
; 基本配置
AppName=CDUT GPR DAQ GUI
AppVersion={#AppVersion}
AppPublisher=CDUT
AppPublisherURL=https://github.com/your-username/CDUT-UavGPR-Controller
AppSupportURL=https://github.com/your-username/CDUT-UavGPR-Controller/issues
AppUpdatesURL=https://github.com/your-username/CDUT-UavGPR-Controller/releases
DefaultDirName={autopf}\CDUT-GPR-DAQ-GUI
DefaultGroupName=CDUT GPR DAQ GUI
AllowNoIcons=yes
LicenseFile=
InfoBeforeFile=
InfoAfterFile=
OutputDir=.
OutputBaseFilename=gpr_daq_gui_installer
Compression=lzma
SolidCompression=yes

; 安装程序图标（暂时移除，使用默认图标）
; SetupIconFile=lib\app_logo.ico

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
Name: "{group}\{cm:ProgramOnTheWeb,CDUT GPR DAQ GUI}"; Filename: "https://github.com/your-username/CDUT-UavGPR-Controller"
Name: "{group}\{cm:UninstallProgram,CDUT GPR DAQ GUI}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\gpr_daq_gui.exe"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppName}"; Filename: "{app}\gpr_daq_gui.exe"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\gpr_daq_gui.exe"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
; 定义应用版本，从GitHub标签获取
#define AppVersion GetEnv("GITHUB_TAG_NAME")

; 处理版本号，移除前缀v
procedure InitializeWizard;
begin
  if Pos('v', AppVersion) = 1 then
  begin
    WizardForm.AppVersionLabel.Caption := Copy(AppVersion, 2, Length(AppVersion) - 1);
  end;
end;