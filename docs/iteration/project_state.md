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

## 当前重要文件

- `README.md`：工具主说明，后续功能升级后必须同步更新。
- `WEBSEA_PROJECT_NOTES.md`：Websea 项目内部署说明。
- `docs/iteration/合约保险对冲工具优化迭代方案.md`：当前优化升级主方案。
- `docs/iteration/agent.md`：后续 AI / 研发协作者工作约定。
- `docs/iteration/project_state.md`：当前项目状态。
- `docs/iteration/git_workflow.md`：Git 管理方式。
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

第一阶段优先做“安全可用”：

1. 真实下单模式强提醒。
2. 一键配置体检。
3. 仓位价值换算展示。
4. 对冲完整性检测。
5. Websea 资金不足预检查。
6. 对冲断线报警与策略暂停。

第一阶段暂不建议默认自动平仓。自动 reduce-only 紧急平仓应放在 Websea 成交回报、reduce-only、风险状态接口稳定后再做。

## 待确认

- Websea 当前仓位接口能否稳定返回多仓、空仓、净仓位、开仓均价、标记价格、强平价格、杠杆、保证金模式、风险率。
- Websea 是否已有可用余额、已占用保证金、冻结保证金、预计开仓所需保证金接口。
- Websea 是否支持 reduce-only 平仓。
- Websea 是否能返回明确订单成交状态和部分成交信息。
- Websea 是否能提供当前账号保险节点状态接口。
