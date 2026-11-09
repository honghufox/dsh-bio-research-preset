# 审稿报告模板（复制后用）

```markdown
# Reviewer report — <稿件编号> — <短标题>
Reviewer: <匿名/编号>  |  Date: <YYYY-MM-DD>  |  Recommendation: <Accept / Minor / Major / Reject>
Confidence: <1–5>（1=超出本人专长，5=本领域核心方向）

## 1. Summary of the submission（3–5 句，证明读懂了）
本研究针对 <问题> ，使用 <模型/设计/样本> ，主要发现是 <结果，带关键定量> 。
作者据此提出 <核心结论> 。稿件的新颖之处在于 <相对已发表工作的差异> 。

## 2. Overall assessment（3–6 句）
- 优点：<最多 2 条，具体到证据，不写「well written」这类空话>
- 核心缺陷：<1 句定性，说明它决定了档位>
- 与近期文献的关系：<最接近的 1–3 篇工作，本文增量在哪>

## 3. claim–evidence 对齐表（可选，但强烈建议）
| # | 稿件 claim | 证据位置 | 统计量 | 强度 | 判定 |
|---|---|---|---|---|---|
| 1 |  | Fig / Table / L |  | 强/中/弱 | 支持/部分/不能判定/超出设计 |

## 4. Major concerns（编号，3–8 条；每条四要素齐备）
### M1. <一句话标题：缺什么>
- 问题：<作者做了什么/没做什么>
- 位置：<Fig 2C；L203–210；Methods p.7 第 2 段>
- 为何重要：<不解决会怎样——结论是否倒、可否外推、是否影响其他图>
- 建议：(a) <最小可行修复> 或 (b) <可接受的替代方案：降级 claim / 补分析 / 补实验>
- 若无法完成：<可接受的降级表述>

### M2. …
（重复上述结构）

## 5. Minor concerns（编号，可直接执行）
- m1. L45：「significantly increased」未给统计量与 n；请改写为「increased by 1.8-fold (Fig 1B; p=0.021, n=4)」。
- m2. Fig 3 legend 未定义误差棒；请注明 ±SD 与 n。
- m3. 参考文献 [17] 与正文所述结论不符；请核对或替换。
- m4. …

## 6. Data and code availability
- 原始数据：<满足 / 需补充 accession 与审稿期访问 token / 「upon request」不符合本刊政策>
- 代码与分析参数：<满足 / 需补充仓库链接与版本表 / 缺随机种子>
- 材料共享：<细胞株/质粒/品系是否可提供，MTA 是否说明>

## 7. Ethics and reporting guidelines
- 适用门控：<ARRIVE 2.0 / CONSORT / STROBE / PRISMA / MIQE / 无>
- 缺失项：<编号列表，如 ARRIVE 关键项 2、3、4 缺失>
- 伦理：<批号是否给出、是否与实验时间匹配、知情同意是否说明>

## 8. Figures and images
- 图注完整性：<缺哪些要素>
- 需提供的原始材料：<未裁剪 Western blot 全膜 / 原始显微图 / 原始数据表>
- 可疑重复：<Fig X 与 Fig Y 的某泳道相似，请提供原始文件以排除排版错误>（**不作指控**）

## 9. Suggestion to the editor（机密，可选）
<是否值得给返修机会、需要哪类第三方审稿人、是否建议核查图像>

## 10. Recommendation
<Accept / Minor revision / Major revision / Reject>，理由 2 句：
- 支持录用的核心证据是 <…>
- 阻断录用的问题是 <…>，属于 <设计层 / 分析层 / 报告层>，其中 <设计层> 无法通过文字修订弥补。
```

## 写作硬规则
1. 每条 major 必须能回答：「如果作者不做，结论会倒吗？」答不出就降为 minor。
2. 每条必须带可定位坐标，禁止「文中某处」「相关图表」。
3. 禁止形容词替代论证：不写「数据薄弱」，写「n=2 无统计检验」。
4. 语气：对事不对人；用「the manuscript」「the authors report」，不用「you」。
5. 建议要给选项（补实验 / 补分析 / 降级 claim），只给一种会逼作者硬扛。
6. 全部 minor 控制在 12 条内；超过说明你在挑格式而非审科学。
