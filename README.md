# CodeRipple

Git历史分析工具 - 追溯bug是否影响目标版本

## 功能

- 检查修复commit是否在目标版本中
- 支持文件移动、功能重构
- 多种追溯策略：commit链、代码块、AST结构、相似度搜索

## 安装

```bash
pip install -e .
```

## 使用

### 基本用法

```bash
# 追溯bug是否影响目标版本
coderipple trace <fix_commit> <target_tag_or_branch>
```

### 示例

```bash
# 检查commit abc123是否影响v1.0.0
coderipple trace abc123 v1.0.0

# 输出JSON格式
coderipple trace abc123 v1.0.0 --output json
```

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 查看覆盖率
pytest --cov=src --cov-report=html
```

## License

MIT
