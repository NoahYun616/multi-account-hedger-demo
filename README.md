# Gate + Websea 多账号对冲仓位跟随系统

这是一个按**仓位**同步、不是按**订单**同步的多账号对冲跟单项目：

- Gate 主账号作为 source；
- Gate 子账号跟随 Gate 主账号；
- Websea 主账号作为 hedge，可同向或反向镜像 Gate 主账号；
- Websea 子账号跟随 Websea 主账号；
- 支持多策略单元、多交易对、配置热加载；
- Gate 主账号通过 **Gate Futures WebSocket** 订阅持仓变化；
- Gate / Websea 执行侧通过 REST 下单与 REST 查询持仓。
- 支持同步状态落盘、并发调仓上限、Telegram 异常告警。

## Websea 项目迭代文档

本工具已纳入 Websea 合约保险对冲工具迭代项目。后续优化升级相关文档统一存放在：

```text
docs/iteration/
```

当前关键文档：

- `docs/iteration/合约保险对冲工具优化迭代方案.md`
- `docs/iteration/agent.md`
- `docs/iteration/project_state.md`
- `docs/iteration/git_workflow.md`
- `WEBSEA_PROJECT_NOTES.md`

每次对工具进行功能优化、配置变更、启动方式变更、风控逻辑变更或接口依赖变更后，都需要同步更新本 README。

本工具目录已使用独立 Git 仓库管理。真实账号配置 `config/accounts.json`、虚拟环境、日志和运行状态文件不进入版本管理。

## 目录

```text
 gate_websea_hedger/
 ├─ app.py
 ├─ launcher.py
 ├─ Dockerfile
 ├─ requirements.txt
 ├─ README.md
 ├─ WEBSEA_PROJECT_NOTES.md
 ├─ docs/
 │  └─ iteration/
 │     ├─ README.md
 │     ├─ 合约保险对冲工具优化迭代方案.md
 │     ├─ agent.md
 │     ├─ project_state.md
 │     └─ git_workflow.md
 ├─ clients/
 │  ├─ base.py
 │  ├─ gate_rest.py
 │  ├─ gate_ws.py
 │  └─ websea_rest.py
 ├─ core/
 │  ├─ config_loader.py
 │  ├─ engine.py
 │  ├─ models.py
 │  ├─ state_store.py
 │  └─ utils.py
 ├─ config/
 │  ├─ global_config.json
 │  ├─ accounts.json
 │  ├─ accounts.json.example
 │  └─ strategy_config.json
 ├─ notify/
 │  └─ telegram_notifier.py
 └─ logs/
```

## 先做这几步

1. 复制 `config/accounts.json.example` 为你自己的 `config/accounts.json`
2. 填入 Gate / Websea 各账户密钥
3. 把 `config/global_config.json` 里的 `dry_run` 先保持为 `true`
4. 启动后先看日志确认：
   - Gate 主账号 WS 能连上
   - 能收到 `futures.positions` 更新
   - 各 follower 只输出 `[DRY_RUN]` 日志，不真实下单
5. 确认没问题，再把 `dry_run` 改为 `false`

## 配置结构

现在配置被压成 3 个文件：

- `global_config.json`：全局运行参数
- `accounts.json`：所有账号和密钥
- `strategy_config.json`：策略单元、主从关系、交易对规则

### strategy_config 的核心概念

每个 unit 只有两条腿：

- `source`
- `hedge`

每条腿下面挂自己的 `followers`，每个交易对只需要写：

- `source_symbol`
- `hedge_symbol`

这样不会再出现一堆 `gate_master / websea_master / gate_symbol / websea_symbol` 来回跳的配置层级。

## 运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python launcher.py
```

运行前建议先做一次静态检查：

```bash
python -m compileall -q app.py launcher.py dashboard.py clients core notify tests
python -m unittest discover -s tests
```

## Docker

```bash
docker build -t gate-websea-hedger .
docker run --rm -it \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  gate-websea-hedger
```

## 热加载

以下文件改动后会自动重载：

- `config/global_config.json`
- `config/accounts.json`
- `config/strategy_config.json`

不需要重启进程。

热加载后，引擎会重建 REST 客户端和 Gate WS 订阅，并重新应用：

- `dry_run`
- `max_concurrent_adjustments`
- `state_file`
- Telegram 告警配置

如果 `dry_run` 为 `false`，启动和热加载时日志会输出真实下单警告。

## 关键说明

### 1. 仓位跟随，不是订单跟随

引擎收到 source 主账号的最新仓位后，会重新计算每个账户的**目标仓位**，再根据“目标 - 当前”的差值决定要不要补单。

### 2. Gate 下单

Gate 执行侧默认使用 **IOC 限价单** 做“接近市价”的调整。

### 3. Websea 下单

Websea 执行侧调用 futures open/close 接口的 market 类型。

### 4. 数量单位

这个系统默认你的 Gate / Websea 两边合约张数具备可比性；如果不一致，请在 `strategy_config.json` 的 `symbols[].ratio` 里调数量换算比例。

### 5. 状态落盘

引擎会把主账号最新仓位和每个 follower 最近一次同步结果写入 `global_config.json` 里的 `state_file`，默认是：

```text
logs/state.json
```

状态文件采用临时文件替换写入，避免进程中断导致 JSON 写坏。

### 6. 告警

`accounts.json` 里的 `telegram` 可用于异常告警：

```json
{
  "telegram": {
    "enabled": true,
    "bot_token": "YOUR_BOT_TOKEN",
    "chat_id": "YOUR_CHAT_ID"
  }
}
```

目前会告警：

- 单批同步失败
- 同步循环异常
- 目标仓位超过 `max_source_pos` / `max_hedge_pos` 被阻断

同类告警会按 `alert_cooldown_sec` 冷却，避免刷屏。

## 常见可调项

`global_config.json`

- `debounce_ms`: 高频去抖
- `max_concurrent_adjustments`: 最大并发同步数
- `dry_run`: 是否真实下单
- `state_file`: 主仓位和最近同步结果保存位置
- `alert_cooldown_sec`: Telegram 同类告警冷却秒数

`strategy_config.json`

- 子账号 `ratio`
- 子账号 `enabled`
- `hedge.mode`: `same` / `opposite`
- `hedge.ratio`
- 每个 symbol 的 step、最小下单量、最大单次调整量
