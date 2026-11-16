# 分段口播前处理 R6.1（沿用 R5.4 验证底盘）

这是已使用的 FFmpeg 绿幕合成与 30fps 剪点算法的可携带版本。Codex 负责语义剪辑和审看，Python负责提取、候选静音剪点、合成、音频及时轴交接。**它不会把“静音剪好了”当成“口误全删了”。** 后半段沿用 `../tutorial`，同一窗口接续。

## 日常使用

下载根目录 R5.4 ZIP，解压并在 Codex 打开整包。粘贴 `START.txt`，附当期分段视频、最新文稿和包装素材。Codex读取根目录AGENTS完成整个流程，用户不用手工填JSON或反复在两个聊天间搬视频。

仍需要 Python 3.11+、FFmpeg/ffprobe（PATH可用）及 faster-whisper：

```powershell
python -m pip install -r pipeline/requirements.txt
```

模型默认 large-v3-turbo，第一次使用需要联网下载；已有模型可在 job.json 的 model 填本机模型目录。普通CPU用int8；GPU能力须实际检查后配置。包不含模型、FFmpeg、API凭据或其他平台登录状态。

## 给执行者的命令

把 job.example.json 复制为本期 job.json。所有输入、script、work、可选background路径相对于job.json；sources是**已核对的语义顺序**。示例的input仅占位，不含真人素材。不要在公开仓库提交本期job。

```powershell
python pipeline/pipeline.py preview jobs/本期/job.json --source 1 --start 2
python pipeline/pipeline.py prepare jobs/本期/job.json
# Codex审听审看并修改edit.json，确认语义及背景审核字段后继续：
python pipeline/pipeline.py render jobs/本期/job.json
python pipeline/test_pipeline.py
```

首次prepare不会覆盖已有edit.json。需要重做转录请用新work目录，原稿和审好的剪点保留。render按本期edit重算全部片段，避免复用失效缓存。preview在审核之前可运行。

### 剪辑清单

`edit.json.sources`保持与job来源顺序一致，每个来源的keep是保留的源秒数区间，按时间递增、不重叠，如 `[[0.3,12.4],[14.1,26.8]]`。notes记删除原因；空keep表示明确不用该来源。review_notes记录实查方法、结果和疑点，不写空泛“通过”。只有真正审完才由Codex置两个审核字段为true，无需用户重复确认。程序检查文件哈希防止审核后素材被替换。

静音候选：-35dB、至少0.8秒，每侧留0.21秒；ASR首尾另留语音余量。阈值可按底噪调整。它可能误判轻声/音乐，必须审听。口误/结巴/重说/多余动作由Codex依据全稿、字级时间和实际影音修正，不自动删所有“嗯”和相同词。

### 固定背景和画质

`assets/studio-medium.png`是这次对话已选定的日光书架/打印机背景，已带中度柔化。medium直接用它；heavy在720×1280合成尺度附加sigma14、3步高斯模糊，沿用已交付成片参数。这里明确是现有高斯柔化配方，并非光学散景模拟。

仅支持与已验收素材相同的**9:16绿幕口播**。色键默认0x5fa557/0.055/0.025，alpha柔化0.35，去绿溢色，前景增益0.97偏移1；它不是自动重打光。新曝光先看试片再调参数。真实桌面若被误抠或背景前景桌子露出，必须调整遮罩/构图，不能直接交付。非绿幕先采用稳定抠像方案；本工具会拒绝未确认的非绿幕输入。

合成内部沿用720×1280，输出1080×1920、30fps、H264/AAC；不是原生全程1080处理。保留源音频，切口4毫秒淡入淡出，视频不变速。遇到真实缺帧先审原片，用补片或合法剪点处理，不假称模糊滤镜能解决卡顿。

### 输出与下一步

- base.mp4：合成后的顺畅基准片。
- narration.wav：从基准片提取的完整原声，未增加BGM；原片已有环境声不会被冒称干声。
- timeline.json：源入出点、剪后时轴、帧数、背景哈希和实际配置。
- words.json：剪后字级ASR候选时轴，后续字幕仍须校对。
- qc.json / qc.log：完整解码、冻结/黑帧/两秒静音扫描及帧数音画差检查；视觉和听审另行记录。
- parts/review_*：每个剪点首尾抽帧，须结合动态查看及试听。
- handoff-input.zip：仅完整音频、字级时间和NEXT；它是Claude交接的输入，**不是已写好的动画/BGM任务包**。

基准片通过后，Codex立即按根AGENTS和tutorial选段、准备并执行后续任务。外部动画和生成服务没有被此脚本自动调用；需要当前环境工具、账号、授权及回交。工具缺失时说明卡在哪一步，不能声称已经得到完整包装成片。
