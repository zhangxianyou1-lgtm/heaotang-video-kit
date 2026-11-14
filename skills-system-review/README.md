# 我的 Codex Skill 系统：现状与公开评审请求

快照日期：2026-11-14。目标：请外部评审者检查这套 Skill 系统的分类、职责、自动选用、冲突与维护问题，提出有依据的精简建议。本文描述现状和待验证问题，不是一套已经验证有效的新方案。

## 1. 我想解决什么问题

我希望只描述工作目标，AI 就能选择需要的技能，不必每次点名。例如：做新 UI 时，应主动使用 UI Discovery 和 UI UX Pro Max；做局部样式修改时，不应启动繁重的需求访谈。

我曾观察到做 UI 时这两个技能没有被明显调用。目前只核查了本机规则，没有取得那次任务的完整执行记录。因此，“漏调用”是用户报告的现象，具体根因尚未确认；不能直接断言是安装损坏、规则冲突或模型没有遵循规则。

## 2. 我的分类：加强型与功能型

这是本人为管理技能采用的术语，不是 Codex 的官方分类。

- **加强型 Skill（也称非功能型）**：帮助 AI 更好地思考、创作、设计和开发，改善工作方法与产出质量。
- **功能型 Skill**：围绕具体任务或外部软件完成操作，例如访问淘宝、操作剪映、处理表格。
- 同一技能可能同时具备两种属性。主分类按本人使用目的确定，技术能力另作说明。不能由“加强型”推断该技能没有脚本、工具或外部操作。

### 已明确归入加强型的 8 项

| 项目 | 单位 | 主要职责 | 分类边界 |
| --- | --- | --- | --- |
| Matt Pocock Skills | 技能包 | 领域建模、诊断、审查、研究、TDD 等工程方法 | 本机另有本地版本，需审查重叠 |
| Ponytail | 技能包 | 控制复杂度、优先复用、最小充分实现 | 精简不能删减明确需求、正确性和验证 |
| Superpowers | 技能包 | 需求、计划、实现、调试、验证等工作流 | 与 Matt Pocock 的部分阶段重叠 |
| ui-discovery | 单个技能 | 澄清视觉方向，形成 UI Brief | 新界面和大改版适用；明确的小改动可跳过完整流程 |
| ui-ux-pro-max | 单个技能 | 设计系统、排版、配色、交互、响应式及可访问性指导 | 有本地检索脚本，须实际执行对应查询才能算完成相关步骤 |
| ppt-master | 单个技能／复合工作流 | 内容组织、演示设计、SVG 和 PPTX 产出 | 按本人意图归入加强型，但同时有明确的制作与导出功能 |
| cli-anything | 单个技能／方法论入口 | 为软件构建、完善和验证 CLI 操作封装 | 是能力构建辅助，也可能生成可运行工具 |
| cli-hub-meta-skill | 单个技能／发现入口 | 发现 CLI 工具和组合工作流 | 辅助选择能力，也包含安装和调用工具的指引 |

原本本地清单中的编号对应关系：1 = cli-anything，2 = cli-hub-meta-skill，20 = ppt-master，22 = ui-discovery，23 = ui-ux-pro-max。

这 8 项混合了“技能包”和“单个技能”，不能与底层技能条目数直接相加比较。其余技能的加强型／功能型归属尚未逐项由本人确认，附录保留来源，不擅自替所有技能定类。

## 3. 系统现状与统计口径

- 本轮会话可见、且已核对本机文件的技能条目：**151 条**。
- 仅按 SKILL.md 中的 name 去重：**137 个名称**。名称相同不代表内容相同。
- 对应目录另有 **45 个附带技能文件**未作为独立条目暴露给本轮会话；它们不是 45 个已经验证可调用的技能。
- 没有把全部旧版本缓存纳入统计；没有历史卸载记录，因此不能据此描述“曾经安装过的全部技能”。
- 这是一份本轮可见性快照，不是全账户、所有项目与所有会话的完整启用状态证明。插件已安装、技能可见、技能已读取、脚本成功运行、任务已验收，是不同状态。
- 本地非系统技能 23 条，系统技能 4 条；另一个用户级目录有 5 条，其中 4 个名称与前者重复。

