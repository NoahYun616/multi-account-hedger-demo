# Multi Account Hedger 使用说明

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
