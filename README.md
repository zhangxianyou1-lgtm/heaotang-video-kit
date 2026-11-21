# 和奥堂视频制作流程包（GitHub 五大视觉模块终极全规则通用版）

2026-11-17｜**GPT 语义总导演 ＋ 五大视觉模块动态配比 ＋ 多智能体防偷懒工业体系**：
1. **`D` 真实人物/新闻/公开纪实实证**（点名真事即强制 ≥3 真实来源择优截取，禁 AI 生图假冒）；
2. **`R` 系统级高逼真客户软件仿真录屏**（`client-scene-recreation` 以假乱真交互录屏，跨页单号金额闭环）；
3. **`A` Claude 零预设风格 · 并行子智能体深雕 ＋ 独立盲审动画与混音**（经实测单段 1900–3100 行多媒介原创代码、词级 0 帧误差 SFX）；
4. **`G` 超现实 3D 奇观视频**（巫师三母本 ＋ `0.0s` 首帧即奇观 ＋ 同画幅因果接触双闭环 ＋ `MiniMax-H3` 单向物理变化）；
5. **`P + PIP` 全屏真人与知识点专门开口小窗双边铁笼**（全屏 `15%–35%` 防失踪防干讲 ＋ 知识点 `≥3` 处 `PIP` 开口 `y≤1420` 同步嵌回 5 分钟原片 ＋ 官方 4 支片头/4.5s 总 Logo 智能卡位 ＋ 总装 `-16 LUFS` 响度标准化）。

[最高执行规范](R6.1_视觉风暴与零穿帮规范.md) · [五大视觉模块与多模型压榨指南](多模型性能压榨指南_GPT_MiniMax_Claude.md) · [一键启动词](START.txt) · [完整制作流程](tutorial/02_收到视频后的完整流程.md) · [原片粗剪流水线](pipeline/README.md)

---

## 快速开始

1. 克隆或解压本仓库（将官方片头库 `片头与栏目包装_20261029` 放在同级或本地忽略目录 `branding/` 下）。
2. 在 Codex 工作区打开本目录，复制 [START.txt](START.txt) 发送，附上**本期 5 分钟绿幕原片 ＋ 文稿**（或仅提供**新文稿**先出排期方案）。
3. 模板位于 [tutorial/03_任务与验收模板/](tutorial/03_任务与验收模板/)（含生成方案模板、Claude 并行子智能体任务模板、整期方案 JSON 模板与验收清单）。

---

## 自检与单期校验命令

```powershell
# 仓库工具链与五大模块模板全套自检
python tools/check_r60_plans.py
python tools/check_r_sim_clean.py --self-check
python tools/align_sfx_words.py --self-check
python pipeline/test_pipeline.py

# 录屏前扫描 R 类仿真软件前端源码（拦截“交互演示/示例数据/演示账号/原稿口径/无真实支付”等叠甲穿帮词）
python tools/check_r_sim_clean.py "jobs/本期名称/sim_ui/"

# 校验新一期方案 JSON（自动拦截 P<15%、P>35%、漏开PIP小窗、D槽少于3真实候选、G提示词<200字或污染）
python tools/check_r60_plans.py --plan "jobs/本期名称/plan.json"

# 正式混音前强制核验词级 SFX 已全部对齐
python tools/check_r60_plans.py --plan "jobs/本期名称/plan.json" --require-aligned-sfx
```
