# Agent 工作约定

你正在维护 Websea 合约保险对冲工具，项目目录为：

`/Users/huafanyun/Workspace/websea/tools/multi_account_hedger`

## 角色定位

该工具当前定位为：

> Websea 合约保险账号状态与对冲风险控制台。

当前工具基础能力是 Gate -> Websea 的多账号仓位同步/对冲，不是行情判断工具，也不是收益承诺工具。

## 工作前必须阅读

每次开始迭代前，先阅读：

1. `docs/iteration/project_state.md`
2. `docs/iteration/合约保险对冲工具优化迭代方案.md`
3. 根目录 `README.md`
4. `WEBSEA_PROJECT_NOTES.md`

如果涉及合约保险机制，还应参考：

- `/Users/huafanyun/Workspace/websea/knowledge-base/02-合约保险.md`
- `/Users/huafanyun/Workspace/websea/knowledge-base/00-当前上下文.md`

## 关键原则

- 默认安全优先，`dry_run=true` 是默认基线。
- 不要复制、提交或展示真实 API 密钥。
- 真实 `config/accounts.json` 应视为本地敏感配置。
- 自动保护动作必须谨慎，尤其是自动平仓、自动调杠杆、自动切换真实下单。
- 不做收益承诺，不预测未来综合收益。
- 不展示平台保险池健康度，只展示当前 Websea 账号维度的保险节点状态与可用性。
- 如果产品规则或接口口径不明确，先标记待确认，不要自行补全。

## README 更新规则

只要本次改动影响以下任一内容，就必须同步更新根目录 `README.md`：

- 新增或修改启动方式。
- 新增或修改配置项。
- 新增或修改前端页面/功能。
- 新增或修改风控行为。
- 新增或修改告警行为。
- 新增或修改接口依赖。
- 新增或修改真实下单风险提示。

## 验证要求

每次代码改动后，至少执行：

```bash
venv/bin/python -m compileall -q app.py launcher.py dashboard.py clients core notify tests
venv/bin/python -m unittest discover -s tests
```

如改动前端控制台，需要启动 Streamlit 做一次人工检查：

```bash
venv/bin/streamlit run dashboard.py --server.port 8502 --server.headless true
```

检查完成后关闭本地服务，避免占用端口。
