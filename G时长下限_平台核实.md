# H3时长与完整镜头修订依据

2026-11-17。此次核对标准MiniMax H3的[官方模型与duration参数](https://platform.minimax.io/docs/api-reference/video-generation-v2-create)：标准H3接受4–15整数秒，H3 Max接受5–15整数秒。只读文档/模型参数核实，未提交生成测试。

先前LibTV get_model记录：Seedance 2.0（star-video2）generate/interpolate均为4–15秒；AutoTake（lib-cinema）均为5–15秒，历史空椅样片请求为6秒。这两项不能代替H3参数。

用户外审修订后，项目采用标准H3：独立G至少4秒、常用4–5.5秒；完整主变化可使用6或7秒并写明理由。九期首镜统一6秒完整G，取消为凑槽而设的2秒代码动画尾态接力。8–11秒可拆同源双G；短R/A要有独立叙事。

H3请求为整数，4.5秒/5.5秒使用槽分别请求5秒/6秒。源入出点待实际产物检查后记录；不变速补时。精确中文和数字采用可控叠层，不依赖模型写字。正式提交前仍以当前入口对应型号/模式参数为准。
