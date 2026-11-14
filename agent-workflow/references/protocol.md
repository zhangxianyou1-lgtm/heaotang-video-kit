# 任务与证据协议

适用于需要多 Agent、独立复查或恢复记录的任务。只用当前 Codex 聊天的原生子 Agent；Python 工具记录状态和检查证据，不启动 Agent、不调用模型 API、不在聊天关闭后运行。

## 1. 建立本次运行

复用 Superpowers 的计划工作区约定 `.superpowers/sdd/<本次运行名>/`，每次目标/计划版本使用独立目录，勿复用其他聊天的运行。已有 progress.md 保留。`run.json` 是本入口最终验收记录；旧助手的 complete 只作为历史线索。

同目录保存 `routing.md`：本次范围、选定主流程、实际技能来源/版本或文件摘要、选择理由、工具就绪结果及必要回退。把这份记录列入相关任务的 inputs；修改路线后重新验收受影响任务。外部插件更新需主控重新核对来源，工具不会自动监听所有插件目录。

主控保存一份 spec.json，含 goal 和 tasks。任务结构如下（字段内容按本次实际替换）：

```json
{
  "goal": "交付经过测试和独立复查的汇总工具",
  "tasks": [
    {
      "id": "summary",
      "title": "实现数据汇总",
      "owns": ["src/summary.py"],
      "depends": [],
      "acceptance": ["有效数据得到正确合计", "无效输入有明确错误"],
      "inputs": ["data/input.json", "tests/check_summary.py"],
      "checks": [["python", "-B", "tests/check_summary.py"]],
      "max_attempts": 3,
      "timeout": 120
    }
  ]
}
```

文件路径相对于任务项目 root；owns 是文件或目录前缀，不是 glob。inputs 是从开始执行到验收保持不变的来源、配置、需求和检查文件，不能与本任务 owns 相交。需要编辑的代码/文档放 owns，交付时列为 artifact；不要又把它声明成只读 input。目录输入会递归计算指纹，应选择明确文件，避免把缓存等运行中会变化的目录放进去。

inputs 和 owns 均不能包含本次台账或日志存储，也不能覆盖其父目录；只引用具体 routing.md 等稳定文件，不引用整个运行目录。检查命令为 argv 数组，不经 shell 解析，不得由 worker 临时换成无关命令。需要运行时依赖的任务先核对环境。

纯文档/视觉交付可明确声明 `"validation": "inspection", "checks": []`，仍需要真实产物和独立审核报告，不能借此跳过代码任务应有的测试。技术检测不能代替视觉、听审或业务验收；这些检查范围写入审核报告与 acceptance。

使用 Python 3.11 或更新版本；下面 `workflow.py` 指本 Skill 的 `scripts/workflow.py`。STATE 指本次 `run.json`，ROOT 指实际任务项目。不要在命令里拼接未验证的用户文本。

```text
python workflow.py init STATE --root ROOT --spec SPEC.json
python workflow.py start STATE TASK --agent ACTUAL_WORKER_ID
python workflow.py submit STATE TASK --artifact RELATIVE_FILE
python workflow.py check STATE TASK
python workflow.py review STATE TASK --agent ACTUAL_REVIEWER_ID --report REVIEW.md --verdict pass
python workflow.py verify STATE TASK
python workflow.py finish STATE
```

这些是接口顺序示例；真实路径由主控传入。参数细节以 `python workflow.py --help` 及对应子命令 `--help` 为准。

## 2. 派发与监督

先核对宿主的实际工具契约。当前桌面若提供 collaboration，则使用 spawn_agent / send_message / followup_task / list_agents / wait_agent；其他宿主按其实际工具映射，不能假装存在某个 API。不要为了内部任务创建用户侧新聊天。

执行者简报至少含：任务目标、实际输入、可写路径、项目约束、明确验收标准、报告位置。不同时派两人修改同一路径；需要共享接口时先确定接口或设依赖。记录派发返回的真实身份，再 start。主控是状态文件的唯一写者。

等待期间继续可独立完成的整合工作；按有界等待观察运行状态、输出和消息。出现具体错误、反复同一失败或工具等待外部时处理原因，不无限重试。先判断 Agent 是否仍在工作，不能只因一段时间没输出就重新派发同一工作。

