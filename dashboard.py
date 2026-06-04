from __future__ import annotations
import asyncio
import html
import json
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from clients.gate_rest import GateRestClient
from clients.websea_rest import WebseaRestClient

CONFIG_DIR = Path("config")
ACCOUNTS_PATH = CONFIG_DIR / "accounts.json"
STRATEGY_PATH = CONFIG_DIR / "strategy_config.json"
GLOBAL_PATH = CONFIG_DIR / "global_config.json"
USAGE_GUIDE_PATH = CONFIG_DIR / "usage_guide.md"

LANGUAGE_OPTIONS = {
    "中文": "zh",
    "English": "en",
}

PAGES = ["分组总览", "账号管理", "新增账号", "策略配置", "交易对配置", "原始配置", "使用说明"]

PAGE_LABELS = {
    "分组总览": "总览",
    "账号管理": "账号",
    "新增账号": "新增账号",
    "策略配置": "策略",
    "交易对配置": "交易对",
    "原始配置": "原始配置",
    "使用说明": "使用说明",
}

I18N = {
    "en": {
        "Gate + Websea 仓位跟随控制台": "Gate + Websea Position Sync Console",
        "语言": "Language",
        "选择页面": "Page",
        "当前状态": "Current Status",
        "运行模式：": "Run mode:",
        "启用账号：": "Enabled accounts:",
        "策略单元：": "Strategy units:",
        "模拟下单": "Dry run",
        "真实下单": "Live trading",
        "模拟": "Dry run",
        "实盘": "Live",
        "启用账号": "Enabled accounts",
        "策略单元": "Strategy units",
        "交易对": "Symbols",
        "运行模式": "Run mode",
        "分组总览": "Group Overview",
        "总览": "Overview",
        "账号管理": "Accounts",
        "账号": "Accounts",
        "新增账号": "Add Account",
        "策略配置": "Strategy",
        "策略": "Strategy",
        "交易对配置": "Symbols",
        "交易对": "Symbols",
        "原始配置": "Raw Config",
        "使用说明": "Guide",
        "查看 Gate 与 Websea 的账号配对、跟随开关、实时余额和持仓。": "View Gate/Websea account pairs, follow switches, live balances, and positions.",
        "维护交易账号、启用状态、接口地址和密钥。": "Manage exchange accounts, enabled state, API endpoints, and credentials.",
        "新增 Gate 或 Websea 账号，并挂载到指定策略单元。": "Add a Gate or Websea account and attach it to a strategy unit.",
        "配置主账号、对冲方向、杠杆、保证金模式和 follower 列表。": "Configure master accounts, hedge direction, leverage, margin mode, and followers.",
        "维护交易对映射、数量换算比例、步进和风控阈值。": "Maintain symbol mapping, amount conversion, steps, and risk limits.",
        "编辑运行参数和原始 JSON，查看同步状态文件。": "Edit runtime settings and raw JSON, and inspect the sync state file.",
        "查看参数中文说明、功能介绍和安全使用流程。": "Read parameter notes, feature descriptions, and safe operating flow.",
        "运行自检": "Preflight Check",
        "后端同步引擎必须单独运行。这里显示启用策略涉及的账号密钥状态和日志更新时间。": "The backend sync engine must run separately. This shows credential status and log update time for enabled strategy accounts.",
        "当前配置存在会阻断同步的问题：有启用账号缺少密钥、被禁用或不存在。": "Current config has blocking sync issues: enabled accounts are missing credentials, disabled, or absent.",
        "启用策略账号的基础配置检查通过。": "Basic configuration check passed for enabled strategy accounts.",
        "实时账户信息": "Live Account Info",
        "按账号读取交易所余额和持仓。缺密钥或接口权限错误会直接显示在表格中。": "Read exchange balances and positions by account. Missing credentials or permission errors are shown in the table.",
        "刷新实时账户信息": "Refresh Live Account Info",
        "实时余额": "Live Balances",
        "实时持仓": "Live Positions",
        "当前无持仓": "No open positions",
        "账号列表": "Account List",
        "密钥默认脱敏展示；替换密钥时在账号详情中输入新值。": "Credentials are masked by default. Enter new values in account details to replace them.",
        "还没有账号": "No accounts yet",
        "密钥字段留空表示保留原值": "Leave credential fields empty to keep existing values",
        "保存账号": "Save Account",
        "已保存": "Saved",
        "确认删除": "Confirm delete",
        "删除账号": "Delete Account",
        "已删除账号并清理策略引用": "Deleted account and cleaned strategy references",
        "新账号会写入 accounts.json，并按选择挂载到指定策略单元。": "New accounts are written to accounts.json and attached to the selected strategy unit.",
        "账号名称": "Account name",
        "交易所": "Exchange",
        "角色": "Role",
        "策略单元名称": "Strategy unit name",
        "主/跟随": "Master/Follow",
        "比例": "Ratio",
        "新增成功": "Added",
        "账号名称不能为空": "Account name is required",
        "策略单元配置": "Strategy Unit Config",
        "策略单元定义 Gate source 与 Websea hedge 的主从关系。": "Strategy units define the master/follower relationship between Gate source and Websea hedge.",
        "新增策略单元": "Add Strategy Unit",
        "策略单元名称不能为空": "Strategy unit name is required",
        "策略单元名称已存在": "Strategy unit name already exists",
        "已新增策略单元": "Strategy unit added",
        "启用策略单元": "Enable strategy unit",
        "Source 主账号": "Source master account",
        "Source 杠杆": "Source leverage",
        "Source 保证金模式": "Source margin mode",
        "Hedge 主账号": "Hedge master account",
        "Hedge 模式": "Hedge mode",
        "Hedge 比例": "Hedge ratio",
        "Hedge 杠杆": "Hedge leverage",
        "Hedge 保证金模式": "Hedge margin mode",
        "保存策略单元": "Save Strategy Unit",
        "策略单元已保存": "Strategy unit saved",
        "确认删除策略单元": "Confirm strategy unit deletion",
        "删除策略单元": "Delete Strategy Unit",
        "已删除策略单元": "Strategy unit deleted",
        "还没有策略单元": "No strategy units yet",
        "交易对规则决定 Gate 仓位如何换算成 Websea 目标仓位。": "Symbol rules decide how Gate positions are converted into Websea target positions.",
        "自动新增交易对": "Auto Add Symbol",
        "只填写 Gate source_symbol，系统会自动推导 Websea 交易对并补齐 ratio、合约面值和基础风控参数。": "Enter only the Gate source_symbol; the system infers Websea symbol, ratio, contract multipliers, and basic risk parameters.",
        "例如 BTC_USDT": "For example BTC_USDT",
        "自动获取并新增": "Fetch and Add",
        "当前交易对": "Current Symbols",
        "当前策略单元还没有交易对": "This strategy unit has no symbols yet",
        "高级参数编辑": "Advanced Parameters",
        "保存交易对配置": "Save Symbol Config",
        "交易对配置已保存": "Symbol config saved",
        "运行配置": "Runtime Config",
        "常用运行参数可以在这里直接保存；更完整配置可在下方 JSON 编辑区修改。": "Common runtime settings can be saved here; full config is editable in the JSON area below.",
        "保存运行配置": "Save Runtime Config",
        "运行配置已保存": "Runtime config saved",
        "状态文件": "State File",
        "状态文件还不存在": "State file does not exist yet",
        "JSON 编辑": "JSON Editor",
        "保存 accounts.json 前需要确认显示完整内容，避免误改密钥。": "Before saving accounts.json, confirm full content display to avoid accidental credential edits.",
        "显示并编辑完整 accounts.json": "Show and edit full accounts.json",
        "确认保存 accounts.json": "Confirm saving accounts.json",
        "已保存 global_config.json": "Saved global_config.json",
        "已保存 strategy_config.json": "Saved strategy_config.json",
        "已保存 accounts.json": "Saved accounts.json",
        "使用说明 Markdown": "Guide Markdown",
        "阅读": "Read",
        "编辑": "Edit",
        "保存使用说明": "Save Guide",
        "使用说明已保存": "Guide saved",
        "恢复默认说明": "Restore Default Guide",
        "已恢复默认使用说明": "Default guide restored",
        "说明内容保存在 config/usage_guide.md，可在页面中直接编辑并保存。": "Guide content is stored in config/usage_guide.md and can be edited directly on this page.",
        "账号配对": "Account Pairs",
        "按 Gate 与 Websea 的 master/sub 关系横向对齐展示。": "Show Gate and Websea accounts side by side by master/sub relationship.",
        "跟随开关": "Follow Switches",
        "快速调整每对子账号的启用状态和跟随比例。": "Quickly adjust each sub-account pair's enabled state and follow ratio.",
        "当前策略单元还没有子账号配对": "This strategy unit has no sub-account pairs yet",
        "未配置 Gate 子账号": "Gate sub not configured",
        "未配置 Websea 子账号": "Websea sub not configured",
        "Gate 跟随": "Gate follow",
        "Gate 比例": "Gate ratio",
        "保存 Gate": "Save Gate",
        "已保存 Gate 跟随配置": "Gate follow config saved",
        "这一组没有 Gate 子账号": "No Gate sub-account in this pair",
        "Websea 跟随": "Websea follow",
        "Websea 比例": "Websea ratio",
        "保存 Websea": "Save Websea",
        "已保存 Websea 跟随配置": "Websea follow config saved",
        "这一组没有 Websea 子账号": "No Websea sub-account in this pair",
        "配置检查": "Config Check",
        "运行健康": "Runtime Health",
        "最高风险": "Highest Risk",
        "正常": "Normal",
        "阻断": "Blocked",
        "未检测": "Unknown",
        "最近更新": "Last Update",
        "未发现运行日志": "No runtime log found",
        "真实下单模式已开启。当前页面不会执行下单，但后端同步引擎可能会真实提交订单。": "Live trading mode is enabled. This page does not place orders, but the backend engine may submit real orders.",
        "模拟运行中。当前配置默认不会真实下单。": "Dry run mode. Current config should not submit real orders by default.",
        "危险操作区": "Danger Zone",
        "该区域会修改敏感配置，请确认后再保存。": "This area changes sensitive config. Review before saving.",
    }
}

