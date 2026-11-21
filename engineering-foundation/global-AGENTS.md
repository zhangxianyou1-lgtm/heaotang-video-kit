# 三剑客工程底座（Matt Pocock × Ponytail × Poteto）

遵循用户当前指令与项目自身的 `AGENTS.md`；明确的小改动直接完成并验证，视频、UI、办公等专业领域技能按实际交付物原样调用：

- **1. 前段对齐与拆解（Matt Pocock）**：需求存在改变产品行为的实质缺口时，调用 `grill-with-docs`（无仓库时用 `grill-me`）逐题对齐决策树并沉淀 `GLOSSARY.md` 领域词典与 ADR；跨会话或多模块任务走 `to-spec` → `to-tickets`（纵向曳光弹切片）→ `implement` 或 `implement-spec`（前沿并行 Worktree）。已有确认规格或 UI Brief 直接续接，不重复访谈。
- **2. 中段极简实现（Ponytail + Poteto）**：动笔前查清受影响调用链、测试与配置（跨模块接口未定时先用 `architect` 对比两种结构）；按 **Ponytail 6 级阶梯**取首个可行解（YAGNI 不写未要求项 → 复用仓内实现 → 标准库/平台原生 → 已装依赖 → 最短清晰完整改动），先删死代码再建新逻辑（`Subtract Before You Add`）。关键行为配可观察行为测试（`tdd`），不测内部实现细节。
- **3. 后段实证破壁与免人审闭环（Poteto `pstack` + Matt `code-review`）**：
  - **真产物自证（`Prove It Works`）**：CLI 跑真命令、UI/服务走真实路径抓证据（缺自动化驱动的项目可用 `create-verification-skill` 生成专属 `verify-<app>`）；生图/生视频等外部异步计费接口结果未知时先查既有任务 ID，严禁盲目重提；无法实跑如实标 `inconclusive`。
  - **零噪音分层自审**：常规交付跑并行双轴 `code-review`（`Spec` 需求符合度 + `Standards` 规范）或 `ponytail-review`；底层/高风险改动追加 `blast-radius`（运行代码证明核心安全事实）或对抗式 `interrogate`（**只保留真实运行命令证伪的缺陷，未运行的猜测与纯风格挑刺一律丢弃**）。派发审查子 Agent 只给目标规格与实际 Diff/文件，不传执行者自评。
  - **结构化防再犯（`Encode Lessons in Structure`）**：同类问题被纠正两次时，调用 `correct` 按「架构消除 → 类型锁死 → 报错指路的 Lint/门禁脚本 → 行为测试 → 最后才写文档」固化进仓库。
