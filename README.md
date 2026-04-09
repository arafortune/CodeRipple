# CodeRipple

Git历史分析工具 - 追溯bug是否影响目标版本

## 功能

- 检查目标版本是否仍受某个修复提交对应的Bug影响
- 显式输出结果状态：`affected`、`not_affected`、`unknown`
- 支持文件移动、功能重构
- 多种追溯策略：commit链、代码块、AST结构、相似度搜索
- 支持批量分析多个目标版本
- 支持 `find-fix` 独立搜索候选修复提交
- 支持 `doctor` 预先诊断 fix、target、config 是否可解析
- 支持按修复提交、提交信息、分支、tag、commit sha 进行分析
- 支持输出结构化分析过程

## 安装

```bash
uv sync
```

## 使用

### 基本用法

```bash
# 1. 推荐的显式参数形式
uv run coderipple affected --fix <fix_commit> --target <branch_or_tag_or_commit>

# 2. 先查找候选修复提交
uv run coderipple find-fix --message "<message>"
uv run coderipple find-fix --message "<message>" --path src/foo.py --since-days 30

# 3. 按提交信息搜索修复commit
uv run coderipple affected --fix-message "<message>" --target <branch_or_tag_or_commit>

# 4. 列出提交信息命中的候选修复提交
uv run coderipple affected --fix-message "<message>" --list-fix-candidates --target <branch_or_tag_or_commit>

# 5. 先诊断fix、target和配置是否都可解析
uv run coderipple doctor --fix <fix_commit> --target <branch_or_tag_or_commit>

# 6. 批量分析多个目标版本
uv run coderipple affected --fix <fix_commit> --target <ref1> --target <ref2>
uv run coderipple affected --fix <fix_commit> --targets-file targets.txt
```

### 子命令

`affected`
用于判断目标版本是否仍受影响。JSON 输出会包含顶层 `status`，`--explain` 时还会附带 `analysis`。

`find-fix`
用于先独立搜索候选修复提交。可用 `--target`、`--path`、`--since-days` 缩小范围。

`doctor`
用于在真正执行 `affected` 前，先诊断仓库、配置、fix 和多个 targets 是否都能被正确解析。

### 示例

```bash
# 检查修复提交 abc123 对应的Bug是否仍影响 v1.0.0
uv run coderipple affected --fix abc123 --target v1.0.0

# 先查找候选修复提交
uv run coderipple find-fix --message "divide by zero" --target release/v1.0
uv run coderipple find-fix --message "divide by zero" --path bug.py --since-days 30

# 按提交信息搜索修复commit
uv run coderipple affected --fix-message "divide by zero" --target release/v1.0

# 当fix-message命中多个候选时，先列候选，再按序号选择
uv run coderipple affected --fix-message "divide by zero" --list-fix-candidates --target release/v1.0
uv run coderipple affected --fix-message "divide by zero" --fix-index 2 --target release/v1.0

# 先批量诊断多个目标版本和配置
uv run coderipple doctor --fix abc123 --target release/v1.0 --target v1.0.1 --config config/coderipple.yaml

# 批量分析多个目标版本
uv run coderipple affected --fix abc123 --target release/v1.0 --target v1.0.1

# 从文件批量读取目标版本
uv run coderipple affected --fix abc123 --targets-file targets.txt

# 输出JSON格式并附带结构化分析过程
uv run coderipple affected --fix abc123 --target v1.0.0 --output json --explain
```

### 参数说明

#### affected

```bash
--fix           显式指定修复commit
--fix-message   按提交信息搜索修复commit
--fix-index     当 --fix-message 命中多个候选时，选择第几个候选
--list-fix-candidates  仅列出 --fix-message 命中的候选提交
--target        指定目标分支、tag或commit，可重复传入
--targets-file  从文件读取多个目标版本，每行一个ref
--repo          指定目标仓库路径
--output        table 或 json
--explain       输出结构化分析过程
```

#### find-fix

```bash
--message       按提交信息搜索候选修复提交
--target        可选目标版本，用于排序时降低已在目标中可达的候选优先级
--path          仅返回直接修改过该路径的提交
--since-days    仅返回最近 N 天内的提交
--limit         控制最多返回多少个候选
--repo          指定目标仓库路径
--output        table 或 json
```

#### doctor

```bash
--fix / --fix-message / --fix-index
--target / --targets-file
--repo
--config
--output
```

### 输出状态

`affected`
目标版本仍受影响，已经找到直接证据。

`not_affected`
目标版本已包含修复或等价修复。

`unknown`
当前策略既没有确认受影响，也没有确认已修复。

## 开发

```bash
# 同步依赖并安装开发依赖
uv sync --extra dev

# 运行测试
uv run pytest

# 查看覆盖率
uv run pytest --cov=src --cov-report=html
```

## License

MIT
