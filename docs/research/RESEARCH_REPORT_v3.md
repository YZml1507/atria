# Atria Demo 方向调研报告 v3（全网×成本×传播数据）

## 服务器实测（这是所有决策的底线）
4核/3.6G内存/无GPU/出网14MB/s
- manim 1080p60: 6秒场景12.7秒，峰值1.1G → 可行
- ffmpeg: 15秒视频17秒，内存150M → 可行
- edge-tts: 2.1秒生成31秒语音，免费 → 强推
- Remotion: 内存1638M占63% → 近OOM危险
- Chromium截图: 2.5秒/帧，90秒视频需112分钟 → 不可行
- MusicGen: 需3G显存 → 出局
- GitHub Actions 公开仓免费 4核16G（本机4倍）

## 交付物真相
= 视频 + Demo说明.md + GitHub仓库
不要求实时在线服务。上首页展示的是视频和仓库。

## 2026 火爆demo四类（有播放量数据）
1. AI失控实况：Inside AI 560万播放；Bottleneck亏损$447 HN 384点
2. AI解开未解之谜：Claude 44分钟破370年密码（176K tokens，个人可复现）
3. AI科学发现：Anthropic 950代理21小时发现类CRISPR酶（HN 414点）
4. AI情绪短片：《纸手机》2.3亿曝光央视转发；3天2人
5. AI野生IP：咕咕嘎嘎30天15亿播放

## Manus 验证的 ROI 真理
2分钟无剪辑屏幕录制：X 20小时破100万播放，9个月1亿美元ARR
= 一两分钟真实任务屏幕录制是 ROI 最高形式
对立面：Gemini 2023宣传片因剪辑造假被下架

## Atria 官方审美（直接取证）
- 官方X强调 Verifiable/Reproducible/Controllable
- 真实可复现artifact > 漂亮宣传片
- Atria GitHub 553星，国内零讨论 = 蓝海

## TOP 3 方向
1. 让Atria当场解开一个真实谜题（公开档案：天文/古籍/密码）
   - 复刻Claude破370年密码路线，成本极低传播极高
2. 让Atria在真实数据流里做出首次发现（科学档案）
3. Manus式一两分钟无剪辑真实任务录屏（成本最低）

## 弃用
- 直播工作台（需实时服务+浏览器渲染，本机不行）
- Three.js粒子（EGL竞态，无显示器无法验证）
- Canvas2D出视频（Chromium截图2.5秒/帧）
- AI生成配乐（MemoryGen需3G显存出局）
