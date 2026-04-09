# CodeRipple

CodeRipple 是一个面向 Git 历史的 Bug 影响分析工具。给定一个修复提交，或一段能够定位修复提交的提交信息，它会判断某个目标分支、tag 或 commit 是否仍然受该 Bug 影响。

核心目标不是回答“这个 fix commit 在不在目标分支里”，而是回答“目标版本是否已经修掉了这个 Bug”。

## 功能概览

- 判断目标版本是否仍受某个修复提交对应的 Bug 影响
- 输出明确状态：`affected`、`not_affected`、`unknown`
- 支持 `fix commit`、`fix-message` 两种修复输入方式
- 支持 branch、tag、commit sha 作为目标版本
- 支持批量分析多个目标版本
- 支持 `find-fix` 独立搜索候选修复提交
- 支持 `doctor` 预先诊断仓库、配置、fix、target 是否可解析
- 支持 `--explain` 输出完整分析过程
- 支持文件移动、等价 backport、拆分回补、轻微重构后的等价修复识别

## 结果语义

`affected`
目标版本仍受影响，系统已经找到直接证据。

`not_affected`
目标版本已包含修复，或已包含等价修复。

`unknown`
当前策略没有找到“仍受影响”的直接证据，也没有足够证据证明“已经修复”。

## 工作原理

CodeRipple 的分析链路分成两层。

第一层是“修复是否已经存在”的快速判定。只要能确认目标版本已经包含修复或等价修复，就直接返回 `not_affected`。

第二层是“Bug 代码是否仍存在”的证据判定。如果第一层无法确认已修复，系统会继续沿着代码块、AST 结构、文本相似度等策略查找目标版本中的 Bug 证据；只有找到直接证据时才返回 `affected`。

这套设计是为了避免一个常见错误：
“目标版本没有 fix commit” 不等于 “目标版本一定有 bug”。

## 策略链路

### 1. `commit_chain`

这是第一层策略，只负责判断“目标版本是否已修复”，不会因为“缺少 fix commit”直接返回 `affected`。

它会按顺序检查：

- 目标版本是否直接包含 `fix commit`
- 目标版本是否存在等价 patch
- 目标版本在被修复文件上的最终内容是否已等价
- 单文件轻微重构后，AST 标准化结果是否等价

如果命中任一条件，结果为 `not_affected`。
如果都没命中，只返回 `unknown`，交给后续策略继续判断。

### 2. `code_block`

提取修复提交中关键的代码块，去目标版本中查找相同或相近的 Bug 代码证据。

当前支持：

- 普通新增/修改型修复
- 仅通过删除 buggy 代码完成的修复
- 删除型修复中的被删代码块匹配

### 3. `ast_structure`

把修复相关代码解析为 AST，比较目标版本中是否存在结构上等价的 Bug 代码，用于覆盖“文本不同但结构相近”的情况。

### 4. `similarity`

做更宽松的相似度搜索，作为最后一层兜底策略。

## 等价修复识别

除了直接包含 `fix commit`，CodeRipple 还会尝试识别这些“已经修好，但 commit 不是同一个”的情况：

- `cherry-pick` / backport 的等价 patch
- 修复被拆成多个 commit 回补，但最终文件状态一致
- 主线修复时发生文件移动，目标版本在旧路径上回补了相同修复
- 单文件轻微重构后，AST 标准化结果与修复后状态等价

这些场景会被判定为 `not_affected`。

反过来，下面这类场景不会被误判成“已修复”：

- 只回补了多文件修复中的一部分
- 只做了部分 backport
- 没有 fix commit，但目标版本其实从未引入对应 bug

## CLI 设计

CLI 只保留三个子命令：

- `affected`
- `find-fix`
- `doctor`

### `affected`

这是主命令，用来判断目标版本是否仍受影响。

```bash
uv run coderipple affected --fix <fix_commit> --target <ref>
uv run coderipple affected --fix-message "<message>" --target <ref>
uv run coderipple affected --fix <fix_commit> --target <ref1> --target <ref2>
uv run coderipple affected --fix <fix_commit> --targets-file targets.txt
```

常用参数：

```bash
--fix                    显式指定修复 commit
--fix-message            按提交信息搜索修复 commit
--fix-index              fix-message 命中多个候选时，选择第几个候选
--list-fix-candidates    仅列出候选提交，不执行分析
--target                 指定目标分支、tag 或 commit，可重复传入
--targets-file           从文件读取多个目标版本，每行一个 ref
--repo                   指定目标仓库路径
--config                 指定配置文件路径
--output                 table 或 json
--explain                输出详细分析过程
```

