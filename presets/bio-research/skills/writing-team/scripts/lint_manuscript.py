#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lint_manuscript.py — 离线稿件一致性体检（writing-team P6 门控 G2/G4/G5 的机械化部分）。

纯标准库、不联网、单文件可运行；中文与英文稿件均可处理。只管"机械可判定"的一致性，
文学质量、论证强度、事实正确性不在本脚本职责内（那属于 review 环节）。

用法
----
    python lint_manuscript.py --input <稿件.md|稿件目录> [--refs <refs.md|refs.bib>]
                             [--config <lint-config.json>] [--figures <图片目录>]
                             [--out md|tsv] [--max-findings N] [--sort location|severity|rule]
    python lint_manuscript.py --selftest          # 内置样例回归，0=通过 2=失败
    python lint_manuscript.py --list-rules        # 打印规则表

退出码
------
    0  未发现 error（warn / info 不影响退出码）
    1  存在 error（阻断级：交叉引用/引用闭环/统计硬错误/过强措辞等）
    2  参数/读取/配置/SELFTEST 失败

规则（每条输出 error/warn/info 三级 + file:line + 片段）
-------------------------------------------------------
R1 交叉引用完整性  正文 `Figure 3` / `Fig. 3` / `图 3` / `Table 2` / `表 2` 是否有对应图注/表头；
                   反向：定义了但从未被引用；重复定义。
R2 缩写            2–10 位全大写 token、中文括号缩写：首次出现是否给全称；文末缩写表是否被当作
                   "已定义"（默认仍告警：首次使用早于缩写表）；重复定义；高频缩写未在 style 登记。
R3 标题与层级      `#` 层级跳级、编号不连续/回退/重号、多级标题缺编号、游离加粗标记 `**。**`。
R4 统计报告        `P = 0.000`、只给 `P < 0.05` 无精确值、`n=` 段无统计方法、`±` 无样本量、
                   `SD/SEM` 未声明。
R5 过强措辞        英语 prove/confirm/demonstrate/cause、`significantly` 无统计量；
                   中文 证明/证实/导致/必然/确证；按 study type（observational/cell/animal/…）分级。
R6 引用闭环        编号制：正文最大编号 > refs 条目数(error)、引用了不存在的条目、编号跳号、未被引用条目；
                   著者-年制（本仓库稿件实际用法）：正文 `（Khan et al 2024）` / `He et al（2026）`
                   是否能在 refs 中找到、年份是否一致、refs 未引用条目。
R7 跨节重复        连续 ≥8 个英文词 / ≥12 个中文字符 的片段在 ≥2 个"节"出现（复制粘贴信号，info）。
                   无小节标题的单节文件退化为"段间重复"。
R8 术语一致        config.synonyms 组内混用（warn）；同一英文术语连字符/大小写不一致（info）。

配置 lint-config.json（全部可选）
---------------------------------
    {
      "study_type": "observational" | "cell" | "animal" | "human_rct" | "mixed" | "unknown",
      "synonyms": [["全谷物", "whole grain"], ["膳食纤维", "dietary fiber"]],
      "registered_abbreviations": ["ALA", "EDA", "C3G"],   // style-guide 已登记缩写
      "abbreviation_whitelist": ["SD", "SEM", "CI"],        // 追加白名单
      "overclaim": {
        "english_causal": ["prove"], "english_demonstrate": ["demonstrate"],
        "english_cause": ["cause"], "chinese_causal": ["证明"],
        "chinese_soft": ["提示"], "replace_defaults": false
      },
      "dup_min_latin_words": 8, "dup_min_cjk_chars": 12,
      "max_unused_refs": 20,
      "refs_style": "auto" | "numeric" | "author-year" | "bib",
      "citation_strict": false,          // true: 著者-年制未匹配 refs 也升级为 error
      "unused_refs_severity": "auto",    // auto|warn|info|off
      "treat_note_as_definition": true,  // 文末 `注：ALA，α-亚麻酸` 是否算定义（默认算，但首用更早仍告警）
      "enabled_rules": ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"]
    }

已知局限（刻意保留的边界，脚本不假装能判断的就不判断）
------------------------------------------------------
* 只做文本匹配，不理解语义：反讽、转述、引文内原文、方法学里合法使用 "caused" 都可能误报。
* 缩写只识别全大写 token（含数字/连字符）；`Nrf2`、`mTORC1`、`Treg` 这类混合大小写符号不判定，
  基因/蛋白符号（GPR109A 等）默认只给 info，避免把符号当"未展开缩写"刷屏；缩写按文件独立判定，
  跨节共享的缩写请在整合稿上跑。
* 图表定义只认"行首图注/表题 / `**表 1**` / `# 表 1` / 带编号的 Markdown 图片 alt"；
  图在 .docx / figures/ 目录时用 `--figures <目录>` 按 figN/图N 文件名免除"图引用无定义"，
  但题注文字是否正确仍无法核对。跨节稿件请用 `--input <目录>` 让所有分节一起参与定义收集。
* R6 用 refs 第一作者姓 + 年份做键，并索引所有作者以识别"按第二作者引用"；但同名不同人、
  中文机构作者、多作者姓氏重排仍可能误配/漏配；著者-年制年份不一致会给精确提示，但不会自动改。
* R7 中文按 12 个汉字 ≈ 8 个词近似，不做分词；表格/公式块可能产生跨表重复误报。
* 不做拼写、语法、参考文献格式、图片分辨率、期刊模板检查（这些用各自工具）。

设计约定
--------
* 所有规则确定、可复现、无随机；同一输入输出逐字节稳定（排序固定）。
* 行号取片段所在行；长段落内用字符偏移反查行号。
* 默认最多输出 500 条（`--max-findings`），被截断时在摘要中注明。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

__version__ = "1.0.0"

# --------------------------------------------------------------------------- #
# 常量与规则元数据
# --------------------------------------------------------------------------- #

RULE_NAMES: dict[str, str] = {
    "R1": "交叉引用完整性",
    "R2": "缩写定义",
    "R3": "标题与层级",
    "R4": "统计报告",
    "R5": "过强措辞",
    "R6": "引用闭环",
    "R7": "跨节重复",
    "R8": "术语一致",
}
RULE_ORDER: list[str] = ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"]
SEVERITY_RANK: dict[str, int] = {"error": 0, "warn": 1, "info": 2}
SEVERITY_ZH: dict[str, str] = {"error": "错误", "warn": "告警", "info": "提示"}

#: 常见统计/单位/实验缩略语：默认不要求展开（可在 config 继续追加）。
DEFAULT_ABBREVIATION_WHITELIST: frozenset[str] = frozenset(
    {
        # statistics
        "SD", "SEM", "SE", "CI", "OR", "HR", "RR", "IRR", "ANOVA", "ANCOVA",
        "MANOVA", "GLM", "GLMM", "LMM", "PCA", "PLS", "ROC", "AUC", "DF", "SS",
        "MS", "FDR", "BH", "KS", "MWU", "IQR", "CV", "RMSE", "AIC", "BIC",
        # molecular / lab
        "DNA", "RNA", "MRNA", "CDNA", "PCR", "QPCR", "RTPCR", "ELISA", "HPLC",
        "LCMS", "GCMS", "TLC", "NMR", "MS", "UV", "IR", "GFP", "RFP", "WT",
        "KO", "KI", "PBS", "FBS", "DMSO", "EDTA", "SDS", "PAGE", "ATP", "ADP",
        "AMP", "NAD", "NADH", "NADPH", "ROS", "RNS", "COX", "LOX", "TNF",
        "IL", "IGF", "EGF", "VEGF", "FGF", "TGF", "BMP", "MHC", "TCR", "BCR",
        # units / misc
        "SI", "USA", "UK", "EU", "WHO", "FAO", "NGO", "BMI", "WHR", "HBA1C",
        "T2DM", "T1DM", "CVD", "CKD", "NAFLD", "IBD", "IBS", "ALP", "ALT",
        "AST", "TC", "TG", "HDL", "LDL", "VLDL", "FFA", "SCFA", "MCT", "PUFA",
        "MUFA", "EPA", "DHA", "AA", "LA", "ALA", "GABA", "BCAA", "AGE", "AGES",
        "RCT", "ITT", "PP", "AE", "SAE", "IRB", "IACUC", "NIH", "FDA", "EFSA",
        "SOP", "QC", "QA", "LOD", "LOQ", "RSD", "DPPH", "ABTS", "FRAP", "ORAC",
    }
)

_ROMAN_NUMERALS = frozenset(
    {"II", "III", "IV", "VI", "VII", "VIII", "IX", "XI", "XII", "XIII", "XIV", "XV", "XX"}
)

#: 英文句首/功能词，避免大小写一致性检查误报。
_EN_STOPWORDS: frozenset[str] = frozenset(
    """the a an this that these those we our us it its they their them he she his her
    i you your in on at of to for with by from as into over under between among per via
    and or but not no nor so if then than when where which while who whom whose what
    is are was were be been being has have had do does did can could may might must
    shall should will would also such more most less least only very much many some any
    all both each every other another same different than there here about after before
    during since until because although though however therefore thus hence moreover
    furthermore however whereas yet still even just well both either neither nor up down
    out off again further once both table figure fig section appendix supplementary
    equation eq chapter part phase stage note notes supplementary data available
    """.split()
)

_PARTICLES = frozenset({"van", "von", "de", "der", "den", "da", "di", "du", "le", "la", "del", "dos", "das"})

_STUDY_SEVERITY: dict[str, dict[str, str]] = {
    "observational": {"causal": "error", "demonstrate": "warn", "significance": "warn"},
    "human_observational": {"causal": "error", "demonstrate": "warn", "significance": "warn"},
    "human_rct": {"causal": "info", "demonstrate": "info", "significance": "info"},
    "animal": {"causal": "warn", "demonstrate": "info", "significance": "info"},
    "cell": {"causal": "warn", "demonstrate": "info", "significance": "info"},
    "in_vitro": {"causal": "warn", "demonstrate": "info", "significance": "info"},
    "mixed": {"causal": "warn", "demonstrate": "info", "significance": "warn"},
    "unknown": {"causal": "warn", "demonstrate": "info", "significance": "warn"},
}

DEFAULT_OVERCLAIM: dict[str, list[str]] = {
    "english_causal": [
        "prove", "proves", "proved", "proven", "confirm", "confirms", "confirmed",
        "establish causality", "establishes causality", "established causality",
        "demonstrate cause", "demonstrates cause", "demonstrated cause", "causal",
    ],
    "english_demonstrate": ["demonstrate", "demonstrates", "demonstrated", "demonstration"],
    "english_cause": ["cause", "causes", "caused"],
    "chinese_causal": ["证明", "证实", "导致", "必然", "确证"],
    "chinese_soft": [],
}

# --------------------------------------------------------------------------- #
# 数据结构
# --------------------------------------------------------------------------- #


@dataclass
class Finding:
    """单条体检结论。"""

    rule: str
    severity: str
    doc: str
    line: int
    message: str
    snippet: str = ""

    def locator(self) -> str:
        return f"{self.doc}:{self.line}"


@dataclass
class SourceLine:
    doc: str
    lineno: int
    text: str


@dataclass
class Section:
    index: int
    doc: str
    level: int
    title: str
    number: str | None
    line: int


@dataclass
class Paragraph:
    doc: str
    lines: list[SourceLine]
    text: str
    section_index: int | None
    is_table: bool = False

    @property
    def start_line(self) -> int:
        return self.lines[0].lineno

    def line_at(self, pos: int) -> int:
        """把段落内字符偏移换算成源文件行号。"""
        if not self.lines:
            return 0
        offset = 0
        for sl in self.lines:
            length = len(sl.text)
            if pos <= offset + length:
                return sl.lineno
            offset += length + 1  # '\n'
        return self.lines[-1].lineno


@dataclass
class Document:
    path: Path
    display: str
    lines: list[SourceLine]
    sections: list[Section]
    paragraphs: list[Paragraph]

    @property
    def text_raw(self) -> str:
        """整篇原文（行间以换行连接）。"""
        return "\n".join(sl.text for sl in self.lines)

    @property
    def text_lower(self) -> str:
        return self.text_raw.lower()

    def paragraphs_of_section(self, index: int | None) -> list[Paragraph]:
        return [p for p in self.paragraphs if p.section_index == index]


