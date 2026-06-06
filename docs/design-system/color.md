# Color

## Design Token

颜色必须以 Token 思维使用，不直接在页面中随意新增颜色。

## Brand Tokens

| Token | Value | 用途 |
| --- | --- | --- |
| `color.primary` | `#14B8A6` | 主按钮、当前导航、关键信息 |
| `color.primary.hover` | `#0D9488` | 主操作 hover |
| `color.primary.bg` | `#ECFDF8` | 信息底色、选中底色 |
| `color.primary.text` | `#0F766E` | 信息文字 |

## Status Tokens

| Token | Value | 用途 |
| --- | --- | --- |
| `color.success` | `#059669` | 正常、通过、完成 |
| `color.success.bg` | `#ECFDF5` | 正常浅底 |
| `color.warning` | `#D97706` | 预警、需关注 |
| `color.warning.bg` | `#FFF7ED` | 预警浅底 |
| `color.danger` | `#E11D48` | 失败、阻断、删除、真实下单 |
| `color.danger.bg` | `#FFF1F2` | 危险浅底 |
| `color.info` | `#2563EB` | 辅助信息 |
| `color.info.bg` | `#EFF6FF` | 信息浅底 |

## Neutral Tokens

| Token | Value | 用途 |
| --- | --- | --- |
| `color.text` | `#111827` | 主文本 |
| `color.text.secondary` | `#6B7280` | 次级文本 |
| `color.text.tertiary` | `#9CA3AF` | 弱提示 |
| `color.border` | `#EEF2F7` | 普通边框 |
| `color.border.strong` | `#E5E7EB` | 强边框 |

## Background Tokens

| Token | Value | 用途 |
| --- | --- | --- |
| `color.bg.layout` | `#F8FAFC` | 页面背景 |
| `color.bg.container` | `#FFFFFF` | 卡片、表格、表单容器 |
| `color.bg.subtle` | `#F3F6F8` | hover、弱背景 |
| `color.bg.table.header` | `#F8FAFC` | 表头 |

## Exchange Brand Tokens

交易所品牌色只用于账号卡片、交易所标识、交易所维度的筛选和图例，不表达成功、失败、危险等运行状态。

| Token | Value | 用途 |
| --- | --- | --- |
| `color.exchange.gate` | `#2354E6` | Gate 品牌主色 |
| `color.exchange.gate.bg` | `#F3F6FF` | Gate 品牌浅底 |
| `color.exchange.gate.border` | `#C7D2FE` | Gate 品牌边框 |
| `color.exchange.websea` | `#06C84A` | Websea 品牌主色 |
| `color.exchange.websea.bg` | `#F0FFF5` | Websea 品牌浅底 |
| `color.exchange.websea.border` | `#B9F8D0` | Websea 品牌边框 |

## 使用规则

- 红色只用于真实危险，不用于装饰。
- 绿色只用于已通过、正常、模拟安全状态。
- 黄色只用于可恢复但需要关注的状态。
- 青绿色用于品牌和当前选中，不用来表达危险。
- 同一页面状态色不超过 3 类。
- 交易所品牌色只用于交易所身份识别，不用于状态表达。

## Color 检查项

- 是否所有颜色都能映射到 Token。
- 是否没有用红色做非危险装饰。
- 是否没有新增未定义颜色。
- 是否状态色含义一致。
