---
name: document-output
description: 科研文档输出：pandoc 把 Markdown 转 Word/PDF（已装，含中文 PDF）、python-docx 生成与编辑 docx、投稿用 Word 文档的格式规范。
whenToUse: 把 Markdown/LaTeX 转成 Word 或 PDF、生成/编辑 .docx、准备投稿文档时
---

# 文档输出（Word / PDF）

## 环境（2026-09-29 实测，链路已实跑验证）
- **pandoc 3.11 已装**：`%LOCALAPPDATA%\Pandoc\pandoc.exe`（Windows 用户级安装），已在**用户 PATH** 上，
  直接写 `pandoc` 即可。（DSH 进程若在安装前启动，需重启 DSH 才会继承新 PATH。）
- **LaTeX 已装**：TinyTeX（TeX Live 2026）在 `F:\dsh\_tools\TinyTeX\bin\windows`，同样在用户 PATH 上；
  中文宏包 `ctex` / `xeCJK` 与 pandoc 模板需要的 `caption` / `csquotes` / `microtype` /
  `parskip` / `soul` / `upquote` 都已装 —— **pandoc 可以直接出中文 PDF**（详见 latex-compile 技能）。
- Python `python-docx` 1.2.0 已装：`import docx`
- `python-pptx` 1.0.2、`openpyxl` 3.1.5 已装；Office 格式互转走 office-* 技能
- ⚠️ 本机**没有 G: 盘**（只有 C/D/E/F）。历史上写的 `G:\dsh\_tools\...` 在这台机器上从来不存在，
  不要再引用。

## Markdown → Word
```
pandoc paper.md -o paper.docx
```
- 期刊格式：先准备一个 `reference.docx`（用 Word 设置好样式），然后
  `pandoc paper.md -o paper.docx --reference-doc=reference.docx`
- 数学公式：`pandoc paper.md -o paper.docx --mathml`（Word 原生公式）
- 表格/图片：标准 Markdown 表格与图片语法即可；图注自动跟随

## Markdown → PDF（TinyTeX 已装，中文实测可用）
```
pandoc paper.md -o paper.pdf --pdf-engine=xelatex -V CJKmainfont="Microsoft YaHei"
```
- 中文 PDF：**必须**指定 `-V CJKmainfont=`（否则 CJK 字符报 missing character）；
  `"Microsoft YaHei"` / `"SimSun"` 都可以
- 学术模板：`--template` 指定期刊模板；`-V geometry:margin=2.5cm` 调页边距
- 若报 `File 'xxx.sty' not found`：`tlmgr install xxx`（用户级，无需管理员）

## python-docx（程序化生成/编辑 Word）
```python
import docx
doc = docx.Document()
doc.add_heading('标题', level=1)
doc.add_paragraph('正文文本')
table = doc.add_table(rows=3, cols=2)   # 表格
table.style = 'Table Grid'
doc.save('output.docx')
```
- 常用：加标题/段落/表格/图片（`doc.add_picture('fig1.png', width=Inches(6))`）
- 修改既有 docx：打开 → 遍历 `doc.paragraphs` 替换文本 → 保存

## 投稿规范
- 多数期刊接受 Word（.docx）：正文 + 图表分开或合并提交，看期刊指南
- 图表按 `Figure 1. 标题` 编号，引用处写 `(Fig. 1)`；表格用三线表风格
- 交付时确认：字体（Times New Roman / 宋体）、行距（通常双倍）、页边距（2.5cm）
- 图表分辨率 ≥300 dpi；矢量图（SVG/PDF）直接嵌入 Word 效果最好

## 流程建议
- 写作用 Markdown（版本管理友好），投稿前用 pandoc 转 docx
- 需要 PDF 时：Markdown →（pandoc）→ PDF；或直接用 LaTeX 模板（见 latex-compile 技能）