@dataclass
class RefIndex:
    """参考文献清单索引（编号制 / 著者-年制 / BibTeX）。"""

    path: Path | None
    style: str  # "numeric" | "bib" | "none"
    entries: dict[int, str] = field(default_factory=dict)
    keys: list[str] = field(default_factory=list)
    surname_years: dict[str, dict[int, list[int]]] = field(default_factory=dict)
    #: 任意作者（不限第一作者）→ {年: [条目号]}，用于识别"按第二作者引用"的错误
    any_author_years: dict[str, dict[int, list[int]]] = field(default_factory=dict)
    #: 条目号 → 第一作者姓（用于提示正确引用形式）
    first_authors: dict[int, str] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.entries)

    def lookup(self, surname: str, year: int) -> list[int]:
        return self.surname_years.get(norm_surname(surname), {}).get(year, [])

    def lookup_any_author(self, surname: str, year: int) -> list[int]:
        return self.any_author_years.get(norm_surname(surname), {}).get(year, [])

    def years_for(self, surname: str) -> list[int]:
        return sorted(self.surname_years.get(norm_surname(surname), {}))

    def has_surname(self, surname: str) -> bool:
        return norm_surname(surname) in self.surname_years


@dataclass
class Config:
    """lint 配置；字段含义见模块 docstring。"""

    study_type: str = "unknown"
    synonyms: list[list[str]] = field(default_factory=list)
    registered_abbreviations: set[str] = field(default_factory=set)
    abbreviation_whitelist: set[str] = field(default_factory=set)
    overclaim: dict[str, list[str]] = field(default_factory=lambda: dict(DEFAULT_OVERCLAIM))
    dup_min_latin_words: int = 8
    dup_min_cjk_chars: int = 12
    max_unused_refs: int = 20
    refs_style: str = "auto"
    citation_strict: bool = False
    unused_refs_severity: str = "auto"
    treat_note_as_definition: bool = True
    enabled_rules: set[str] = field(default_factory=lambda: set(RULE_ORDER))
    warnings: list[str] = field(default_factory=list)

    def severity(self, category: str) -> str:
        matrix = _STUDY_SEVERITY.get(self.study_type, _STUDY_SEVERITY["unknown"])
        return matrix.get(category, "warn")

    def whitelist(self) -> set[str]:
        return set(DEFAULT_ABBREVIATION_WHITELIST) | set(self.abbreviation_whitelist)


# --------------------------------------------------------------------------- #
# 文本工具
# --------------------------------------------------------------------------- #

_CJK = r"\u4e00-\u9fff\u3400-\u4dbf"
#: 全称允许的字符：汉字 + 拉丁 + 数字 + 希腊字母（α-亚麻酸）与常见连接符。
_FULL_CHARS = _CJK + r"A-Za-z0-9\u0370-\u03ff/·'\-"

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
NUMBER_PREFIX_RE = re.compile(r"^(?P<num>\d+(?:\.\d+)*)(?=[\s.．、:：]|$)")

_FIG_REF_RE = re.compile(r"(?:Figure|Figs?\.?|图)\s*(\d{1,3})")
_TAB_REF_RE = re.compile(r"(?:Table|Tabs?\.?|表)\s*(\d{1,3})")
_FIG_DEF_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:\*\*|__)?\s*(?:Figure|Fig\.?|图)\s*(\d{1,3})(?=[\s:：.．、\-—)）*]|$)"
)
_TAB_DEF_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:\*\*|__)?\s*(?:Table|表)\s*(\d{1,3})(?=[\s:：.．、\-—)）*]|$)"
)
_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
#: 行首 `图1 显示…` / `Table 1 lists…` 是正文引用而非图注/表题。
_CAPTION_VERB_RE = re.compile(
    r"^\s*[:：.．、\-—]?\s*(?:shows?|showed|showing|details?|details|presents?|lists?|listed|"
    r"illustrates?|depicts?|summari[sz]es?|demonstrates?|reports?|gives?|provides?|"
    r"显示|展示|表明|列出|给出|汇总|总结|概括|对比|描述|说明)"
)

_ABBR_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9])[A-Z][A-Z0-9]{1,9}(?:[-/][A-Z0-9]{1,9})*"
    r"(?![A-Za-z0-9\u0370-\u03ff])(?!-[A-Za-z0-9\u0370-\u03ff])"
)
_DEF_FULL_THEN_ABBR_RE = re.compile(
    r"(?P<full>[%s][%s]*(?:[ ][%s]+)*)"
    r"\s*[（(]\s*(?P<abbr>[A-Z][A-Z0-9]{1,9}(?:[-/][A-Z0-9]{1,9})*)\s*[)）]" % (_FULL_CHARS, _FULL_CHARS, _FULL_CHARS)
)
_DEF_ABBR_THEN_FULL_RE = re.compile(
    r"(?P<abbr>[A-Z][A-Z0-9]{1,9}(?:[-/][A-Z0-9]{1,9})*)\s*[（(]\s*(?P<full>[^（）()\n]{2,40})\s*[)）]"
)
_DEF_COMMA_RE = re.compile(
    r"(?P<full>[A-Za-z][A-Za-z0-9\- ]{7,60}),\s*(?P<abbr>[A-Z][A-Z0-9]{1,9})(?![A-Za-z0-9])"
)
_NOTE_LINE_RE = re.compile(r"^\s*(?:注|Notes?|Abbreviations?|缩写(?:表)?)\s*[:：]")
_NOTE_ITEM_RE = re.compile(
    r"(?P<abbr>[A-Z][A-Z0-9]{1,9}(?:[-/][A-Z0-9]{1,9})*)\s*[，,]\s*(?P<full>[^；;，,\n]{2,48})"
)
_CN_FUNCTION_STARTS = "的了和与在对为由及或而其这那该此所被把使让且并但若则即等以从向将已可应需较更最很不未无有是在"

_P_VALUE_EQ_ZERO_RE = re.compile(r"\b[Pp]\s*[=＝]\s*\.?0(?:\.0+)?\b")
_P_VALUE_ANY_RE = re.compile(r"\b[Pp]\s*[=＝<>＜]\s*\.?\d+(?:\.\d+)?")
_P_THRESHOLD_RE = re.compile(r"\b[Pp]\s*[<＜]\s*\.?0?\.\d+")
_STAT_VALUE_RE = re.compile(
    r"(?:\b[Pp]\s*[=＝<>＜]\s*\.?\d+)|(?:\b[tF]\s*[=＝]\s*\d)|(?:χ\s*[²2]?\s*[=＝]\s*\d)"
    r"|(?:\b(?:OR|HR|RR|IRR)\s*[=＝]\s*\d)|(?:95\s*%\s*CI)|(?:\bCI\s*[:：=]?\s*[\[(])"
)
_N_RE = re.compile(r"\b[nN]\s*[=＝]\s*\d+")
_PM_RE = re.compile(r"±")
_SD_SEM_RE = re.compile(r"\b(?:SD|SEM|s\.d\.|s\.e\.)\b")
_PM_DECL_RE = re.compile(r"(?:mean\s*±\s*(?:SD|SEM)|均值\s*±\s*(?:标准差|标准误)|平均值\s*±\s*(?:标准差|标准误)|x̄\s*±\s*s\b|\(\s*mean\s*±\s*(?:s\.?d\.?|SD)\s*\))", re.I)
_METHOD_WORDS = (
    "t检验", "t 检验", "方差分析", "ANOVA", "协方差", "卡方", "χ2", "χ²", "Mann", "Whitney",
    "Wilcoxon", "Kruskal", "log-rank", "log rank", "Cox", "回归", "模型", "混合线性",
    "线性混合", "随机效应", "Fisher", "Spearman", "Pearson", "相关分析", "检验",
    "test", "regression", "model", "GLMM", "GEE", "bootstrap", "置换检验", "Bonferroni",
    "FDR", "多重比较", "post hoc", "事后检验", "统计",
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？!?；;])\s*|\n+")

_PAREN_GROUP_RE = re.compile(r"[（(]([^（）()]{2,160})[)）]")
_CN_CITE_CHUNK_RE = re.compile(
    r"^(?P<auth>[%s·]{2,14}?)(?:等)?\s*(?P<year>(?:19|20)\d{2})(?P<suf>[a-z])?$" % _CJK
)
_EN_CITE_CHUNK_RE = re.compile(
    r"^(?P<auth>[A-Z][A-Za-zÀ-ÿ'’\-]+(?:\s+(?:et\s+al\.?|and\s+[A-Z][A-Za-zÀ-ÿ'’\-]+|(?:[A-Z]\.?\s*)+))?)"
    r"\s+(?P<year>(?:19|20)\d{2})(?P<suf>[a-z])?$"
)
_INLINE_EN_CITE_RE = re.compile(
    r"(?P<auth>[A-Z][A-Za-zÀ-ÿ'’\-]+(?:\s+[A-Z][A-Za-zÀ-ÿ'’\-.]*)*(?:\s+et\s+al\.?)?)"
    r"\s*[（(]\s*(?P<year>(?:19|20)\d{2})(?P<suf>[a-z]?)\s*[)）]"
)
_INLINE_CN_CITE_RE = re.compile(
    r"(?P<auth>[%s·]{2,14}?)(?:等)?[（(]\s*(?P<year>(?:19|20)\d{2})(?P<suf>[a-z]?)\s*[)）]" % _CJK
)
_NUMERIC_CITE_RE = re.compile(r"[\[［]\s*(\d{1,3}(?:\s*[-–—~,，]\s*\d{1,3})*)\s*[\]］]")
_PANDOC_CITE_RE = re.compile(r"\[@([A-Za-z0-9][\w:.\-]*)\]|@([A-Za-z][\w:.\-]*)")

_NUM_REF_LINE_RE = re.compile(r"^\s*\[?(\d{1,4})\]?\s*[.)、．]\s+(.+?)\s*$")
_BIB_ENTRY_RE = re.compile(r"@(?P<kind>\w+)\s*\{\s*(?P<key>[^,\s]+)\s*,(?P<body>.*?)\n\}", re.S)
_BIB_AUTHOR_RE = re.compile(r"author\s*=\s*[\{\"]([^\}\"]+)", re.I)
_BIB_YEAR_RE = re.compile(r"year\s*=\s*[\{\"]?(\d{4})", re.I)


def norm_surname(name: str) -> str:
    """把姓规范化用于比对（去标点、去空格、小写、全角转半角）。"""
    text = unicodedata.normalize("NFKC", name or "").strip()
    text = re.sub(r"[\s'’.\-]", "", text)
    text = re.sub(r"[，,；;　]", "", text)
    return text.lower()


def squeeze(text: str) -> str:
    """压缩空白，便于片段展示。"""
    return re.sub(r"\s+", " ", text or "").strip()


def snippet_at(text: str, start: int, end: int, width: int = 36) -> str:
    """取匹配位置前后各 width 字符的片段（用于报告定位）。"""
    if not text:
        return ""
    a = max(0, start - width)
    b = min(len(text), end + width)
    frag = squeeze(text[a:b])
    prefix = "…" if a > 0 else ""
    suffix = "…" if b < len(text) else ""
    return f"{prefix}{frag}{suffix}"


def line_snippet(text: str, limit: int = 96) -> str:
    frag = squeeze(text)
    return frag if len(frag) <= limit else frag[: limit - 1] + "…"


def has_cjk(text: str) -> bool:
    return bool(re.search(r"[%s]" % _CJK, text))


def split_sentences(text: str) -> list[str]:
    parts = [p for p in _SENTENCE_SPLIT_RE.split(text) if p and p.strip()]
    return parts


def expand_numeric_group(group: str) -> list[int]:
    """展开 `1,3-5` 形式为编号列表。"""
    numbers: list[int] = []
    for piece in re.split(r"[,，]", group):
        piece = piece.strip()
        if not piece:
            continue
        m = re.match(r"^(\d{1,3})\s*[-–—~]\s*(\d{1,3})$", piece)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            if lo <= hi and hi - lo <= 100:
                numbers.extend(range(lo, hi + 1))
            continue
        if piece.isdigit():
            numbers.append(int(piece))
    return numbers


# --------------------------------------------------------------------------- #
# 文档解析
# --------------------------------------------------------------------------- #


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def build_document(path: Path, display: str) -> Document:
    """读入 Markdown 文本并切成行 / 节 / 段。"""
    raw = read_text(path).splitlines()
    lines = [SourceLine(display, i, t) for i, t in enumerate(raw, 1)]
    sections: list[Section] = []
    paragraphs: list[Paragraph] = []
    current: list[SourceLine] = []
    current_section: int | None = None
    in_fence = False

    def flush() -> None:
        nonlocal current
        if not current:
            return
        text = "\n".join(sl.text for sl in current)
        nonblank = [sl.text.strip() for sl in current if sl.text.strip()]
        is_table = bool(nonblank) and all(t.startswith("|") for t in nonblank)
        paragraphs.append(Paragraph(display, list(current), text, current_section, is_table))
        current = []

    for sl in lines:
        stripped = sl.text.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            flush()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not stripped:
            flush()
            continue
        match = HEADING_RE.match(sl.text)
        if match:
            flush()
            title = match.group(2).strip()
            num_match = NUMBER_PREFIX_RE.match(title)
            sections.append(
                Section(
                    index=len(sections),
                    doc=display,
                    level=len(match.group(1)),
                    title=title,
                    number=num_match.group("num") if num_match else None,
                    line=sl.lineno,
                )
            )
            current_section = len(sections) - 1
            continue
        current.append(sl)
    flush()
    return Document(path=path, display=display, lines=lines, sections=sections, paragraphs=paragraphs)


