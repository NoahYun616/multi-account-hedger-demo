# Websea 项目内部署说明

本目录由 `/Users/huafanyun/Downloads/multi_account_hedger` 拷贝而来，用于后续在 Websea 项目内迭代“合约保险对冲工具”。

## 当前部署策略

为了避免密钥泄露，项目内版本没有复制原始 `config/accounts.json` 的真实账号密钥，而是使用 `config/accounts.json.example` 生成了占位版 `config/accounts.json`。

同时做了两个安全默认值：

- `config/global_config.json` 中 `dry_run` 已设为 `true`，默认只模拟运行。
- 缺少密钥的子账号 follower 已默认禁用，避免启动时因为占位账号阻断测试。

真实运行前，需要在控制台或 `config/accounts.json` 中填写 Gate / Websea API 凭证，并确认 API 不包含提币权限。

## 推荐本地启动方式

使用 Python 3.10 或 3.11。当前项目已用 Python 3.11 建立虚拟环境：

```bash
cd /Users/huafanyun/Workspace/websea/tools/multi_account_hedger
source venv/bin/activate
```

启动前端控制台：

```bash
venv/bin/streamlit run dashboard.py --server.port 8502 --server.headless true
```

浏览器打开：

```text
http://localhost:8502
```

如果同一局域网设备需要访问：

```bash
ipconfig getifaddr en0
venv/bin/streamlit run dashboard.py --server.address 0.0.0.0 --server.port 8502 --server.headless true
```

启动同步引擎：

```bash
source venv/bin/activate
python launcher.py
```

## 真实下单前检查

真实下单前必须确认：

- `config/global_config.json` 中 `dry_run` 是否仍为 `true`。
- Gate / Websea API 只开启查询和交易权限，不能开启提币权限。
- 已用小仓位在 dry run 下验证 Gate source 仓位变化、Websea hedge 目标仓位、交易对 ratio 和合约面值。
- `logs/system.log` 和 `logs/state.json` 中的同步结果符合预期。
- 交易对的 `source_amount_multiplier`、`hedge_amount_multiplier`、`ratio`、`min_sync_delta`、`max_source_pos`、`max_hedge_pos` 和 `max_adjust_qty` 已核对。

## 工具机制简述

该工具按“仓位”同步，不按“订单”复制。

默认逻辑：

- Gate 主账号作为 source，由 WebSocket 监听持仓变化。
- Gate 子账号可同向跟随 Gate 主账号。
- Websea 主账号按 hedge 规则同向或反向调仓。
- Websea 子账号只有在 Websea 主账号同步成功后才跟随。

用于合约保险场景时，常见配置是 Gate 与 Websea 两边形成对冲仓位，让 Websea 侧产生可控亏损或盈利，同时用另一侧仓位对冲行情风险。但该策略是否可持续，取决于手续费、滑点、资金费率、保险规则、节点冻结/失效、风控规则和平台资金池状态，不能只按理论收益估算。

## 后续迭代方向

- 把合约保险节点、保费、空投、冻结、失效等数据接入看板。
- 加入保险收益测算：手续费、滑点、资金费率、保费、节点到账周期、节点失效率。
- 增加策略风控：最大日亏损、最大净敞口、单币种最大敞口、连续失败暂停。
- 对接 Websea 保险账户状态，避免仅根据仓位判断策略收益。
- 增加配置审计，明确区分模拟运行、真实运行、仅看板模式。
