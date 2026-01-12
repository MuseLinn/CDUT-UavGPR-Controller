# 自动构建和发布指南

## 概述
本项目使用 GitHub Actions 实现自动构建和发布功能。当您推送带有 `v*` 格式的 Git 标签时，系统会自动在多个平台上构建可执行文件并发布到 GitHub Releases。

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

当您执行第 3 步后，GitHub Actions 将自动启动构建流程，在 Windows、Linux 和 macOS 平台上分别构建可执行文件。

## 构建流程说明

GitHub Actions 工作流定义在 `.github/workflows/build-release.yml` 中，主要包含以下步骤：

1. 设置 Python 环境
2. 安装依赖项（包括 PyInstaller 和项目依赖）
3. 使用 PyInstaller 和 `main_gui.spec` 配置文件构建可执行文件
4. 将构建产物上传到 GitHub Releases

## 本地构建测试

如果您想在本地测试构建过程，可以运行：

```bash
python build_local.py
```

这将在本地尝试构建可执行文件，帮助您提前发现潜在问题。

## 构建产物

构建完成后，您可以在 GitHub 项目的 "Releases" 页面找到生成的可执行文件，包括：

- Windows: `gpr_daq_gui.exe`
- Linux: `gpr_daq_gui`
- macOS: `gpr_daq_gui`

## 注意事项

- 确保 `main_gui.spec` 文件始终与项目结构保持同步
- 图标文件 `lib/app_logo.png` 必须存在于项目中（构建时会自动转换为适当的图标格式）
- 版本标签必须遵循 `v*` 格式（如 v1.0.0, v2.1.3 等）
- 项目依赖已更新至 requirements.txt，包括 Pillow 用于图标处理