## 4. 当前已有的路由规则

用户级约定要求：开发应用、网站、工具、功能变更、故障修复、重构和审查代码时，先读取 `engineering-workflow-guide`。普通问答、纯文案和独立办公／媒体任务使用对应能力。

统一入口是供 AI 阅读和遵循的规则文件；本次未验证存在一个独立程序，能够在漏读时强制阻止实施。

| 任务 | 入口当前规定的路线 |
| --- | --- |
| 明确的小改动、局部样式修正 | 直接处理，按风险做检查 |
| 新界面或重大视觉改版 | ui-discovery → ui-ux-pro-max → 实现与预览 |
| 复杂业务或跨模块功能 | 复用已有流程，按需选择建模、规格和实现 |
| 故障或回归 | 采用一套诊断流程，不同时启动多套 |
| 已有规格继续实施 | 从未完成阶段继续，不重启需求访谈 |
| 独立办公／图片／视频制作 | 使用专门技能，不强行套用整个开发流程 |

其他已存在的约束：沿用用户已确认的需求、UI Brief 和技术栈；只加载当前阶段有关的技能；不要求用户挑选插件；同一阶段保留一套主流程；不默认启动并行代理；技能选择不扩大外部操作授权。

### UI 的具体交接

1. UI Discovery 先检查已有上下文、设计和组件约定，只询问未解决且影响结果的选择。
2. 新 UI 或重大改版形成可审阅的 UI Brief；复用已经确认的信息和授权，不反复确认同一事项。
3. UI UX Pro Max 在 Brief 内提供设计系统与实现指导。新页面／项目要求设计系统查询；针对性问题用适当的 domain 或 stack 查询。
4. 进行实现和预览，检查与需求相关的布局、交互和状态。

### PPT 与 CLI 的边界

- ppt-master 自带制作流程和确认节点；独立演示文稿任务不应默认增加通用软件项目的分支、测试或开发脚手架。
- cli-anything 要求按所选模式读取配套方法论和规范，单独读取入口文件不等于完成能力构建。
- cli-hub-meta-skill 提倡先检查现有能力，再按任务需要安装，避免为一个需求批量安装整个工具集。

## 5. 希望评审者重点检查的问题

以下是审查线索，并非已经确认的全部故障。

| 问题 | 当前证据 | 尚缺的证据／希望得到的建议 |
| --- | --- | --- |
| 新 UI 的加强型技能可能漏用 | 路由文件有明确要求，用户报告历史任务未明显调用 | 检查当次任务上下文、实际读取记录及设计查询，区分未提示与未执行 |
| 纯 UI 设计是否被统一入口覆盖 | 用户级入口主要以开发任务描述触发；UI 技能自身范围更广 | 只做设计稿、不给代码的请求，是否也能可靠选择两个技能 |
| 同名技能与版本重叠 | 两份 Matt Pocock 包，以及两个本地目录的同名技能同时可见 | 比较内容差异、实际选择路径与升级策略；不能只按名称删除 |
| 多套方法论重复执行 | Matt Pocock、Superpowers、Ponytail 有交叉职责；入口要求选一套主流程 | 是否仍会重复计划、访谈、测试或确认；建议明确谁负责哪个阶段 |
| 路由引用的技能未必本轮可见 | 入口提到 to-spec、to-tickets、implement 等，但不在本轮暴露的独立技能列表中；对应包内有附带文件 | 这是正常的按需读取、配置差异还是失效引用；应如何明确回退 |
| 确认节点与自主推进不一致 | UI Discovery 和 PPT 有确认节点；入口要求复用既有确认 | 哪些决定需要新确认，哪些应直接沿用，能否避免两头走极端 |
| 精简原则与完整工作流冲突 | Ponytail 鼓励最小实现；其他技能可能要求较完整过程 | 如何让简单改动简短，同时不漏掉明确需求和必要验证 |
| 技能描述的适用范围交叉 | UI、Figma、CloudBase、Sites、演示和媒体技能各有流程 | 是否因工具或平台存在而错误扩大使用范围；哪些任务只需专门技能 |
| 分类混合了包、技能和能力 | 本人关注的 8 项单位并不一致 | 是否保留两大主类，再用包／技能、流程／工具等标签补充 |
| “已调用”缺少可观察证据 | 安装清单只能证明文件存在与本轮可见 | 是否用简短的选择理由、读取与执行记录、产物和验收结果即可，不建立复杂新系统 |

