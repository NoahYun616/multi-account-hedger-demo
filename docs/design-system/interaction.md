# Interaction

## Hover

Hover 用于提示可交互。

规则：

- 卡片 hover 只用于可点击卡片。
- 表格行 hover 使用弱背景色。
- 按钮 hover 加深主色或边框色。
- 不对纯展示 KPI 添加强 hover 动效。

## Active

Active 表示当前选中或按下状态。

导航 Active：

- 使用 `color.primary.bg` 背景。
- 使用 `color.primary.text` 文字。
- 左侧可加 3px 选中条，但不要过重。

按钮 Active：

- 主按钮颜色加深。
- 保持文字清晰可读。

## Disabled

Disabled 表示不可操作。

规则：

- 降低透明度或使用弱文本色。
- 必须有原因说明，尤其是跟单、真实下单、保存等关键操作。
- 禁用按钮不得只靠颜色区分。

## Loading

Loading 用于等待数据或提交。

规则：

- 页面初次加载使用 Skeleton。
- 局部刷新使用按钮 loading 或表格 loading。
- 长操作需要展示进度或明确提示。

禁止：

- 没有反馈地等待。
- 用全屏 loading 遮住可继续阅读的内容。

## Focus

Focus 必须可见，满足键盘操作。

规则：

- 表单控件 focus 使用主色边框。
- 按钮 focus 使用外发光或 outline。
- 不移除浏览器默认 focus 后没有替代样式。

## Interaction 检查项

- 可点击元素是否有 hover。
- 当前导航是否明显。
- 禁用状态是否有原因。
- 加载过程是否有反馈。
- 键盘 focus 是否可见。