DEFAULT_CONTRACT_AMOUNT_MULTIPLIERS = {
    ("gate", "BTC_USDT"): Decimal("0.0001"),
    ("gate", "ETH_USDT"): Decimal("0.01"),
    ("gate", "SOL_USDT"): Decimal("1"),
    ("websea", "BTC-USDT"): Decimal("0.001"),
    ("websea", "ETH-USDT"): Decimal("0.01"),
    ("websea", "SOL-USDT"): Decimal("0.1"),
    ("gate", "DOGE_USDT"): Decimal("1"),
    ("websea", "DOGE-USDT"): Decimal("1"),
    ("gate", "XRP_USDT"): Decimal("1"),
    ("websea", "XRP-USDT"): Decimal("1"),
    ("gate", "ADA_USDT"): Decimal("1"),
    ("websea", "ADA-USDT"): Decimal("1"),
    ("gate", "BNB_USDT"): Decimal("0.01"),
    ("websea", "BNB-USDT"): Decimal("0.01"),
    ("gate", "LINK_USDT"): Decimal("0.1"),
    ("websea", "LINK-USDT"): Decimal("0.1"),
    ("gate", "AVAX_USDT"): Decimal("0.1"),
    ("websea", "AVAX-USDT"): Decimal("0.1"),
}

DEFAULT_USAGE_GUIDE = """# Multi Account Hedger 使用说明

## 1. 系统做什么

本系统按“仓位”同步，不按“订单”逐笔复制。

Gate 主账号作为 source，系统监听 Gate Futures WebSocket 的仓位变化。只要主账号仓位发生变化，系统会读取策略配置，计算每个目标账号应该达到的目标仓位，然后按“目标仓位 - 当前仓位”的差值进行调仓。

当前默认结构：

- Gate master：负责触发信号
- Gate sub：跟随 Gate master 同方向仓位
- Websea master：按 hedge 规则开对冲仓位
- Websea sub：仅在 Websea master 成功后才跟随

## 2. 日常使用流程

1. 在“账号管理”确认 master 账号密钥有效。
2. 暂时不用或缺密钥的 sub 账号可以先禁用，也可以保持启用，系统会记录错误并跳过。
3. 在“策略配置”确认 Gate master、Websea master、sub 列表、跟随比例和 hedge 方向。
4. 在“交易对配置”确认 Gate 合约、Websea 合约、ratio、最小同步量和风控上限。
5. 启动后端程序 `venv/bin/python launcher.py`。
6. 在“分组总览”点击“刷新实时账户信息”，确认余额和持仓显示正常。
7. 小数量下单验证 master 跟随逻辑。
8. 检查 `logs/system.log` 和 `logs/state.json`，确认是否真实发出 Websea/Gate 请求。

## 3. 关键参数

### dry_run

- `true`：模拟下单，只记录将要发送的请求。
- `false`：真实下单。

切换到 `false` 前，应先用小仓位完整验证。

### hedge.mode

- `opposite`：Websea 与 Gate source 反向。
- `same`：Websea 与 Gate source 同向。

例如 Gate BTC 多仓，`opposite` 会让 Websea 开 BTC 空仓。

### symbols[].ratio

source 到 hedge 的同步张数比例。

例如：

- Gate BTC size = `100`
- BTC ratio = `0.1`
- Websea target = `-10`

如果 `hedge.mode=opposite`，目标方向会取反。

### min_sync_delta

小于该差值时不下单，避免因为极小差异频繁补单。

### max_source_pos / max_hedge_pos

目标仓位绝对值上限。超过上限会阻断同步并记录日志。

### max_adjust_qty

单次最大调整张数。目标差值过大时会裁剪到该数量。

## 4. 持仓 size 与实际数量

交易所返回的 `size` 通常是合约张数，不一定等于真实币数量。

前端实时持仓会显示：

- 持仓size：交易所原始张数
- 实际数量：按合约面值换算后的币数量

默认合约面值：

| 交易所 | BTC | ETH | SOL |
| --- | ---: | ---: | ---: |
| Gate | 0.0001 | 0.01 | 1 |
| Websea | 0.001 | 0.01 | 0.1 |

示例：

- Gate `BTC_USDT size=100` = `0.01 BTC`
- Websea `BTC-USDT size=10` = `0.01 BTC`

如果交易所调整合约面值，可以在 `strategy_config.json` 的交易对里增加：

- `source_amount_multiplier`
- `hedge_amount_multiplier`

## 5. Master 与 Sub 容错规则

当前同步规则：

- Gate master 的 WebSocket 仓位更新被接收后，视为 source master 成功。
- Gate sub 报错不会阻断 Websea master。
- Websea master 成功后，Websea sub 才会启动。
- Websea master 失败时，对应 Websea sub 不启动。
- sub 账号缺密钥、密钥错误或接口权限异常，会记录为 `sub_error_ignored`，不会拖垮 master。

## 6. 常见问题

### Gate 下单后 Websea 没跟随

优先检查：

- 后端 `launcher.py` 是否正在运行。
- 日志是否出现 `gate ws connected`。
- 日志是否出现 `source master accepted`。
- `dry_run` 是否符合预期。
- Websea master 密钥是否有效。

### sub 没跟随

查看 `logs/state.json` 对应账号的 `last_sync`。常见原因：

- 缺少 API key/token
- API key 无合约权限
- Websea 返回 `not getting the current user`
- Gate 返回 `Invalid key provided`
- 目标差值小于 `min_sync_delta`

### 前端余额或持仓显示 ERROR

这通常是读取账户接口失败，不一定影响其他账号。展开错误信息看具体账号和接口返回。

## 7. 风险提示

`dry_run=false` 时系统可能真实下单。修改方向、比例、交易对、账号启用状态或密钥前，建议先暂停后端程序，确认配置后再启动。
"""

PAGE_META = {
    "分组总览": ("总览", "查看运行状态、配置检查、账号配对、实时余额和持仓。"),
    "账号管理": ("账号", "维护交易账号、启用状态、接口地址和密钥。"),
    "新增账号": ("新增账号", "新增 Gate 或 Websea 账号，并挂载到指定策略单元。"),
    "策略配置": ("策略", "配置主账号、对冲方向、杠杆、保证金模式和 follower 列表。"),
    "交易对配置": ("交易对", "维护交易对映射、数量换算比例、步进和风控阈值。"),
    "原始配置": ("原始配置", "编辑运行参数和原始 JSON，查看同步状态文件。"),
    "使用说明": ("使用说明", "查看参数中文说明、功能介绍和安全使用流程。"),
}


def current_language():
    return st.session_state.get("language", "zh")


def tr(text):
    if text is None:
        return text
    if current_language() == "zh":
        return text
    return I18N.get(current_language(), {}).get(str(text), text)


def page_label(page):
    return tr(PAGE_LABELS.get(page, page))


def page_from_label(label):
    for page in PAGES:
        if page_label(page) == label:
            return page
    return label


class DashboardRuntime:
    http_timeout = 10
    order_retry_times = 3
    order_retry_delay_sec = 0.5
    dry_run = True