## 6. 建议用这些场景检查路由

以下是待执行的检查方案，不是已通过的测试结果。

| 输入场景 | 预期行为 | 常见失败信号 |
| --- | --- | --- |
| 帮我设计一个新的管理后台 | 明确 UI 方向，使用两个 UI 加强型技能，形成设计指导后交付 | 直接套模板写页面，无 Brief 或设计依据 |
| 只做一份 App UI 设计方案，暂时不编码 | 根据 UI 任务选用设计技能 | 因未要求编码而完全漏掉 UI 路由 |
| 把现有按钮间距改成 8px | 复用现有样式、局部修改和检查 | 重新进行完整访谈或产品规格设计 |
| 按已确认的 UI Brief 继续第二页 | 复用已有决定，只补实际缺口 | 重复询问已经确定的配色和风格 |
| 修复纯后端解析错误 | 诊断实际调用链，做最小充分修复 | 无关地启动 UI 或云平台流程 |
| 将材料做成 PPT | 使用相应演示制作流程 | 启动整套应用开发流程 |
| 在淘宝查找某种商品 | 选择淘宝功能型技能及可用工具 | 仅给出设计方法论，没有执行实际任务 |
| 为已有软件构建 CLI | 读取 cli-anything 对应模式，构建并验证 | 混淆“发现现成 CLI”与“构建新 CLI” |

## 7. 希望评审意见如何提交

请优先指出可以复现、定位到规则或记录的问题，格式建议如下：

```text
问题：
涉及的技能／规则：
证据与触发场景：
影响：
最小修改建议：
验证修改是否有效的方法：
仍然不确定的部分：
```

优先审查 UI 路由是否可靠、重复来源是否造成选择混乱、主流程是否唯一。请不要仅因数量多就建议全部卸载，也不要默认再增加一个总控框架。

## 8. 材料范围

本文根据本轮会话技能目录、本机 SKILL.md 与工程入口及其插件选择表整理。已阅读并摘要的重点是工程入口、UI Discovery、UI UX Pro Max、CLI-Anything、CLI-Hub 和 PPT Master 的相关说明；附录并不代表已审计全部 151 条技能内容。

不公开凭据、账号配置、浏览器资料、私人项目内容或本机绝对路径。本文是审查说明与清单，不是完整可安装备份，不批量重新分发第三方技能源码。历史任务的调用日志尚未收集，运行时是否漏调用须另行验证。

## 附录：本轮可见技能清单

下表保留重复来源，便于评审；不把同名条目擅自合并。


