# Atria Demo 共创计划 - 已确认事实（调研中）

## 官方筛选标准（问卷原文，2026-09-28 创建）
五维评分：Demo创意、完成可行性、展示效果、与Atria-Dawn能力的契合程度、参与者过往经验
特别欢迎：「你来自某个专业领域、有一个只有这个领域的人才会想到的 Atria-Dawn 用法」
期待：「做出一些我们自己都没想到的东西」
不要求参与者一定有成熟的 Demo 开发经历

## 交付物要求
- 邮件主题：[Atria Demo共建] 作品名称 - 姓名或团队名
- 压缩包：AtriaDemo_作品名称_姓名或团队名.zip
- 压缩包内：Demo说明.md + Demo录制视频
- 邮件正文附 GitHub 仓库链接（源码不入压缩包）
- 第一批截止：2026-10-03 23:59
- 邮箱：atria_ai@163.com

## 技术报告精读结论（arXiv 2609.15818）
- 训练哲学：Verifiable Experience Pipeline
- 经验内化四要素：任务+轨迹+产物+验证证据 同时成立
- 三原则：模型内化经验 / Harness组织过程 / 环境判定后果
- 产出必须落到五类可观察证据之一：
  1) 成功运行的实验 2) 可复现的指标 3) 真实生成的文件 4) 可检查的模型 5) 有来源支撑的报告
- 能力四维：Discovery / Creation / Delivery / Cybersecurity
- benchmark 16项中5项第一：AutomationBench、BFCL v4、CyberGym、DeepSearchQA、BrowseComp
- 领先集中在：工具调用、深度检索、网络安全
- 短板（官方自认）：长程专业交付（SWE-bench Pro/Terminal-Bench/GDPval/JobBench）落后 Claude Opus 5
- 模型纯文本输入（accepts text input only），256K上下文，单次输出上限64K
- 正式版路由确认：调 Atria-Dawn-Preview 回显 Atria-Dawn

## 竞争情报
- 全网讨论极少：LINUX DO 4个薅羊毛帖，B站/小红书/V2EX/知乎无人晒参赛
- 问卷 answer_count=0，首批窗口竞争极小
- 团队约2/3是高校学生，年轻团队

## 环境验证（本机已实测）
- Atria API 可调通（discovery-api.intern-ai.org.cn，回显 Atria-Dawn）
- akshare 0.1秒拉真实A股日线（平安银行 57根K线）
- manim 渲染通过（HelloCube.mp4，ffmpeg可用）
- Python 3.12 venv 在 /home/ubuntu/atria/.venv
- 本机无A股历史数据（research-finai那批已删除）

## 外部调研补充
- manim_skill（AI agent生成3Blue1Brown风格动画）GitHub 1087星，2026-01-22创建——该模式已被验证受欢迎
- ManimTrainer 论文（arXiv 2604.18364）：LLM+manim 的渲染成功率研究，Qwen3 Coder 30B 达 94% RSR


## 补充调研结论（3路重跑结果）

### 金融 demo 评分卡（关键风险提示）
传播端优势：A股重返4000点、2.5亿股民、「AI炒股」已成短视频流量密码
  （北京日报统计30条热门AI炒股视频单条点赞可超5800，评论满是'怎么弄''能教吗'）
  B站/知乎'AI实盘炒股大赛'内容自带爽文剧本（中国模型包揽冠亚军、GPT-5亏损垫底）
评审端软肋（核心风险）：非金融背景技术评委无法验证策略有效性
  市场充斥'AI股神'翻车证据：记者同一指令问三次结果无一重合；'AI推荐10只股票9只下跌'
  评委会下意识把你的demo与这些负面案例关联
监管端：2026证监会主席吴清陆家嘴论坛明确表态'严查借科技之名蹭热点、炒概念'
  → 绝对不能做成'AI选股/荐股'，必须定位为研究工具

### 视频呈现形式结论（翻车案例警示）
两派路线：
- 真实录屏+真人解说：Devin、OpenAI Operator、Anthropic computer use
  （终端/浏览器实画面、20秒-2.5分钟核心片段、有配音无炫技音乐）
- 电影级后期包装：Manus、Google Gemini、国内发布会
对技术评审，真实录屏明显更受认可。造假翻车代价极高：
- Gemini 2023宣传片被爆非实时拼接，被BBB判误导下架
- Devin Upwork演示被逐帧质疑造假，真实评测仅3/20任务通过，估值$350M→$2B后口碑反噬
- Optifye.ai的YC发布演示因表演成分过重被群嘲
→ 结论：用真实录屏，不用后期包装

### 同类活动规律
manim_skill（AI生成3Blue1Brown风格动画）1087星验证该模式受欢迎
ManimTrainer论文：LLM+manim渲染成功率94%


## 第二批调研：三个关键修正

### 修正1：范围必须收窄到「一件事端到端做完」
JetBrains 评委原话：最常见的失败是「五件事各做一半，没有一件事端到端 work」
我之前推的「量化复盘官」覆盖 Discovery→Creation→Delivery 三维 = 范围太大，有失败模式风险
→ 必须砍到一条流水线，一个核心场景

### 修正2：「策略验证」是评委无法验证的黑盒 = 唯一致命选择
金融评分卡结论逐字：「纯策略型 demo 在非金融评委面前约等于'不可验证的黑盒'，
  是这评分卡上唯一致命的选择」
评委无法判定 PEAD 漂移是否成立 → 你的策略结论对他们是不可分辨的真假
且深圳证监局2026直接点破「篡改回测数据伪造盈利假象」是行业污点
→ 绝不能以「策略收益/策略成立」为卖点，必须以「引擎/过程本身」为卖点
→ 杂交策略：用直觉可验证的形式包装金融内核

### 修正3：领域专精 > 技术深度（跨所有平台的第一名规律）
Anthropic 两届 hackathon 第一名：医生转行开发者(Medkit)、设计师(Tekton)
  律师和医生在 Anthropic SF 场击败职业开发者
官方获奖叙事 =「这个人是谁、他从哪来、他为什么是唯一会做这件事的人」
→ 用户的量化背景必须放在叙事核心，不是侧注

### 其余高价值规律
- 可交互 > 纯视频（但本比赛交付物规定是视频）
- 90秒内必须有「现在居然可能了」对比时刻，不做功能巡览
- 叙事必须来自亲历痛点：让评委共享你世界里的挫败感
- 技术深度翻译成可核对证据（Tekton 3D构件可点击溯源、Sim Francisco 0.4%误差）
  评委要的不是「我管线多复杂」而是「我怎么知道它没瞎编」
- 能力契合：演示主轴必须是「只有本模型才做得到」
  Atria 第一的 benchmark：工具调用BFCL、深度检索DeepSearchQA/BrowseComp、自动化AutomationBench
- 真实录屏+诚实剪辑（翻车案例：Gemini/Devin/Optifye）
- 保留1-2个agent小失误/自我修正镜头，可信度比完美高一倍
- 视频 60-90秒，1080p横屏，绝不超过2分钟（评委只看前30秒）
- 子agent已验证 ffmpeg 录屏/剪辑/字幕流水线（make_demo.sh + storyboard.md）
- 社会价值是官方主动加分杠杆（Google/Anthropic 都给了医疗无障碍）
