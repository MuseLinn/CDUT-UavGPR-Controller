# 自动构建和发布指南

## 概述
本项目使用 GitHub Actions 实现自动构建和发布功能。当您推送带有 `v*` 格式的 Git 标签时，系统会自动在 Windows 平台上构建可执行文件并发布到 GitHub Releases。此外，项目还配置了 Pull Request 检查工作流，用于验证代码是否能够正常编译和通过安全检查。

## GitHub Actions 工作流

### 1. 构建发布工作流 (build-release.yml)
- **触发条件**：推送带有 `v*` 格式的 Git 标签
- **运行环境**：Windows Latest
- **主要功能**：构建可执行文件、创建安装包、发布到 GitHub Releases

### 2. 拉取请求检查工作流 (pull-request-check.yml)
- **触发条件**：提交 Pull Request 到 main 或 master 分支
- **运行环境**：Windows Latest
- **主要功能**：检查代码编译状态、执行安全扫描、验证代码质量

## 如何触发构建

1. 确保您的代码已提交并推送到 GitHub：
   ```bash
   git add .
   git commit -m "提交信息"
   git push origin main
   ```

2. 创建一个带版本号的标签（格式为 `v*`）：
   ```bash
   git tag -a v1.0.0 -m "版本 1.0.0"
   ```

3. 推送标签到远程仓库：
   ```bash
   git push origin v1.0.0
   ```

当您执行第 3 步后，GitHub Actions 将自动启动构建流程，在 Windows 平台上构建可执行文件。

## 构建流程说明

### 构建发布工作流 (build-release.yml)
工作流定义在 `.github/workflows/build-release.yml` 中，主要包含以下步骤：

1. 设置 Python 环境（Python 3.10）
2. 安装依赖项（包括 PyInstaller 和项目依赖）
3. 使用 PyInstaller 和 `main_gui.spec` 配置文件构建可执行文件
4. 提取版本号
5. 将构建产物打包为 zip 文件
6. 使用 Inno Setup 构建 EXE 安装包
7. 生成发布说明
8. 将构建产物上传到 GitHub Releases

### 拉取请求检查工作流 (pull-request-check.yml)
工作流定义在 `.github/workflows/pull-request-check.yml` 中，主要包含以下步骤：

1. 设置 Python 环境（Python 3.10）
2. 安装依赖项（包括 PyInstaller、bandit 和 flake8）
3. 使用 PyInstaller 执行构建检查
4. 使用 Bandit 进行安全扫描
5. 使用 Flake8 检查代码质量
6. 使用 Safety 检查依赖安全漏洞

## 本地构建测试

如果您想在本地测试构建过程，可以运行：

```bash
# 安装依赖
python -m pip install --upgrade pip
pip install pyinstaller
pip install -r requirements.txt || echo "requirements.txt not found, installing common packages"

# 执行构建
cd src
pyinstaller main_gui.spec --noupx
```

这将在本地尝试构建可执行文件，帮助您提前发现潜在问题。

## 构建产物

### 构建发布工作流产物
构建完成后，您可以在 GitHub 项目的 "Releases" 页面找到生成的文件，包括：

- Zip 包：`gpr_daq_gui_v{版本号}.zip`
- EXE 安装包：`gpr_daq_gui_v{版本号}_installer.exe`

### 拉取请求检查工作流产物
此工作流主要用于验证代码质量，不会生成可发布的产物，但会在 GitHub 上显示检查结果。

## 注意事项

- 确保 `main_gui.spec` 文件始终与项目结构保持同步
- 图标文件 `lib/app_logo.png` 必须存在于项目中（构建时会使用）
- 版本标签必须遵循 `v*` 格式（如 v1.0.0, v2.1.3 等）
- 项目依赖已更新至 requirements.txt
- 构建过程需要 Windows 环境，因为使用了 Inno Setup 生成安装包
- 拉取请求检查工作流会在每次提交 PR 时自动运行，确保代码质量
