# CodeRipple

Git历史分析工具 - 追溯bug是否影响目标版本

## 功能

- 检查目标版本是否仍受某个修复提交对应的Bug影响
- 支持文件移动、功能重构
- 多种追溯策略：commit链、代码块、AST结构、相似度搜索
- 支持按修复提交、提交信息、分支、tag、commit sha 进行分析
- 支持输出结构化分析过程

## 安装

```bash
uv sync
```

## 使用

### 基本用法

```bash
# 兼容旧用法：按 fix commit 和目标ref 追溯
uv run coderipple trace <fix_commit> <target_tag_or_branch>

# 更推荐的显式参数形式
uv run coderipple affected --fix <fix_commit> --target <branch_or_tag_or_commit>

# 先查找候选修复提交
uv run coderipple find-fix --message "<message>"

# 按提交信息搜索修复commit
uv run coderipple trace --fix-message "<message>" --target <branch_or_tag_or_commit>

# 列出提交信息命中的候选修复提交
uv run coderipple trace --fix-message "<message>" --list-fix-candidates --target <branch_or_tag_or_commit>

# 批量分析多个目标版本
uv run coderipple affected --fix <fix_commit> --target <ref1> --target <ref2>
uv run coderipple affected --fix <fix_commit> --targets-file targets.txt
```

### 示例

```bash
# 检查修复提交 abc123 对应的Bug是否仍影响 v1.0.0
uv run coderipple affected --fix abc123 --target v1.0.0

# 先查找候选修复提交
uv run coderipple find-fix --message "divide by zero" --target release/v1.0

# 使用旧位置参数形式
uv run coderipple trace abc123 v1.0.0

# 按提交信息搜索修复commit
uv run coderipple trace --fix-message "divide by zero" --target release/v1.0

# 当fix-message命中多个候选时，先列候选，再按序号选择
uv run coderipple trace --fix-message "divide by zero" --list-fix-candidates --target release/v1.0
uv run coderipple trace --fix-message "divide by zero" --fix-index 2 --target release/v1.0

# 批量分析多个目标版本
uv run coderipple affected --fix abc123 --target release/v1.0 --target v1.0.1

# 从文件批量读取目标版本
uv run coderipple affected --fix abc123 --targets-file targets.txt

# 输出JSON格式并附带结构化分析过程
uv run coderipple trace --fix abc123 --target v1.0.0 --output json --explain
```

### 参数说明

```bash
--fix           显式指定修复commit
--fix-message   按提交信息搜索修复commit
--fix-index     当 --fix-message 命中多个候选时，选择第几个候选
--list-fix-candidates  仅列出 --fix-message 命中的候选提交
find-fix        独立搜索候选修复提交
--target        指定目标分支、tag或commit，可重复传入
--targets-file  从文件读取多个目标版本，每行一个ref
--repo          指定目标仓库路径
--output        table 或 json
--explain       输出结构化分析过程
```

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
