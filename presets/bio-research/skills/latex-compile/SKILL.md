---
name: latex-compile
description: 用 TinyTeX 编译 LaTeX 论文为 PDF：latexmk/xelatex 工作流、中文支持（ctex/xeCJK，已装）、缺失宏包安装、常见报错处理。
whenToUse: 编译 .tex 文件为 PDF、处理 LaTeX 报错、安装缺失宏包时
---

# LaTeX 编译（TinyTeX）

## 环境（2026-09-29 实测，已实跑编译通过）
- **TinyTeX（TeX Live 2026）已装**：`F:\dsh\_tools\TinyTeX\bin\windows`，已在**用户 PATH** 上，
  `xelatex` / `latexmk` / `pdflatex` / `tlmgr` 直接可用。（DSH 进程若在安装前启动，需重启 DSH
  才会继承新 PATH；没有就写全路径。）
- **中文支持已装**：`ctex` / `xeCJK`（连同 47 个依赖包），中文论文直接用 `ctex` 文档类即可。
- pandoc 的 LaTeX 模板依赖也已装：`caption` / `csquotes` / `microtype` / `parskip` / `soul` / `upquote`；
  TinyTeX-1 自带 booktabs / geometry / hyperref / natbib / amsmath / graphicx。
- ⚠️ 本机**没有 G: 盘**（只有 C/D/E/F）——历史上写的 `G:\dsh\_tools\TinyTeX` 在这台机器上从来不存在。

## 常用编译命令
- `latexmk -xelatex main.tex`（推荐，自动处理多轮编译与参考文献）
- `xelatex -interaction=nonstopmode main.tex`（单轮，快速看错误）
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
- 报错 `! LaTeX Error: File 'xxx.sty' not found` 时：`tlmgr install xxx`（用户级，无需管理员）
- tlmgr 需要网络（DSH 沙箱内可能需临时授权），默认仓库已设为 tlnet 镜像
- TinyTeX-1 已含大部分常用包（article/amsmath/geometry/graphicx/hyperref/booktabs/natbib 等）；
  中文（ctex/xeCJK）与 pandoc 模板依赖（caption/csquotes/microtype/parskip/soul/upquote）也已补齐
- 装新包后重新编译

## 常见问题
- 多轮编译：目录/交叉引用需要编译 2–3 次；`latexmk` 自动处理
- 编译中断留 `.aux/.log/.out`：交付前清理（或加 `.gitignore`：`*.aux *.log *.out *.toc *.bbl *.blg *.fls *.fdb_latexmk`）
- 大文件报错定位：看 `.log` 里第一个 `!` 之后的上下文
- 字体问题：`\usepackage{fontspec}` 后 `\setmainfont` 指定系统字体

## 输出
- 默认输出到源文件目录；交付时给 `.tex` 源 + 编译出的 `.pdf`
- 期刊模板：把期刊提供的 `.cls/.sty` 放到项目目录再编译