def parse_refs(path: Path) -> RefIndex:
    """解析参考文献清单：`1. xxx` 编号制、`[1] xxx`、或 BibTeX `@article{key,...}`。"""
    text = read_text(path)
    index = RefIndex(path=path, style="none")

    bib_matches = list(_BIB_ENTRY_RE.finditer(text))
    numeric_entries: dict[int, str] = {}
    for raw_line in text.splitlines():
        m = _NUM_REF_LINE_RE.match(raw_line)
        if m:
            num = int(m.group(1))
            body = m.group(2).strip()
            if body:
                numeric_entries[num] = body

    if bib_matches:
        index.style = "bib"
        for match in bib_matches:
            body = match.group("body")
            author_match = _BIB_AUTHOR_RE.search(body)
            year_match = _BIB_YEAR_RE.search(body)
            key = match.group("key").strip()
            index.keys.append(key)
            plain = squeeze(body)
            entry_no = len(index.keys)
            index.entries[entry_no] = plain
            year = int(year_match.group(1)) if year_match else None
            if author_match:
                authors = [a.strip() for a in re.split(r"\s+and\s+", author_match.group(1)) if a.strip()]
                surnames: list[str] = []
                for author in authors:
                    if has_cjk(author):
                        surnames.append(author[:16])
                        continue
                    first = re.split(r"[,，]", author)[0].strip() or author
                    tokens = first.split()
                    surname = tokens[0] if tokens else first
                    if surname.lower() in _PARTICLES and len(tokens) > 1:
                        surname = f"{surname} {tokens[1]}"
                    surnames.append(surname)
                if surnames:
                    index.first_authors[entry_no] = surnames[0]
                    if year:
                        index.surname_years.setdefault(norm_surname(surnames[0]), {}).setdefault(year, []).append(entry_no)
                if year:
                    for surname in surnames[1:]:
                        index.any_author_years.setdefault(norm_surname(surname), {}).setdefault(year, []).append(entry_no)
        return index

    if numeric_entries:
        index.style = "numeric"
        index.entries = numeric_entries
        for num, body in numeric_entries.items():
            register_entry(index, num, body)
        return index

    # 兜底：无编号也无 bib 的纯文本清单，按行当条目
    plain_lines = [squeeze(x) for x in text.splitlines() if squeeze(x) and not x.strip().startswith("#")]
    if plain_lines:
        index.style = "numeric"
        for i, body in enumerate(plain_lines, 1):
            index.entries[i] = body
            register_entry(index, i, body)
    return index


def parse_author_list(body: str) -> list[str]:
    """从条目开头的作者块解析作者姓列表（中英文混排均可）。"""
    block = re.split(r"．|\.\s|\.$", body.strip(), maxsplit=1)[0]
    surnames: list[str] = []
    for piece in re.split(r"[，,、;；]|\s+and\s+", block):
        piece = piece.strip().strip(".")
        if not piece or piece.lower() in {"et", "al", "et al"}:
            continue
        if has_cjk(piece):
            surnames.append(piece[:16])
            continue
        tokens = piece.split()
        if not tokens:
            continue
        surname = tokens[0].strip(".,;:")
        if surname.lower() in _PARTICLES and len(tokens) > 1:
            surname = f"{surname} {tokens[1].strip('.,;:')}"
        if len(surname) >= 2:
            surnames.append(surname)
    return surnames


def register_entry(index: RefIndex, num: int, body: str) -> None:
    """把一条参考文献写进第一作者索引与任意作者索引。"""
    year = extract_year(body)
    surnames = parse_author_list(body)
    parsed = first_author_year(body)
    if parsed:
        surname, parsed_year = parsed
        index.first_authors[num] = surname
        index.surname_years.setdefault(norm_surname(surname), {}).setdefault(parsed_year, []).append(num)
        year = parsed_year
    if year:
        for surname in surnames:
            index.any_author_years.setdefault(norm_surname(surname), {}).setdefault(year, []).append(num)


def extract_year(entry: str) -> int | None:
    """从参考文献条目中稳健地取出版年。

    不能简单取"最后一个 4 位数字"：页码区间（如 `137:2043-2048`）会命中 2048。
    这里优先取"期刊卷期格式"上下文中的年份（`, 2026, 17:1930-1940`），并排除页码范围内数字。
    """
    best: tuple[int, int] | None = None  # (score, year)
    for match in re.finditer(r"(?:19|20)\d{2}", entry):
        start, end = match.span()
        prev_ch = entry[start - 1] if start > 0 else ""
        next_ch = entry[end] if end < len(entry) else ""
        dash_chars = "-–—‑"
        if (prev_ch and prev_ch in dash_chars) or (next_ch and next_ch in dash_chars):
            continue  # 页码范围中的数字，不是年份
        tail = entry[end:]
        score = 0
        if re.match(r"\s*[,;，；]\s*\d{1,5}\s*[:：]", tail):
            score += 6  # 年, 卷:页
        elif re.match(r"\s*[,;，；]\s*[A-Za-z]?\d", tail):
            score += 3
        if re.search(r"[,;.．，；]\s*$", entry[:start]):
            score += 1
        if re.match(r"\s*[)）]", tail):
            score += 1  # 如 (2020年)
        candidate = (score, int(match.group(0)))
        if best is None or candidate[0] >= best[0]:
            best = candidate
    if best is None:
        return None
    year = best[1]
    return year if 1900 <= year <= 2100 else None


def first_author_year(entry: str) -> tuple[str, int] | None:
    """从参考文献条目中取（第一作者姓, 出版年）。"""
    body = entry.strip()
    if not body:
        return None
    head = re.split(r"[，,．.]", body, maxsplit=1)[0].strip()
    if not head:
        return None
    if has_cjk(head):
        surname = head[:16]
    else:
        tokens = head.split()
        if not tokens:
            return None
        surname = tokens[0].strip(".,;:")
        if surname.lower() in _PARTICLES and len(tokens) > 1:
            surname = f"{surname} {tokens[1].strip('.,;:')}"
    year = extract_year(body)
    if year is None:
        return None
    return surname, year


# --------------------------------------------------------------------------- #
# 配置
# --------------------------------------------------------------------------- #


def load_config(path: str | None) -> Config:
    """读取 JSON 配置；未知键只告警不中断，保证向前兼容。"""
    cfg = Config()
    if not path:
        return cfg
    raw = read_text(Path(path))
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("--config 必须是 JSON 对象")
    known = {
        "study_type", "synonyms", "registered_abbreviations", "abbreviation_whitelist",
        "overclaim", "dup_min_latin_words", "dup_min_cjk_chars", "max_unused_refs",
        "refs_style", "citation_strict", "unused_refs_severity",
        "treat_note_as_definition", "enabled_rules",
    }
    for key in data:
        if key not in known:
            cfg.warnings.append(f"config 未知键被忽略: {key}")

    if "study_type" in data:
        cfg.study_type = str(data["study_type"]).strip().lower()
        if cfg.study_type not in _STUDY_SEVERITY:
            cfg.warnings.append(f"未知 study_type={cfg.study_type!r}，按 unknown 处理")
    if "synonyms" in data:
        groups = data["synonyms"]
        if isinstance(groups, list):
            for group in groups:
                if isinstance(group, list) and len([g for g in group if isinstance(g, str) and g.strip()]) >= 2:
                    cfg.synonyms.append([str(g).strip() for g in group if isinstance(g, str) and g.strip()])
                else:
                    cfg.warnings.append("synonyms 组需为长度≥2 的字符串数组，已忽略一组")
    if "registered_abbreviations" in data:
        cfg.registered_abbreviations = {str(x).upper() for x in data["registered_abbreviations"]}
    if "abbreviation_whitelist" in data:
        cfg.abbreviation_whitelist = {str(x).upper() for x in data["abbreviation_whitelist"]}
    if "overclaim" in data and isinstance(data["overclaim"], dict):
        override = data["overclaim"]
        replace = bool(override.get("replace_defaults", False))
        target = {} if replace else {k: list(v) for k, v in DEFAULT_OVERCLAIM.items()}
        for key, value in override.items():
            if key == "replace_defaults":
                continue
            if key not in DEFAULT_OVERCLAIM:
                cfg.warnings.append(f"overclaim 未知键被忽略: {key}")
                continue
            if isinstance(value, list):
                target[key] = [str(v) for v in value]
        cfg.overclaim = target
    if "dup_min_latin_words" in data:
        cfg.dup_min_latin_words = max(3, int(data["dup_min_latin_words"]))
    if "dup_min_cjk_chars" in data:
        cfg.dup_min_cjk_chars = max(6, int(data["dup_min_cjk_chars"]))
    if "max_unused_refs" in data:
        cfg.max_unused_refs = max(0, int(data["max_unused_refs"]))
    if "refs_style" in data:
        style = str(data["refs_style"]).lower()
        if style in {"auto", "numeric", "author-year", "bib"}:
            cfg.refs_style = style
        else:
            cfg.warnings.append(f"未知 refs_style={style!r}，按 auto 处理")
    if "citation_strict" in data:
        cfg.citation_strict = bool(data["citation_strict"])
    if "unused_refs_severity" in data:
        sev = str(data["unused_refs_severity"]).lower()
        if sev in {"auto", "warn", "info", "off"}:
            cfg.unused_refs_severity = sev
        else:
            cfg.warnings.append(f"未知 unused_refs_severity={sev!r}，按 auto 处理")
    if "treat_note_as_definition" in data:
        cfg.treat_note_as_definition = bool(data["treat_note_as_definition"])
    if "enabled_rules" in data:
        enabled = {str(x).upper() for x in data["enabled_rules"]}
        cfg.enabled_rules = {r for r in enabled if r in RULE_NAMES}
        if len(cfg.enabled_rules) != len(enabled):
            cfg.warnings.append("enabled_rules 含未知规则号，已忽略")
    return cfg


# --------------------------------------------------------------------------- #
# R1 交叉引用完整性
# --------------------------------------------------------------------------- #


def rule_xref(docs: Sequence[Document], ctx: "LintContext") -> list[Finding]:
    findings: list[Finding] = []
    fig_defs: dict[int, list[tuple[str, int, str]]] = defaultdict(list)
    tab_defs: dict[int, list[tuple[str, int, str]]] = defaultdict(list)
    fig_refs: list[tuple[str, int, int, str]] = []
    tab_refs: list[tuple[str, int, int, str]] = []
    def_lines: set[tuple[str, int]] = set()

    for doc in docs:
        for sl in doc.lines:
            text = sl.text
            for match in _FIG_DEF_RE.finditer(text):
                if _CAPTION_VERB_RE.match(text[match.end():]):
                    continue
                num = int(match.group(1))
                fig_defs[num].append((doc.display, sl.lineno, squeeze(text)[:100]))
                def_lines.add((doc.display, sl.lineno))
            for match in _TAB_DEF_RE.finditer(text):
                if _CAPTION_VERB_RE.match(text[match.end():]):
                    continue
                num = int(match.group(1))
                tab_defs[num].append((doc.display, sl.lineno, squeeze(text)[:100]))
                def_lines.add((doc.display, sl.lineno))
            for match in _IMG_RE.finditer(text):
                alt = match.group(1)
                num_match = re.search(r"(?:Figure|Fig\.?|图)\s*(\d{1,3})", alt)
                if num_match:
                    num = int(num_match.group(1))
                    fig_defs[num].append((doc.display, sl.lineno, squeeze(text)[:100]))
                    def_lines.add((doc.display, sl.lineno))
        for para in doc.paragraphs:
            if para.is_table:
                continue
            for match in _FIG_REF_RE.finditer(para.text):
                line = para.line_at(match.start())
                if (doc.display, line) in def_lines:
                    continue
                fig_refs.append((doc.display, line, int(match.group(1)), snippet_at(para.text, match.start(), match.end())))
            for match in _TAB_REF_RE.finditer(para.text):
                line = para.line_at(match.start())
                if (doc.display, line) in def_lines:
                    continue
                tab_refs.append((doc.display, line, int(match.group(1)), snippet_at(para.text, match.start(), match.end())))

    for kind, refs, defs in (("图", fig_refs, fig_defs), ("表", tab_refs, tab_defs)):
        for doc_name, line, num, snip in refs:
            if num in defs:
                continue
            if kind == "图" and num in ctx.figure_numbers:
                continue  # --figures 目录里有对应图形文件（题注仍需人眼确认）
            findings.append(
                Finding(
                    "R1", "error", doc_name, line,
                    f"正文引用{kind}{num}，但本次输入的稿件中未找到{kind}{num}的图注/表题定义"
                    "（若该图/表在其它分节或 figures/ 中，请以 --input <目录> 运行并补齐题注）",
                    snip,
                )
            )
        for num, places in defs.items():
            if len(places) > 1:
                for place in places:
                    findings.append(
                        Finding("R1", "warn", place[0], place[1], f"{kind}{num} 被重复定义 {len(places)} 次", place[2])
                    )
            if not any(r[2] == num for r in refs):
                place = places[0]
                findings.append(
                    Finding("R1", "warn", place[0], place[1], f"{kind}{num} 已定义但正文从未引用", place[2])
                )
    if ctx.figure_numbers:
        listed = ", ".join(f"图{n}←{ctx.figure_files[n]}" for n in sorted(ctx.figure_numbers))
        anchor = docs[0].display if docs else "-"
        findings.append(
            Finding("R1", "info", anchor, 1,
                    f"--figures 目录识别到图形文件：{listed}；仅免除图引用缺失告警，图注文字仍需人工核对", listed)
        )
    return findings


