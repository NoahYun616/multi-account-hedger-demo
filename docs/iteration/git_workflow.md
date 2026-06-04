# Git 管理方式

本工具从 2026-06-04 开始使用独立 Git 仓库管理，仓库根目录为：

`/Users/huafanyun/Workspace/websea/tools/multi_account_hedger`

## 管理原则

- 只管理合约保险对冲工具本身，不把整个 Websea 知识库根目录纳入该仓库。
- 每次功能迭代、配置结构变化、风控逻辑变化、接口依赖变化，都应形成一次清晰提交。
- 真实账号配置、API 密钥、本地虚拟环境、日志和运行状态不进入 Git。
- 工具能力变化后必须同步更新根目录 `README.md` 和 `docs/iteration/project_state.md`。

## 忽略范围

当前 `.gitignore` 已忽略：

- `venv/`
- `__pycache__/`
- `*.py[cod]`
- `.DS_Store`
- `logs/*.log`
- `logs/*.json`
- `config/accounts.json`

其中 `config/accounts.json` 是本地敏感配置文件，只能由 `config/accounts.json.example` 复制生成，并由使用者自行填写。

## 推荐提交节奏

每个提交尽量只表达一个清晰意图，例如：

- 新增配置体检。
- 新增真实下单模式提醒。
- 新增仓位价值换算展示。
- 调整 Websea 余额预检查。
- 更新 README 和迭代文档。

提交前建议执行：

```bash
venv/bin/python -m compileall -q app.py launcher.py dashboard.py clients core notify tests
venv/bin/python -m unittest discover -s tests
git status --short
```

## 常用命令

查看状态：

```bash
git status --short
```

查看改动：

```bash
git diff
```

提交改动：

```bash
git add <files>
git commit -m "描述本次迭代"
```

查看历史：

```bash
git log --oneline --decorate -n 10
```