| # | Skill | Source |
| --- | --- | --- |
| 1 | `imagegen` | Local skills (including system) |
| 2 | `openai-docs` | Local skills (including system) |
| 3 | `skill-creator` | Local skills (including system) |
| 4 | `skill-installer` | Local skills (including system) |
| 5 | `cli-anything` | Local skills (including system) |
| 6 | `cli-hub-meta-skill` | Local skills (including system) |
| 7 | `client-scene-recreation` | Local skills (including system) |
| 8 | `dreamina-cli` | Local skills (including system) |
| 9 | `general-video` | Local skills (including system) |
| 10 | `hyperframes` | Local skills (including system) |
| 11 | `hyperframes-animation` | Local skills (including system) |
| 12 | `hyperframes-audio` | Local skills (including system) |
| 13 | `hyperframes-cli` | Local skills (including system) |
| 14 | `hyperframes-core` | Local skills (including system) |
| 15 | `hyperframes-creative` | Local skills (including system) |
| 16 | `hyperframes-keyframes` | Local skills (including system) |
| 17 | `hyperframes-registry` | Local skills (including system) |
| 18 | `hyperframes-studio` | Local skills (including system) |
| 19 | `jianying-editor` | Local skills (including system) |
| 20 | `liyifan-aigc-editing` | Local skills (including system) |
| 21 | `media-use` | Local skills (including system) |
| 22 | `motion-graphics` | Local skills (including system) |
| 23 | `moyu-wangjie-editing` | Local skills (including system) |
| 24 | `ppt-master` | Local skills (including system) |
| 25 | `taobao-native` | Local skills (including system) |
| 26 | `ui-discovery` | Local skills (including system) |
| 27 | `ui-ux-pro-max` | Local skills (including system) |
| 28 | `engineering-workflow-guide` | User-level skills |
| 29 | `hyperframes` | User-level skills |
| 30 | `hyperframes-cli` | User-level skills |
| 31 | `hyperframes-registry` | User-level skills |
| 32 | `media-use` | User-level skills |
| 33 | `compshare-cli` | compshare-cli |
| 34 | `libtv-blender-live-action` | libtv |
| 35 | `libtv-to-treatment` | libtv |
| 36 | `music-driven-product-ad` | libtv |
| 37 | `code-review` | mattpocock-skills |
| 38 | `codebase-design` | mattpocock-skills |
| 39 | `diagnosing-bugs` | mattpocock-skills |
| 40 | `domain-modeling` | mattpocock-skills |
| 41 | `pr` | mattpocock-skills |
| 42 | `prototype` | mattpocock-skills |
| 43 | `research` | mattpocock-skills |
| 44 | `tdd` | mattpocock-skills |
| 45 | `wizard` | mattpocock-skills |
| 46 | `grilling` | mattpocock-skills |
| 47 | `writing-for-agents` | mattpocock-skills |
| 48 | `sites-building` | sites |
| 49 | `sites-hosting` | sites |
| 50 | `sites-mcp` | sites |
| 51 | `sites-preview-troubleshooting` | sites |
| 52 | `computer-use` | computer-use |
| 53 | `figma-code-connect` | figma |
| 54 | `figma-code-workflows` | figma |
| 55 | `figma-create-new-file` | figma |
| 56 | `figma-design-to-code` | figma |
| 57 | `figma-generate-design` | figma |
| 58 | `figma-generate-diagram` | figma |
| 59 | `figma-generate-library` | figma |
| 60 | `figma-generative-plugins` | figma |
| 61 | `figma-implement-motion` | figma |
| 62 | `figma-shaders` | figma |
| 63 | `figma-spec` | figma |
| 64 | `figma-swiftui` | figma |
| 65 | `figma-use` | figma |
| 66 | `figma-use-figjam` | figma |
| 67 | `figma-use-motion` | figma |
| 68 | `figma-use-slides` | figma |
| 69 | `google-docs` | google-drive |
| 70 | `google-drive` | google-drive |
| 71 | `google-drive-comments` | google-drive |
| 72 | `google-sheets` | google-drive |
| 73 | `google-slides` | google-drive |
| 74 | `maintain-space` | pages |
| 75 | `manage-schedules` | pages |
| 76 | `organize-space` | pages |
| 77 | `write-page` | pages |
| 78 | `sites` | sites |
| 79 | `sites-remix` | sites |
| 80 | `brainstorming` | superpowers |
| 81 | `diagnosing-superpowers` | superpowers |
| 82 | `dispatching-parallel-agents` | superpowers |
| 83 | `executing-plans` | superpowers |
| 84 | `finishing-a-development-branch` | superpowers |
| 85 | `receiving-code-review` | superpowers |
| 86 | `requesting-code-review` | superpowers |
| 87 | `subagent-driven-development` | superpowers |
| 88 | `systematic-debugging` | superpowers |
| 89 | `test-driven-development` | superpowers |
| 90 | `using-git-worktrees` | superpowers |
| 91 | `using-superpowers` | superpowers |
| 92 | `verification-before-completion` | superpowers |
| 93 | `writing-plans` | superpowers |
| 94 | `writing-skills` | superpowers |
| 95 | `create-pet` | work-pets |
| 96 | `pets` | work-pets |
| 97 | `update-pet` | work-pets |
| 98 | `plugin-management` | plugin-management |
| 99 | `visualize` | visualize |
| 100 | `documents` | documents |
| 101 | `pdf` | pdf |
| 102 | `Presentations` | presentations |
| 103 | `excel-live-control` | spreadsheets |
| 104 | `Spreadsheets` | spreadsheets |
| 105 | `template-creator` | template-creator |
| 106 | `code-review` | matt-pocock-skills-local |
| 107 | `codebase-design` | matt-pocock-skills-local |
| 108 | `diagnosing-bugs` | matt-pocock-skills-local |
| 109 | `domain-modeling` | matt-pocock-skills-local |
| 110 | `grilling` | matt-pocock-skills-local |
| 111 | `prototype` | matt-pocock-skills-local |
| 112 | `research` | matt-pocock-skills-local |
| 113 | `resolving-merge-conflicts` | matt-pocock-skills-local |
| 114 | `tdd` | matt-pocock-skills-local |
| 115 | `wizard` | matt-pocock-skills-local |
| 116 | `writing-for-agents` | matt-pocock-skills-local |
| 117 | `ponytail` | ponytail |
| 118 | `ponytail-audit` | ponytail |
| 119 | `ponytail-debt` | ponytail |
| 120 | `ponytail-gain` | ponytail |
| 121 | `ponytail-help` | ponytail |
| 122 | `ponytail-review` | ponytail |
| 123 | `ai-model-nodejs` | cloudbase |
| 124 | `ai-model-web` | cloudbase |
| 125 | `ai-model-wechat` | cloudbase |
| 126 | `auth-nodejs-cloudbase` | cloudbase |
| 127 | `auth-tool-cloudbase` | cloudbase |
| 128 | `auth-web-cloudbase` | cloudbase |
| 129 | `auth-wechat-miniprogram` | cloudbase |
| 130 | `cloud-functions` | cloudbase |
| 131 | `cloud-storage-web` | cloudbase |
| 132 | `cloudbase-agent` | cloudbase |
| 133 | `cloudbase-cli` | cloudbase |
| 134 | `cloudbase-code-review` | cloudbase |
| 135 | `cloudbase` | cloudbase |
| 136 | `cloudbase-platform` | cloudbase |
| 137 | `cloudbase-wechat-integration` | cloudbase |
| 138 | `cloudrun-development` | cloudbase |
| 139 | `data-model-creation` | cloudbase |
| 140 | `http-api-cloudbase` | cloudbase |
| 141 | `miniprogram-development` | cloudbase |
| 142 | `cloudbase-document-database-web-sdk` | cloudbase |
| 143 | `cloudbase-document-database-in-wechat-miniprogram` | cloudbase |
| 144 | `ops-inspector` | cloudbase |
| 145 | `postgresql-development-cloudbase` | cloudbase |
| 146 | `relational-database-mcp-cloudbase` | cloudbase |
| 147 | `relational-database-web-cloudbase` | cloudbase |
| 148 | `spec-workflow` | cloudbase |
| 149 | `ui-design` | cloudbase |
| 150 | `web-development` | cloudbase |
| 151 | `cloudbase-sites-runtime` | cloudbase-sites |