# --------------------------------------------------------------------------- #
# R2 缩写
# --------------------------------------------------------------------------- #


def _looks_like_full_name(full: str) -> bool:
    """判断括号内的文字是否像"全称"（而不是引用/年份/未定说明）。"""
    stripped = full.strip().rstrip("。；;，,")
    if len(stripped) < 2:
        return False
    if stripped[0] in _CN_FUNCTION_STARTS:
        return False
    if re.fullmatch(r"[A-Z0-9\-/]{2,10}", stripped):
        return False
    if re.search(r"(?:19|20)\d{2}", stripped):
        return False  # 著者-年制引用，如 AMPK（Zhang 2023）
    if re.match(r"^(?:未|不|待|无|暂|非|尚)", stripped):
        return False  # 如 AMPK（受体未定）
    return True


def _abbr_base(abbr: str) -> str:
    """取缩写的主干（`IL-10`→`IL`，`COX-2`→`COX`），用于白名单匹配。"""
    return re.split(r"[-/]", abbr)[0].upper()


def _looks_like_gene_symbol(abbr: str) -> bool:
    """基因/受体/通路标准符号（含数字，或 C 链长命名如 C21），默认只给 info。"""
    if re.fullmatch(r"C\d{1,2}", abbr):
        return True
    return bool(re.search(r"\d", abbr))


def rule_abbreviations(docs: Sequence[Document], ctx: "LintContext") -> list[Finding]:
    findings: list[Finding] = []
    whitelist = ctx.config.whitelist()

    for doc in docs:
        definitions: dict[str, list[tuple[int, str, str]]] = defaultdict(list)  # abbr -> (line, full, kind)
        occurrences: dict[str, list[int]] = defaultdict(list)

        for para in doc.paragraphs:
            text = para.text
            # 表格单元格里的“缩写（说明）”多为表格简写或引用，不当作定义（但计入使用）
            if not para.is_table:
                # 定义：全称（缩写） / 缩写（全称） / full, ABBR / 文末注：ABBR，全称
                for match in _DEF_FULL_THEN_ABBR_RE.finditer(text):
                    abbr = match.group("abbr")
                    full = match.group("full").strip()
                    if _looks_like_full_name(full):
                        definitions[abbr].append((para.line_at(match.start("abbr")), full, "inline"))
                for match in _DEF_ABBR_THEN_FULL_RE.finditer(text):
                    abbr = match.group("abbr")
                    full = match.group("full").strip()
                    if _looks_like_full_name(full):
                        definitions[abbr].append((para.line_at(match.start("abbr")), full, "abbr-first"))
                for match in _DEF_COMMA_RE.finditer(text):
                    definitions[match.group("abbr")].append((para.line_at(match.start("abbr")), match.group("full").strip(), "comma"))
                first_line = para.lines[0].text
                if _NOTE_LINE_RE.match(first_line):
                    for match in _NOTE_ITEM_RE.finditer(text):
                        definitions[match.group("abbr")].append((para.line_at(match.start("abbr")), match.group("full").strip(), "note"))
            for match in _ABBR_TOKEN_RE.finditer(text):
                token = match.group(0)
                occurrences[token].append(para.line_at(match.start()))

        for abbr in sorted(set(definitions) | set(occurrences)):
            defs = definitions.get(abbr, [])
            inline_defs = [d for d in defs if d[2] != "note"]
            note_defs = [d for d in defs if d[2] == "note"]
            note_line = min((d[0] for d in note_defs), default=None)
            all_uses = list(occurrences.get(abbr, []))
            body_uses = list(all_uses)
            # 定义/缩写表处自身的那次出现不算正文使用
            for line, _full, _kind in defs:
                if line in body_uses:
                    body_uses.remove(line)
            first_use = min(body_uses) if body_uses else (inline_defs[0][0] if inline_defs else (note_line or 1))

            # 未定义的缩写：白名单主干的 hyphen 变体（IL-10/COX-2）也放过；重复出现的纯字母缩写才 warn
            if abbr.upper() in whitelist or _abbr_base(abbr) in whitelist:
                continue
            if _looks_like_gene_symbol(abbr) or len(body_uses) < 2:
                undefined_severity = "info"
            else:
                undefined_severity = "warn"
            if len(inline_defs) >= 2:
                for line, full, _kind in inline_defs[1:]:
                    findings.append(
                        Finding("R2", "warn", doc.display, line, f"缩写 {abbr} 被重复定义（首次定义在第 {inline_defs[0][0]} 行）", f"{abbr}（{full}）")
                    )
            if not defs:
                findings.append(
                    Finding(
                        "R2", undefined_severity, doc.display, first_use,
                        f"缩写 {abbr} 未给出全称（首次出现）；若为基因/受体/通路标准符号可加入白名单或 style-guide",
                        abbr,
                    )
                )
                continue

            if note_line is not None and not inline_defs:
                if not ctx.config.treat_note_as_definition:
                    findings.append(
                        Finding("R2", "warn", doc.display, note_line,
                                f"缩写 {abbr} 只在文末缩写表中列出（配置要求正文首次出现给全称）", abbr)
                    )
                elif first_use < note_line:
                    findings.append(
                        Finding(
                            "R2", "warn", doc.display, first_use,
                            f"缩写 {abbr} 首次正文使用早于文末缩写表（第 {note_line} 行）；首次出现处未给全称",
                            abbr,
                        )
                    )
                elif not body_uses:
                    findings.append(
                        Finding("R2", "info", doc.display, note_line,
                                f"缩写 {abbr} 只在文末缩写表出现，正文未使用（可删除或补用于正文）", abbr)
                    )
            if inline_defs and not body_uses:
                findings.append(
                    Finding("R2", "info", doc.display, inline_defs[0][0],
                            f"缩写 {abbr} 定义后正文未再使用", defs[0][1])
                )

        if ctx.config.registered_abbreviations:
            for abbr, lines in occurrences.items():
                if len(lines) < 5:
                    continue
                if abbr.upper() in ctx.config.registered_abbreviations or abbr.upper() in whitelist:
                    continue
                findings.append(
                    Finding("R2", "info", doc.display, lines[0],
                            f"高频缩写 {abbr}（{len(lines)} 次）未在 style-guide/config.registered_abbreviations 登记", abbr)
                )
    return findings


# --------------------------------------------------------------------------- #
# R3 标题与层级
# --------------------------------------------------------------------------- #


def rule_headings(docs: Sequence[Document], ctx: "LintContext") -> list[Finding]:
    findings: list[Finding] = []
    for doc in docs:
        # 层级跳级
        previous: Section | None = None
        for section in doc.sections:
            if previous is not None and section.level - previous.level > 1:
                findings.append(
                    Finding("R3", "warn", doc.display, section.line,
                            f"标题层级跳级：H{previous.level}→H{section.level}（{previous.title[:24]} → {section.title[:24]}）",
                            section.title)
                )
            previous = section

        # 同父编号连续性 / 重号 / 回退
        by_parent: dict[str, list[Section]] = defaultdict(list)
        for section in doc.sections:
            if section.number:
                parent = ".".join(section.number.split(".")[:-1])
                by_parent[parent].append(section)
        for parent, siblings in by_parent.items():
            seen: dict[int, Section] = {}
            last: Section | None = None
            for section in siblings:
                last_part = int(section.number.split(".")[-1])
                if last_part in seen:
                    findings.append(
                        Finding("R3", "warn", doc.display, section.line,
                                f"标题编号重号：{section.number}（另见第 {seen[last_part].line} 行）", section.title)
                    )
                seen[last_part] = section
                if last is not None:
                    prev_part = int(last.number.split(".")[-1])
                    if last_part - prev_part > 1:
                        findings.append(
                            Finding("R3", "warn", doc.display, section.line,
                                    f"标题编号跳号：{last.number} → {section.number}（缺 {parent + '.' if parent else ''}{prev_part + 1}）",
                                    section.title)
                        )
                    elif last_part < prev_part and last.number == section.number:
                        pass
                last = section

        # 同级标题缺编号
        for section in doc.sections:
            if section.number:
                continue
            siblings = [s for s in doc.sections if s.level == section.level and s.number]
            if siblings:
                findings.append(
                    Finding("R3", "warn", doc.display, section.line,
                            f"标题缺少编号：H{section.level} 同级其它标题均带编号", section.title)
                )

        # 游离/空加粗标记（`**。**`、`**。` 等）
        for sl in doc.lines:
            text = sl.text
            if re.search(r"\*\*\s*[。，、；：,.;:]\s*\*\*", text) or re.search(r"\*\*\s*[。，、；：,.;:]\s*(?=\S)", text):
                findings.append(
                    Finding("R3", "info", doc.display, sl.lineno,
                            "疑似游离加粗标记（空强调或断开的 ** 对）", line_snippet(text))
                )
    return findings


# --------------------------------------------------------------------------- #
# R4 统计报告
# --------------------------------------------------------------------------- #


def rule_statistics(docs: Sequence[Document], ctx: "LintContext") -> list[Finding]:
    findings: list[Finding] = []
    doc_has_method = False
    for doc in docs:
        if any(word.lower() in doc.text_lower for word in _METHOD_WORDS if word.isascii()):
            doc_has_method = True
        if any(word in doc.text_raw for word in _METHOD_WORDS if not word.isascii()):
            doc_has_method = True

    for doc in docs:
        for para in doc.paragraphs:
            if para.is_table:
                continue
            text = para.text
            # P = 0.000 之类
            for match in _P_VALUE_EQ_ZERO_RE.finditer(text):
                findings.append(
                    Finding("R4", "error", doc.display, para.line_at(match.start()),
                            "统计量写作 P = 0.000 不可接受：应写 P < 0.001（或给出精确到下界的值）",
                            snippet_at(text, match.start(), match.end()))
                )
            # 只有阈值没有精确值
            threshold_hits = [m for m in _P_THRESHOLD_RE.finditer(text) if not _P_VALUE_EQ_ZERO_RE.match(text, m.start())]
            has_exact = bool(re.search(r"\b[Pp]\s*[=＝]\s*\.?\d+", text)) or bool(_STAT_VALUE_RE.search(text))
            if threshold_hits and not has_exact:
                match = threshold_hits[0]
                findings.append(
                    Finding("R4", "warn", doc.display, para.line_at(match.start()),
                            "只给出 P 阈值（如 P<0.05）而无精确 P 值/统计量；主结局应给精确值",
                            snippet_at(text, match.start(), match.end()))
                )
            # n= 但无统计方法
            n_matches = list(_N_RE.finditer(text))
            if n_matches:
                method_nearby = _method_nearby(doc, para)
                if not method_nearby:
                    findings.append(
                        Finding("R4", "warn", doc.display, para.line_at(n_matches[0].start()),
                                "出现 n= 但该段/本节未见统计方法说明（检验、方差分析、回归等）",
                                snippet_at(text, n_matches[0].start(), n_matches[0].end()))
                    )
            # ± 无样本量
            pm_matches = list(_PM_RE.finditer(text))
            if pm_matches and not n_matches:
                findings.append(
                    Finding("R4", "warn", doc.display, para.line_at(pm_matches[0].start()),
                            "报告了 ± 离散度但同段未见样本量 n；读者无法判断变异范围",
                            snippet_at(text, pm_matches[0].start(), pm_matches[0].end()))
                )
            # SD/SEM 未声明 & ± 后未声明类型
            sd_sem = _SD_SEM_RE.search(text)
            if pm_matches and not (sd_sem or _PM_DECL_RE.search(text)):
                findings.append(
                    Finding("R4", "info", doc.display, para.line_at(pm_matches[0].start()),
                            "± 后未声明为 SD 还是 SEM（全段无 mean±SD / 均值±标准差 说明）",
                            snippet_at(text, pm_matches[0].start(), pm_matches[0].end()))
                )
            elif sd_sem and not _PM_DECL_RE.search(text) and not _PM_DECL_RE.search(doc.text_raw):
                findings.append(
                    Finding("R4", "info", doc.display, para.line_at(sd_sem.start()),
                            "使用了 SD/SEM 但未说明 ± 后为哪一种离散度", snippet_at(text, sd_sem.start(), sd_sem.end()))
                )
    return findings


