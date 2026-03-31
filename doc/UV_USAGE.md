# CodeRipple 使用uv管理

## 安装uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm.exe -ProgressAction, ProgressBar; Invoke-WebRequest -Uri https://astral.sh/uv/install.ps1 -OutFile install.ps1; .\install.ps1"
```

## 安装依赖

```bash
# 同步依赖（安装到.venv）
uv sync

# 安装开发依赖
uv sync --extra dev
```

## 运行项目

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行CLI
coderipple trace abc123 v1.0.0

# 或直接使用uv运行
uv run coderipple trace abc123 v1.0.0
```

## 运行测试

```bash
# 使用uv运行pytest
uv run pytest

# 运行特定测试
uv run pytest tests/unit/test_ast_parser.py

# 带覆盖率
uv run pytest --cov=src
```

## 添加依赖

```bash
# 添加生产依赖
uv add requests

# 添加开发依赖
uv add --dev pytest

# 添加特定版本
uv add "requests>=2.0.0"
```

## 更新依赖

```bash
# 更新所有依赖
uv lock --upgrade

# 更新特定包
uv lock --upgrade-package requests
```

## 常用命令

```bash
# 查看依赖树
uv tree

# 查看已安装的包
uv pip list

# 移除依赖
uv remove requests

# 清理虚拟环境
uv sync --clean
```

## Python版本管理

```bash
# 设置Python版本
uv python pin 3.9

# 查看当前Python版本
uv python --version
```

## 项目配置

pyproject.toml已配置：
- 项目信息
- 依赖管理
- 开发依赖
- 脚本配置
- 入口点配置

## 与传统方式对比

| 操作 | pip | uv |
|------|-----|-----|
| 安装依赖 | pip install -r requirements.txt | uv sync |
| 添加依赖 | pip install package | uv add package |
| 更新依赖 | pip install --upgrade package | uv lock --upgrade |
| 运行命令 | python -m module | uv run module |
| 虚拟环境 | python -m venv venv | 自动管理 |
| 锁文件 | requirements.txt | uv.lock |

## 优势

1. **更快**：用Rust编写，比pip快10-100倍
2. **更可靠**：更好的依赖解析
3. **更安全**：自动创建和管理虚拟环境
4. **更简单**：单一配置文件
5. **更现代**：支持PEP 621标准