工具不能证明 worker 实际只写了 owns；主控还要检查 diff、新文件和范围外修改。隔离工作树在实际需要时使用。JSON 的身份和状态是合作协议，不防御拥有同等文件写权限的恶意 Agent。

## 3. 实际审核与修复

start 保存执行开始时的输入、规格和依赖证明；submit 在文件已经存在后检查这些基线未改变，再登记当前产物指纹。执行期间输入或依赖改变时，不把旧结果重新盖成新版本，需 repair 后重新 start。check 执行预先规定的命令并保存实际日志。主控另派独立 reviewer；报告至少包含：检查对象、对应验收项、实际执行/查看范围、缺陷及依据、仍未验证项、结论。交付物以当前文件为准，不能只读 worker 总结。

存在缺陷使用 `review ... --verdict fail`，进入 repair；技术检查失败或超时也进入 repair。先重新 start 保存本次执行基线，再交给执行者修改；修改完成后依次 submit、check、review、verify。每次 start 消耗一次执行尝试，默认上限 3；旧尝试和日志保留。达到上限说明具体失败原因与可继续方案，不把失败强行标 verified。

已审核或已验证后发生修改，使用：

```text
python workflow.py repair STATE TASK --reason "实际发生的变更或问题"
python workflow.py start STATE TASK --agent ACTUAL_WORKER_ID
```

重新走受影响任务的验收；依赖任务也要重核。状态检查会显示证据陈旧；最终 finish 会重新核验全部任务，不能因为此前曾成功就省略。检查命令修改了受审输入/产物时，也需要重新建立并审核当前版本。

review 和 verify 的身份检查只防止误填同一执行者；不同字符串不是独立审查证明，主控必须保留真实宿主派发记录。代码检查日志也只能证明那个命令实际运行，验收条件选得是否正确还需独立审查。

## 4. 外部等待与恢复

```text
python workflow.py wait STATE TASK --reason "视频生成结果未知，正在查询" --external-id PROVIDER_TASK_ID
python workflow.py resume STATE TASK --resolution "已查该 ID，任务完成并下载到实际路径"
python workflow.py status STATE
```

wait 保留任务及外部 ID；resume 必须写明实际核对结果，不等于允许再次付费提交。无法查询时保持 waiting_external，并完成其他可独立工作。无任务 ID 时保存工具回执和请求关联信息，说明未知状态，不编造 ID。

重新打开聊天后，核对 root、目标和本次运行，读取 status 与历史事件。verified 只有在当前指纹仍有效时可复用。正在执行的任务先核对宿主/外部状态；已消失的 worker 不能当作完成，按剩余预算恢复或明确失败。wait/resume 不重置执行基线；旧版记录缺少开始时的基线时保留其历史，重新执行与审核，不能补写一个假基线。

命令超时有失败证据；标准库进程超时不保证终止所有外部孙进程或远端任务。重试之前检查实际进程/外部任务，避免重复执行。

## 5. 视频与其他领域接入

视频继续使用原 pipeline。渲染前的 keep、背景与关键配置审核，和渲染后的实际成片听审/动态观看分为不同任务。把相关文件列为 inputs 或 artifact；旧 reviewed 布尔值不替代当前版本审核。保留原 source SHA、帧量化、主时轴和技术 QC。

任务粒度按独立验收划分，不为每个工具调用建立任务。UI 用实际页面/设计、关键状态及适用尺寸验证；PPT 用实际导出和版式；异步生成区分提交、终态、下载和内容质量。

## 6. 交付与改进

主控整合成果后 finish，交付实际文件、验证范围和剩余限制。保存本次证据和复盘，不删除唯一副本。临时工作区已被 Git 忽略，公开文档只放通用摘要和无私密数据的验证样例。

在运行目录记录 `retrospective.md`：真实问题 → 原因证据 → 最小规则修正 → 回归场景 → 实际结果。候选规则通过独立检查后在已授权项目采用；原规则和验证结果可由 Git 回退。尚未运行的回归明确写待验证，不凭一次成功宣称系统已经长期自我优化。