def _method_nearby(doc: Document, para: Paragraph) -> bool:
    section_text = " ".join(p.text for p in doc.paragraphs if p.section_index == para.section_index)
    haystack = section_text if section_text else doc.text_raw
    for word in _METHOD_WORDS:
        if word in haystack:
            return True
    return False


# --------------------------------------------------------------------------- #
# R5 过强措辞
# --------------------------------------------------------------------------- #


def rule_overclaim(docs: Sequence[Document], ctx: "LintContext") -> list[Finding]:
    findings: list[Finding] = []
    config = ctx.config
    causal_en = [w.lower() for w in config.overclaim.get("english_causal", [])]
    demo_en = [w.lower() for w in config.overclaim.get("english_demonstrate", [])]
    cause_en = [w.lower() for w in config.overclaim.get("english_cause", [])]
    causal_cn = config.overclaim.get("chinese_causal", [])
    soft_cn = config.overclaim.get("chinese_soft", [])

    for doc in docs:
        for para in doc.paragraphs:
            if para.is_table:
                continue
            text = para.text
            sentences = split_sentences(text)
            offsets: list[int] = []
            cursor = 0
            for sentence in sentences:
                start = text.find(sentence, cursor)
                offsets.append(start if start >= 0 else cursor)
                cursor = (start if start >= 0 else cursor) + len(sentence)
            sentence_has_stat = [bool(_STAT_VALUE_RE.search(sentence)) for sentence in sentences]

            def nearby_stat(index: int) -> bool:
                return sentence_has_stat[index] or (index > 0 and sentence_has_stat[index - 1]) or (
                    index + 1 < len(sentence_has_stat) and sentence_has_stat[index + 1]
                )

            for index, sentence in enumerate(sentences):
                base = offsets[index]
                lower = sentence.lower()

                def emit(word: str, category: str, severity: str, note: str = "") -> None:
                    start = lower.find(word.lower())
                    if start < 0:
                        return
                    message = f"过强/因果措辞「{word}」{note}"
                    findings.append(
                        Finding("R5", severity, doc.display, para.line_at(base + start),
                                message, snippet_at(text, base + start, base + start + len(word)))
                    )

                for word in causal_en:
                    if not re.search(r"\b" + re.escape(word) + r"\b", lower):
                        continue
                    if word == "causal" and re.search(r"causal(?:ly)?\s+(?:inference|analysis|model|association|relationship)", lower):
                        continue
                    emit(word, "causal", config.severity("causal"), f"（study_type={config.study_type}；{_causal_hint(config)}）")
                for word in demo_en:
                    if re.search(r"\b" + re.escape(word) + r"\b", lower):
                        emit(word, "demonstrate", config.severity("demonstrate"), "：观察/动物/细胞研究宜用 show/indicate/associate")
                for word in cause_en:
                    if re.search(r"\b" + re.escape(word) + r"\b", lower) and not re.search(
                        re.escape(word) + r"[- ]specific|specific\s+" + re.escape(word), lower
                    ):
                        emit(word, "causal", config.severity("causal"), "：因果表述需干预或机制证据支撑")
                for word in causal_cn:
                    for match in re.finditer(re.escape(word), sentence):
                        findings.append(
                            Finding("R5", config.severity("causal"), doc.display, para.line_at(base + match.start()),
                                    f"过强/因果措辞「{word}」（study_type={config.study_type}；{_causal_hint(config)}）",
                                    snippet_at(text, base + match.start(), base + match.end()))
                        )
                for word in soft_cn:
                    for match in re.finditer(re.escape(word), sentence):
                        findings.append(
                            Finding("R5", "info", doc.display, para.line_at(base + match.start()),
                                    f"弱化措辞「{word}」：确认是否与证据强度匹配（info）",
                                    snippet_at(text, base + match.start(), base + match.end()))
                        )
                for word in ("significantly", "significant"):
                    if re.search(r"\b" + word + r"\b", lower) and not nearby_stat(index):
                        start = lower.find(word)
                        findings.append(
                            Finding("R5", config.severity("significance"), doc.display, para.line_at(base + start),
                                    f"「{word}」未在同句/邻句给出 P 值或统计量；显著性声明需附统计结果",
                                    snippet_at(text, base + start, base + start + len(word)))
                        )
                for word in ("显著", "显著性"):
                    if word not in sentence or nearby_stat(index):
                        continue
                    start = sentence.find(word)
                    before = sentence[max(0, start - 10):start]
                    if re.search(r"无论|不管|多么", before):
                        continue  # “无论多么显著”属修辞，不是统计声明
                    findings.append(
                        Finding("R5", config.severity("significance"), doc.display, para.line_at(base + start),
                                f"「{word}」未在同句/邻句给出 P 值或统计量；中文稿同样要求统计支撑",
                                snippet_at(text, base + start, base + start + len(word)))
                    )
                    break
    # 同一行同一措辞只报一次（避免“被证明……这些证明”重复刷屏）
    deduped: dict[tuple[str, int, str], Finding] = {}
    for finding in findings:
        deduped.setdefault((finding.doc, finding.line, finding.message), finding)
    return list(deduped.values())


def _causal_hint(config: Config) -> str:
    if config.study_type in {"observational", "human_observational"}:
        return "观察性研究不能作因果断言，宜改为 associated with / 与…相关"
    if config.study_type in {"cell", "animal", "in_vitro"}:
        return "模型系统结论外推到人需降级措辞"
    return "请按证据层级降级措辞或补干预/机制证据"


# --------------------------------------------------------------------------- #
# R6 引用闭环
# --------------------------------------------------------------------------- #


@dataclass
class Citation:
    doc: str
    line: int
    surname: str
    year: int
    suffix: str
    kind: str  # "author-year" | "numeric" | "key"


def extract_citations(docs: Sequence[Document]) -> tuple[list[Citation], set[int], set[str]]:
    citations: list[Citation] = []
    numeric: set[int] = set()
    keys: set[str] = set()

    for doc in docs:
        for para in doc.paragraphs:
            if para.is_table:
                continue
            text = para.text
            for match in _NUMERIC_CITE_RE.finditer(text):
                line = para.line_at(match.start())
                for num in expand_numeric_group(match.group(1)):
                    numeric.add(num)
                    citations.append(Citation(doc.display, line, "", num, "", "numeric"))
            for match in _PANDOC_CITE_RE.finditer(text):
                key = match.group(1) or match.group(2)
                if not key:
                    continue
                keys.add(key)
                citations.append(Citation(doc.display, para.line_at(match.start()), "", 0, "", "key"))
            seen_spans: set[tuple[int, int]] = set()
            for group_match in _PAREN_GROUP_RE.finditer(text):
                group = group_match.group(1)
                group_start = group_match.start(1)
                if not re.search(r"(?:19|20)\d{2}", group):
                    continue
                for piece in re.split(r"[,，;；、]\s*", group):
                    piece = piece.strip()
                    if not piece:
                        continue
                    parsed = _parse_citation_piece(piece)
                    if not parsed:
                        continue
                    surname, year, suffix = parsed
                    if year < 1900 or year > 2100:
                        continue
                    if _is_stop_author(surname):
                        continue
                    # 计算该片段的绝对位置（近似：整组内检索）
                    rel = group.find(piece)
                    start = group_start + (rel if rel >= 0 else 0)
                    if (start, start + len(piece)) in seen_spans:
                        continue
                    seen_spans.add((start, start + len(piece)))
                    citations.append(Citation(doc.display, para.line_at(start), surname, year, suffix, "author-year"))
            for regex, is_cn in ((_INLINE_EN_CITE_RE, False), (_INLINE_CN_CITE_RE, True)):
                for match in regex.finditer(text):
                    surname = _first_author_surname(match.group("auth").strip())
                    if is_cn:
                        surname = re.sub(r"等$", "", surname)
                    year = int(match.group("year"))
                    suffix = match.group("suf") or ""
                    if _is_stop_author(surname):
                        continue
                    citations.append(
                        Citation(doc.display, para.line_at(match.start()), surname, year, suffix, "author-year")
                    )
    # 去重（同一文件同一行同一作者年只报一次）
    unique: dict[tuple[str, int, str, int], Citation] = {}
    for cite in citations:
        key = (cite.doc, cite.line, norm_surname(cite.surname), cite.year)
        unique.setdefault(key, cite)
    return list(unique.values()), numeric, keys


def _first_author_surname(auth: str) -> str:
    """从 `Khan et al` / `Yang Y et al` / `Smith and Jones` / `章根木和姚甘火` 中取第一作者姓。"""
    text = re.sub(r"\s+et\s+al\.?$", "", auth.strip(), flags=re.I)
    text = re.split(r"\s+and\s+|\s*&\s*|\s+等$", text)[0].strip()
    # 中文双作者 `A和B`：只取第一作者
    text = re.split(r"(?<=[\u4e00-\u9fff])和(?=[\u4e00-\u9fff])", text)[0].strip()
    parts = text.split()
    while len(parts) > 1 and re.fullmatch(r"[A-Z][a-z]?\.?", parts[-1]):
        parts.pop()
    return " ".join(parts) if parts else text


def _parse_citation_piece(piece: str) -> tuple[str, int, str] | None:
    match = _EN_CITE_CHUNK_RE.match(piece) or _CN_CITE_CHUNK_RE.match(piece)
    if not match:
        return None
    auth = _first_author_surname(match.group("auth").strip())
    if auth.lower().startswith("et al"):
        return None
    year = int(match.group("year"))
    return auth, year, match.group("suf") or ""


def _is_stop_author(name: str) -> bool:
    low = name.lower().strip()
    if not low:
        return True
    if low in _EN_STOPWORDS:
        return True
    if low in {"et", "al", "and", "等"}:
        return True
    if re.fullmatch(r"[A-Z]", name):
        return True
    return False


