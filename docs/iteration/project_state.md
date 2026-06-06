# 项目状态

更新时间：2026-06-04

## 当前阶段

合约保险对冲工具已完成基础部署，准备按照《合约保险对冲工具优化迭代方案》进入迭代升级阶段。

当前重点不是扩展交易策略，而是补齐：

- 对冲完整性检测。
- 资金不足预检查。
- 对冲断线告警与保护。
- 强平风险监控。
- 真实下单模式强提醒。
- 当前 Websea 账号保险节点状态展示。

## 已完成

- 工具已部署到 `tools/multi_account_hedger/`。
- 工具已在 `tools/multi_account_hedger/` 内使用独立 Git 仓库管理。
- 已创建 Python 3.11 虚拟环境 `venv/`。
- 已安装依赖。
- 已将 `config/global_config.json` 的 `dry_run` 设为 `true`。
- 已使用示例配置生成占位版 `config/accounts.json`，没有复制真实账号密钥。
- 已默认禁用缺少密钥的子账号 follower。
- 已通过基础验证：
  - 静态编译通过。
  - 单元测试通过。
  - Streamlit 控制台可启动。
- 已新增迭代文档目录：`docs/iteration/`。
- 已新增 Git 管理说明：`docs/iteration/git_workflow.md`。
- 已新增前端风格草案：`docs/iteration/frontend_style_guide.md`。
- 已按前端风格草案完成一版现有页面视觉与布局改造，未新增业务功能，未修改同步/下单逻辑。
- 已将只读数据表统一为浅色工作台表格；可编辑表格仍保留 Streamlit 原生编辑器，避免改变现有编辑交互。
- 已参考 AI Relay 仪表盘重新调整现有页面风格和信息层级：侧边栏去除重复状态信息，页头减少重复指标，总览页改为四张核心状态卡片 + 系统状态明细。
- 已按本工具内 `docs/design-system/` 完成一版规范化 UI 调整：CSS 变量切换为 Design Token 命名，KPI、表格、空状态、侧栏与页头按长期规范收敛。
- 已调整新增账号流程：新增页只写入 `accounts.json`，不再选择角色、策略单元或比例；Gate 固定为 source，Websea 固定为 hedge，策略关系需在“策略配置”中手动挂载。

## 当前重要文件

- `README.md`：工具主说明，后续功能升级后必须同步更新。
- `WEBSEA_PROJECT_NOTES.md`：Websea 项目内部署说明。
- `docs/iteration/合约保险对冲工具优化迭代方案.md`：当前优化升级主方案。
- `docs/iteration/agent.md`：后续 AI / 研发协作者工作约定。
- `docs/iteration/project_state.md`：当前项目状态。
- `docs/iteration/git_workflow.md`：Git 管理方式。
- `docs/iteration/frontend_style_guide.md`：前端风格草案，待确认后作为后续 UI 标准。
- `config/global_config.json`：全局运行参数。
- `config/accounts.json`：本地账号配置，敏感文件，不应提交真实密钥。
- `config/strategy_config.json`：策略单元、交易对、跟随比例和风控阈值配置。

## 关键产品决策

- 工具不做行情判断。
- 工具不做收益承诺。
- 工具不计算资金费率、持仓时间成本或未来综合收益。
- 工具不展示平台保险池健康度，也不替平台判断保险池承压情况。
- 工具只展示当前 Websea 账号维度的保险节点状态与可用性。
- 自动平仓、自动调杠杆、自动切换真实下单等动作必须谨慎，默认应有明确配置、告警和人工确认边界。

## 下一步建议

当前前端已完成第二版表现层改造。后续如继续做 UI，应优先补齐：

- 配置体检独立页面。
- 对冲监控独立页面。
- 当前 Websea 账号保险节点页面。
- 策略单元状态机与告警列表展示。

第一阶段优先做“安全可用”：

1. 真实下单模式强提醒。
2. 一键配置体检。
3. 仓位价值换算展示。
4. 对冲完整性检测。
5. Websea 资金不足预检查。
6. 对冲断线报警与策略暂停。

第一阶段暂不建议默认自动平仓。自动 reduce-only 紧急平仓应放在 Websea 成交回报、reduce-only、风险状态接口稳定后再做。

前端迭代建议先确认 `frontend_style_guide.md`。确认后，后续新增页面、调整布局、加入配置体检、对冲监控、保险节点状态等功能时，统一按该风格执行。

## 待确认

- Websea 当前仓位接口能否稳定返回多仓、空仓、净仓位、开仓均价、标记价格、强平价格、杠杆、保证金模式、风险率。
- Websea 是否已有可用余额、已占用保证金、冻结保证金、预计开仓所需保证金接口。
- Websea 是否支持 reduce-only 平仓。
- Websea 是否能返回明确订单成交状态和部分成交信息。
- Websea 是否能提供当前账号保险节点状态接口。
