# CodeRipple 详细设计文档

## 1. 目标

CodeRipple 用于回答一个具体问题：

给定一个修复提交，目标版本是否仍然受这个 Bug 影响。

这里的关键不是判断：

- `fix commit` 是否可达

而是判断：

- 目标版本是否已经包含修复或等价修复
- 如果没有，目标版本里是否仍然存在对应的 Bug 代码证据

这也是当前项目最重要的语义约束。

## 2. 结果模型

系统对外暴露三种状态：

- `affected`
- `not_affected`
- `unknown`

含义如下：

`affected`
已经找到足够直接的 Bug 证据，能够确认目标版本仍受影响。

`not_affected`
已经确认目标版本包含修复，或包含等价修复。

`unknown`
当前策略没有确认“仍受影响”，也没有确认“已经修复”。

内部结果结构由 [result.py](/Volumes/kernel_disk/CodeRipple/src/core/result.py) 中的 `TraceResult` 表示，核心字段是：

- `found`
- `commit`
- `method`
- `confidence`
- `details`

其中：

- `found=True` 对应最终状态 `affected`
- `found=False` 还需要结合 `details` 中的修复证据，区分 `not_affected` 和 `unknown`

## 3. 总体架构

项目采用“CLI -> 主流程 -> 策略 -> 底层能力”的分层结构。

### 3.1 分层

`src/cli`
负责命令解析、参数校验、结果渲染、JSON/table 输出、帮助信息。

`src/core`
负责主流程调度和结果聚合。

`src/core/strategies`
负责具体追溯策略实现。

`src/git`
负责 Git 仓库读能力和等价修复检测能力。

`src/parser`
负责 AST 解析、标准化、特征提取和相似度相关能力。

`src/config`
负责配置加载和默认配置。

### 3.2 当前主要文件

- [main.py](/Volumes/kernel_disk/CodeRipple/src/cli/main.py)
- [tracer.py](/Volumes/kernel_disk/CodeRipple/src/core/tracer.py)
- [result.py](/Volumes/kernel_disk/CodeRipple/src/core/result.py)
- [commit_chain.py](/Volumes/kernel_disk/CodeRipple/src/core/strategies/commit_chain.py)
- [code_block.py](/Volumes/kernel_disk/CodeRipple/src/core/strategies/code_block.py)
- [ast_structure.py](/Volumes/kernel_disk/CodeRipple/src/core/strategies/ast_structure.py)
- [similarity.py](/Volumes/kernel_disk/CodeRipple/src/core/strategies/similarity.py)
- [repo.py](/Volumes/kernel_disk/CodeRipple/src/git/repo.py)
- [__init__.py](/Volumes/kernel_disk/CodeRipple/src/config/__init__.py)

## 4. CLI 设计

当前 CLI 只保留三个子命令：

- `affected`
- `find-fix`
- `doctor`

### 4.1 `affected`

主命令，用于判断目标版本是否仍受影响。

支持两类 fix 输入：

- `--fix <commit>`
- `--fix-message "<message>"`

支持两类 target 输入：

- 重复传入 `--target`
- `--targets-file`

支持两类输出：

- `table`
- `json`

支持 `--explain` 输出详细分析过程。

### 4.2 `find-fix`

在不知道 `fix commit` 时，先按提交信息搜索候选修复提交。

当前支持：

- `--message`
- `--target`
- `--path`
- `--since-days`
- `--limit`

### 4.3 `doctor`

在正式分析前先验证输入，包括：

- repo 是否可解析
- config 是否可解析
- fix 是否可解析
- target 是否可解析

## 5. 主流程设计

主流程在 [tracer.py](/Volumes/kernel_disk/CodeRipple/src/core/tracer.py) 的 `BugTracer` 中。

### 5.1 策略加载

当前按优先级加载四种策略：

1. `commit_chain`
2. `code_block`
3. `ast_structure`
4. `similarity`

### 5.2 执行逻辑

对于每个目标版本：

1. 依次执行策略
2. 记录每次策略尝试，保存到 `attempts`
3. 如果某个策略直接确认 `affected`，立即返回
4. 如果某个策略确认“目标版本已修复”，立即返回 `not_affected`
5. 如果所有策略都没有决定性证据，返回 `unknown`

### 5.3 短路规则

这是当前实现中的关键约束：

- 命中修复证据后，必须短路返回，不能再让后续模糊策略翻回去
- `commit_chain` 不能因为“fix commit 不可达”就直接返回 `affected`

这条约束是为了解决早期版本曾经出现过的严重误判。

## 6. 策略设计

## 6.1 `commit_chain`

实现位置：
[commit_chain.py](/Volumes/kernel_disk/CodeRipple/src/core/strategies/commit_chain.py)

职责：
只判断“目标版本是否已经修复”，不判断“目标版本一定带 bug”。

当前检查顺序：

1. `fix commit` 是否直接可达
2. 是否存在 `patch-id` 等价提交
3. 被修复文件的最终内容是否等价
4. 单文件场景下，AST 标准化后的最终状态是否等价