def rule_citations(docs: Sequence[Document], ctx: "LintContext") -> list[Finding]:
    findings: list[Finding] = []
    refs = ctx.refs
    if refs is None or refs.total == 0:
        if ctx.refs_requested:
            findings.append(Finding("R6", "warn", docs[0].display if docs else "-", 1, "已提供 --refs 但未解析出任何条目，引用闭环规则跳过", ""))
        return findings

    citations, numeric, keys = extract_citations(docs)
    number_cites = [c for c in citations if c.kind == "numeric"]
    author_cites = [c for c in citations if c.kind == "author-year"]
    key_cites = [c for c in citations if c.kind == "key"]

    used_refs: set[int] = set()
    refs_total = refs.total
    refs_numbers = set(refs.entries.keys())

    # ---- 编号制 ----
    if number_cites:
        max_cited = max(c.year for c in number_cites)  # numeric 复用 year 字段存编号
        if max_cited > refs_total:
            worst = max(number_cites, key=lambda c: c.year)
            findings.append(
                Finding("R6", "error", worst.doc, worst.line,
                        f"正文最大引用编号 [{max_cited}] 超过 refs 条目数（{refs_total} 条）——编号越界/refs 不全",
                        f"[{worst.year}]")
            )
        missing = sorted(n for n in numeric if refs_numbers and n not in refs_numbers)
        if missing:
            sample = ", ".join(str(n) for n in missing[:10])
            findings.append(
                Finding("R6", "error", number_cites[0].doc, number_cites[0].line,
                        f"正文引用了 refs 中不存在的编号：{sample}{'…' if len(missing) > 10 else ''}", f"[{missing[0]}]")
            )
        if refs_numbers and len(numeric) >= 0.5 * len(refs_numbers):
            gaps = sorted(set(range(1, max(numeric) + 1)) - numeric)
            if gaps:
                findings.append(
                    Finding("R6", "info", number_cites[0].doc, number_cites[0].line,
                            "正文引用编号不连续，缺：" + _format_ranges(gaps), "")
                )
        used_refs |= {n for n in numeric if n in refs_numbers}

    # ---- 著者-年制（本仓库稿件实际用法）----
    if author_cites and refs.surname_years:
        unmatched: list[Citation] = []
        mismatched: list[Citation] = []
        second_author: list[tuple[Citation, list[int]]] = []
        for cite in author_cites:
            hits = refs.lookup(cite.surname, cite.year)
            if hits:
                used_refs |= set(hits)
                continue
            if refs.has_surname(cite.surname):
                mismatched.append(cite)
                continue
            other_hits = refs.lookup_any_author(cite.surname, cite.year)
            if other_hits:
                second_author.append((cite, other_hits))
                used_refs |= set(other_hits)
                continue
            unmatched.append(cite)
        for cite in mismatched:
            years = refs.years_for(cite.surname)
            findings.append(
                Finding("R6", "warn", cite.doc, cite.line,
                        f"正文引用（{cite.surname} {cite.year}）的年份与 refs 记录不一致：refs 中该姓氏为 "
                        + ", ".join(str(y) for y in years),
                        f"{cite.surname} {cite.year}")
            )
        for cite, hits in second_author:
            entry_no = hits[0]
            first = refs.first_authors.get(entry_no, "?")
            findings.append(
                Finding("R6", "warn", cite.doc, cite.line,
                        f"正文以非第一作者（{cite.surname} {cite.year}）引用 refs 第 {entry_no} 条；"
                        f"该条第一作者为 {first}，著者-年制应按第一作者引用（如 {first} {cite.year}）",
                        f"{cite.surname} {cite.year}")
            )
        for cite in unmatched:
            severity = "error" if ctx.config.citation_strict else "warn"
            findings.append(
                Finding("R6", severity, cite.doc, cite.line,
                        f"正文引用（{cite.surname} {cite.year}）在 refs 清单中找不到对应条目（姓+年份均未命中）",
                        f"{cite.surname} {cite.year}")
            )

    # ---- bib key ----
    if key_cites and refs.keys:
        key_set = set(refs.keys)
        for cite in key_cites:
            if cite.kind != "key":
                continue
            raw_key = None
            for k in keys:
                if k.lower() not in key_set:
                    raw_key = k
            if raw_key:
                findings.append(
                    Finding("R6", "error", cite.doc, cite.line, f"正文引用键 @{raw_key} 在 BibTeX 中不存在", f"@{raw_key}")
                )
                break

    # ---- refs 从未被引用 ----
    unused = sorted(refs_numbers - used_refs) if refs_numbers else []
    if unused:
        ratio = len(unused) / max(1, refs_total)
        severity = ctx.config.unused_refs_severity
        if severity == "auto":
            single_section = len(docs) == 1
            severity = "info" if (single_section and ratio > 0.5) else "warn"
        if severity != "off":
            shown = unused[: max(0, ctx.config.max_unused_refs)]
            note = "（输入为单节文件，refs 为全文清单，未引用条目多半属于其它章节；自动降为 info）" if severity == "info" else ""
            findings.append(
                Finding("R6", severity, docs[0].display if docs else "-", 1,
                        f"refs 中从未被正文引用的条目共 {len(unused)}/{refs_total} 条{note}；"
                        "前若干条：" + ", ".join(str(n) for n in shown) + ("…" if len(unused) > len(shown) else ""),
                        "")
            )
    return findings


def _format_ranges(numbers: Sequence[int]) -> str:
    if not numbers:
        return ""
    parts: list[str] = []
    start = prev = numbers[0]
    for num in numbers[1:]:
        if num == prev + 1:
            prev = num
            continue
        parts.append(str(start) if start == prev else f"{start}-{prev}")
        start = prev = num
    parts.append(str(start) if start == prev else f"{start}-{prev}")
    return ", ".join(parts)


# --------------------------------------------------------------------------- #
# R7 跨节重复
# --------------------------------------------------------------------------- #


@dataclass
class DupUnit:
    """R7 的重复检测单元：一节（单节文件则每一个段落）。"""

    uid: str
    doc: str
    label: str
    latin: list[tuple[str, int]]
    cjk: list[tuple[str, int]]


def _build_dup_units(docs: Sequence[Document]) -> list[DupUnit]:
    units: list[DupUnit] = []

    def make(doc: Document, label: str, paras: Sequence[Paragraph]) -> DupUnit:
        latin: list[tuple[str, int]] = []
        cjk: list[tuple[str, int]] = []
        for para in paras:
            for sl in para.lines:
                for match in re.finditer(r"[A-Za-z][A-Za-z0-9\-']*", sl.text):
                    latin.append((match.group(0).lower(), sl.lineno))
                for match in re.finditer(r"[%s]" % _CJK, sl.text):
                    cjk.append((match.group(0), sl.lineno))
        return DupUnit(f"{doc.display}::{label}", doc.display, label, latin, cjk)

    for doc in docs:
        if len(doc.sections) >= 2:
            for section in doc.sections:
                body = [p for p in doc.paragraphs if p.section_index == section.index]
                if body:
                    units.append(make(doc, f"§{section.number or section.index}", body))
        else:
            # 单节文件（本仓库常见：一节一个文件）退化为段间比较，否则规则形同虚设
            for idx, para in enumerate(doc.paragraphs):
                if para.is_table or len(squeeze(para.text)) < 20:
                    continue
                units.append(make(doc, f"¶{idx + 1}", [para]))
    return units


def rule_duplicates(docs: Sequence[Document], ctx: "LintContext") -> list[Finding]:
    """检测 ≥N 词 / ≥M 汉字 的跨节重复片段（info：抄袭或复制粘贴信号）。"""
    findings: list[Finding] = []
    units = _build_dup_units(docs)
    if len(units) < 2:
        return findings
    for label, window, kind_zh in (
        ("latin", ctx.config.dup_min_latin_words, "词"),
        ("cjk", ctx.config.dup_min_cjk_chars, "汉字"),
    ):
        findings.extend(_duplicate_runs(units, label, window, kind_zh))
    return findings


def _duplicate_runs(units: Sequence[DupUnit], label: str, window: int, kind_zh: str) -> list[Finding]:
    """把重叠 shingle 合并成极大重复块，避免同一个复制段刷出几十条。"""
    token_lists = [u.latin if label == "latin" else u.cjk for u in units]
    shingle_map: dict[tuple[str, ...], list[tuple[int, int]]] = defaultdict(list)
    for ui, toks in enumerate(token_lists):
        values = [t for t, _line in toks]
        for start in range(0, max(0, len(values) - window + 1)):
            shingle_map[tuple(values[start: start + window])].append((ui, start))

    pair_starts: dict[tuple[int, int], set[tuple[int, int]]] = defaultdict(set)
    for places in shingle_map.values():
        if len(places) < 2:
            continue
        for i in range(len(places)):
            for j in range(i + 1, len(places)):
                ua, sa = places[i]
                ub, sb = places[j]
                if ua == ub:
                    continue
                if ua > ub:
                    ua, ub, sa, sb = ub, ua, sa, sb
                pair_starts[(ua, ub)].add((sa, sb))

    findings: list[Finding] = []
    per_pair_limit = 8
    for (ua, ub), starts in sorted(pair_starts.items()):
        runs: list[list[int]] = []  # [startA, endA, startB, endB] 含端点 token 下标
        for sa, sb in sorted(starts):
            if runs and sa == runs[-1][1] + 1 and sb == runs[-1][3] + 1:
                runs[-1][1] = sa + window - 1
                runs[-1][3] = sb + window - 1
            else:
                runs.append([sa, sa + window - 1, sb, sb + window - 1])
        # 极大化：长块优先，且 A/B 两侧都不与已选块重叠
        runs.sort(key=lambda r: (-(r[1] - r[0]), r[0]))
        chosen: list[list[int]] = []
        for run in runs:
            overlap_a = any(not (run[1] < other[0] or run[0] > other[1]) for other in chosen)
            overlap_b = any(not (run[3] < other[2] or run[2] > other[3]) for other in chosen)
            if overlap_a or overlap_b:
                continue
            chosen.append(run)
        chosen.sort(key=lambda r: r[0])
        for run in chosen[:per_pair_limit]:
            matched = run[1] - run[0] + 1
            phrase = _dup_phrase(units[ua], run[0], matched, label)
            line_a = _token_line(units[ua], run[0], label)
            line_b = _token_line(units[ub], run[2], label)
            findings.append(
                Finding(
                    "R7", "info", units[ua].doc, line_a,
                    f"与 {units[ub].label}（第 {line_b} 行）存在连续 {matched} 个{kind_zh}的重复片段："
                    f"「{phrase[:60]}{'…' if len(phrase) > 60 else ''}」",
                    phrase[:80],
                )
            )
    return findings


def _dup_phrase(unit: DupUnit, start: int, length: int, label: str) -> str:
    toks = unit.latin if label == "latin" else unit.cjk
    chunk = [t for t, _line in toks[start: start + length]]
    return " ".join(chunk) if label == "latin" else "".join(chunk)


def _token_line(unit: DupUnit, index: int, label: str) -> int:
    toks = unit.latin if label == "latin" else unit.cjk
    if not toks:
        return 1
    return toks[min(index, len(toks) - 1)][1]


# --------------------------------------------------------------------------- #
# R8 术语一致
# --------------------------------------------------------------------------- #


def rule_terminology(docs: Sequence[Document], ctx: "LintContext") -> list[Finding]:
    findings: list[Finding] = []
    config = ctx.config

    for doc in docs:
        prose = "\n".join(p.text for p in doc.paragraphs if not p.is_table)
        lines = _iter_prose_lines(doc)

        # 同义词组混用
        for group in config.synonyms:
            counts: list[tuple[int, str]] = []
            for variant in group:
                count = _count_variant(prose, variant)
                if count:
                    counts.append((count, variant))
            if len(counts) >= 2:
                variants = "；".join(f"{variant}({count})" for count, variant in sorted(counts, reverse=True))
                first_line = _first_variant_line(lines, group)
                detail = "首选「%s」" % sorted(counts, reverse=True)[0][1]
                findings.append(
                    Finding("R8", "warn", doc.display, first_line,
                            f"同义术语混用：{variants}；{detail}，其余变体建议统一", variants)
                )

        # 连字符不一致
        hyphenated: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for sl in doc.lines:
            for match in re.finditer(r"\b[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+\b", sl.text):
                surface = match.group(0)
                key = surface.replace("-", "").lower()
                hyphenated[key][surface] += 1
        for key, surfaces in sorted(hyphenated.items()):
            if len(surfaces) < 2:
                continue
            total = sum(surfaces.values())
            if total < 3:
                continue
            variants = " / ".join(f"{s}({c})" for s, c in sorted(surfaces.items(), key=lambda kv: -kv[1]))
            first_line = _first_surface_line(doc, list(surfaces)[0])
            findings.append(
                Finding("R8", "info", doc.display, first_line,
                        f"同一术语连字符写法不一致：{variants}", variants)
            )
        # 同一术语连字符 vs 空格（如 whole-grain / whole grain）
        for key, surfaces in sorted(hyphenated.items()):
            surface = max(surfaces, key=lambda s: surfaces[s])
            spaced = surface.replace("-", " ")
            spaced_count = len(re.findall(r"\b" + re.escape(spaced) + r"\b", prose, re.I))
            if spaced_count >= 1 and sum(surfaces.values()) >= 1:
                line = _first_surface_line(doc, surface)
                findings.append(
                    Finding("R8", "info", doc.display, line,
                            f"连字符写法不统一：{surface}({sum(surfaces.values())}) vs {spaced}({spaced_count})",
                            f"{surface} / {spaced}")
                )

        # 同一英文术语大小写不一致（内部大小写/全大写混用）
        case_map: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for sl in doc.lines:
            if HEADING_RE.match(sl.text):
                continue
            for match in re.finditer(r"\b[A-Za-z][A-Za-z0-9]{1,9}\b", sl.text):
                surface = match.group(0)
                if surface.lower() in _EN_STOPWORDS:
                    continue
                if surface[0].islower() and not any(ch.isupper() for ch in surface[1:]):
                    key = surface.lower()
                elif surface[0].isupper() and not any(ch.isupper() for ch in surface[1:]):
                    key = surface.lower()  # 句首大写归一
                else:
                    key = surface.lower()
                case_map[key][surface] += 1
        for key, surfaces in sorted(case_map.items()):
            if len(surfaces) < 2:
                continue
            has_internal_upper = any(sum(1 for ch in s if ch.isupper()) >= 2 or any(ch.isupper() for ch in s[1:]) for s in surfaces)
            if not has_internal_upper:
                continue
            variants = " / ".join(f"{s}({c})" for s, c in sorted(surfaces.items(), key=lambda kv: -kv[1]))
            line = _first_surface_line(doc, sorted(surfaces)[0])
            findings.append(
                Finding("R8", "info", doc.display, line, f"同一术语大小写不一致：{variants}", variants)
            )
    return findings


