# CodeRipple 设计文档

## 1. 项目概述

### 1.1 功能目标
分析Git历史，检查修复commit是否影响商用版本

### 1.2 核心挑战
- 文件移动
- 跨仓库移动
- 功能完全重构

## 2. 核心功能

### 2.1 多层追溯策略
1. Commit链追溯（精确度100%）
2. 代码块内容追溯（精确度95%）
3. AST结构追溯（精确度90%）
4. 代码相似度搜索（精确度85%）

### 2.2 远程仓库管理
- 自动拉取商用版本
- 支持多种认证方式
- 智能缓存

## 3. 技术方案

### 3.1 依赖库
- gitpython: Git操作
- tree-sitter: 代码解析
- click: CLI框架

### 3.2 核心模块
- src/core/: 追溯引擎
- src/git/: Git操作封装
- src/parser/: 代码解析
- src/cli/: 命令行接口

## 4. 对外接口

### 4.1 命令行接口
```bash
coderipple trace <fix_commit> <target>
```

### 4.2 Python API
```python
from coderipple import BugTracer

tracer = BugTracer()
result = tracer.trace(fix_commit, target)
```

## 5. 实现计划

- Phase 1: Git操作层
- Phase 2: 代码解析层
- Phase 3: 追溯策略层
- Phase 4: 集成层
- Phase 5: CLI层