输出规则：

- 命中以上任一条件 -> `not_affected`
- 都未命中 -> `unknown`

绝不在这里直接输出 `affected`。

## 6.2 `code_block`

实现位置：
[code_block.py](/Volumes/kernel_disk/CodeRipple/src/core/strategies/code_block.py)

职责：
从修复提交中提取更直接的代码证据，在目标版本中定位仍然存在的 Bug 代码块。

当前已覆盖：

- 普通新增型修复
- 修改型修复
- 仅删除 buggy 代码的修复

删除型修复场景下，不再依赖新增行，而是使用被删除代码作为查询块。

## 6.3 `ast_structure`

实现位置：
[ast_structure.py](/Volumes/kernel_disk/CodeRipple/src/core/strategies/ast_structure.py)

职责：
在文本变化较大时，基于 AST 结构继续搜索目标版本里的 Bug 证据。

适合覆盖：

- 变量重命名
- 轻微重构
- 文本不同但结构相近

## 6.4 `similarity`

实现位置：
[similarity.py](/Volumes/kernel_disk/CodeRipple/src/core/strategies/similarity.py)

职责：
提供最后一层更宽松的文本/特征相似度兜底匹配。

它的精度低于前两层，因此放在末尾。

## 7. Git 能力设计

核心实现位于 [repo.py](/Volumes/kernel_disk/CodeRipple/src/git/repo.py)。

当前提供的关键能力包括：

- commit 解析与缓存
- 文件内容读取与缓存
- `is_ancestor`
- 提交遍历
- 按提交信息搜索 commit
- fix-message 候选排序
- `patch-id` 等价提交识别
- 最终文件状态等价判断
- AST 等价状态判断

### 7.1 `fix-message`

当前实现是全历史扫描 `--all`，做不区分大小写的子串匹配。

排序依据包括：

- 摘要精确匹配程度
- 摘要前缀命中情况
- 提交时间
- 相对目标版本的可达性

之前存在“只搜最近 500 个提交”的问题，已经移除默认截断。

### 7.2 等价修复识别

当前支持三层等价修复识别：

1. 等价 patch
2. 最终文件状态等价
3. 单文件 AST 等价

其中最终文件状态等价还支持：

- 路径变化后按 basename 找候选文件
- 拆分 backport 后的最终一致状态

## 8. Parser 设计

`src/parser` 主要负责代码表示和归一化能力。

### 8.1 AST 解析

负责把代码解析成 AST。

### 8.2 AST 标准化

负责去掉表面差异，构造更稳定的结构指纹。

当前标准化已经覆盖：

- 标识符标准化
- 函数参数名标准化
- 指纹生成

### 8.3 相似度与特征

为最后一层 `similarity` 策略提供支持。

## 9. Explain 设计

`--explain` 的目标不是输出不可审计的内部思维，而是输出可验证证据链。

当前 explain 结构包括：

- `inputs`
- `summary`
- `decision_path`
- `final_decision`
- `strategies`

每个策略节点都包含：

- `method`
- `status`
- `confidence`
- `summary`
- `evidence`

这样可以直接看到：

- 哪一层先命中
- 为什么继续往后执行
- 为什么最终停在某一层
- 具体证据是什么

## 10. 配置设计

配置在 [__init__.py](/Volumes/kernel_disk/CodeRipple/src/config/__init__.py) 中实现。

默认配置项包括：

- `cache_path`
- `similarity_threshold`
- `log_level`

当前默认配置文件路径是：

`config/coderipple.yaml`

## 11. 测试设计

测试分三层：

`tests/unit`
覆盖底层能力和各策略的局部行为。

`tests/integration`
覆盖 `BugTracer` 主流程和策略协作行为。

`tests/e2e`
覆盖真实 CLI 命令和完整 Git 历史场景。

当前重点回归场景包括：

- fix commit 可达
- target 从未引入 bug
- 等价 patch backport
- 部分 backport
- 拆分 backport
- 文件移动后的 backport
- 删除型修复
- `fix-message` 搜索
- `--explain` 输出
- 批量 targets

## 12. 当前边界

当前实现并不承诺解决所有“语义等价”问题。

已明确覆盖的是：

- 直接修复
- 等价 patch
- 最终文件状态等价
- 单文件轻微重构后的 AST 等价

尚未完全覆盖的通常是更复杂场景，例如：

- 大范围重写后仅行为等价
- 多文件大重构后的深层语义等价
- 跨语言或生成代码场景

因此，`unknown` 仍然是合理且必要的状态，而不是失败状态。

## 13. 演进原则

后续扩展时必须坚持这些约束：

- 不把“缺少 fix”当成“确认受影响”
- 不让后续模糊策略推翻已经确认的 `not_affected`
- 新策略必须输出结构化证据，而不是只输出布尔值
- CLI 对外语义优先保持简单，详细信息放进 `--explain`
