# Windows 打包与运行说明

## 重要说明

Windows 的 `.exe` 需要在 Windows 系统上构建。请在 Windows 10/11 上执行本目录里的 `build_windows.bat`。

本构建包默认不会携带真实 `config/accounts.json`，只携带 `config/accounts.json.example`。首次运行前请复制并填写：

```bat
copy config\accounts.json.example config\accounts.json
```

## 构建环境

1. 安装 Python 3.10 或 3.11。
2. 打开项目目录。
3. 双击运行：

```text
build_windows.bat
```

脚本会自动：

- 创建 `.venv-build`
- 安装依赖和 PyInstaller
- 执行语法检查和单元测试
- 构建两个 exe
- 生成发布压缩包

构建产物位于：

```text
release\MultiAccountHedger-Windows.zip
```

## 发布包内容

解压 `MultiAccountHedger-Windows.zip` 后会看到：

```text
MultiAccountHedger-Windows\
  Dashboard\
    MultiAccountHedgerDashboard.exe
  Engine\
    MultiAccountHedgerEngine.exe
  config\
    accounts.json.example
    global_config.json
    strategy_config.json
  logs\
  启动前端控制台.bat
  启动同步引擎.bat
```

如果构建过程中只看到 `dist\MultiAccountHedgerEngine` 或 `dist\MultiAccountHedgerDashboard`，说明 PyInstaller 单个 exe 已经生成，但发布包还没有组装完成。请等命令行出现：

```text
Build complete:
...\release\MultiAccountHedger-Windows.zip
```

最终给别人使用的是 `release` 目录，不是 PyInstaller 临时使用的 `build` 目录。

## 运行方式

### 前端控制台

双击：

```text
启动前端控制台.bat
```

默认会打开：

```text
http://localhost:8502
```

如果终端里出现类似：

```text
Uvicorn server started on 0.0.0.0:8501
Local URL: http://localhost:3000
```

请以 `Local URL` 显示的地址为准。`8501` 可能只是 Streamlit 后端端口，直接访问会显示 `Not Found`。新版启动入口已经强制把浏览器访问端口固定为 `8502`。

如果要改端口，可在命令行中设置：

```bat
set HEDGER_DASHBOARD_PORT=8503
启动前端控制台.bat
```

### 同步引擎

确认配置无误后，双击：

```text
启动同步引擎.bat
```

同步引擎会读取：

```text
config\global_config.json
config\accounts.json
config\strategy_config.json
```

日志写入：

```text
logs\system.log
logs\state.json
```

## 安全建议

1. 首次运行请保持 `global_config.json` 里的 `dry_run=true`。
2. 先打开前端控制台，确认 Gate / Websea 账号、交易对、比例和方向。
3. 点击“刷新实时账户信息”，确认余额和持仓读取正常。
4. 查看 `logs\system.log`，确认没有接口签名或权限错误。
5. 小仓位验证无误后，再将 `dry_run` 改为 `false`。

当 `dry_run=false` 时，同步引擎可能真实下单。不要把包含真实 `accounts.json` 的发布包发给无关人员。