### `find-fix`

在还不知道 `fix commit` 时，先按提交信息搜索候选修复提交。

```bash
uv run coderipple find-fix --message "divide by zero"
uv run coderipple find-fix --message "divide by zero" --target release/v1.0
uv run coderipple find-fix --message "divide by zero" --path bug.py --since-days 30
```

它会返回候选 commit 列表，并综合这些因素排序：

- 提交摘要匹配度
- 提交时间
- 相对目标版本的可达性

### `doctor`

在真正执行分析前，先检查输入是否合法，提前暴露歧义和配置问题。

```bash
uv run coderipple doctor --fix abc123 --target release/v1.0
uv run coderipple doctor --fix-message "divide by zero" --target release/v1.0 --output json
```

它会诊断：

- 仓库路径是否有效
- 配置文件是否可解析
- `fix` / `fix-message` 是否可解析
- `target` / `targets-file` 中的 ref 是否可解析

## 分析输出

### Table 输出

默认输出适合人读，会显示：

- 最终结论
- 命中的方法
- 置信度
- 尝试过的策略数

加上 `--explain` 后，还会显示：

- 输入解析结果
- 策略执行路径
- 最终决策理由
- 每个策略的 `status / summary / evidence`

### JSON 输出

JSON 输出适合脚本集成，顶层会包含：

```json
{
  "status": "affected | not_affected | unknown",
  "affected": true,
  "commit": "matched_commit_or_null",
  "method": "matched_method_or_null",
  "confidence": 0.0,
  "details": {}
}
```

批量目标分析时会返回 `targets` 数组。

加上 `--explain` 后，还会额外返回：

- `resolved_fix`
- `resolved_target`
- `analysis.inputs`
- `analysis.decision_path`
- `analysis.final_decision`
- `analysis.strategies`

## 架构设计

项目按“命令入口 -> 主流程 -> 策略 -> Git/解析能力”分层。

### 模块分层

`src/cli`
命令行入口，负责参数解析、结果渲染、帮助信息和 JSON/table 输出。

`src/core`
主流程和结果模型。
`BugTracer` 会按优先级加载策略，依次执行，并负责短路规则和 attempts 记录。

`src/core/strategies`
具体追溯策略实现：

- `commit_chain.py`
- `code_block.py`
- `ast_structure.py`
- `similarity.py`

`src/git`
Git 能力封装，提供 commit 查询、patch-id、历史遍历、等价文件状态比较、AST 等价判断等能力。

`src/parser`
代码解析与特征提取，包括 AST 解析、标准化、结构特征和相似度计算。

`src/config`
配置加载与默认值管理。

### 执行流程

`affected` 的主流程大致如下：

1. 解析 `fix` 或 `fix-message`
2. 解析一个或多个 `target`
3. 加载配置并初始化 `BugTracer`
4. 依次执行策略
5. 若命中“已修复”证据，直接返回 `not_affected`
6. 若命中“Bug 仍存在”证据，返回 `affected`
7. 若所有策略都无法给出决定性结论，返回 `unknown`

### 设计约束

这个项目当前有几个明确的设计边界：

- `commit_chain` 不能把“未包含 fix”当成“仍受影响”
- 只有找到直接 Bug 证据时，才能返回 `affected`
- 只要能确认存在修复或等价修复，就应优先返回 `not_affected`
- `--explain` 输出的是可验证证据链，不是不可审计的自由文本推理

## 配置

默认配置在缺少配置文件时自动启用：

```yaml
cache_path: ~/.coderipple/cache
similarity_threshold: 0.85
log_level: INFO
```

默认配置文件路径是：

```bash
config/coderipple.yaml
```

## 目录结构

```text
src/
  cli/            # 命令行入口
  config/         # 配置管理
  core/           # 追溯主流程与结果模型
  core/strategies/# 各类追溯策略
  git/            # Git 仓库能力封装
  parser/         # AST、特征提取、相似度能力
tests/
  e2e/            # CLI 端到端测试
  integration/    # 主流程集成测试
  unit/           # 策略与底层能力单测
```

## 开发

安装依赖：

```bash
uv sync --extra dev
```

运行测试：

```bash
uv run pytest
```

只跑 CLI 端到端：

```bash
uv run pytest tests/e2e/test_cli.py
```

查看帮助：

```bash
uv run coderipple --help
uv run coderipple affected --help
uv run coderipple find-fix --help
uv run coderipple doctor --help
```

## License

MIT