def _iter_prose_lines(doc: Document) -> list[SourceLine]:
    return doc.lines


def _count_variant(text: str, variant: str) -> int:
    if has_cjk(variant) or re.search(r"\s", variant):
        return len(re.findall(re.escape(variant), text))
    return len(re.findall(r"(?<![A-Za-z])" + re.escape(variant) + r"(?![A-Za-z])", text, re.I))


def _first_variant_line(lines: Sequence[SourceLine], variants: Sequence[str]) -> int:
    for sl in lines:
        for variant in variants:
            if variant in sl.text:
                return sl.lineno
    return 1


def _first_surface_line(doc: Document, surface: str) -> int:
    pattern = re.compile(re.escape(surface))
    for sl in doc.lines:
        if pattern.search(sl.text):
            return sl.lineno
    return 1


# --------------------------------------------------------------------------- #
# 运行器
# --------------------------------------------------------------------------- #


@dataclass
class LintContext:
    config: Config
    refs: RefIndex | None
    refs_requested: bool
    #: `--figures` 目录里识别出的图号（只用于免除"图引用无定义"，不参与反向检查）
    figure_numbers: set[int] = field(default_factory=set)
    figure_files: dict[int, str] = field(default_factory=dict)


def run_rules(
    docs: Sequence[Document],
    refs: RefIndex | None,
    config: Config,
    refs_requested: bool = False,
    figure_numbers: dict[int, str] | None = None,
) -> list[Finding]:
    """按启用规则运行全部检查并返回排序后的结论。"""
    figure_files = dict(figure_numbers or {})
    ctx = LintContext(
        config=config,
        refs=refs,
        refs_requested=refs_requested,
        figure_numbers=set(figure_files),
        figure_files=figure_files,
    )
    findings: list[Finding] = []
    runners = {
        "R1": lambda: rule_xref(docs, ctx),
        "R2": lambda: rule_abbreviations(docs, ctx),
        "R3": lambda: rule_headings(docs, ctx),
        "R4": lambda: rule_statistics(docs, ctx),
        "R5": lambda: rule_overclaim(docs, ctx),
        "R6": lambda: rule_citations(docs, ctx),
        "R7": lambda: rule_duplicates(docs, ctx),
        "R8": lambda: rule_terminology(docs, ctx),
    }
    for rule_id in RULE_ORDER:
        if rule_id not in config.enabled_rules:
            continue
        findings.extend(runners[rule_id]())
    findings.sort(key=lambda f: (f.doc, f.line, SEVERITY_RANK.get(f.severity, 9), f.rule, f.message))
    return findings


# --------------------------------------------------------------------------- #
# 输出
# --------------------------------------------------------------------------- #


def rule_counts(findings: Sequence[Finding]) -> dict[str, Counter]:
    counts: dict[str, Counter] = {rule: Counter() for rule in RULE_ORDER}
    for finding in findings:
        counts.setdefault(finding.rule, Counter())[finding.severity] += 1
    return counts


def render_markdown(findings: Sequence[Finding], docs: Sequence[Document], refs: RefIndex | None, config: Config, truncated: bool) -> str:
    totals = Counter(f.severity for f in findings)
    out: list[str] = []
    out.append("# 稿件一致性体检报告")
    out.append("")
    out.append("- 输入：" + "；".join(f"`{d.display}`" for d in docs))
    if refs and refs.path:
        out.append(f"- refs：`{refs.path}`（{refs.total} 条，{refs.style}）")
    else:
        out.append("- refs：未提供（R6 引用闭环跳过）")
    out.append(f"- study_type：`{config.study_type}`（决定 R5 过强措辞分级）")
    out.append(f"- 规则：{', '.join(sorted(config.enabled_rules))}")
    verdict = "存在 error，判定不通过（退出码 1）" if totals["error"] else "无 error，机械一致性通过（退出码 0）"
    out.append(f"- 结论：{verdict}；error {totals['error']} / warn {totals['warn']} / info {totals['info']}")
    if truncated:
        out.append("- 注意：输出已按 --max-findings 截断")
    out.append("")
    out.append("## 规则命中统计")
    out.append("")
    out.append("| 规则 | 说明 | error | warn | info | 合计 |")
    out.append("| --- | --- | ---: | ---: | ---: | ---: |")
    counts = rule_counts(findings)
    for rule in RULE_ORDER:
        if rule not in config.enabled_rules:
            continue
        counter = counts[rule]
        out.append(
            f"| {rule} | {RULE_NAMES[rule]} | {counter['error']} | {counter['warn']} | {counter['info']} "
            f"| {sum(counter.values())} |"
        )
    out.append(f"| 合计 | — | {totals['error']} | {totals['warn']} | {totals['info']} | {len(findings)} |")
    out.append("")
    out.append("## 逐条结论")
    out.append("")
    if not findings:
        out.append("（无）")
        return "\n".join(out) + "\n"
    out.append("| # | 级别 | 规则 | 位置 | 说明 | 片段 |")
    out.append("| ---: | --- | --- | --- | --- | --- |")
    for i, finding in enumerate(findings, 1):
        message = finding.message.replace("|", "\\|").replace("\n", " ")
        snippet = finding.snippet.replace("|", "\\|").replace("\n", " ")
        out.append(
            f"| {i} | {finding.severity} | {finding.rule} | `{finding.locator()}` | {message} | {snippet} |"
        )
    return "\n".join(out) + "\n"


def render_tsv(findings: Sequence[Finding]) -> str:
    rows = ["severity\trule\trule_name\tfile\tline\tmessage\tsnippet"]
    for finding in findings:
        cells = [
            finding.severity,
            finding.rule,
            RULE_NAMES.get(finding.rule, ""),
            finding.doc,
            str(finding.line),
            finding.message,
            finding.snippet,
        ]
        rows.append("\t".join(cell.replace("\t", " ").replace("\n", " ") for cell in cells))
    return "\n".join(rows) + "\n"


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def collect_inputs(target: Path) -> tuple[list[Path], Path]:
    """返回（按文件名排序的输入文件列表, 展示根目录）。"""
    if target.is_dir():
        files = [
            p for p in target.iterdir()
            if p.is_file() and p.suffix.lower() in {".md", ".markdown", ".txt"} and not p.name.startswith(".")
        ]
        files.sort(key=lambda p: p.name)
        return files, target
    if target.is_file():
        return [target], target.parent
    raise FileNotFoundError(f"输入不存在: {target}")


FIGURE_FILE_RE = re.compile(r"(?i)(?:^|[_\-\s])(?:fig(?:ure)?)[_\-\s]?(\d{1,3})")


def scan_figure_dir(path: Path) -> dict[int, str]:
    """扫 `--figures` 目录的文件名，识别 fig1/Figure-2/图3 这类图号 → 文件名。"""
    mapping: dict[int, str] = {}
    for candidate in sorted(path.iterdir(), key=lambda p: p.name):
        if not candidate.is_file():
            continue
        match = FIGURE_FILE_RE.search(candidate.stem) or re.search(
            r"(?i)^(?:图|fig(?:ure)?)\s*[_\-\s]?(\d{1,3})", candidate.stem
        )
        if match:
            mapping.setdefault(int(match.group(1)), candidate.name)
    return mapping


def rel_display(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lint_manuscript.py",
        description="离线稿件一致性体检（交叉引用/缩写/标题/统计/过强措辞/引用闭环/跨节重复/术语一致）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python lint_manuscript.py --input drafts/1.2.4_样章.md\n"
            "  python lint_manuscript.py --input drafts --refs refs/_used_in_review.md --config lint-config.json\n"
            "  python lint_manuscript.py --input drafts --out tsv > report.tsv\n"
            "  python lint_manuscript.py --selftest\n"
        ),
    )
    parser.add_argument("--input", "-i", help="稿件 .md 文件或目录（目录按文件名排序拼接）")
    parser.add_argument("--refs", "-r", help="参考文献清单（`1. xxx` 编号制 / .bib）")
    parser.add_argument("--config", "-c", help="JSON 配置（synonyms / 白名单 / overclaim / study_type）")
    parser.add_argument("--out", "-o", choices=["md", "markdown", "tsv"], default="md", help="输出格式，默认 markdown 到 stdout")
    parser.add_argument("--figures", help="可选：图片目录；按 figN/图N 文件名免除 R1 的图引用缺失告警")
    parser.add_argument("--max-findings", type=int, default=500, help="最多输出条数，默认 500")
    parser.add_argument("--sort", choices=["location", "severity", "rule"], default="location", help="输出排序，默认 location")
    parser.add_argument("--selftest", action="store_true", help="运行内置样例回归（0 通过 / 2 失败）")
    parser.add_argument("--list-rules", action="store_true", help="打印规则表后退出")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    # Windows 控制台默认 GBK：输出里带 ¶ / ✓ / ± 等字符会抛 UnicodeEncodeError。
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_rules:
        for rule in RULE_ORDER:
            print(f"{rule}\t{RULE_NAMES[rule]}")
        return 0
    if args.selftest:
        return selftest()

    if not args.input:
        parser.error("必须提供 --input（或使用 --selftest / --list-rules）")
    try:
        config = load_config(args.config)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[lint] 读取配置失败: {exc}", file=sys.stderr)
        return 2

    for warning in config.warnings:
        print(f"[lint] {warning}", file=sys.stderr)

    try:
        files, root = collect_inputs(Path(args.input))
    except FileNotFoundError as exc:
        print(f"[lint] {exc}", file=sys.stderr)
        return 2
    if not files:
        print(f"[lint] 目录中没有 .md/.markdown/.txt 文件: {args.input}", file=sys.stderr)
        return 2

    docs = [build_document(path, rel_display(path, root)) for path in files]
    figure_numbers: dict[int, str] | None = None
    if args.figures:
        figures_dir = Path(args.figures)
        if not figures_dir.is_dir():
            print(f"[lint] --figures 不是目录: {figures_dir}", file=sys.stderr)
            return 2
        figure_numbers = scan_figure_dir(figures_dir)
        if not figure_numbers:
            print(f"[lint] --figures 目录未识别到 figN/图N 命名的图形文件: {figures_dir}", file=sys.stderr)
    refs: RefIndex | None = None
    if args.refs:
        refs_path = Path(args.refs)
        if not refs_path.is_file():
            print(f"[lint] refs 文件不存在: {refs_path}", file=sys.stderr)
            return 2
        refs = parse_refs(refs_path)
        if config.refs_style != "auto":
            if config.refs_style == "author-year":
                # 仅影响解读：仍用解析出的著者-年索引
                pass
    findings = run_rules(
        docs, refs, config, refs_requested=bool(args.refs), figure_numbers=figure_numbers
    )

    if args.sort == "severity":
        findings.sort(key=lambda f: (SEVERITY_RANK.get(f.severity, 9), f.doc, f.line))
    elif args.sort == "rule":
        findings.sort(key=lambda f: (RULE_ORDER.index(f.rule), f.doc, f.line))

    truncated = False
    if len(findings) > args.max_findings:
        findings = findings[: args.max_findings]
        truncated = True

    if args.out == "tsv":
        sys.stdout.write(render_tsv(findings))
    else:
        sys.stdout.write(render_markdown(findings, docs, refs, config, truncated))

    has_error = any(f.severity == "error" for f in findings)
    return 1 if has_error else 0


# --------------------------------------------------------------------------- #
# SELFTEST：内置中英文样例断言（回归用）
# --------------------------------------------------------------------------- #


