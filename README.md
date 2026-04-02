# CodeRipple

Git历史分析工具 - 追溯bug是否影响目标版本

## 功能

- 检查目标版本是否尚未包含修复commit，从而判断Bug是否仍受影响
- 支持文件移动、功能重构
- 多种追溯策略：commit链、代码块、AST结构、相似度搜索

## 安装

```bash
uv sync
```

## 使用

### 基本用法

```bash
# 追溯bug是否影响目标版本
uv run coderipple trace <fix_commit> <target_tag_or_branch>
```

### 示例

```bash
# 检查修复提交 abc123 对应的Bug是否仍影响 v1.0.0
uv run coderipple trace abc123 v1.0.0

# 输出JSON格式
uv run coderipple trace abc123 v1.0.0 --output json
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
