---
name: latex-compile
description: 用本机 TinyTeX 编译 LaTeX 论文为 PDF：latexmk/xelatex 工作流、中文支持（ctex/xeCJK）、缺失宏包安装、参考文献与常见报错处理。
whenToUse: 编译 .tex 文件为 PDF、处理 LaTeX 报错、安装缺失宏包时
---

# LaTeX 编译（TinyTeX）

## 环境
- TinyTeX 便携发行版（推荐从 https://github.com/rstudio/tinytex-releases/releases 下载 TinyTeX-1-windows，解压后 `bin\windows` 下有 `xelatex.exe` / `latexmk.exe` / `pdflatex.exe` / `tlmgr.bat`；下文以 `<TINYTEX>` 代指解压目录，按本机实际路径替换）
- 中文支持：先 `tlmgr install xeCJK ctex`（本技能已按已装中文支持编写），中文论文直接用 `ctex` 文档类
- 直接调用全路径使用：`& "<TINYTEX>\bin\windows\xelatex.exe" ...`
- 常用编译命令（Windows PowerShell）：
  - `& "<TINYTEX>\bin\windows\latexmk.exe" -xelatex main.tex`（推荐，自动处理多轮编译与参考文献）
  - `& "<TINYTEX>\bin\windows\xelatex.exe" -interaction=nonstopmode main.tex`（单轮，快速看错误）
  - `pdflatex main.tex`（无中文需求时）

## 中文论文
- 用 `ctex` 文档类（`\documentclass[UTF8]{ctexart}` / `ctexrep` / `ctexbook`），内部含 xeCJK，无需额外配置字体
- 或用 `\usepackage{xeCJK}` + `\setCJKmainfont{SimSun}` 等手动指定中文字体
- 编译必须用 `xelatex`（pdflatex 不支持中文）

## 参考文献
- 简单引用：`thebibliography` 环境（无需外部工具）
- BibTeX：`.bib` 文件 + `\bibliography{refs}`；`latexmk` 会自动跑 bibtex
- biblatex：`\usepackage[style=nature]{biblatex}` + biber；用 `latexmk -xelatex -bibtex` 或 `-biber` 参数

## 缺失宏包
- 报错 `! LaTeX Error: File 'xxx.sty' not found` 时：`& "<TINYTEX>\bin\windows\tlmgr.bat" install xxx`（经 cmd 调用）
- tlmgr 需要网络；默认仓库可在安装时设为国内镜像：`tlmgr option repository https://mirrors.tuna.tsinghua.edu.cn/CTAN/systems/texlive/tlnet`
- TinyTeX-1 已含大部分常用包（article/amsmath/geometry/graphicx/hyperref/booktabs/natbib 等）
- 装新包后重新编译

## 常见问题
- 多轮编译：目录/交叉引用需要编译 2–3 次；`latexmk` 自动处理
- 编译中断留 `.aux/.log/.out`：交付前清理（或加 `.gitignore`：`*.aux *.log *.out *.toc *.bbl *.blg *.fls *.fdb_latexmk`）
- 大文件报错定位：看 `.log` 里第一个 `!` 之后的上下文
- 字体问题：`\usepackage{fontspec}` 后 `\setmainfont` 指定系统字体

## 输出
- 默认输出到源文件目录；交付时给 `.tex` 源 + 编译出的 `.pdf`
- 期刊模板：把期刊提供的 `.cls/.sty` 放到项目目录再编译