def _doc_from_text(name: str, text: str) -> Document:
    base = Path(name)
    doc_lines = [SourceLine(name, i, t) for i, t in enumerate(text.splitlines(), 1)]
    sections: list[Section] = []
    paragraphs: list[Paragraph] = []
    current: list[SourceLine] = []
    current_section: int | None = None
    in_fence = False

    def flush() -> None:
        nonlocal current
        if not current:
            return
        joined = "\n".join(sl.text for sl in current)
        stripped = [sl.text.strip() for sl in current if sl.text.strip()]
        paragraphs.append(
            Paragraph(name, list(current), joined, current_section, bool(stripped) and all(s.startswith("|") for s in stripped))
        )
        current = []

    for sl in doc_lines:
        stripped = sl.text.strip()
        if stripped.startswith("```"):
            flush()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not stripped:
            flush()
            continue
        heading = HEADING_RE.match(sl.text)
        if heading:
            flush()
            title = heading.group(2).strip()
            num = NUMBER_PREFIX_RE.match(title)
            sections.append(Section(len(sections), name, len(heading.group(1)), title, num.group("num") if num else None, sl.lineno))
            current_section = len(sections) - 1
            continue
        current.append(sl)
    flush()
    return Document(path=base, display=name, lines=doc_lines, sections=sections, paragraphs=paragraphs)


def _fixtures() -> tuple[list[Document], RefIndex, Config]:
    cn = "\n".join(
        [
            "# 1.2.4 中文测试章",
            "",
            "本研究共纳入120例患者，结果显示干预组显著优于对照组。图3展示了主要结局，表2列出了基线特征。",
            "我们证明该通路是必需的（P = 0.000）。血浆浓度为1.9 ± 0.6 nmol/L。",
            "",
            "丁酸是Ⅰ/Ⅱ类HDAC的抑制剂，可提高组蛋白乙酰化。该结论必然成立，导致疾病风险下降。",
            "",
            "### 1.2.4.1 机械重复测试",
            "",
            "实验结果表明该通路在模型动物中具有保护作用，且这一作用可被抑制剂逆转。",
            "",
            "### 1.2.4.2 再次重复",
            "",
            "实验结果表明该通路在模型动物中具有保护作用，且这一作用可被抑制剂逆转。",
            "",
            "全谷物（whole grain）是核心；全谷物（whole grain）与膳食纤维（dietary fiber）并称。",
            "IIS通路延长寿命，但BRE未定义。",
            "",
            "| 指标 | 值 |",
            "| --- | --- |",
            "| 年龄 | 5 |",
            "",
            "结尾段落引用（张三 2020）与（Smith 2019），并混用 Nrf2 与 NRF2。",
            "",
            "注：IIS，胰岛素/胰岛素样生长因子信号通路；MAO，单胺氧化酶。",
        ]
    )
    en = "\n".join(
        [
            "# 1.2.5 English test section",
            "",
            "We prove that the intervention causes remission in all animals. Levels were significantly higher after treatment.",
            "The n=12 samples were analyzed. Whole-grain diet reduced risk.",
            "",
            "### 1.2.5.1 Results",
            "",
            "Figure 1 shows the effect. Table 1 lists baselines. Whole grain intake was high and the quick brown fox jumps over the lazy dog every morning.",
            "",
            "### 1.2.5.2 Replication",
            "",
            "Again the quick brown fox jumps over the lazy dog in a second section.",
            "",
            "**Table 1** Baseline characteristics.",
            "",
            "（Smith 2019）was cited, and（王五 2021）is missing from refs.",
        ]
    )
    num_text = "\n".join(
        [
            "# 1.9 编号引用测试",
            "",
            "编号引用测试：见表见 [1]，另见 [2]。但这里引用了并不存在的 [9]，属编号跳号。",
        ]
    )
    refs_text = "\n".join(
        [
            "1. Smith J, Doe A. A title. Journal, 2019, 1:1-2",
            "2. 张三，李四．题名．期刊，2020，1:1-2",
            "3. 编号测试条目. Journal, 2022, 2:3-4",
        ]
    )
    refs_path = Path("<selftest-refs.md>")
    refs = parse_refs_from_text(refs_path, refs_text)
    config = Config(
        study_type="observational",
        synonyms=[["全谷物", "whole grain"], ["膳食纤维", "dietary fiber"]],
    )
    return [_doc_from_text("cn.md", cn), _doc_from_text("en.md", en), _doc_from_text("num.md", num_text)], refs, config


def parse_refs_from_text(path: Path, text: str) -> RefIndex:
    """parse_refs 的内存版（selftest 用）。"""
    index = RefIndex(path=path, style="none")
    numeric_entries: dict[int, str] = {}
    for raw_line in text.splitlines():
        match = _NUM_REF_LINE_RE.match(raw_line)
        if match:
            numeric_entries[int(match.group(1))] = match.group(2).strip()
    if numeric_entries:
        index.style = "numeric"
        index.entries = numeric_entries
        for num, body in numeric_entries.items():
            register_entry(index, num, body)
    return index


def selftest() -> int:
    """内置样例回归：逐条断言 8 类规则的关键命中。返回 0 通过 / 2 失败。"""
    docs, refs, config = _fixtures()
    findings = run_rules(docs, refs, config, refs_requested=True)
    keys = {(f.rule, f.severity) for f in findings}
    messages = "\n".join(f"{f.rule}\t{f.severity}\t{f.locator()}\t{f.message}" for f in findings)

    checks: list[tuple[str, bool, str]] = []

    def check(name: str, condition: bool, hint: str = "") -> None:
        checks.append((name, condition, hint))

    check("R1 图表引用无定义 -> error", ("R1", "error") in keys, "图3/图1/表2 应无定义")
    check("R1 有定义且被引用不报错", not any(f.rule == "R1" and f.severity == "error" and "Table 1" in f.message for f in findings))
    check("R2 未定义缩写 BRE -> warn/info", any(f.rule == "R2" and "BRE" in f.message for f in findings))
    check("R2 缩写表晚于首用 -> warn", any(f.rule == "R2" and "IIS" in f.message for f in findings))
    check("R3 标题跳级 -> warn", any(f.rule == "R3" and "跳级" in f.message for f in findings))
    check("R4 P = 0.000 -> error", any(f.rule == "R4" and "P = 0.000" in f.message for f in findings))
    check("R4 ± 无样本量 -> warn", any(f.rule == "R4" and "±" in f.message for f in findings))
    check("R4 n= 无统计方法 -> warn", any(f.rule == "R4" and "n=" in f.message for f in findings))
    check("R5 中文 证明/必然/导致 -> 命中", any(f.rule == "R5" and ("证明" in f.message or "必然" in f.message) for f in findings))
    check("R5 英文 prove/causes -> error(observational)", any(f.rule == "R5" and f.severity == "error" and "prove" in f.message for f in findings))
    check("R5 significantly 无统计量 -> warn", any(f.rule == "R5" and "significantly" in f.message for f in findings))
    check("R6 著者-年未匹配 -> warn", any(f.rule == "R6" and "王五" in f.message for f in findings))
    check("R6 编号越界 -> error", any(f.rule == "R6" and f.severity == "error" and "超过" in f.message for f in findings), "num.md 引用了 [9]")
    check("R6 编号引用不存在的条目 -> error", any(f.rule == "R6" and f.severity == "error" and "不存在" in f.message for f in findings))
    check("R6 年份一致不报错", not any(f.rule == "R6" and "Smith" in f.message and "不一致" in f.message for f in findings))
    check("R6 未引用 refs 条目 -> 报告", any(f.rule == "R6" and "从未被正文引用" in f.message for f in findings))
    check("R7 跨节英文重复 -> info", any(f.rule == "R7" and f.severity == "info" and "quick brown fox" in f.message for f in findings))
    check("R7 跨节中文重复 -> info", any(f.rule == "R7" and "实验结果表明" in f.message for f in findings))
    check("R8 同义词混用 -> warn", any(f.rule == "R8" and "同义术语混用" in f.message for f in findings))
    check("R8 大小写不一致 -> info", any(f.rule == "R8" and "大小写不一致" in f.message for f in findings))
    check("R8 连字符不一致 -> info", any(f.rule == "R8" and "连字符" in f.message for f in findings))

    # 渲染与退出码逻辑
    md = render_markdown(findings, docs, refs, config, truncated=False)
    tsv = render_tsv(findings)
    check("markdown 渲染含规则统计表", "规则命中统计" in md and "| R1 |" in md)
    check("tsv 渲染含表头", tsv.startswith("severity\trule"))
    check("error 存在时 exit=1", (1 if any(f.severity == "error" for f in findings) else 0) == 1)
    clean_findings = run_rules(
        [_doc_from_text("clean.md", "# 1.1 干净\n\n（Smith 2019）与图1、表1。\n\n![图1 示意图](fig1.png)\n\n**表1** 基线。\n")],
        None,
        Config(),
    )
    check("无 error 时 exit=0", (1 if any(f.severity == "error" for f in clean_findings) else 0) == 0)

    failures = [item for item in checks if not item[1]]
    for name, ok, hint in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}{('  // ' + hint) if (hint and not ok) else ''}")
    print()
    print(f"selftest: {len(checks) - len(failures)}/{len(checks)} passed")
    if failures:
        print("\n--- 失败时的全部命中（调试用）---")
        print(messages)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())


# =========================================================================== #
# 实测记录（2026-11-06，Windows，Python 3.10.2，纯标准库，无网络）
# --------------------------------------------------------------------------- #
# 自测：
#   python lint_manuscript.py --selftest
#   → 25/25 passed，退出码 0
#   （中英文混合样例覆盖 R1–R8 每条规则；含编号制 [9] 越界、著者-年制年份不符、
#     第二作者引用、跨节重复合并、游离加粗等断言）
#
# 真实稿件（1.2.4_样章.md，refs=_used_in_review.md 165 条编号制，36 条正文引用全部命中）：
#   python lint_manuscript.py --input "E:\2026\毕业论文综述部分撰写\drafts\1.2.4_样章.md" \
#     --refs "E:\2026\毕业论文综述部分撰写\refs\_used_in_review.md"
#   → 退出码 1；error 2 / warn 8 / info 14
#     R1 2/0/0（图1、表1 无图注/表题）  R2 0/5/12  R3 0/0/0  R4 0/0/0
#     R5 0/3/0（显著×2、必然×1）       R6 0/0/1（单节视角 129/165 条未引用，自动降 info）
#     R7 0/0/1（第 11/17 行 12 字短语重复） R8 0/0/0
#
# 真实稿件（1.2.5.md）：
#   python lint_manuscript.py --input "E:\2026\毕业论文综述部分撰写\drafts\1.2.5.md" \
#     --refs "E:\2026\毕业论文综述部分撰写\refs\_used_in_review.md"
#   → 退出码 1；error 1 / warn 11 / info 12
#     R1 1/0/0（表2 无表题）  R2 0/4/9（IIS/SOD/CAT/MDA 仅在文末缩写表定义）
#     R3 0/0/1（第 17 行 **。** 游离加粗）  R4 0/1/1（1.9 ± 0.6 nmol/L 无 n、未声明 SD/SEM）
#     R5 0/6/0（显著×4、证明×2）  R6 0/0/1  R7 0/0/0  R8 0/0/0
#
# 全稿（9 个分节）+ refs + --figures：
#   python lint_manuscript.py --input "E:\2026\毕业论文综述部分撰写\drafts" \
#     --refs "E:\2026\毕业论文综述部分撰写\refs\_used_in_review.md" \
#     --figures "E:\2026\毕业论文综述部分撰写\figures"
#   → 退出码 1；error 2 / warn 40 / info 74（耗时 ~0.5 s）
#     R1 2/0/1：--figures 认出 图1–图4 文件名，error 从 5 降到 2（只剩 表1、表2 无题注）
#     R6 0/3/0：refs 仅 5/165 条从未被引用；抓到 "Nesse 1991"（refs 第 150 条第一作者为
#              Williams，按第二作者引用）与 "Le 2003"（应为 Le Poul 2003，姓氏截断）
#     R3 0/0/3：1.2.5 / 1.2.6 / 1.2.7 各一处 **。** 游离加粗
#     R7 0/0/13：如 1.2.6 内跨段复制「碳水化合物含量蛋白含量与」、1.2.4「的绝大部分以酯键锚定于细」
#
# 已知误报/局限（实测确认，详见模块 docstring 与 references/lint-examples.md）：
#   * R2 对基因/受体符号（GPR109A、AMPK、NFAT、HMGCR…）默认 info/warn，需白名单收敛；
#     缩写按文件独立判定，跨节共享缩写应在整合稿上跑。
#   * R5 会把评价性比较（“解释力度显著高于…”）误判为统计声明；「显著」语用边界需人工复核。
#   * R1 只认 Markdown 中的图注/表题；--figures 仅按文件名免除告警，不核对题注文字。
#   * R7 中文以 12 汉字≈8 词近似（不分词）；单节文件退化为段间重复。
#   * R6 以“第一作者姓+年份”匹配，同名不同人/机构作者仍可能误配。
# =========================================================================== #

