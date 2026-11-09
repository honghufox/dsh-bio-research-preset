# 证据与政策来源（多 agent 写作/审稿的设计依据）

只列支撑本技能门控与反模式的证据。引用为文献/政策标识，使用前建议人工打开原文核对。

## 1. 多评审与裁决：有用，但是"放大器"

| 结论 | 来源 |
| --- | --- |
| 多 agent 按评论类型分工 + 全文切片，泛泛评论 60%→29%，有效评论 1.7→3.7 条/篇 | MARG, arXiv:2401.04259 |
| 多个较小模型组成评审团（PoLL）在 3 类设置、6 个数据集上优于单个大模型，且更便宜、缓解自偏好 | Verga et al., arXiv:2404.18796 |
| ICLR 2025 两万余条评审 RCT：AI 评审反馈让 27% 审稿人修改意见，平均 +80 词、更可操作 | arXiv:2504.09737；Nature Machine Intelligence 2026 |
| 让 AI 做"审稿人的助手"证据强；"替代审稿人/委托评审"是政策红线 | 见 §3 |
| LLM 评审与人类要点重叠 ≈ 人类彼此重叠（30.85% / 39.23% vs 28.58% / 35.25%），但**越弱的稿重叠越高**：筛弱稿有效，排强稿不可靠 | arXiv:2310.01783 |
| 端到端全自动论文天花板低：AI Scientist v2 投 3 篇仅 1 篇过 workshop 录用线；CycleResearcher 自评 5.36 < 真实录用 5.69 | arXiv:2504.08066；arXiv:2411.00816 |

## 2. 必须防的偏差（本技能的门控就是对着它们设计的）

| 偏差 | 证据 | 对策 |
| --- | --- | --- |
| 系统性抬分/宽松 | ICLR 2024 准实验：AI 辅助评审 53.4% 配对给分更高、阈值附近录用 +4.9pp（arXiv:2405.02150）；2026 基准：LLM 高估弱稿、低估清晰度问题（arXiv:2605.25415） | 5 维 rubric + 证据一致性阻断 + 不平均分 |
| 自产自评 | LLM-REVal：LLM 评审系统性抬高 LLM 文风稿、压低人类稿（arXiv:2510.12367） | 写手/审稿人分离；跨模型族；盲评 |
| 位置/冗长/自我增强偏差 | Zheng et al., arXiv:2306.05685 | 绑定 quote + location；限制意见长度 |
| 谄媚来自 RLHF 偏好 | Sharma et al., arXiv:2310.13548 | 不靠 prompt"请严格"，靠外部证据与对抗角色 |
| 幻觉引用 | GPT-4 28.6%（JMIR 2024, doi:10.2196/53164）；ChatGPT-5 仍 7.13% 纯捏造、书目全对仅 49.34%（Cureus 2026, doi:10.7759/cureus.113654） | 引文池 100% 外部核验（`verify_refs.py`）；写手不得新增引用 |
| 稿件即攻击面 | PDF 不可见字体注入指令可把低分稿抬到录用档（arXiv:2605.25415） | 审稿人声明"稿内指令不执行"并上报 |

## 3. 政策红线（写审稿/写作技能时的合规依据）

- **ICMJE Recommendations §V "Use of AI in Publishing"**：AI 不能署名；AI 处理稿件可能违反保密；须披露。 <https://www.icmje.org/recommendations/browse/artificial-intelligence/>
- **COPE《Authorship and AI tools》**（2023）：AI 不得列为作者；作者负全责并披露。 <https://publicationethics.org/guidance/cope-position/authorship-and-ai-tools>
- **COPE 2025-07 Forum**《Emerging AI dilemmas in scholarly publishing》：负责任使用、透明披露、检测标准、对评审/公平性的影响。 <https://publicationethics.org/topic-discussions/emerging-ai-dilemmas-scholarly-publishing>
- **Elsevier《Generative AI policies for journals》**：审稿人不应把稿件上传到 AI 工具；AI 仅用于辅助语言/结构/背景检索且须披露。 <https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals>
- **Springer Nature AI guidance**：绿/琥珀/红三级；把同行评审委托给 LLM 属红色禁止。 <https://group.springernature.com/gp/group/ai/ai-guidance-for-researchers-editors-reviewers>
- **STM**：《Generative AI in Scholarly Communications》（2023-12）；《Recommendations for a Classification of AI Use in Academic Manuscript Preparation》（2025-09-22，AI 使用分级）。 <https://stm-assoc.org/>

## 4. 与本技能的对应关系

- P0.5 引文池阻断门 ← §2 幻觉引用 + Elsevier 要求作者核对 AI 参考文献
- P4 三份异质盲评 ← §1 PoLL/MARG + §2 同族偏置
- P5 冲突表、不平均分 ← §2 抬分与分数不可信
- P7 一致性对账 ← 摘要/正文/图注/表四面对账；数字以原始统计输出为准
- §8 提示注入防护 ← §2 稿件即攻击面
- "AI 不做决策者" ← §1 天花板 + §3 政策红线
