# 三剑客工程底座（Matt Pocock × Ponytail × Poteto `pstack`）

本目录将三位一线工程作者的最新开源 Agent 技能按 **「前段对齐拆解 → 中段极简编码 → 后段实证免审」** 组装成一套**零重名冲突、零手工状态机台账、跨宿主通用（Codex / Antigravity / Claude Code）**的工程底座，同时不改动任何业务/媒体领域技能（视频、UI、PPT 等）。

---

## 一、三剑客分工与上游溯源（共 47 个原版技能）

| 阶段 | 模块目录 | 上游仓库 | 技能数 | 核心解决的问题与代表技能 |
| :--- | :--- | :--- | :---: | :--- |
| **1. 前段：方向对齐与拆单** | [`mattpocock-skills/`](mattpocock-skills/) | [`mattpocock/skills`](https://github.com/mattpocock/skills) (`v1.3.2`) | **27** | **防需求跑偏与上下文腐化**：`grill-with-docs`（逐题追问决策树并维护 `GLOSSARY.md` 领域词典与 ADR）、`to-spec` → `to-tickets`（纵向曳光弹工单）→ `implement` / `implement-spec`（DAG 前沿并行 Worktree 实施）、双轴 `code-review`（`Spec` + `Standards`） |
| **2. 中段：极简编码刹车片** | [`ponytail/`](ponytail/) | [`DietrichGebert/ponytail`](https://github.com/DietrichGebert/ponytail) (`v5.3.3`) | **6** | **防强模型过度设计（Over-engineering）**：6 级极简阶梯（YAGNI → 仓内复用 → 标准库/原生 → 已装依赖 → 一行清晰实现 → 最小完整 Diff），配 `ponytail-review`（值班工程师视角查并发负载风险与可删代码行数） |
| **3. 后段：实证破壁与免人审** | [`pstack-poteto/`](pstack-poteto/) | [`cursor/plugins/pstack`](https://github.com/cursor/plugins/tree/main/pstack) (`@poteto`) | **14** | **把人从肉眼盯代码与手点页面中解放出来**：`interrogate`（对抗式审查：**只保留真实运行命令证伪的 Bug**，零主观废话）、`blast-radius`（运行代码证明改动安全的核心事实）、`create/maintain-verification-skill`（生成项目专属 `.agents/skills/verify-<app>/` 端到端自验与功能地图）、`correct`（重复错误按 架构→类型→Lint脚本→测试 固化）、`poteto-principles`（24 条高信任工程原则完整合集） |

精确上游提交哈希与许可证信息见 [`UPSTREAM.json`](UPSTREAM.json)；全局轻量触发指针见 [`global-AGENTS.md`](global-AGENTS.md)。

---

## 二、一键自检与跨电脑实装

仅依赖 Python 3.11+ 标准库：

```powershell
# 1. 结构、元数据与零重名冲突自检
python -X utf8 engineering-foundation/install_foundation.py --check

# 2. 预览本机将要写入/更新的路径（不修改任何文件）
python -X utf8 engineering-foundation/install_foundation.py --dry-run

# 3. 一键实装到本机 Codex 与 Antigravity（自动备份原配置，保留自定义章节）
python -X utf8 engineering-foundation/install_foundation.py
```

---

## 三、日常怎么用（最少心智负担）

1. **平时直接说大白话**：全局 `AGENTS.md`（及 Antigravity 插件内置规则）已挂载 ~20 行轻量指针，AI 会默认遵守 Ponytail 极简阶梯、土豆姐 `Prove It Works` 实跑自证与双轴审查。
2. **需求模糊的大功能**：点名 `grill-with-docs` 对齐决策树并生成 `GLOSSARY.md`，再走 `to-spec` → `to-tickets` → `implement-spec`。
3. **不想人肉盯高风险 Diff**：点名 `interrogate`（对抗式破壁，没跑出真实报错的废话一条不留）或 `blast-radius`；新项目第一次接入点名 `create-verification-skill` 建好自动端到端验证技能。
4. **同一个坑说了两遍**：点名 `correct`，让 AI 把教训变成架构约束、类型错误或门禁脚本（像本仓的 `check_r60_plans.py` 一样），而不是继续往文档里堆废话。