def load_json(path: Path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_text(path: Path, default: str = ""):
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8")


def save_text(path: Path, text: str):
    path.write_text(text, encoding="utf-8")


def inject_theme():
    st.markdown(
        """
        <style>
        :root {
          --bg: #F6F8FA;
          --panel: #FFFFFF;
          --panel-soft: #F8FAFC;
          --line: #E5E7EB;
          --line-strong: #CBD5E1;
          --text: #111827;
          --muted: #6B7280;
          --muted-light: #9CA3AF;
          --accent: #2563EB;
          --accent-soft: #EFF6FF;
          --accent-text: #1D4ED8;
          --danger: #DC2626;
          --danger-soft: #FEF2F2;
          --warning: #D97706;
          --warning-soft: #FFF7ED;
          --ok: #16A34A;
          --ok-soft: #ECFDF3;
          --paused: #6B7280;
        }

        .stApp {
          background: var(--bg);
          color: var(--text);
        }

        #MainMenu,
        div[data-testid="stAppDeployButton"],
        div[data-testid="stToolbarActions"],
        div[data-testid="stDecoration"],
        div[data-testid="stStatusWidget"] {
          display: none !important;
          visibility: hidden !important;
          height: 0 !important;
        }

        div[data-testid="stToolbar"] {
          background: transparent !important;
          visibility: visible !important;
        }

        header[data-testid="stHeader"] {
          background: transparent !important;
          height: 0 !important;
          min-height: 0 !important;
        }

        button[data-testid="stBaseButton-headerNoPadding"] {
          visibility: visible !important;
        }

        button[data-testid="stExpandSidebarButton"] {
          position: fixed !important;
          top: 16px !important;
          left: 16px !important;
          z-index: 1000001 !important;
          width: 32px !important;
          height: 32px !important;
          border: 1px solid var(--line) !important;
          border-radius: 8px !important;
          background: #ffffff !important;
          color: var(--text) !important;
          box-shadow: 0 8px 24px rgba(15, 23, 42, .10) !important;
        }

        .block-container {
          padding-top: 1rem;
          padding-bottom: 3rem;
          max-width: 1440px;
        }

        section[data-testid="stSidebar"] {
          background: #ffffff;
          border-right: 1px solid var(--line);
          color: var(--text);
        }

        section[data-testid="stSidebar"] * {
          color: var(--text) !important;
        }

        section[data-testid="stSidebar"] h1 {
          font-size: 1.35rem;
          color: var(--text);
          margin-bottom: .25rem;
        }

        section[data-testid="stSidebar"] [role="radiogroup"] label {
          border-radius: 6px;
          padding: .35rem .45rem;
          margin-bottom: .15rem;
        }

        section[data-testid="stSidebar"] [role="radiogroup"] label,
        section[data-testid="stSidebar"] [role="radiogroup"] label p,
        section[data-testid="stSidebar"] [role="radiogroup"] label span,
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
          color: var(--text) !important;
        }

        section[data-testid="stSidebar"] [role="radiogroup"] label:hover {
          background: var(--panel-soft);
        }

        label,
        label p,
        label span,
        [data-testid="stWidgetLabel"],
        [data-testid="stWidgetLabel"] p,
        [data-testid="stWidgetLabel"] span {
          color: var(--text) !important;
        }

        .stCheckbox label,
        .stCheckbox label p,
        .stRadio label,
        .stRadio label p {
          color: var(--text) !important;
        }

        .app-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 1rem;
          padding: 1rem 1.1rem;
          border: 1px solid var(--line);
          border-radius: 8px;
          background: var(--panel);
          margin-bottom: 1rem;
        }

        .app-title {
          font-size: 1.45rem;
          line-height: 1.2;
          font-weight: 700;
          color: var(--text);
          margin: 0;
          letter-spacing: 0;
        }

        .app-subtitle {
          margin-top: .35rem;
          color: var(--muted);
          font-size: .92rem;
        }

        .status-row {
          display: flex;
          flex-wrap: wrap;
          gap: .45rem;
          justify-content: flex-end;
          max-width: 780px;
        }

        .status-pill {
          display: inline-flex;
          align-items: center;
          min-height: 28px;
          border-radius: 999px;
          padding: .25rem .65rem;
          font-size: .78rem;
          font-weight: 650;
          border: 1px solid var(--line);
          background: var(--panel-soft);
          color: var(--text);
          white-space: nowrap;
        }

        .status-pill.ok {
          color: var(--ok);
          background: var(--ok-soft);
          border-color: #abefc6;
        }

        .status-pill.warn {
          color: var(--warning);
          background: var(--warning-soft);
          border-color: #fedf89;
        }

        .status-pill.danger {
          color: var(--danger);
          background: var(--danger-soft);
          border-color: #fecdca;
        }

        .status-pill.info {
          color: var(--accent-text);
          background: var(--accent-soft);
          border-color: #BFDBFE;
        }

        .mode-banner {
          display: flex;
          align-items: flex-start;
          gap: .65rem;
          border-radius: 8px;
          padding: .75rem .9rem;
          border: 1px solid var(--line);
          background: var(--panel);
          margin-bottom: 1rem;
        }

        .mode-banner.danger {
          background: var(--danger-soft);
          border-color: #FCA5A5;
          color: var(--danger);
        }

        .mode-banner.ok {
          background: var(--ok-soft);
          border-color: #BBF7D0;
          color: var(--ok);
        }

        .mode-banner-title {
          font-weight: 760;
          margin-bottom: .15rem;
        }

        .mode-banner-copy {
          color: var(--text);
          font-size: .88rem;
        }

        .section-heading {
          margin-top: 1.15rem;
          margin-bottom: .45rem;
          font-size: 1.05rem;
          font-weight: 700;
          color: var(--text);
        }

        .section-note {
          margin-top: -.2rem;
          margin-bottom: .75rem;
          color: var(--muted);
          font-size: .88rem;
        }

        .panel {
          border: 1px solid var(--line);
          background: var(--panel);
          border-radius: 8px;
          padding: .9rem;
          margin-bottom: 1rem;
        }

        .danger-panel {
          border: 1px solid #FCA5A5;
          background: var(--danger-soft);
          border-radius: 8px;
          padding: .9rem;
          margin: .75rem 0 1rem;
        }

        .danger-panel-title {
          color: var(--danger);
          font-weight: 760;
          margin-bottom: .2rem;
        }

        .danger-panel-copy {
          color: var(--text);
          font-size: .88rem;
        }

        .metric-band {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: .75rem;
          margin-bottom: 1rem;
        }

        .metric-tile {
          background: var(--panel);
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: .85rem .9rem;
        }

        .metric-tile.danger {
          border-color: #FCA5A5;
          background: var(--danger-soft);
        }

        .metric-tile.warn {
          border-color: #FED7AA;
          background: var(--warning-soft);
        }

        .metric-tile.ok {
          border-color: #BBF7D0;
          background: var(--ok-soft);
        }

        .metric-label {
          color: var(--muted);
          font-size: .78rem;
          margin-bottom: .25rem;
        }

        .metric-value {
          color: var(--text);
          font-size: 1.35rem;
          font-weight: 750;
          line-height: 1.15;
        }

        .metric-help {
          color: var(--muted);
          font-size: .72rem;
          margin-top: .25rem;
        }

        div[data-testid="stExpander"] {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: var(--panel);
          box-shadow: none;
        }

        div[data-testid="stExpander"] details summary {
          font-weight: 700;
        }

        div[data-testid="stDataFrame"],
        div[data-testid="stTable"] {
          border-radius: 8px;
          overflow: hidden;
          color: var(--text);
        }

        div[data-testid="stDataFrame"] *,
        div[data-testid="stTable"] * {
          color: var(--text);
        }

        .ws-table-wrap {
          border: 1px solid var(--line);
          border-radius: 8px;
          overflow-x: auto;
          background: var(--panel);
          margin: .65rem 0 1rem;
        }

        table.ws-table {
          width: 100%;
          border-collapse: collapse;
          font-size: .84rem;
          color: var(--text);
        }

        table.ws-table thead th {
          background: #F1F5F9;
          color: #374151;
          font-weight: 720;
          text-align: left;
          padding: .62rem .7rem;
          border-bottom: 1px solid var(--line);
          white-space: nowrap;
        }

        table.ws-table tbody td {
          padding: .6rem .7rem;
          border-bottom: 1px solid #EEF2F7;
          vertical-align: top;
        }

        table.ws-table tbody tr:last-child td {
          border-bottom: 0;
        }

        table.ws-table tbody tr:hover td {
          background: #F8FAFC;
        }

        div[data-testid="stAlert"] {
          border-radius: 8px;
        }

        .stButton > button,
        .stDownloadButton > button,
        button[kind="primary"] {
          border-radius: 6px;
          border: 1px solid var(--line-strong);
          background: #ffffff;
          color: var(--text);
          box-shadow: none;
          font-weight: 650;
        }

        .stButton > button *,
        .stDownloadButton > button * {
          color: inherit !important;
        }

        .stButton > button:hover {
          border-color: var(--accent);
          color: var(--accent);
        }

        button[kind="primary"] {
          background: var(--accent) !important;
          border-color: var(--accent) !important;
          color: #ffffff !important;
        }

        button[kind="primary"] * {
          color: #ffffff !important;
        }

        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div,
        textarea {
          border-radius: 6px !important;
          color: var(--text) !important;
          background: #ffffff !important;
        }

        input,
        textarea,
        [contenteditable="true"] {
          color: var(--text) !important;
        }

        h1, h2, h3, h4 {
          letter-spacing: 0;
        }

        code {
          color: var(--accent-text);
          background: #F1F5F9;
          border-radius: 4px;
          padding: .08rem .25rem;
        }

        @media (max-width: 900px) {
          .app-header {
            flex-direction: column;
          }
          .status-row {
            justify-content: flex-start;
          }
          .metric-band {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
        }

        @media (max-width: 560px) {
          .metric-band {
            grid-template-columns: 1fr;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_section(title, note=None):
    st.markdown(f'<div class="section-heading">{tr(title)}</div>', unsafe_allow_html=True)
    if note:
        st.markdown(f'<div class="section-note">{tr(note)}</div>', unsafe_allow_html=True)


def esc(value):
    return html.escape(str(value))


def status_pill(label, class_name=""):
    return f'<span class="status-pill {class_name}">{esc(label)}</span>'


def render_table(data):
    df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    if df.empty:
        st.info(tr("暂无数据") if current_language() == "zh" else "No data")
        return
    table_html = df.to_html(index=False, escape=True, classes="ws-table", border=0)
    st.markdown(f'<div class="ws-table-wrap">{table_html}</div>', unsafe_allow_html=True)


def risk_summary(accounts_data, strategy_data, global_data):
    checks = pd.DataFrame(preflight_rows(accounts_data, strategy_data))
    has_blocker = not checks.empty and (checks["状态"] == "ERROR").any()
    dry_run = bool(global_data.get("dry_run", True))
    state_path = Path(global_data.get("state_file", "logs/state.json"))
    log_path = Path("logs/system.log")
    if has_blocker or not dry_run:
        level = "阻断" if has_blocker else "预警"
        cls = "danger" if has_blocker or not dry_run else "warn"
    else:
        level = "正常"
        cls = "ok"
    if log_path.exists():
        updated = datetime.fromtimestamp(log_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    elif state_path.exists():
        updated = datetime.fromtimestamp(state_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    else:
        updated = tr("未发现运行日志")
    return {
        "checks": checks,
        "has_blocker": has_blocker,
        "dry_run": dry_run,
        "level": level,
        "class": cls,
        "updated": updated,
    }


def render_mode_banner(global_data):
    dry_run = bool(global_data.get("dry_run", True))
    if dry_run:
        title = tr("模拟下单")
        copy = tr("模拟运行中。当前配置默认不会真实下单。")
        cls = "ok"
    else:
        title = tr("真实下单")
        copy = tr("真实下单模式已开启。当前页面不会执行下单，但后端同步引擎可能会真实提交订单。")
        cls = "danger"
    st.markdown(
        f"""
        <div class="mode-banner {cls}">
          <div>
            <div class="mode-banner-title">{esc(title)}</div>
            <div class="mode-banner-copy">{esc(copy)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_danger_panel(title, copy):
    st.markdown(
        f"""
        <div class="danger-panel">
          <div class="danger-panel-title">{esc(tr(title))}</div>
          <div class="danger-panel-copy">{esc(tr(copy))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def dashboard_metrics(accounts_data, strategy_data, global_data):
    accounts = accounts_data.get("accounts", {})
    units = strategy_data.get("units", [])
    enabled_accounts = sum(1 for cfg in accounts.values() if cfg.get("enabled", True))
    enabled_units = sum(1 for unit in units if unit.get("enabled", True))
    symbol_count = sum(len(unit.get("symbols", [])) for unit in units)
    dry_run = bool(global_data.get("dry_run", True))
    checks = pd.DataFrame(preflight_rows(accounts_data, strategy_data))
    blocker_count = int((checks["状态"] == "ERROR").sum()) if not checks.empty else 0
    return [
        {"label": tr("启用账号"), "value": enabled_accounts, "class": ""},
        {"label": tr("策略单元"), "value": enabled_units, "class": ""},
        {"label": tr("交易对"), "value": symbol_count, "class": ""},
        {
            "label": tr("配置检查"),
            "value": tr("阻断") if blocker_count else tr("正常"),
            "class": "danger" if blocker_count else "ok",
            "help": f"{blocker_count} blocker" if blocker_count else "",
        },
    ]


def used_strategy_accounts(strategy_data):
    used = []
    for unit in strategy_data.get("units", []):
        if not unit.get("enabled", True):
            continue
        source = unit.get("source", {})
        hedge = unit.get("hedge", {})
        for role, account in [
            ("source master", source.get("account")),
            ("hedge master", hedge.get("account")),
        ]:
            if account:
                used.append({"unit": unit.get("name"), "role": role, "account": account})
        for item in source.get("followers", []):
            if item.get("enabled", True):
                used.append({"unit": unit.get("name"), "role": "source follower", "account": item.get("account")})
        for item in hedge.get("followers", []):
            if item.get("enabled", True):
                used.append({"unit": unit.get("name"), "role": "hedge follower", "account": item.get("account")})
    return used


def account_has_credentials(cfg):
    if cfg.get("exchange") == "gate":
        return bool(cfg.get("api_key") or cfg.get("key")) and bool(cfg.get("api_secret") or cfg.get("secret"))
    if cfg.get("exchange") == "websea":
        return bool(cfg.get("token") or cfg.get("api_key")) and bool(cfg.get("secret_key") or cfg.get("api_secret"))
    return False


def preflight_rows(accounts_data, strategy_data):
    accounts = accounts_data.get("accounts", {})
    rows = []
    for item in used_strategy_accounts(strategy_data):
        cfg = accounts.get(item["account"], {})
        exists = bool(cfg)
        enabled = bool(cfg.get("enabled", True)) if exists else False
        has_credentials = account_has_credentials(cfg) if exists else False
        status = "OK" if exists and enabled and has_credentials else "ERROR"
        if not exists:
            reason = "账号不存在"
        elif not enabled:
            reason = "账号已禁用"
        elif not has_credentials:
            reason = "缺少 API key/token 或 secret"
        else:
            reason = ""
        rows.append({
            "状态": status,
            "策略单元": item["unit"],
            "角色": item["role"],
            "账号": item["account"],
            "交易所": cfg.get("exchange", ""),
            "原因": reason,
        })
    return rows


def log_health_row(global_data):
    log_path = Path("logs/system.log")
    state_path = Path(global_data.get("state_file", "logs/state.json"))
    rows = []
    for label, path in [("系统日志", log_path), ("状态文件", state_path)]:
        if path.exists():
            updated = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            rows.append({"文件": label, "路径": str(path), "最后更新": updated, "大小": path.stat().st_size})
        else:
            rows.append({"文件": label, "路径": str(path), "最后更新": "不存在", "大小": 0})
    return rows


def render_metric_band(metrics):
    html = ['<div class="metric-band">']
    for item in metrics:
        if isinstance(item, dict):
            label = item.get("label", "")
            value = item.get("value", "")
            cls = item.get("class", "")
            help_text = item.get("help", "")
        else:
            label, value = item
            cls = ""
            help_text = ""
        help_html = f'<div class="metric-help">{esc(help_text)}</div>' if help_text else ''
        html.append(
            f'<div class="metric-tile {cls}">'
            f'<div class="metric-label">{esc(label)}</div>'
            f'<div class="metric-value">{esc(value)}</div>'
            f'{help_html}'
            '</div>'
        )
    html.append('</div>')
    st.markdown("".join(html), unsafe_allow_html=True)


def render_app_header(page, accounts_data, strategy_data, global_data):
    title, subtitle = PAGE_META.get(page, (page, ""))
    risk = risk_summary(accounts_data, strategy_data, global_data)
    dry_run = risk["dry_run"]
    enabled_accounts = sum(1 for cfg in accounts_data.get("accounts", {}).values() if cfg.get("enabled", True))
    enabled_units = sum(1 for unit in strategy_data.get("units", []) if unit.get("enabled", True))
    mode_class = "ok" if dry_run else "danger"
    mode_text = tr("模拟下单") if dry_run else tr("真实下单")
    check_class = "danger" if risk["has_blocker"] else "ok"
    check_text = f"{tr('配置检查')}：{tr('阻断') if risk['has_blocker'] else tr('正常')}"
    risk_text = f"{tr('最高风险')}：{tr(risk['level'])}"
    html = f"""
    <div class="app-header">
      <div>
        <div class="app-title">{esc(tr(title))}</div>
        <div class="app-subtitle">{esc(tr(subtitle))}</div>
      </div>
      <div class="status-row">
        {status_pill(mode_text, mode_class)}
        {status_pill(check_text, check_class)}
        {status_pill(risk_text, risk["class"])}
        {status_pill(f"{tr('最近更新')}：{risk['updated']}", "info")}
        {status_pill(f"{tr('启用账号')} {enabled_accounts}", "")}
        {status_pill(f"{tr('策略单元')} {enabled_units}", "")}
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    render_mode_banner(global_data)


def mask_key(value):
    if not value:
        return ""
    value = str(value)
    if len(value) <= 8:
        return "***"
    return value[:4] + "****" + value[-4:]


def ensure_files():
    CONFIG_DIR.mkdir(exist_ok=True)
    if not ACCOUNTS_PATH.exists():
        save_json(ACCOUNTS_PATH, {"accounts": {}, "telegram": {"enabled": False, "bot_token": "", "chat_id": ""}})
    if not STRATEGY_PATH.exists():
        save_json(STRATEGY_PATH, {"units": []})
    if not GLOBAL_PATH.exists():
        save_json(GLOBAL_PATH, {
            "poll_interval_sec": 1,
            "debounce_ms": 80,
            "http_timeout": 10,
            "ws_ping_interval": 10,
            "ws_ping_timeout": 10,
            "reconnect_delay_sec": 3,
            "state_file": "logs/state.json",
            "alert_cooldown_sec": 60,
            "sync_timeout_warn_sec": 3,
            "max_position_deviation": "0",
            "dry_run": True,
            "log_level": "INFO",
            "max_concurrent_adjustments": 20,
            "min_reload_interval_sec": 1,
            "order_retry_times": 3,
            "order_retry_delay_sec": 0.5
        })
    if not USAGE_GUIDE_PATH.exists():
        save_text(USAGE_GUIDE_PATH, DEFAULT_USAGE_GUIDE)


def default_unit(unit_name: str):
    return {
        "name": unit_name,
        "enabled": True,
        "source": {"account": "", "exchange": "gate", "settle": "usdt", "leverage": 10, "margin_mode": "cross", "followers": []},
        "hedge": {"account": "", "exchange": "websea", "mode": "opposite", "ratio": "1", "leverage": 10, "margin_mode": "cross", "followers": []},
        "symbols": []
    }


def add_account(account_name: str, exchange: str, api_key: str, api_secret: str,
                user_id: str = "", role: str = "sub", unit_name: str = "unit_1",
                side: str = "source", ratio: str = "1"):
    accounts_data = load_json(ACCOUNTS_PATH)
    strategy_data = load_json(STRATEGY_PATH)
    accounts = accounts_data.setdefault("accounts", {})

    if exchange == "gate":
        accounts[account_name] = {
            "enabled": True, "exchange": "gate", "api_key": api_key, "api_secret": api_secret,
            "key": api_key, "secret": api_secret, "user_id": user_id,
            "base_url": "https://api.gateio.ws/api/v4", "ws_url": "wss://fx-ws.gateio.ws/v4/ws/usdt"
        }
    else:
        accounts[account_name] = {
            "enabled": True, "exchange": "websea", "token": api_key, "secret_key": api_secret,
            "api_key": api_key, "api_secret": api_secret, "base_url": "https://oapi.websea.com"
        }

    units = strategy_data.setdefault("units", [])
    unit = next((u for u in units if u.get("name") == unit_name), None)
    if unit is None:
        unit = default_unit(unit_name)
        units.append(unit)

    if role == "master":
        unit[side]["account"] = account_name
        unit[side]["exchange"] = exchange
    else:
        followers = unit[side].setdefault("followers", [])
        if not any(x.get("account") == account_name for x in followers):
            followers.append({"account": account_name, "ratio": ratio or "1", "enabled": False})  # 默认不跟随

    save_json(ACCOUNTS_PATH, accounts_data)
    save_json(STRATEGY_PATH, strategy_data)


def update_follower_config(unit_name, leg_name, account_name, enabled, ratio):
    strategy_data = load_json(STRATEGY_PATH)
    for unit in strategy_data.get("units", []):
        if unit.get("name") != unit_name:
            continue
        leg = unit.get(leg_name, {})
        for f in leg.get("followers", []):
            if f.get("account") == account_name:
                f["enabled"] = bool(enabled)
                f["ratio"] = str(ratio)
                save_json(STRATEGY_PATH, strategy_data)
                return
    raise ValueError(f"没有找到 follower: {unit_name}/{leg_name}/{account_name}")


def account_display_rows(accounts_data):
    rows = []
    for name, cfg in accounts_data.get("accounts", {}).items():
        rows.append({
            "name": name,
            "enabled": bool(cfg.get("enabled", True)),
            "exchange": cfg.get("exchange", ""),
            "api_key": mask_key(cfg.get("api_key") or cfg.get("token")),
            "api_secret": mask_key(cfg.get("api_secret") or cfg.get("secret_key") or cfg.get("secret")),
            "user_id": cfg.get("user_id", ""),
            "base_url": cfg.get("base_url", ""),
            "ws_url": cfg.get("ws_url", ""),
        })
    return rows


def account_names(accounts_data, exchange=None):
    names = []
    for name, cfg in accounts_data.get("accounts", {}).items():
        if exchange is None or cfg.get("exchange") == exchange:
            names.append(name)
    return names


def select_index(options, value):
    if value in options:
        return options.index(value)
    return 0


def validate_decimal_text(value, field_name):
    try:
        dec = Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"{field_name} 必须是数字: {value}") from exc
    if not dec.is_finite():
        raise ValueError(f"{field_name} 必须是有限数字: {value}")


def fetch_json_url(url: str, timeout: float = 8):
    req = urllib.request.Request(url, headers={"User-Agent": "multi-account-hedger-dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def infer_hedge_symbol(source_symbol: str):
    return source_symbol.strip().upper().replace("_", "-")


def default_symbol_limits(source_symbol: str):
    return {
        "max_source_pos": "99999999",
        "max_hedge_pos": "99999999",
        "max_adjust_qty": "99999999",
    }


def fallback_multiplier(exchange: str, symbol: str):
    multiplier = DEFAULT_CONTRACT_AMOUNT_MULTIPLIERS.get((exchange, symbol))
    if multiplier is not None:
        return multiplier
    base = base_asset(symbol)
    if base in {"BTC"}:
        return Decimal("0.0001") if exchange == "gate" else Decimal("0.001")
    if base in {"ETH", "BNB"}:
        return Decimal("0.01")
    if base in {"SOL", "DOGE", "XRP", "ADA"}:
        return Decimal("1") if exchange == "gate" else Decimal("0.1" if base == "SOL" else "1")
    return Decimal("1")


def auto_symbol_config(source_symbol: str, settle: str = "usdt"):
    source_symbol = source_symbol.strip().upper()
    if not source_symbol:
        raise ValueError("请先填写 source_symbol")
    if "_" not in source_symbol:
        raise ValueError("source_symbol 建议使用 Gate 格式，例如 BTC_USDT")

    hedge_symbol = infer_hedge_symbol(source_symbol)
    warnings = []
    gate_info = {}
    websea_info = {}

    try:
        gate_url = (
            "https://api.gateio.ws/api/v4/futures/"
            f"{urllib.parse.quote(settle or 'usdt')}/contracts/{urllib.parse.quote(source_symbol)}"
        )
        gate_info = fetch_json_url(gate_url)
    except Exception as exc:
        warnings.append(f"Gate 合约信息获取失败，已使用本地默认值：{exc}")

    try:
        websea_url = (
            "https://oapi.websea.com/v1/futures/info?"
            f"symbol={urllib.parse.quote(hedge_symbol)}"
        )
        websea_data = fetch_json_url(websea_url)
        result = websea_data.get("result", [])
        websea_info = result[0] if result else {}
        if int(websea_data.get("errno", 0) or 0) != 0:
            warnings.append(f"Websea 合约信息返回异常：{websea_data.get('errmsg')}")
    except Exception as exc:
        warnings.append(f"Websea 合约信息获取失败，已使用本地默认值：{exc}")

    source_multiplier = (
        decimal_or_none(gate_info.get("quanto_multiplier"))
        or fallback_multiplier("gate", source_symbol)
    )
    hedge_multiplier = (
        decimal_or_none(websea_info.get("contract_price"))
        or fallback_multiplier("websea", hedge_symbol)
    )
    if not gate_info.get("quanto_multiplier"):
        warnings.append(f"Gate {source_symbol} 未获取到在线合约面值，已填入可编辑默认值 {format_decimal(source_multiplier)}")
    if not websea_info.get("contract_price"):
        warnings.append(f"Websea {hedge_symbol} 未获取到在线合约面值，已填入可编辑默认值 {format_decimal(hedge_multiplier)}")
    if hedge_multiplier == 0:
        hedge_multiplier = Decimal("1")
        warnings.append("Websea 合约面值为 0，已临时按 1 处理，请在高级参数中校正。")

    ratio = source_multiplier / hedge_multiplier
    limits = default_symbol_limits(source_symbol)
    source_min_qty = gate_info.get("order_size_min")
    if source_min_qty in (None, "", 0, "0"):
        source_min_qty = "1"

    return {
        "config": {
            "source_symbol": source_symbol,
            "hedge_symbol": hedge_symbol,
            "enabled": True,
            "ratio": format_decimal(ratio),
            "source_amount_multiplier": format_decimal(source_multiplier),
            "hedge_amount_multiplier": format_decimal(hedge_multiplier),
            "min_sync_delta": "1",
            "source_step": "1",
            "hedge_step": "1",
            "source_min_qty": str(source_min_qty),
            "hedge_min_qty": "1",
            **limits,
        },
        "warnings": warnings,
        "gate_info": gate_info,
        "websea_info": websea_info,
    }


def save_account_edits(account_name, cfg, enabled, base_url, ws_url, user_id, api_key, api_secret):
    cfg["enabled"] = bool(enabled)
    if base_url:
        cfg["base_url"] = base_url.strip()
    if cfg.get("exchange") == "gate":
        cfg["user_id"] = user_id.strip()
        if ws_url:
            cfg["ws_url"] = ws_url.strip()
        if api_key:
            cfg["api_key"] = api_key.strip()
            cfg["key"] = api_key.strip()
        if api_secret:
            cfg["api_secret"] = api_secret.strip()
            cfg["secret"] = api_secret.strip()
    else:
        if api_key:
            cfg["token"] = api_key.strip()
            cfg["api_key"] = api_key.strip()
        if api_secret:
            cfg["secret_key"] = api_secret.strip()
            cfg["api_secret"] = api_secret.strip()


def remove_account_references(strategy_data, account_name):
    for unit in strategy_data.get("units", []):
        for leg_name in ("source", "hedge"):
            leg = unit.get(leg_name, {})
            if leg.get("account") == account_name:
                leg["account"] = ""
            leg["followers"] = [
                item for item in leg.get("followers", [])
                if item.get("account") != account_name
            ]


def normalize_symbol_rows(rows):
    normalized = []
    for row in rows:
        if not row:
            continue
        source_symbol = str(row.get("source_symbol") or "").strip()
        hedge_symbol = str(row.get("hedge_symbol") or "").strip()
        if not source_symbol and not hedge_symbol:
            continue
        if not source_symbol or not hedge_symbol:
            raise ValueError("每个交易对必须同时填写 source_symbol 和 hedge_symbol")

        item = {
            "source_symbol": source_symbol,
            "hedge_symbol": hedge_symbol,
            "enabled": bool(row.get("enabled", True)),
            "ratio": str(row.get("ratio", "1")),
            "source_amount_multiplier": str(row.get("source_amount_multiplier", "")),
            "hedge_amount_multiplier": str(row.get("hedge_amount_multiplier", "")),
            "min_sync_delta": str(row.get("min_sync_delta", "0")),
            "source_step": str(row.get("source_step", "1")),
            "hedge_step": str(row.get("hedge_step", "1")),
            "source_min_qty": str(row.get("source_min_qty", "1")),
            "hedge_min_qty": str(row.get("hedge_min_qty", "1")),
            "max_source_pos": str(row.get("max_source_pos", "")),
            "max_hedge_pos": str(row.get("max_hedge_pos", "")),
            "max_adjust_qty": str(row.get("max_adjust_qty", "")),
        }
        for field in [
            "ratio", "source_amount_multiplier", "hedge_amount_multiplier",
            "min_sync_delta", "source_step", "hedge_step",
            "source_min_qty", "hedge_min_qty", "max_source_pos",
            "max_hedge_pos", "max_adjust_qty",
        ]:
            if item[field] != "":
                validate_decimal_text(item[field], field)
        for nullable in ("source_amount_multiplier", "hedge_amount_multiplier", "max_source_pos", "max_hedge_pos", "max_adjust_qty"):
            if item[nullable] == "":
                item.pop(nullable)
        normalized.append(item)
    if not normalized:
        raise ValueError("至少需要保留一个交易对")
    return normalized


def masked_accounts_data(accounts_data):
    data = json.loads(json.dumps(accounts_data, ensure_ascii=False))
    for cfg in data.get("accounts", {}).values():
        for key in ("api_key", "api_secret", "key", "secret", "token", "secret_key"):
            if cfg.get(key):
                cfg[key] = mask_key(cfg[key])
    telegram = data.get("telegram", {})
    if telegram.get("bot_token"):
        telegram["bot_token"] = mask_key(telegram["bot_token"])
    return data


def account_summary(accounts, account_name):
    cfg = accounts.get(account_name or "", {})
    if not account_name:
        return {
            "account": "",
            "enabled": "",
            "exchange": "",
            "api_key": "",
        }
    return {
        "account": account_name,
        "enabled": bool(cfg.get("enabled", True)),
        "exchange": cfg.get("exchange", ""),
        "api_key": mask_key(cfg.get("api_key") or cfg.get("token")),
    }


def paired_account_rows(unit, accounts):
    source = unit.get("source", {})
    hedge = unit.get("hedge", {})
    rows = []

    source_master = account_summary(accounts, source.get("account"))
    hedge_master = account_summary(accounts, hedge.get("account"))
    rows.append({
        "组": "master-master",
        "Gate账号": source_master["account"],
        "Gate启用": source_master["enabled"],
        "Gate Key": source_master["api_key"],
        "Gate比例": "1",
        "Websea账号": hedge_master["account"],
        "Websea启用": hedge_master["enabled"],
        "Websea Key": hedge_master["api_key"],
        "Websea比例": str(hedge.get("ratio", "1")),
        "Hedge模式": hedge.get("mode", "same"),
    })

    source_followers = source.get("followers", [])
    hedge_followers = hedge.get("followers", [])
    total = max(len(source_followers), len(hedge_followers))
    for idx in range(total):
        source_member = source_followers[idx] if idx < len(source_followers) else {}
        hedge_member = hedge_followers[idx] if idx < len(hedge_followers) else {}
        source_acc = account_summary(accounts, source_member.get("account"))
        hedge_acc = account_summary(accounts, hedge_member.get("account"))
        rows.append({
            "组": f"sub-sub #{idx + 1}",
            "Gate账号": source_acc["account"],
            "Gate启用": bool(source_member.get("enabled", False)) if source_member else "",
            "Gate Key": source_acc["api_key"],
            "Gate比例": str(source_member.get("ratio", "")),
            "Websea账号": hedge_acc["account"],
            "Websea启用": bool(hedge_member.get("enabled", False)) if hedge_member else "",
            "Websea Key": hedge_acc["api_key"],
            "Websea比例": str(hedge_member.get("ratio", "")),
            "Hedge模式": "",
        })
    return rows


def build_client(account_name, account_cfg, global_data):
    exchange = account_cfg.get("exchange")
    runtime = DashboardRuntime()
    runtime.http_timeout = float(global_data.get("http_timeout", 10))
    runtime.order_retry_times = int(global_data.get("order_retry_times", 3))
    runtime.order_retry_delay_sec = float(global_data.get("order_retry_delay_sec", 0.5))
    runtime.dry_run = True

    if exchange == "gate":
        return GateRestClient(account_name=account_name,
                              api_key=account_cfg.get("api_key") or account_cfg.get("key"),
                              api_secret=account_cfg.get("api_secret") or account_cfg.get("secret"),
                              user_id=account_cfg.get("user_id"),
                              base_url=account_cfg.get("base_url") or "https://api.gateio.ws/api/v4",
                              runtime=runtime)
    if exchange == "websea":
        return WebseaRestClient(account_name=account_name,
                                token=account_cfg.get("token") or account_cfg.get("api_key"),
                                secret_key=account_cfg.get("secret_key") or account_cfg.get("api_secret"),
                                base_url=account_cfg.get("base_url") or "https://oapi.websea.com",
                                runtime=runtime)
    raise ValueError(f"unsupported exchange: {exchange}")


async def fetch_account_runtime(account_name, account_cfg, global_data):
    client = build_client(account_name, account_cfg, global_data)
    try:
        await client.start()
        balance = await client.get_balance() if hasattr(client, "get_balance") else {}
        positions = await client.get_all_positions() if hasattr(client, "get_all_positions") else []
        return {"account": account_name, "exchange": account_cfg.get("exchange"), "balance": balance, "positions": positions}
    finally:
        await client.close()


def decimal_or_none(value):
    try:
        if value in (None, ""):
            return None
        return Decimal(str(value))
    except Exception:
        return None


def format_decimal(value: Decimal):
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def base_asset(symbol: str | None):
    if not symbol:
        return ""
    return str(symbol).replace("_", "-").split("-")[0]


def build_contract_amount_index(strategy_data):
    index = {}
    for unit in strategy_data.get("units", []):
        if not unit.get("enabled", True):
            continue
        for rule in unit.get("symbols", []):
            if not rule.get("enabled", True):
                continue
            source_symbol = rule.get("source_symbol")
            hedge_symbol = rule.get("hedge_symbol")
            source_multiplier = (
                decimal_or_none(rule.get("source_amount_multiplier"))
                or DEFAULT_CONTRACT_AMOUNT_MULTIPLIERS.get(("gate", source_symbol))
            )
            hedge_multiplier = (
                decimal_or_none(rule.get("hedge_amount_multiplier"))
                or DEFAULT_CONTRACT_AMOUNT_MULTIPLIERS.get(("websea", hedge_symbol))
            )
            if source_symbol and source_multiplier is not None:
                asset = base_asset(source_symbol)
                index[("gate", source_symbol)] = {
                    "multiplier": source_multiplier,
                    "asset": asset,
                    "formula": f"{source_symbol} size × {format_decimal(source_multiplier)} = {asset} amount",
                }
            if hedge_symbol and hedge_multiplier is not None:
                asset = base_asset(hedge_symbol)
                index[("websea", hedge_symbol)] = {
                    "multiplier": hedge_multiplier,
                    "asset": asset,
                    "formula": f"{hedge_symbol} size × {format_decimal(hedge_multiplier)} = {asset} amount",
                }
    return index


def enrich_position_row(row: dict, amount_index: dict):
    exchange = str(row.get("exchange", "")).lower()
    symbol = row.get("symbol")
    raw_size = decimal_or_none(row.get("size"))
    rule = amount_index.get((exchange, symbol))
    enriched = dict(row)
    enriched["raw_size"] = str(row.get("size", ""))
    if raw_size is None or rule is None:
        enriched["display_quantity"] = str(row.get("size", ""))
        enriched["actual_amount"] = str(row.get("size", ""))
        enriched["amount_unit"] = ""
        enriched["contract_multiplier"] = ""
        enriched["conversion_formula"] = ""
        return enriched

    amount = raw_size.copy_abs() * rule["multiplier"]
    enriched["actual_amount"] = format_decimal(amount)
    enriched["display_quantity"] = enriched["actual_amount"]
    enriched["amount_unit"] = rule["asset"]
    enriched["contract_multiplier"] = format_decimal(rule["multiplier"])
    enriched["conversion_formula"] = rule["formula"]
    return enriched


def build_position_charts(position_rows: list):
    if not position_rows:
        return None
    df = pd.DataFrame(position_rows)
    # 类型安全
    for col in ['display_quantity', 'size', 'pnl']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    if 'display_quantity' not in df.columns:
        df['display_quantity'] = df.get('size', 0)

    fig = go.Figure()
    side_colors = {
        ("gate", "LONG"): "#0f766e",
        ("gate", "SHORT"): "#b42318",
        ("websea", "LONG"): "#2563eb",
        ("websea", "SHORT"): "#a15c07",
    }
    for exch in df['exchange'].unique():
        for side in ['LONG', 'SHORT']:
            df_side = df[(df['exchange'] == exch) & (df['side'] == side)]
            if df_side.empty: continue
            fig.add_trace(go.Bar(
                x=df_side['account'] + " | " + df_side['symbol'],
                y=df_side['display_quantity'] if side == 'LONG' else -df_side['display_quantity'],
                name=f"{exch} {side}",
                marker_color=side_colors.get((str(exch).lower(), side), "#64748b"),
            ))
    fig.update_layout(title="各账号多空仓位（正=多，负=空）", barmode='relative',
                      xaxis_tickangle=-35, yaxis_title="实际币数量", height=400,
                      margin=dict(l=20, r=20, t=50, b=80),
                      paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
                      font=dict(color="#18212f"))

    pnl_fig = go.Figure()
    pnl_colors = {"gate": "#0f766e", "websea": "#2563eb"}
    for exch in df['exchange'].unique():
        df_exch = df[df['exchange'] == exch]
        if df_exch.empty: continue
        pnl_fig.add_trace(go.Scatter(
            x=df_exch['account'] + " | " + df_exch['symbol'],
            y=df_exch['pnl'],
            mode='lines+markers',
            name=f"{exch} PnL",
            line=dict(color=pnl_colors.get(str(exch).lower(), "#64748b"), width=2),
            marker=dict(size=7),
        ))
    pnl_fig.update_layout(title="各账号未实现盈亏", yaxis_title="PnL", height=300,
                          margin=dict(l=20, r=20, t=50, b=80),
                          paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
                          font=dict(color="#18212f"))
    return fig, pnl_fig


def grouped_units_view(strategy_data, accounts_data):
    accounts = accounts_data.get("accounts", {})
    for unit in strategy_data.get("units", []):
        with st.expander(f"{tr('策略单元')}：{unit.get('name')}", expanded=True):
            render_table(paired_account_rows(unit, accounts))

            render_section("跟随开关", "快速调整每对子账号的启用状态和跟随比例。")
            source = unit.get("source", {})
            hedge = unit.get("hedge", {})
            source_followers = source.get("followers", [])
            hedge_followers = hedge.get("followers", [])
            total = max(len(source_followers), len(hedge_followers))

            if total == 0:
                st.info(tr("当前策略单元还没有子账号配对"))

            for idx in range(total):
                source_member = source_followers[idx] if idx < len(source_followers) else None
                hedge_member = hedge_followers[idx] if idx < len(hedge_followers) else None
                gate_label = source_member.get("account") if source_member else tr("未配置 Gate 子账号")
                websea_label = hedge_member.get("account") if hedge_member else tr("未配置 Websea 子账号")
                st.markdown(f"#### {gate_label} & {websea_label}")
                col1, col2 = st.columns(2)
                with col1:
                    if source_member:
                        enabled = st.checkbox(
                            tr("Gate 跟随"),
                            value=bool(source_member.get("enabled", False)),
                            key=f"{unit.get('name')}_source_{source_member.get('account')}_enabled",
                        )
                        ratio = st.text_input(
                            tr("Gate 比例"),
                            value=str(source_member.get("ratio", "1")),
                            key=f"{unit.get('name')}_source_{source_member.get('account')}_ratio",
                        )
                        if st.button(tr("保存 Gate"), key=f"{unit.get('name')}_source_{source_member.get('account')}_save"):
                            update_follower_config(
                                unit_name=unit.get("name"),
                                leg_name="source",
                                account_name=source_member.get("account"),
                                enabled=enabled,
                                ratio=ratio,
                            )
                            st.success(tr("已保存 Gate 跟随配置"))
                            st.rerun()
                    else:
                        st.info(tr("这一组没有 Gate 子账号"))
                with col2:
                    if hedge_member:
                        enabled = st.checkbox(
                            tr("Websea 跟随"),
                            value=bool(hedge_member.get("enabled", False)),
                            key=f"{unit.get('name')}_hedge_{hedge_member.get('account')}_enabled",
                        )
                        ratio = st.text_input(
                            tr("Websea 比例"),
                            value=str(hedge_member.get("ratio", "1")),
                            key=f"{unit.get('name')}_hedge_{hedge_member.get('account')}_ratio",
                        )
                        if st.button(tr("保存 Websea"), key=f"{unit.get('name')}_hedge_{hedge_member.get('account')}_save"):
                            update_follower_config(
                                unit_name=unit.get("name"),
                                leg_name="hedge",
                                account_name=hedge_member.get("account"),
                                enabled=enabled,
                                ratio=ratio,
                            )
                            st.success(tr("已保存 Websea 跟随配置"))
                            st.rerun()
                    else:
                        st.info(tr("这一组没有 Websea 子账号"))
            render_section("交易对")
            render_table(unit.get("symbols", []))


def help_page():
    render_section("使用说明", "说明内容保存在 config/usage_guide.md，可在页面中直接编辑并保存。")
    guide_text = load_text(USAGE_GUIDE_PATH, DEFAULT_USAGE_GUIDE)
    tab_preview, tab_edit = st.tabs([tr("阅读"), tr("编辑")])

    with tab_preview:
        st.markdown(guide_text)

    with tab_edit:
        edited_text = st.text_area(
            tr("使用说明 Markdown"),
            value=guide_text,
            height=680,
            key="usage_guide_editor",
        )
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button(tr("保存使用说明"), type="primary"):
                save_text(USAGE_GUIDE_PATH, edited_text)
                st.success(tr("使用说明已保存"))
                st.rerun()
        with col2:
            if st.button(tr("恢复默认说明")):
                save_text(USAGE_GUIDE_PATH, DEFAULT_USAGE_GUIDE)
                st.success(tr("已恢复默认使用说明"))
                st.rerun()


def main():
    st.set_page_config(page_title="Multi Account Hedger", layout="wide", initial_sidebar_state="expanded")
    inject_theme()
    ensure_files()
    accounts_data = load_json(ACCOUNTS_PATH)
    strategy_data = load_json(STRATEGY_PATH)
    global_data = load_json(GLOBAL_PATH)

    with st.sidebar:
        st.title("Multi Account Hedger")
        selected_language = st.selectbox(
            "Language / 语言",
            list(LANGUAGE_OPTIONS.keys()),
            index=list(LANGUAGE_OPTIONS.values()).index(current_language()) if current_language() in LANGUAGE_OPTIONS.values() else 0,
            key="language_selector",
        )
        st.session_state["language"] = LANGUAGE_OPTIONS[selected_language]
        st.caption(tr("Gate + Websea 仓位跟随控制台"))
        page = st.radio(tr("选择页面"), PAGES, format_func=page_label)
        st.divider()
        st.caption(tr("当前状态"))
        side_risk = risk_summary(accounts_data, strategy_data, global_data)
        st.markdown(
            " ".join([
                status_pill(tr("模拟下单") if side_risk["dry_run"] else tr("真实下单"), "ok" if side_risk["dry_run"] else "danger"),
                status_pill(f"{tr('最高风险')}：{tr(side_risk['level'])}", side_risk["class"]),
            ]),
            unsafe_allow_html=True,
        )
        st.caption(f"{tr('启用账号')}：{sum(1 for cfg in accounts_data.get('accounts', {}).values() if cfg.get('enabled', True))}")
        st.caption(f"{tr('策略单元')}：{sum(1 for unit in strategy_data.get('units', []) if unit.get('enabled', True))}")

    render_app_header(page, accounts_data, strategy_data, global_data)

    if page == "分组总览":
        render_metric_band(dashboard_metrics(accounts_data, strategy_data, global_data))
        render_section("运行自检", "后端同步引擎必须单独运行。这里显示启用策略涉及的账号密钥状态和日志更新时间。")
        checks = pd.DataFrame(preflight_rows(accounts_data, strategy_data))
        if not checks.empty and (checks["状态"] == "ERROR").any():
            st.error(tr("当前配置存在会阻断同步的问题：有启用账号缺少密钥、被禁用或不存在。"))
        elif not checks.empty:
            st.success(tr("启用策略账号的基础配置检查通过。"))
        if checks.empty:
            st.info(tr("未检测"))
        else:
            render_table(checks)
        render_section("运行健康")
        render_table(log_health_row(global_data))

        render_section("账号配对", "按 Gate 与 Websea 的 master/sub 关系横向对齐展示。")
        grouped_units_view(strategy_data, accounts_data)
        render_section("实时账户信息", "按账号读取交易所余额和持仓。缺密钥或接口权限错误会直接显示在表格中。")
        if st.button(tr("刷新实时账户信息")):
            runtime_rows = []
            position_rows = []
            amount_index = build_contract_amount_index(strategy_data)
            accounts = accounts_data.get("accounts", {})
            if accounts:
                progress = st.progress(0)
                for idx, (account_name, acc_cfg) in enumerate(accounts.items()):
                    if not acc_cfg.get("enabled", True):
                        runtime_rows.append({"account": account_name, "exchange": acc_cfg.get("exchange"),
                                             "balance": "DISABLED", "available": "", "unrealized_pnl": ""})
                        continue
                    try:
                        result = asyncio.run(fetch_account_runtime(account_name, acc_cfg, global_data))
                        bal = result.get("balance") or {}
                        runtime_rows.append({
                            "account": account_name, "exchange": result["exchange"],
                            "balance": str(bal.get("balance", "0")),
                            "available": str(bal.get("available", "0")),
                            "unrealized_pnl": str(bal.get("unrealized_pnl", "0"))
                        })
                        for pos in result.get("positions", []):
                            row = {"account": account_name, "exchange": result["exchange"], **pos}
                            position_rows.append(enrich_position_row(row, amount_index))
                    except Exception as e:
                        runtime_rows.append({"account": account_name, "exchange": acc_cfg.get("exchange"),
                                             "balance": "ERROR", "available": "", "unrealized_pnl": str(e)})
                    progress.progress((idx + 1) / max(len(accounts), 1))
            render_section("实时余额")
            render_table(runtime_rows)
            render_section("实时持仓")
            if position_rows:
                position_df = pd.DataFrame(position_rows)
                preferred_cols = [
                    "account", "exchange", "symbol", "side",
                    "raw_size", "actual_amount", "amount_unit",
                    "entry_price", "liq_price", "pnl",
                ]
                visible_cols = [col for col in preferred_cols if col in position_df.columns]
                display_df = position_df[visible_cols].rename(columns={
                    "account": "账号",
                    "exchange": "交易所",
                    "symbol": "合约",
                    "side": "方向",
                    "raw_size": "持仓size",
                    "actual_amount": "实际数量",
                    "amount_unit": "币种",
                    "entry_price": "开仓均价",
                    "liq_price": "强平价",
                    "pnl": "未实现盈亏",
                })
                render_table(display_df)
                charts = build_position_charts(position_rows)
                if charts:
                    pos_fig, pnl_fig = charts
                    st.plotly_chart(pos_fig, use_container_width=True)
                    st.plotly_chart(pnl_fig, use_container_width=True)
            else:
                st.info(tr("当前无持仓"))

    if page == "账号管理":
        render_metric_band(dashboard_metrics(accounts_data, strategy_data, global_data))
        accounts = accounts_data.get("accounts", {})
        render_section("账号列表", "密钥默认脱敏展示；替换密钥时在账号详情中输入新值。")
        render_table(account_display_rows(accounts_data))

        if not accounts:
            st.info(tr("还没有账号"))

        for name, cfg in accounts.items():
            with st.expander(f"{name} ({cfg.get('exchange')})", expanded=False):
                st.caption(tr("密钥字段留空表示保留原值"))
                enabled = st.checkbox(tr("启用账号"), value=cfg.get("enabled", True), key=f"enable_{name}")
                base_url = st.text_input("REST Base URL", value=cfg.get("base_url", ""), key=f"base_url_{name}")
                user_id = ""
                ws_url = ""
                if cfg.get("exchange") == "gate":
                    user_id = st.text_input("Gate User ID", value=cfg.get("user_id", ""), key=f"user_id_{name}")
                    ws_url = st.text_input("Gate WS URL", value=cfg.get("ws_url", ""), key=f"ws_url_{name}")
                api_key = st.text_input("新 API Key / Token", value="", key=f"api_key_{name}", type="password")
                api_secret = st.text_input("新 API Secret", value="", key=f"api_secret_{name}", type="password")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(tr("保存账号"), key=f"save_{name}"):
                        save_account_edits(name, cfg, enabled, base_url, ws_url, user_id, api_key, api_secret)
                        save_json(ACCOUNTS_PATH, accounts_data)
                        st.success(tr("已保存"))
                        st.rerun()
                with col2:
                    confirm_delete = st.checkbox(tr("确认删除"), key=f"delete_confirm_{name}")
                    if confirm_delete:
                        render_danger_panel("危险操作区", "该区域会修改敏感配置，请确认后再保存。")
                    if st.button(tr("删除账号"), key=f"delete_{name}", disabled=not confirm_delete):
                        accounts.pop(name, None)
                        remove_account_references(strategy_data, name)
                        save_json(ACCOUNTS_PATH, accounts_data)
                        save_json(STRATEGY_PATH, strategy_data)
                        st.success(tr("已删除账号并清理策略引用"))
                        st.rerun()

    if page == "新增账号":
        render_section("新增账号", "新账号会写入 accounts.json，并按选择挂载到指定策略单元。")
        st.info(tr("密钥默认脱敏展示；替换密钥时在账号详情中输入新值。"))
        with st.form("add_account_form"):
            account_name = st.text_input(tr("账号名称"))
            exchange = st.selectbox(tr("交易所"), ["gate", "websea"])
            role = st.selectbox(tr("角色"), ["master", "sub"])
            api_key = st.text_input("API Key / Token", type="password")
            api_secret = st.text_input("API Secret", type="password")
            user_id = st.text_input("Gate User ID")
            unit_name = st.text_input(tr("策略单元名称"), "unit_1")
            side = st.selectbox(tr("主/跟随"), ["source", "hedge"])
            ratio = st.text_input(tr("比例"), "1")
            submitted = st.form_submit_button(tr("新增账号"))
            if submitted:
                try:
                    if not account_name.strip():
                        raise ValueError(tr("账号名称不能为空"))
                    validate_decimal_text(ratio, tr("比例"))
                    add_account(
                        account_name.strip(),
                        exchange,
                        api_key.strip(),
                        api_secret.strip(),
                        user_id=user_id.strip(),
                        role=role,
                        unit_name=unit_name.strip() or "unit_1",
                        side=side,
                        ratio=ratio,
                    )
                    st.success(tr("新增成功"))
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    if page == "策略配置":
        render_section("策略单元配置", "策略单元定义 Gate source 与 Websea hedge 的主从关系。")
        gate_accounts = account_names(accounts_data, "gate")
        websea_accounts = account_names(accounts_data, "websea")

        with st.form("new_unit_form"):
            render_section("新增策略单元")
            new_unit_name = st.text_input(tr("策略单元名称"), key="new_unit_name")
            create_unit = st.form_submit_button(tr("新增策略单元"))
            if create_unit:
                if not new_unit_name.strip():
                    st.error(tr("策略单元名称不能为空"))
                    st.stop()
                if any(u.get("name") == new_unit_name.strip() for u in strategy_data.get("units", [])):
                    st.error(tr("策略单元名称已存在"))
                    st.stop()
                strategy_data.setdefault("units", []).append(default_unit(new_unit_name.strip()))
                save_json(STRATEGY_PATH, strategy_data)
                st.success(tr("已新增策略单元"))
                st.rerun()

        for unit in strategy_data.get("units", []):
            with st.expander(unit.get("name"), expanded=True):
                source = unit.setdefault("source", {})
                hedge = unit.setdefault("hedge", {})

                enabled = st.checkbox(tr("启用策略单元"), value=bool(unit.get("enabled", True)), key=f"{unit.get('name')}_enabled")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### Source / Gate")
                    source_accounts = gate_accounts or [source.get("account", "")]
                    source_account = st.selectbox(
                        tr("Source 主账号"),
                        source_accounts,
                        index=select_index(source_accounts, source.get("account")),
                        key=f"{unit.get('name')}_source_account",
                    )
                    source_leverage = st.number_input(
                        tr("Source 杠杆"),
                        min_value=1,
                        max_value=200,
                        value=int(source.get("leverage") or 10),
                        key=f"{unit.get('name')}_source_leverage",
                    )
                    source_margin_mode = st.selectbox(
                        tr("Source 保证金模式"),
                        ["cross", "isolated"],
                        index=select_index(["cross", "isolated"], source.get("margin_mode", "cross")),
                        key=f"{unit.get('name')}_source_margin",
                    )
                    source_settle = st.text_input("Source settle", value=source.get("settle", "usdt"), key=f"{unit.get('name')}_source_settle")
                with col2:
                    st.markdown("#### Hedge / Websea")
                    hedge_accounts = websea_accounts or [hedge.get("account", "")]
                    hedge_account = st.selectbox(
                        tr("Hedge 主账号"),
                        hedge_accounts,
                        index=select_index(hedge_accounts, hedge.get("account")),
                        key=f"{unit.get('name')}_hedge_account",
                    )
                    hedge_mode = st.selectbox(
                        tr("Hedge 模式"),
                        ["opposite", "same"],
                        index=select_index(["opposite", "same"], hedge.get("mode", "opposite")),
                        key=f"{unit.get('name')}_hedge_mode",
                    )
                    hedge_ratio = st.text_input(tr("Hedge 比例"), value=str(hedge.get("ratio", "1")), key=f"{unit.get('name')}_hedge_ratio")
                    hedge_leverage = st.number_input(
                        tr("Hedge 杠杆"),
                        min_value=1,
                        max_value=200,
                        value=int(hedge.get("leverage") or 10),
                        key=f"{unit.get('name')}_hedge_leverage",
                    )
                    hedge_margin_mode = st.selectbox(
                        tr("Hedge 保证金模式"),
                        ["cross", "isolated"],
                        index=select_index(["cross", "isolated"], hedge.get("margin_mode", "cross")),
                        key=f"{unit.get('name')}_hedge_margin",
                    )

                follower_rows = []
                for leg_name in ("source", "hedge"):
                    for item in unit.get(leg_name, {}).get("followers", []):
                        follower_rows.append({
                            "leg": leg_name,
                            "account": item.get("account", ""),
                            "enabled": bool(item.get("enabled", False)),
                            "ratio": str(item.get("ratio", "1")),
                        })
                edited_followers = st.data_editor(
                    pd.DataFrame(follower_rows),
                    num_rows="dynamic",
                    width="stretch",
                    key=f"{unit.get('name')}_followers",
                )

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(tr("保存策略单元"), key=f"{unit.get('name')}_save_unit"):
                        try:
                            validate_decimal_text(hedge_ratio, tr("Hedge 比例"))
                            unit["enabled"] = bool(enabled)
                            source.update({
                                "account": source_account,
                                "exchange": "gate",
                                "settle": source_settle.strip() or "usdt",
                                "leverage": int(source_leverage),
                                "margin_mode": source_margin_mode,
                            })
                            hedge.update({
                                "account": hedge_account,
                                "exchange": "websea",
                                "mode": hedge_mode,
                                "ratio": str(hedge_ratio),
                                "leverage": int(hedge_leverage),
                                "margin_mode": hedge_margin_mode,
                            })

                            source["followers"] = []
                            hedge["followers"] = []
                            for row in edited_followers.to_dict("records"):
                                leg_name = str(row.get("leg", "")).strip()
                                account = str(row.get("account", "")).strip()
                                if not leg_name or not account:
                                    continue
                                if leg_name not in {"source", "hedge"}:
                                    raise ValueError("followers 的 leg 只能是 source 或 hedge")
                                ratio_value = str(row.get("ratio", "1"))
                                validate_decimal_text(ratio_value, "follower ratio")
                                unit[leg_name].setdefault("followers", []).append({
                                    "account": account,
                                    "ratio": ratio_value,
                                    "enabled": bool(row.get("enabled", False)),
                                })

                            save_json(STRATEGY_PATH, strategy_data)
                            st.success(tr("策略单元已保存"))
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))
                with col2:
                    confirm_delete = st.checkbox(tr("确认删除策略单元"), key=f"{unit.get('name')}_delete_confirm")
                    if confirm_delete:
                        render_danger_panel("危险操作区", "该区域会修改敏感配置，请确认后再保存。")
                    if st.button(tr("删除策略单元"), key=f"{unit.get('name')}_delete_unit", disabled=not confirm_delete):
                        strategy_data["units"] = [u for u in strategy_data.get("units", []) if u.get("name") != unit.get("name")]
                        save_json(STRATEGY_PATH, strategy_data)
                        st.success(tr("已删除策略单元"))
                        st.rerun()

    if page == "交易对配置":
        render_section("交易对配置", "交易对规则决定 Gate 仓位如何换算成 Websea 目标仓位。")
        units = strategy_data.get("units", [])
        if not units:
            st.info(tr("还没有策略单元"))
        else:
            unit_names = [u.get("name") for u in units]
            selected_unit_name = st.selectbox(tr("策略单元"), unit_names)
            unit = next(u for u in units if u.get("name") == selected_unit_name)
            symbols = unit.setdefault("symbols", [])

            render_section("自动新增交易对", "只填写 Gate source_symbol，系统会自动推导 Websea 交易对并补齐 ratio、合约面值和基础风控参数。")
            source_settle = unit.get("source", {}).get("settle", "usdt")
            col1, col2 = st.columns([2, 1])
            with col1:
                new_source_symbol = st.text_input(
                    "Source Symbol",
                    value="",
                    placeholder=tr("例如 BTC_USDT"),
                    key=f"{selected_unit_name}_auto_source_symbol",
                )
            with col2:
                st.text_input("Gate settle", value=source_settle, disabled=True, key=f"{selected_unit_name}_auto_settle")

            if st.button(tr("自动获取并新增"), type="primary"):
                try:
                    auto_result = auto_symbol_config(new_source_symbol, source_settle)
                    new_item = auto_result["config"]
                    symbols = [
                        item for item in symbols
                        if item.get("source_symbol") != new_item["source_symbol"]
                    ]
                    symbols.append(new_item)
                    unit["symbols"] = symbols
                    save_json(STRATEGY_PATH, strategy_data)
                    for warning in auto_result["warnings"]:
                        st.warning(warning)
                    st.success(
                        f"{tr('新增成功')} {new_item['source_symbol']} -> {new_item['hedge_symbol']}，"
                        f"ratio={new_item['ratio']}"
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

            render_section("当前交易对")
            if symbols:
                summary_cols = [
                    "source_symbol", "hedge_symbol", "enabled", "ratio",
                    "source_amount_multiplier", "hedge_amount_multiplier",
                    "min_sync_delta",
                ]
                summary_df = pd.DataFrame(symbols)
                visible_summary_cols = [col for col in summary_cols if col in summary_df.columns]
                render_table(
                    summary_df[visible_summary_cols].rename(columns={
                        "source_symbol": "Gate合约",
                        "hedge_symbol": "Websea合约",
                        "enabled": "启用",
                        "ratio": "同步比例",
                        "source_amount_multiplier": "Gate面值",
                        "hedge_amount_multiplier": "Websea面值",
                        "min_sync_delta": "最小同步差",
                    })
                )
            else:
                st.info(tr("当前策略单元还没有交易对"))

            with st.expander(tr("高级参数编辑"), expanded=False):
                st.caption(tr("维护交易对映射、数量换算比例、步进和风控阈值。"))
                edited_symbols = st.data_editor(
                    pd.DataFrame(symbols),
                    num_rows="dynamic",
                    width="stretch",
                    key=f"{selected_unit_name}_symbols_editor",
                )

                if st.button(tr("保存交易对配置")):
                    try:
                        unit["symbols"] = normalize_symbol_rows(edited_symbols.to_dict("records"))
                        save_json(STRATEGY_PATH, strategy_data)
                        st.success(tr("交易对配置已保存"))
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

    if page == "原始配置":
        render_section("运行配置", "常用运行参数可以在这里直接保存；更完整配置可在下方 JSON 编辑区修改。")
        if not bool(global_data.get("dry_run", True)):
            render_danger_panel("真实下单", "真实下单模式已开启。当前页面不会执行下单，但保存配置可能影响后端同步引擎。")
        dry_run = st.checkbox("dry_run", value=bool(global_data.get("dry_run", True)))
        max_concurrent = st.number_input(
            "max_concurrent_adjustments",
            min_value=1,
            max_value=200,
            value=int(global_data.get("max_concurrent_adjustments", 20)),
        )
        state_file = st.text_input("state_file", value=global_data.get("state_file", "logs/state.json"))
        alert_cooldown = st.number_input(
            "alert_cooldown_sec",
            min_value=1,
            max_value=3600,
            value=int(global_data.get("alert_cooldown_sec", 60)),
        )
        if st.button(tr("保存运行配置")):
            global_data["dry_run"] = bool(dry_run)
            global_data["max_concurrent_adjustments"] = int(max_concurrent)
            global_data["state_file"] = state_file.strip() or "logs/state.json"
            global_data["alert_cooldown_sec"] = int(alert_cooldown)
            save_json(GLOBAL_PATH, global_data)
            st.success(tr("运行配置已保存"))
            st.rerun()

        render_section("状态文件")
        state_path = Path(global_data.get("state_file", "logs/state.json"))
        if state_path.exists():
            st.json(load_json(state_path))
        else:
            st.info(tr("状态文件还不存在"))

        render_section("JSON 编辑", "保存 accounts.json 前需要确认显示完整内容，避免误改密钥。")
        render_danger_panel("危险操作区", "该区域会修改敏感配置，请确认后再保存。")
        tab_global, tab_strategy, tab_accounts = st.tabs(["global_config.json", "strategy_config.json", "accounts.json"])
        with tab_global:
            global_text = st.text_area(
                "global_config.json",
                value=json.dumps(global_data, ensure_ascii=False, indent=2),
                height=320,
                key="global_raw",
            )
            if st.button(tr("保存 global_config.json")):
                try:
                    save_json(GLOBAL_PATH, json.loads(global_text))
                    st.success(tr("已保存 global_config.json"))
                    st.rerun()
                except Exception as exc:
                    st.error(f"JSON 格式错误: {exc}")
        with tab_strategy:
            strategy_text = st.text_area(
                "strategy_config.json",
                value=json.dumps(strategy_data, ensure_ascii=False, indent=2),
                height=420,
                key="strategy_raw",
            )
            if st.button(tr("保存 strategy_config.json")):
                try:
                    save_json(STRATEGY_PATH, json.loads(strategy_text))
                    st.success(tr("已保存 strategy_config.json"))
                    st.rerun()
                except Exception as exc:
                    st.error(f"JSON 格式错误: {exc}")
        with tab_accounts:
            show_secret = st.checkbox(tr("显示并编辑完整 accounts.json"))
            if show_secret:
                accounts_text = st.text_area(
                    "accounts.json",
                    value=json.dumps(accounts_data, ensure_ascii=False, indent=2),
                    height=420,
                    key="accounts_raw",
                )
                confirm_save_accounts = st.checkbox(tr("确认保存 accounts.json"))
                if st.button(tr("保存 accounts.json"), disabled=not confirm_save_accounts):
                    try:
                        save_json(ACCOUNTS_PATH, json.loads(accounts_text))
                        st.success(tr("已保存 accounts.json"))
                        st.rerun()
                    except Exception as exc:
                        st.error(f"JSON 格式错误: {exc}")
            else:
                st.json(masked_accounts_data(accounts_data))

    if page == "使用说明":
        help_page()


if __name__ == "__main__":
    main()
