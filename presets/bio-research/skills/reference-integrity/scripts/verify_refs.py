#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_refs.py — 参考文献真实性与撤稿/勘误状态校验（Crossref + PubMed E-utilities + Europe PMC）。

仅用 Python 3 标准库（urllib / json / argparse / csv / re / socket），无需 pip 安装任何包。

用法示例：
    python verify_refs.py --input refs.bib
    python verify_refs.py --input refs.txt --out ref_report.tsv --json ref_report.json
    python verify_refs.py --text "见 10.1038/s41586-020-2649-2 与 PMID: 32572269"
    python verify_refs.py --doi 10.1016/S0140-6736(97)11096-0 --doi 10.1126/science.abb2507
    python verify_refs.py --input refs.bib --use-proxy        # 显式使用系统/环境代理

输出列（TSV）：input, kind, resolved_doi, pmid, title, journal, year, first_author,
exists, retracted, corrected, flags
退出码：0 = 全部 exists 且无 retracted；1 = 有 NOT_FOUND / ERROR / retracted。
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import os
import random
import re
import socket
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

VERSION = "1.0.0"

CROSSREF_WORKS = "https://api.crossref.org/works/"
PUBMED_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
EPMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

DEFAULT_TIMEOUT = 20          # 单请求超时（秒）
DEFAULT_RETRIES = 2           # 失败重试次数（总计尝试 3 次）
DELAY_MIN, DELAY_MAX = 0.4, 0.6   # 相邻请求间隔（秒）

# 书目匹配（GB/T 7714 等无 DOI/PMID 的引用）阈值
MATCH_THRESHOLD = 0.80        # >= 0.80 且年份差 <= 1 -> MATCHED
AMBIGUOUS_THRESHOLD = 0.60    # 0.60–0.80 -> AMBIGUOUS（人工确认）
YEAR_TOLERANCE = 1
CROSSREF_BIB_ROWS = 5
CROSSREF_BIB_SELECT = ("DOI,title,container-title,issued,author,volume,page,"
                       "updated-by,update-to,relation")

COLUMNS = [
    "input", "kind", "resolved_doi", "pmid", "title", "journal",
    "year", "first_author", "exists", "retracted", "corrected", "flags",
    # --bibliographic 模式追加列（默认留空，不影响原有 12 列的含义与顺序）
    "match_confidence", "matched_title", "matched_journal", "matched_year",
]

# ---------------------------------------------------------------- 正则表

# DOI 后缀只取 ASCII 合法字符，避免把紧随其后的中文/全角标点吞进 DOI
DOI_RE = re.compile(r"10\.\d{4,9}/[A-Za-z0-9\-._;:()/<>~\[\]%*+!$&=?]+")
PMID_LABELED_RE = re.compile(r"(?i)\bpmid\s*[:#\s]*(\d{1,8})\b")
PMID_URL_RE = re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d{1,8})")
BARE_NUMBER_RE = re.compile(r"^\d{1,8}$")
BIB_FIELD_RE = re.compile(r"\s*,?\s*([A-Za-z][A-Za-z0-9_:.\-]*)\s*=\s*")
YEAR_RE = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")

RETRACTION_HINTS = ("retract", "withdraw")
CORRECTION_HINTS = ("correction", "erratum", "corrected", "addendum")
EOC_HINTS = ("expression of concern", "concern")


class RemoteError(Exception):
    """远程接口失败；code 形如 http-503 / timeout / network:xxx / bad-json。"""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


# ---------------------------------------------------------------- 小工具

def clean_text(value, limit=400):
    """单行化 + 限长，保证 TSV/JSON 可读。"""
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\t", " ").replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text[:limit]


def short_reason(text, limit=60):
    text = clean_text(text, limit)
    return text or "unknown"


def slug_reason(text):
    """把底层网络异常归成稳定短码，保证 TSV 里 ERROR:<reason> 可读且稳定。"""
    raw = str(text or "")
    lowered = raw.lower()
    if "timed out" in lowered or "10060" in raw:
        return "timeout"
    if "10061" in raw or "refused" in lowered or "积极拒绝" in raw:
        return "connection-refused"
    if "getaddrinfo" in lowered or "11001" in raw or "name or service not known" in lowered:
        return "dns-failure"
    if "certificate" in lowered or "[ssl" in lowered or "ssl:" in lowered:
        return "tls-error"
    if "reset" in lowered or "10054" in raw:
        return "connection-reset"
    if "unreachable" in lowered or "10051" in raw:
        return "network-unreachable"
    slug = re.sub(r"[^0-9A-Za-z_.:\-]+", "-", raw).strip("-")
    return slug[:48] or "unknown"


def trim_doi(raw):
    """去掉 DOI 尾部粘连的句读符号；保留 DOI 自带括号（如 (97)11096-0）。"""
    doi = (raw or "").strip()
    while doi:
        last = doi[-1]
        if last in ".,;:'\"<>":
            doi = doi[:-1]
            continue
        if last == ")" and doi.count(")") > doi.count("("):
            doi = doi[:-1]
            continue
        if last == "]" and doi.count("]") > doi.count("["):
            doi = doi[:-1]
            continue
        if last == "}" and doi.count("}") > doi.count("{"):
            doi = doi[:-1]
            continue
        if last == "(" and doi.count("(") > doi.count(")"):
            doi = doi[:-1]
            continue
        if last == "[" and doi.count("[") > doi.count("]"):
            doi = doi[:-1]
            continue
        break
    return doi


def normalize_doi(raw):
    """把 doi:10.x / https://doi.org/10.x / 裸 10.x 统一成裸 DOI；非法返回 ''。"""
    text = (raw or "").strip().strip("<>\"'()[]{}")
    text = re.sub(r"(?i)^\s*(doi|dx\.doi\.org|https?://(dx\.)?doi\.org/)\s*[:/]?\s*", "", text)
    text = text.strip()
    match = DOI_RE.search(text)
    if not match:
        return ""
    return trim_doi(match.group(0))


def digits_only(raw):
    text = (raw or "").strip()
    match = re.fullmatch(r"\d{1,10}", text)
    return text if match else ""


def plausible_bare_pmid(token):
    """无标签的纯数字：排除 1900–2100 的年份误判，其余 1–8 位数字视作 PMID。"""
    if not BARE_NUMBER_RE.match(token):
        return False
    number = int(token)
    if len(token) <= 4 and 1900 <= number <= 2100:
        return False
    return 1 <= number <= 99_999_999


def read_text_file(path):
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        try:
            with open(path, "r", encoding=encoding) as handle:
                return handle.read()
        except (UnicodeDecodeError, LookupError):
            continue
        except OSError as exc:
            raise SystemExit("无法读取输入文件 %s：%s" % (path, exc))
    raise SystemExit("无法解码输入文件 %s（尝试了 utf-8/gb18030/latin-1）" % path)


# ---------------------------------------------------------------- 输入解析

def parse_bib_fields(body):
    """解析一条 BibTeX 条目正文 -> {"__key__": key, field: value}。支持嵌套花括号。"""
    depth = 0
    cut = 0
    for index, char in enumerate(body):
        if char in "{(":
            depth += 1
        elif char in "})":
            depth -= 1
        elif char == "," and depth == 0:
            cut = index
            break
    else:
        cut = len(body)
    key = body[:cut].strip()
    rest = body[cut + 1:]
    fields = {}
    pos = 0
    while pos < len(rest):
        match = BIB_FIELD_RE.match(rest, pos)
        if not match:
            nxt = rest.find(",", pos)
            if nxt == -1:
                break
            pos = nxt + 1
            continue
        name = match.group(1).lower()
        cursor = match.end()
        if cursor < len(rest) and rest[cursor] in "{":
            depth = 0
            end = cursor
            while end < len(rest):
                if rest[end] == "{":
                    depth += 1
                elif rest[end] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                end += 1
            value = rest[cursor + 1:end]
            pos = end + 1
        elif cursor < len(rest) and rest[cursor] == '"':
            end = rest.find('"', cursor + 1)
            if end == -1:
                end = len(rest) - 1
            value = rest[cursor + 1:end]
            pos = end + 1
        else:
            token = re.match(r"[^,\s}]+", rest[cursor:])
            if not token:
                break
            value = token.group(0)
            pos = cursor + token.end()
        fields.setdefault(name, clean_text(value, 2000))
    return {"__key__": key, **fields}


def parse_bib_entries(text):
    """扫描整份 .bib，返回条目字段列表。"""
    entries = []
    index = 0
    while True:
        at = text.find("@", index)
        if at == -1:
            break
        match = re.match(r"@\s*([A-Za-z]+)\s*[{(]", text[at:])
        if not match:
            index = at + 1
            continue
        kind = match.group(1).lower()
        open_pos = at + match.end() - 1
        depth = 0
        cursor = open_pos
        while cursor < len(text):
            char = text[cursor]
            if char in "{(":
                depth += 1
            elif char in "})":
                depth -= 1
                if depth == 0:
                    break
            cursor += 1
        body = text[open_pos + 1:cursor]
        index = cursor + 1
        if kind in ("comment", "string", "preamble"):
            continue
        entries.append(parse_bib_fields(body))
    return entries


def scan_text(text):
    """从自由文本抽取 DOI / PMID，保持出现顺序。"""
    found = []  # (pos, kind, value)
    for match in DOI_RE.finditer(text):
        doi = trim_doi(match.group(0))
        if doi and "/" in doi:
            found.append((match.start(), "doi", doi))
    for match in PMID_LABELED_RE.finditer(text):
        found.append((match.start(1), "pmid", match.group(1)))
    for match in PMID_URL_RE.finditer(text):
        found.append((match.start(1), "pmid", match.group(1)))
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.strip().strip(",;")
        if BARE_NUMBER_RE.match(stripped) and plausible_bare_pmid(stripped):
            found.append((offset + line.find(stripped), "pmid", stripped))
        offset += len(line)
    found.sort(key=lambda item: (item[0], item[1]))
    return found


def items_from_csv(text):
    """CSV：优先按表头 doi/pmid 列取值；否则逐格识别 DOI 与 PMID。"""
    rows = []
    try:
        reader = csv.reader(text.splitlines())
        table = [row for row in reader if any(cell.strip() for cell in row)]
    except csv.Error:
        return scan_text(text) if text.strip() else []
    if not table:
        return []
    header = [cell.strip().lower() for cell in table[0]]
    doi_cols = [i for i, name in enumerate(header) if "doi" in name]
    pmid_cols = [i for i, name in enumerate(header) if "pmid" in name or "pubmed" in name]
    body = table[1:] if (doi_cols or pmid_cols) else table
    for offset, row in enumerate(body):
        position = offset + 1
        hit = False
        for column in doi_cols:
            if column < len(row):
                doi = normalize_doi(row[column])
                if doi:
                    rows.append((position, "doi", doi))
                    hit = True
        for column in pmid_cols:
            if column < len(row):
                pmid = digits_only(row[column])
                if pmid:
                    rows.append((position, "pmid", pmid))
                    hit = True
        if hit:
            continue
        for cell in row:
            doi = normalize_doi(cell)
            if doi:
                rows.append((position, "doi", doi))
                continue
            value = cell.strip().strip(",;")
            if plausible_bare_pmid(value) and len(value) >= 6:
                rows.append((position, "pmid", value))
    return rows


def items_from_bib(path, allow_bibliographic=False):
    entries = parse_bib_entries(read_text_file(path))
    items = []
    for entry in entries:
        key = entry.get("__key__", "")
        source = "bib:%s" % (key or "?")
        doi = normalize_doi(entry.get("doi", ""))
        if not doi:
            for field in ("url", "note", "howpublished", "eprint", "journal", "booktitle"):
                candidate = entry.get(field, "")
                if not candidate:
                    continue
                match = DOI_RE.search(candidate)
                if match:
                    doi = trim_doi(match.group(0))
                    break
        pmid = digits_only(entry.get("pmid", ""))
        if not pmid:
            for field in ("note", "url", "pmid", "eprint"):
                match = PMID_LABELED_RE.search(entry.get(field, "") or "")
                if match:
                    pmid = match.group(1)
                    break
        if doi:
            items.append({"pos": 0, "kind": "doi", "value": doi, "source": source,
                          "expect_pmid": pmid})
        elif pmid:
            items.append({"pos": 0, "kind": "pmid", "value": pmid, "source": source,
                          "expect_pmid": ""})
        elif allow_bibliographic:
            # 无 DOI/PMID：用 bib 字段做书目检索
            ref = {
                "raw": source,
                "authors": entry.get("author", ""),
                "first_author": first_author_of(entry.get("author", "")),
                "title": clean_text(entry.get("title", ""), 500),
                "journal": clean_text(entry.get("journal") or entry.get("booktitle") or "", 160),
                "year": first_year(entry.get("year"), entry.get("date")),
                "volume_pages": clean_text(entry.get("pages", ""), 60),
            }
            items.append({"pos": 0, "kind": "bibliographic", "value": source,
                          "source": source, "expect_pmid": "", "ref": ref})
        else:
            items.append({"pos": 0, "kind": "bib-no-id", "value": source,
                          "source": source, "expect_pmid": ""})
    return items


# ---------------------------------------------------------------- 书目匹配（GB/T 7714 等无 DOI 引用）

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
LIST_MARKER_RE = re.compile(r"^\s*(?:[-*+]|\[\d+\]|\d{1,3}[.、)）])\s*")
ET_AL_RE = re.compile(r"(?i)^et\s+al\.?\s*")
AUTHOR_PARTICLES = ("van", "von", "de", "der", "del", "da", "di", "la", "le")


def looks_like_author_chunk(chunk):
    """作者段判断：≤4 个词、含字母、首词大写或介词。

    用词数而非字符集判断，才能兼容 Delmée / Ferrières / Seppälä 等带变音符的姓名。
    """
    text = chunk.strip(" .,;:")
    if not text:
        return True
    if re.fullmatch(r"(?i)et\s+al", text):
        return True
    if not re.search(r"[^\W\d_]", text, re.UNICODE):
        return False
    tokens = text.split()
    if len(tokens) > 4:
        return False
    return any(token[:1].isupper() or token.lower() in AUTHOR_PARTICLES
               for token in tokens)


def strip_leading_authors(segment):
    """作者列表与题目被同一分隔符粘连时，剥掉前导作者段。

    例："... Koren S, et al A complete reference genome improves ..." -> 只留题目。
    """
    segment = str(segment or "").strip()
    chunks = [chunk.strip() for chunk in segment.split(",")]
    index = 0
    while index < len(chunks) and looks_like_author_chunk(chunks[index]):
        index += 1
    if 0 < index < len(chunks):
        rest = ", ".join(chunks[index:]).strip()
    else:
        rest = segment
    rest = ET_AL_RE.sub("", rest)
    return rest.strip(" ,;，")


def has_cjk(text):
    return bool(CJK_RE.search(str(text or "")))


def split_reference_segments(text):
    """按句子分隔符切分：作者段 / 题目段 / 期刊+年份段（兼容全角 ．与半角 . ）。"""
    normalized = str(text or "").replace("。", "．")
    segments = []
    for piece in re.split(r"．|\.\s+", normalized):
        cleaned = piece.strip(" \t\r\n．.,;:，。；：、")
        if cleaned:
            segments.append(cleaned)
    return segments


def first_author_of(authors_text):
    for bit in re.split(r"[,，;；]", str(authors_text or "")):
        bit = re.sub(r"(?i)\s*et\s+al\.?$", "", bit.strip())
        if bit:
            return clean_text(bit, 80)
    return ""


def parse_bibliographic_reference(text):
    """解析一条无 DOI/PMID 的引用：作者/题目/期刊/年份/卷页。

    兼容 GB/T 7714 中文格式（全角 ．，：）与英文 Vancouver 格式（半角 ". "）。
    """
    raw = LIST_MARKER_RE.sub("", clean_text(text, 1200)).strip()
    ref = {"raw": raw, "authors": "", "first_author": "", "title": "",
           "journal": "", "year": "", "volume_pages": ""}
    segments = split_reference_segments(raw)
    if not segments:
        return ref
    if len(segments) == 1:
        ref["title"] = segments[0]
        match = YEAR_RE.search(segments[0])
        if match:
            ref["year"] = match.group(1)
        return ref

    journal_index = -1
    for index in range(len(segments) - 1, 0, -1):
        if YEAR_RE.search(segments[index]):
            journal_index = index
            break

    if journal_index <= 0:
        ref["authors"] = segments[0]
        ref["first_author"] = first_author_of(segments[0])
        body = segments[1:] or segments[:1]
        ref["title"] = max(body, key=len).strip()
        match = YEAR_RE.search(raw)
        if match:
            ref["year"] = match.group(1)
        return ref

    ref["authors"] = segments[0]
    ref["first_author"] = first_author_of(segments[0])
    title_parts = segments[1:journal_index]
    if title_parts:
        ref["title"] = " ".join(title_parts).strip()
    else:
        # 作者与题目被同一分隔符粘连：剥掉前导作者段（如 "... Koren S, et al A complete ..."）
        ref["title"] = strip_leading_authors(segments[journal_index - 1])

    tail = segments[journal_index]
    match = YEAR_RE.search(tail)
    if match:
        ref["year"] = match.group(1)
    bits = [bit.strip(" ．.,;:，。；：") for bit in re.split(r"[,，]", tail) if bit.strip()]
    journal_bits = []
    volume_bits = []
    for bit in bits:
        if YEAR_RE.fullmatch(bit.strip()):
            continue
        if not journal_bits:
            if "：" in bit and not re.search(r"[A-Za-z]", bit.split("：")[0]):
                bit = bit.split("：")[-1]   # 出版地：出版社 -> 出版社
            journal_bits.append(bit)
        else:
            volume_bits.append(bit)
    ref["journal"] = clean_text(" ".join(journal_bits), 120)
    ref["volume_pages"] = clean_text(" ".join(volume_bits), 60)
    return ref


GREEK_TO_LATIN = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon",
    "ζ": "zeta", "η": "eta", "θ": "theta", "κ": "kappa", "λ": "lambda",
    "μ": "mu", "ν": "nu", "ξ": "xi", "π": "pi", "ρ": "rho", "σ": "sigma",
    "τ": "tau", "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega",
}


def normalize_for_match(text):
    text = unicodedata.normalize("NFKC", str(text or "")).lower()
    # 希腊字母转写：标题里 β-glucans / beta-glucans 混用很常见
    text = "".join(GREEK_TO_LATIN.get(char, char) for char in text)
    text = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def title_similarity(left, right):
    """题目相似度（0–1）：difflib 比值与词级 Jaccard 取较大值。"""
    left_norm, right_norm = normalize_for_match(left), normalize_for_match(right)
    if not left_norm or not right_norm:
        return 0.0
    ratio = difflib.SequenceMatcher(None, left_norm, right_norm).ratio()
    tokens_left = set(left_norm.split())
    tokens_right = set(right_norm.split())
    if tokens_left and tokens_right:
        jaccard = len(tokens_left & tokens_right) / len(tokens_left | tokens_right)
    else:
        jaccard = 0.0
    return round(max(ratio, jaccard), 3)


def containment_boost(reference_title, candidate_title, base_score):
    """引用题目常带章节标题/副标题/机构附注：候选题目被完整包含时给一次兜底加分。"""
    ref_norm = normalize_for_match(reference_title)
    cand_norm = normalize_for_match(candidate_title)
    if len(cand_norm) >= 25 and cand_norm in ref_norm:
        if len(cand_norm) / max(len(ref_norm), 1) >= 0.5:
            return max(base_score, 0.90)
    if len(ref_norm) >= 25 and ref_norm in cand_norm:
        if len(ref_norm) / max(len(cand_norm), 1) >= 0.5:
            return max(base_score, 0.90)
    return base_score


def crossref_query(ctx, params):
    """执行一次 Crossref works 检索；select 字段被拒时自动退化为不 select。"""
    full = dict(params)
    if ctx.email:
        full.setdefault("mailto", ctx.email)
    payload = fetch_json(ctx, CROSSREF_WORKS + "?" + urllib.parse.urlencode(full))
    if payload is None:
        full.pop("select", None)
        payload = fetch_json(ctx, CROSSREF_WORKS + "?" + urllib.parse.urlencode(full))
    if not payload:
        return None
    return ((payload.get("message") or {}).get("items")) or []


# Crossref 里有一类"关于某文的记录"（评论、推荐、决定信、勘误），题目里带着原文题目，
# 容易被当成原文命中，需要降权。
META_RECORD_PREFIXES = (
    "faculty opinions recommendation of",
    "comment on:",
    "response to comment on:",
    "decision letter:",
    "decision letter for",
    "editor's evaluation:",
    "editorial expression of concern",
    "publisher correction:",
    "correction to:",
)
META_RECORD_PENALTY = 0.20


def meta_record_penalty(candidate_title):
    lowered = normalize_for_match(candidate_title)
    for prefix in META_RECORD_PREFIXES:
        if lowered.startswith(normalize_for_match(prefix)):
            return META_RECORD_PENALTY, prefix
    return 0.0, ""


def best_candidate(ref, items):
    """在候选里按题目相似度（含包含关系加分、年份降权、元记录降权）选最佳。"""
    ref_title = ref.get("title") or ""
    ref_year = ref.get("year") or ""
    best = None
    for item in items or []:
        candidate_title = (item.get("title") or [""])[0]
        candidate_journal = (item.get("container-title") or [""])[0]
        raw_score = title_similarity(ref_title, candidate_title)
        raw_score = containment_boost(ref_title, candidate_title, raw_score)
        journal_score = title_similarity(ref.get("journal"), candidate_journal) \
            if ref.get("journal") and candidate_journal else None
        meta_penalty, meta_prefix = meta_record_penalty(candidate_title)
        candidate_year = first_year(item.get("issued"))
        year_delta = None
        if ref_year and candidate_year:
            try:
                year_delta = abs(int(ref_year) - int(candidate_year))
            except ValueError:
                year_delta = None
        penalty = meta_penalty
        if year_delta is not None and year_delta > YEAR_TOLERANCE:
            # 高相似但年份不符，通常是评论/勘误/再发表版本，降权避免误判 MATCHED
            penalty += min(0.25, 0.08 * year_delta)
        confidence = round(max(0.0, raw_score - penalty), 3)
        entry = {"item": item, "confidence": confidence, "year_delta": year_delta,
                 "candidate_year": candidate_year, "title": candidate_title,
                 "journal": candidate_journal, "journal_score": journal_score,
                 "meta_prefix": meta_prefix}
        if best is None:
            best = entry
            continue
        if entry["confidence"] > best["confidence"] + 0.03:
            best = entry
        elif abs(entry["confidence"] - best["confidence"]) <= 0.03:
            # 分数接近时优先期刊对得上的候选（区分原文与译文/再发表版）
            if (entry["journal_score"] or 0.0) > (best["journal_score"] or 0.0) + 0.2:
                best = entry
    return best


def bibliographic_candidates(ctx, title, journal, year):
    """先按题目精确检索（query.title，精度高），不足再退化成书目检索（query.bibliographic）。"""
    if not title:
        return []
    title_items = crossref_query(ctx, {
        "query.title": title,
        "rows": str(CROSSREF_BIB_ROWS),
        "select": CROSSREF_BIB_SELECT,
    })
    if title_items:
        probe = best_candidate({"title": title, "journal": journal, "year": year}, title_items)
        if probe and probe["confidence"] >= MATCH_THRESHOLD:
            return title_items

    bib_query = " ".join(part for part in (title, journal, year) if part)
    bib_items = crossref_query(ctx, {
        "query.bibliographic": bib_query,
        "rows": str(CROSSREF_BIB_ROWS),
        "select": CROSSREF_BIB_SELECT,
    })
    if bib_items is None:
        return title_items
    if not title_items:
        return bib_items
    seen = {(item.get("DOI") or "").lower() for item in title_items}
    return title_items + [item for item in bib_items
                          if (item.get("DOI") or "").lower() not in seen]


def apply_best_candidate(row, ref, best):
    """把最佳候选写进报告行，并给出 MATCHED / AMBIGUOUS / NOT_FOUND。"""
    ref_title = ref.get("title") or row["_query"]
    if best is None:
        row["exists"] = "NOT_FOUND"
        row["flags"].append("no-crossref-candidate")
        return

    item = best["item"]
    row["match_confidence"] = "%.3f" % best["confidence"]
    row["matched_title"] = clean_text(best["title"], 300)
    row["matched_journal"] = clean_text(best["journal"], 160)
    row["matched_year"] = best["candidate_year"]
    row["resolved_doi"] = clean_text(item.get("DOI") or "", 200)
    row["_retraction_known"] = True
    crossref_update_signals(row, item, best["title"])

    if best["year_delta"]:
        row["flags"].append("year-offset:%d" % best["year_delta"])
    if best.get("meta_prefix"):
        row["flags"].append("meta-record-candidate:%s" % clean_text(best["meta_prefix"], 40))
    if (best["journal_score"] is not None and best["confidence"] >= 0.90
            and best["journal_score"] < 0.35):
        # 题目高度一致但期刊对不上：常见于译文/再发表版本，或引用里的期刊写错
        row["flags"].append("journal-mismatch:ref=%s,matched=%s" % (
            clean_text(ref.get("journal"), 40), clean_text(best["journal"], 40)))
    if best["confidence"] >= MATCH_THRESHOLD:
        row["exists"] = "MATCHED"
    elif best["confidence"] >= AMBIGUOUS_THRESHOLD:
        row["exists"] = "AMBIGUOUS"
        row["flags"].append("manual-check-required")
    else:
        row["exists"] = "NOT_FOUND"
        row["flags"].append("low-similarity:%.3f" % best["confidence"])
        if has_cjk(ref_title):
            row["flags"].append("crossref-coverage-limited")


def reference_entries_from_text(text):
    """把参考文献列表（每行一条，可带 1./[1]/- 前缀）抽成可做书目检索的条目。"""
    entries = []
    for raw_line in text.splitlines():
        if raw_line.lstrip().startswith("#"):
            continue
        line = LIST_MARKER_RE.sub("", raw_line.strip()).strip()
        if not line:
            continue
        if DOI_RE.search(line) or PMID_LABELED_RE.search(line):
            continue  # 已有 DOI/PMID，走常规路径
        if len(line) < 30 or not YEAR_RE.search(line):
            continue
        words = len(re.findall(r"[A-Za-z]+", line))
        cjk_chars = len(CJK_RE.findall(line))
        if words < 5 and cjk_chars < 8:
            continue
        entries.append(line)
    return entries


def collect_items(args):
    """合并 --input / --text / --doi / --pmid，去重并保持顺序。"""
    items = []
    bibliographic = bool(getattr(args, "bibliographic", False))
    for path in args.input or []:
        if not os.path.isfile(path):
            raise SystemExit("输入文件不存在：%s" % path)
        lower = path.lower()
        basename = os.path.basename(path)
        if lower.endswith(".bib"):
            items.extend(items_from_bib(path, allow_bibliographic=bibliographic))
            continue
        text = read_text_file(path)
        if lower.endswith(".csv"):
            found = items_from_csv(text)
        else:
            found = scan_text(text)
        for position, kind, value in found:
            items.append({"pos": position, "kind": kind, "value": value,
                          "source": basename, "expect_pmid": ""})
        if bibliographic and not lower.endswith(".csv"):
            # 参考文献列表（.md/.txt），逐行做书目检索
            for position, line in enumerate(reference_entries_from_text(text)):
                items.append({"pos": position, "kind": "bibliographic", "value": line,
                              "source": basename, "expect_pmid": "",
                              "ref": parse_bibliographic_reference(line)})
    if args.text:
        for position, kind, value in scan_text(args.text):
            items.append({"pos": position, "kind": kind, "value": value,
                          "source": "--text", "expect_pmid": ""})
        if bibliographic:
            for position, line in enumerate(reference_entries_from_text(args.text)):
                items.append({"pos": position, "kind": "bibliographic", "value": line,
                              "source": "--text", "expect_pmid": "",
                              "ref": parse_bibliographic_reference(line)})
    for raw in args.doi or []:
        doi = normalize_doi(raw)
        if doi:
            items.append({"pos": 0, "kind": "doi", "value": doi, "source": "--doi",
                          "expect_pmid": ""})
        else:
            items.append({"pos": 0, "kind": "invalid", "value": clean_text(raw, 80),
                          "source": "--doi", "expect_pmid": ""})
    for raw in args.pmid or []:
        pmid = digits_only(raw)
        if pmid:
            items.append({"pos": 0, "kind": "pmid", "value": pmid, "source": "--pmid",
                          "expect_pmid": ""})
        else:
            items.append({"pos": 0, "kind": "invalid", "value": clean_text(raw, 80),
                          "source": "--pmid", "expect_pmid": ""})
    return items


# ---------------------------------------------------------------- 网络层

class Throttle:
    """保证相邻请求间隔 0.4–0.6 秒（或 --interval 固定值）。"""

    def __init__(self, interval=None):
        self.interval = interval
        self.last = 0.0

    def wait(self):
        delay = self.interval if self.interval else random.uniform(DELAY_MIN, DELAY_MAX)
        gap = delay - (time.monotonic() - self.last)
        if gap > 0:
            time.sleep(gap)
        self.last = time.monotonic()


class Ctx:
    def __init__(self, args):
        self.timeout = args.timeout
        self.retries = max(0, args.retries)
        self.interval = args.interval
        self.throttle = Throttle(args.interval)
        self.email = args.email
        self.tool = args.tool
        self.use_epmc = not args.no_europepmc
        self.verbose = not args.quiet
        self.headers = {
            "User-Agent": "dsh-verify-refs/%s (python-urllib; mailto:%s)"
                          % (VERSION, self.email),
            "Accept": "application/json",
            "Connection": "close",
        }
        if args.use_proxy:
            # 走环境/系统代理（默认 ProxyHandler 会读取 http(s)_proxy 与 Windows 注册表）
            self.opener = urllib.request.build_opener()
        else:
            # 关键：直连 opener + no_proxy=*，绕开 Windows 注册表代理把 https 指到 HTTP 代理端口
            self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def sleep_backoff(self, attempt):
        time.sleep(min(3.0, (self.interval or DELAY_MAX) * (attempt + 2)))


def configure_direct_http(use_proxy):
    """默认强制直连：设置 no_proxy=* / NO_PROXY=*，并清掉 urllib 看到的代理来源。"""
    if use_proxy:
        return
    os.environ["no_proxy"] = "*"
    os.environ["NO_PROXY"] = "*"
    # 某些环境里 urllib 仍会从注册表取代理；下面确保 getproxies 看到的是空集
    os.environ.pop("http_proxy", None)
    os.environ.pop("https_proxy", None)
    os.environ.pop("HTTP_PROXY", None)
    os.environ.pop("HTTPS_PROXY", None)
    os.environ.pop("all_proxy", None)
    os.environ.pop("ALL_PROXY", None)


def fetch_json(ctx, url):
    """GET 一个 JSON 接口；404/400/410 返回 None（=确定不存在），其它失败抛 RemoteError。"""
    code = "unknown"
    attempts = ctx.retries + 1
    for attempt in range(attempts):
        ctx.throttle.wait()
        try:
            request = urllib.request.Request(url, headers=ctx.headers)
            with ctx.opener.open(request, timeout=ctx.timeout) as response:
                payload = response.read()
            try:
                return json.loads(payload.decode("utf-8", "replace"))
            except ValueError:
                code = "bad-json"
                if attempt < attempts - 1:
                    ctx.sleep_backoff(attempt)
                    continue
                raise RemoteError(code)
        except urllib.error.HTTPError as exc:
            if exc.code in (400, 404, 410):
                return None
            if exc.code in (401, 403):
                raise RemoteError("http-%d" % exc.code)
            code = "http-%d" % exc.code
            if attempt < attempts - 1:
                ctx.sleep_backoff(attempt)
                continue
            raise RemoteError(code)
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            text = str(reason).lower()
            if isinstance(reason, (TimeoutError, socket.timeout)) or "timed out" in text:
                code = "timeout"
            else:
                code = slug_reason(reason)
            if attempt < attempts - 1:
                ctx.sleep_backoff(attempt)
                continue
            raise RemoteError(code)
    raise RemoteError(code)


# ---------------------------------------------------------------- 三个数据源

def first_year(*candidates):
    for candidate in candidates:
        if not candidate:
            continue
        if isinstance(candidate, dict):
            parts = candidate.get("date-parts") or []
            if parts and parts[0]:
                for value in parts[0]:
                    if isinstance(value, int) and 1000 <= value <= 2200:
                        return str(value)
            continue
        match = YEAR_RE.search(str(candidate))
        if match:
            return match.group(1)
    return ""


def crossref_lookup(ctx, doi):
    """Crossref works/<doi>；返回 message dict 或 None（不存在）。"""
    url = CROSSREF_WORKS + urllib.parse.quote(doi, safe="")
    if ctx.email:
        url += "?mailto=" + urllib.parse.quote(ctx.email, safe="")
    payload = fetch_json(ctx, url)
    if not payload:
        return None
    message = payload.get("message")
    return message if isinstance(message, dict) else None


def crossref_update_signals(row, message, title_text=""):
    """从 Crossref message 的 updated-by/update-to/relation 提取撤稿/勘误/关注声明信号。

    DOI 精确解析与书目匹配（--bibliographic）共用这一套判定逻辑。
    """
    stripped = str(title_text or "").lstrip()
    if stripped[:9].upper() == "RETRACTED":
        row["_signals"].add("retracted:crossref-title-prefix")
        row["flags"].append("title-prefixed-RETRACTED")

    for item in message.get("updated-by") or []:
        kind = str(item.get("type") or "").lower()
        label = str(item.get("label") or item.get("source") or "").lower()
        date = ""
        updated = item.get("updated") or {}
        if isinstance(updated, dict):
            date = first_year(updated)
        token = ("%s%s" % (item.get("label") or item.get("type") or "update",
                           ("@" + date) if date else ""))
        if any(hint in kind or hint in label for hint in RETRACTION_HINTS):
            row["_signals"].add("retracted:crossref(%s)" % clean_text(token, 80))
        elif any(hint in kind or hint in label for hint in CORRECTION_HINTS):
            row["_signals"].add("corrected:crossref(%s)" % clean_text(token, 80))
        elif any(hint in kind or hint in label for hint in EOC_HINTS):
            row["_signals"].add("eoc:crossref(%s)" % clean_text(token, 80))

    for item in message.get("update-to") or []:
        kind = str(item.get("type") or "").lower()
        target = clean_text(item.get("DOI") or "", 200)
        if any(hint in kind for hint in RETRACTION_HINTS):
            row["flags"].append("this-doi-is-retraction-notice:%s" % (target or "?"))
        elif any(hint in kind for hint in CORRECTION_HINTS):
            row["flags"].append("this-doi-is-correction-notice:%s" % (target or "?"))

    relation = message.get("relation") or {}
    if isinstance(relation, dict):
        for key in relation:
            lowered = str(key).lower()
            if "retract" in lowered:
                row["_signals"].add("retracted:crossref-relation")
            elif "correct" in lowered or "erratum" in lowered:
                row["_signals"].add("corrected:crossref-relation")


def apply_crossref(row, message):
    row["exists"] = "yes"
    row["resolved_doi"] = clean_text(message.get("DOI") or row.get("_query"), 200)
    title = message.get("title") or []
    if not row["title"] and title:
        row["title"] = clean_text(title[0], 300)
    container = message.get("container-title") or []
    if not row["journal"] and container:
        row["journal"] = clean_text(container[0], 160)
    if not row["year"]:
        row["year"] = first_year(message.get("issued"), message.get("published-print"),
                                 message.get("published-online"), message.get("published"),
                                 message.get("created"))
    if not row["first_author"]:
        authors = message.get("author") or []
        if authors:
            first = next((a for a in authors if a.get("sequence") == "first"), authors[0])
            name = first.get("family") or first.get("name") or ""
            if not name and first.get("given"):
                name = first["given"]
            row["first_author"] = clean_text(name, 120)
    row["_retraction_known"] = True
    crossref_update_signals(row, message, row["title"])


def epmc_search(ctx, query):
    params = {
        "query": query,
        "format": "json",
        "resultType": "core",
        "pageSize": "1",
    }
    url = EPMC_SEARCH + "?" + urllib.parse.urlencode(params)
    payload = fetch_json(ctx, url)
    if not payload:
        return None
    results = ((payload.get("resultList") or {}).get("result")) or []
    return results[0] if results else None


def apply_epmc_row(row, record):
    """Europe PMC core 记录：撤稿/勘误信号 + 元数据兜底。"""
    row["_retraction_known"] = True

    status = str(record.get("publicationStatus") or "").lower()
    if "retract" in status:
        row["_signals"].add("retracted:europepmc(publicationStatus)")

    for pub_type in (record.get("pubTypeList") or {}).get("pubType") or []:
        lowered = str(pub_type).lower()
        if "retracted publication" in lowered or "withdrawal" in lowered:
            row["_signals"].add("retracted:europepmc(pubtype=%s)" % clean_text(pub_type, 40))
        elif "retraction notice" in lowered:
            # 这条记录本身是撤稿声明，不是被撤稿的原文
            row["flags"].append("this-record-is-retraction-notice")

    for entry in (record.get("commentCorrectionList") or {}).get("commentCorrection") or []:
        kind = str(entry.get("type") or "").lower()
        if "retraction in" in kind or kind in ("retraction", "retracted publication"):
            row["_signals"].add("retracted:europepmc(%s)" % clean_text(kind, 40))
        elif "retraction of" in kind:
            row["flags"].append("this-record-is-retraction-notice")
        elif any(hint in kind for hint in CORRECTION_HINTS):
            row["_signals"].add("corrected:europepmc(%s)" % clean_text(kind, 40))
        elif any(hint in kind for hint in EOC_HINTS):
            row["_signals"].add("eoc:europepmc(%s)" % clean_text(kind, 40))

    flagged = record.get("isRetracted")
    if isinstance(flagged, str) and flagged.strip().lower() in ("y", "yes", "true", "1"):
        row["_signals"].add("retracted:europepmc(isRetracted)")
    elif flagged is True:
        row["_signals"].add("retracted:europepmc(isRetracted)")

    if not row["title"] and record.get("title"):
        row["title"] = clean_text(str(record["title"]).rstrip("."), 300)
    if not row["journal"]:
        journal = ((record.get("journalInfo") or {}).get("journal") or {}).get("title") \
            or record.get("journalTitle")
        if journal:
            row["journal"] = clean_text(journal, 160)
    if not row["year"] and record.get("pubYear"):
        row["year"] = first_year(record.get("pubYear"))
    if not row["first_author"] and record.get("authorString"):
        row["first_author"] = clean_text(str(record["authorString"]).split(",")[0], 120)
    if not row["pmid"] and record.get("pmid"):
        row["pmid"] = clean_text(str(record["pmid"]), 20)
    if not row["resolved_doi"] and record.get("doi"):
        row["resolved_doi"] = clean_text(record["doi"], 200)


def pubmed_esummary(ctx, pmid):
    params = {
        "db": "pubmed",
        "id": pmid,
        "retmode": "json",
        "tool": ctx.tool,
        "email": ctx.email,
    }
    url = PUBMED_ESUMMARY + "?" + urllib.parse.urlencode(params)
    payload = fetch_json(ctx, url)
    if not payload:
        return None
    result = payload.get("result") or {}
    record = result.get(str(pmid)) or {}
    if not isinstance(record, dict) or record.get("error"):
        return None
    return record


def apply_esummary(row, record):
    row["exists"] = "yes"
    row["_retraction_known"] = True
    if record.get("title"):
        row["title"] = clean_text(str(record["title"]).rstrip("."), 300)
    if record.get("source"):
        row["journal"] = clean_text(record["source"], 160)
    if not row["year"]:
        row["year"] = first_year(record.get("pubdate"), record.get("sortpubdate"),
                                 record.get("epubdate"))
    authors = record.get("authors") or []
    if authors and isinstance(authors[0], dict):
        row["first_author"] = clean_text(authors[0].get("name") or "", 120)
    for article_id in record.get("articleids") or []:
        if str(article_id.get("idtype", "")).lower() == "doi" and not row["resolved_doi"]:
            row["resolved_doi"] = clean_text(article_id.get("value") or "", 200)


# ---------------------------------------------------------------- 逐条校验

def new_row(value, kind, source):
    return {
        "input": clean_text(value, 300),
        "kind": kind,
        "resolved_doi": "",
        "pmid": "",
        "title": "",
        "journal": "",
        "year": "",
        "first_author": "",
        "exists": "pending",
        "retracted": "unknown",
        "corrected": "unknown",
        "flags": [],
        "match_confidence": "",
        "matched_title": "",
        "matched_journal": "",
        "matched_year": "",
        "_source": source,
        "_expect_pmid": "",
        "_query": value,
        "_ref": None,
        "_signals": set(),
        "_retraction_known": False,
    }


def verify_row(row, ctx):
    kind = row["kind"]
    if kind == "bib-no-id":
        row["exists"] = "NOT_FOUND"
        row["flags"].append("no-doi-or-pmid-in-bib-entry")
        return
    if kind == "invalid":
        row["exists"] = "ERROR:unrecognised-identifier"
        row["flags"].append("input-not-a-doi-or-pmid")
        return

    if kind == "bibliographic":
        # 无 DOI/PMID 的引用（GB/T 7714 等）：Crossref 书目检索 + 题目相似度判定
        ref = row.get("_ref") or parse_bibliographic_reference(row["_query"])
        row["title"] = clean_text(ref.get("title") or "", 300)
        row["journal"] = clean_text(ref.get("journal") or "", 160)
        row["year"] = ref.get("year") or ""
        row["first_author"] = clean_text(ref.get("first_author") or "", 120)
        if has_cjk(ref.get("title")):
            row["flags"].append("cjk-reference")
        try:
            items = bibliographic_candidates(ctx, ref.get("title"),
                                             ref.get("journal"), ref.get("year"))
        except RemoteError as exc:
            row["exists"] = "ERROR:%s" % exc.code
            row["flags"].append("crossref-error:%s" % exc.code)
            return
        if items is None:
            row["exists"] = "ERROR:lookup-failed"
            row["flags"].append("bibliographic-lookup-failed")
            return
        if not items:
            row["exists"] = "NOT_FOUND"
            row["flags"].append("no-crossref-candidate;possibly-unindexed")
            if has_cjk(ref.get("title")):
                row["flags"].append("crossref-coverage-limited")
            return
        best = best_candidate(ref, items)
        apply_best_candidate(row, ref, best)
        return

    query = row["_query"]
    statuses = []  # [(source, state[, detail])]，state ∈ {"hit", "miss", "error"}

    if kind == "doi":
        message = None
        try:
            message = crossref_lookup(ctx, query)
            statuses.append(("crossref", "hit" if message else "miss"))
        except RemoteError as exc:
            statuses.append(("crossref", "error", exc.code))
            row["flags"].append("crossref-error:%s" % exc.code)
        if message:
            apply_crossref(row, message)
        if ctx.use_epmc:
            try:
                record = epmc_search(ctx, 'DOI:"%s"' % query)
                statuses.append(("epmc", "hit" if record else "miss"))
            except RemoteError as exc:
                record = None
                statuses.append(("epmc", "error", exc.code))
                row["flags"].append("europepmc-error:%s" % exc.code)
            if record:
                before = row["exists"]
                apply_epmc_row(row, record)
                if before != "yes":
                    row["exists"] = "yes"
                    row["flags"].append("crossref-miss;epmc-resolved")
    else:  # pmid
        record = None
        try:
            record = pubmed_esummary(ctx, query)
            statuses.append(("pubmed", "hit" if record else "miss"))
        except RemoteError as exc:
            statuses.append(("pubmed", "error", exc.code))
            row["flags"].append("pubmed-error:%s" % exc.code)
        if record:
            apply_esummary(row, record)
        row["pmid"] = row["pmid"] or query
        if ctx.use_epmc:
            try:
                hit = epmc_search(ctx, "EXT_ID:%s" % query)
                statuses.append(("epmc", "hit" if hit else "miss"))
            except RemoteError as exc:
                hit = None
                statuses.append(("epmc", "error", exc.code))
                row["flags"].append("europepmc-error:%s" % exc.code)
            if hit:
                before = row["exists"]
                apply_epmc_row(row, hit)
                if before != "yes":
                    row["exists"] = "yes"
                    row["flags"].append("pubmed-miss;epmc-resolved")

    # 汇总 exists：至少一个来源命中即视为存在；全部来源都失败才是 ERROR，否则 NOT_FOUND
    if row["exists"] != "yes":
        failures = [item for item in statuses if item[1] == "error"]
        if failures and not any(item[1] == "hit" for item in statuses):
            reasons = []
            for item in failures:
                code = item[2] if len(item) > 2 else "lookup-failed"
                if code not in reasons:
                    reasons.append(code)
            row["exists"] = "ERROR:%s" % (",".join(reasons) or "lookup-failed")
        else:
            row["exists"] = "NOT_FOUND"
            checked = []
            for item in statuses:
                if item[0] not in checked:
                    checked.append(item[0])
            row["flags"].append("not-found-in:%s" % "+".join(checked))

    # bib 里显式给出的 pmid 与实际解析的 pmid 不一致 -> 强完整性信号
    expected = row.get("_expect_pmid") or ""
    if expected and row["pmid"] and digits_only(expected) != digits_only(row["pmid"]):
        row["flags"].append("pmid-mismatch:bib=%s,resolved=%s" % (expected, row["pmid"]))


def finalize_row(row):
    signals = sorted(row["_signals"])
    for signal in signals:
        row["flags"].append(signal)
    has_retract = any(signal.startswith("retracted") for signal in signals)
    has_correct = any(signal.startswith("corrected") for signal in signals)
    if has_retract:
        row["retracted"] = "yes"
    elif row["_retraction_known"] and row["exists"] == "yes":
        row["retracted"] = "no"
    else:
        row["retracted"] = "unknown"
    if has_correct:
        row["corrected"] = "yes"
    elif row["_retraction_known"] and row["exists"] == "yes":
        row["corrected"] = "no"
    else:
        row["corrected"] = "unknown"

    seen = []
    for flag in row["flags"]:
        flag = clean_text(flag, 200)
        if flag and flag not in seen:
            seen.append(flag)
    row["flags"] = ";".join(seen)
    if row["year"] and not re.fullmatch(r"\d{4}", row["year"]):
        match = YEAR_RE.search(row["year"])
        row["year"] = match.group(1) if match else ""


# ---------------------------------------------------------------- 输出

def write_tsv(path, rows):
    directory = os.path.dirname(os.path.abspath(path))
    if directory and not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", quoting=csv.QUOTE_MINIMAL,
                            lineterminator="\n")
        writer.writerow(COLUMNS)
        for row in rows:
            writer.writerow([clean_text(row.get(column, ""), 300) for column in COLUMNS])


def write_json(path, rows, summary):
    directory = os.path.dirname(os.path.abspath(path))
    if directory and not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)
    payload = {
        "meta": {
            "script": "verify_refs.py",
            "version": VERSION,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "sources": ["crossref", "pubmed-esummary", "europepmc"],
        },
        "summary": summary,
        "rows": [{column: row.get(column, "") for column in COLUMNS} for row in rows],
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def summarise(rows):
    counts = {
        "total": len(rows),
        "exists": sum(1 for row in rows if row["exists"] == "yes"),
        "matched": sum(1 for row in rows if row["exists"] == "MATCHED"),
        "ambiguous": sum(1 for row in rows if row["exists"] == "AMBIGUOUS"),
        "not_found": sum(1 for row in rows if row["exists"] == "NOT_FOUND"),
        "errors": sum(1 for row in rows if str(row["exists"]).startswith("ERROR:")),
        "retracted": sum(1 for row in rows if row["retracted"] == "yes"),
        "corrected": sum(1 for row in rows if row["corrected"] == "yes"),
    }
    counts["eoc"] = sum(1 for row in rows if "eoc:" in str(row["flags"]))
    # NOT_FOUND 细分（互斥）：无法自动核验 / 有候选但元数据不符 / 确认不存在
    unverifiable = 0
    mismatch = 0
    for row in rows:
        if row["exists"] != "NOT_FOUND":
            continue
        flags = str(row["flags"])
        if "possibly-unindexed" in flags or "crossref-coverage-limited" in flags:
            unverifiable += 1
        elif "low-similarity:" in flags:
            mismatch += 1
    counts["unverifiable"] = unverifiable
    counts["mismatch"] = mismatch
    counts["absent"] = max(0, counts["not_found"] - unverifiable - mismatch)
    counts["failing"] = sum(
        1 for row in rows
        if row["exists"] not in ("yes", "MATCHED") or row["retracted"] == "yes")
    return counts


# ---------------------------------------------------------------- CLI

def build_parser():
    parser = argparse.ArgumentParser(
        prog="verify_refs.py",
        description="校验参考文献是否真实存在、是否被撤稿/勘误（Crossref + PubMed + Europe PMC）。",
        epilog="退出码：0=全部核实存在（yes/MATCHED）且无撤稿；"
               "1=有 NOT_FOUND / AMBIGUOUS / ERROR / retracted。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", action="append", metavar="FILE",
                        help="输入文件（.bib / .txt / .md / .csv，可重复给多次）")
    parser.add_argument("--text", metavar="TEXT", help="直接给出含 DOI/PMID 的文本片段")
    parser.add_argument("--doi", action="append", metavar="DOI", help="直接给 DOI（可重复）")
    parser.add_argument("--pmid", action="append", metavar="PMID", help="直接给 PMID（可重复）")
    parser.add_argument("--bibliographic", action="store_true",
                        help="对没有 DOI/PMID 的引用（如 GB/T 7714 中文格式）做 Crossref 书目匹配："
                             "解析题目/期刊/年份，输出 MATCHED / AMBIGUOUS / NOT_FOUND 与 match_confidence")
    parser.add_argument("--limit", type=int, default=None, metavar="N",
                        help="只校验前 N 条（快速抽查大列表时用）")
    parser.add_argument("--out", default="ref_report.tsv", metavar="PATH",
                        help="TSV 报告路径（默认 ref_report.tsv）")
    parser.add_argument("--json", dest="json_path", metavar="PATH", help="额外输出 JSON 报告")
    parser.add_argument("--use-proxy", action="store_true",
                        help="使用环境/系统代理（默认为直连：no_proxy=* + 空代理 opener）")
    parser.add_argument("--insecure-noproxy", action="store_true",
                        help="兼容旧参数：直连是默认行为，本参数无副作用")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help="单请求超时秒数（默认 20）")
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES,
                        help="失败重试次数（默认 2）")
    parser.add_argument("--interval", type=float, default=None,
                        help="固定请求间隔秒数（默认每次随机 0.4–0.6）")
    parser.add_argument("--email", default=os.environ.get("NCBI_EMAIL")
                        or "dsh-verify-refs@users.noreply.github.com",
                        help="联系邮箱（Crossref polite pool / NCBI 要求；可用 NCBI_EMAIL 环境变量）")
    parser.add_argument("--tool", default="dsh-verify-refs", help="NCBI tool 参数")
    parser.add_argument("--no-europepmc", action="store_true",
                        help="跳过 Europe PMC（更快，但会少了勘误/撤稿的第二来源）")
    parser.add_argument("--skip-unidentified", action="store_true",
                        help="跳过 .bib 中既无 DOI 也无 PMID 的条目（默认会作为 NOT_FOUND 报出）")
    parser.add_argument("--quiet", action="store_true", help="不打印逐条进度")
    parser.add_argument("--version", action="version", version="verify_refs.py " + VERSION)
    return parser


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream.isatty():
                # 真实控制台：沿用系统编码（中文 Windows 为 cp936），只兜底不可编码字符
                stream.reconfigure(errors="replace")
            else:
                # 被重定向/管道捕获时统一 UTF-8，避免父子进程编码不一致导致乱码
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # pragma: no cover - 老环境无 reconfigure
            pass

    parser = build_parser()
    args = parser.parse_args(argv)
    configure_direct_http(args.use_proxy)
    ctx = Ctx(args)

    items = collect_items(args)
    if not items:
        sys.stderr.write("没有从输入中找到任何 DOI/PMID/可检索引用。"
                         "用 --input/--text/--doi/--pmid 提供"
                         "（GB/T 7714 等无标识引用请加 --bibliographic）。\n")
        return 1

    rows = []
    seen = {}
    for item in items:
        if item["kind"] == "bib-no-id":
            if args.skip_unidentified:
                continue
            row = new_row(item["value"], "bib-no-id", item["source"])
            row["_expect_pmid"] = ""
            seen[item["value"] + "|" + item["source"]] = row
            rows.append(row)
            continue
        key = item["kind"] + ":" + item["value"].lower()
        if key in seen:
            if "duplicate-input" not in seen[key]["flags"]:
                seen[key]["flags"].append("duplicate-input")
            continue
        row = new_row(item["value"], item["kind"], item["source"])
        row["_expect_pmid"] = item.get("expect_pmid", "")
        row["_ref"] = item.get("ref")
        seen[key] = row
        rows.append(row)

    if args.limit is not None and args.limit > 0:
        rows = rows[:args.limit]
    if args.skip_unidentified:
        rows = [row for row in rows if row["kind"] != "bib-no-id"]

    total = len(rows)
    for index, row in enumerate(rows, 1):
        try:
            verify_row(row, ctx)
        except KeyboardInterrupt:
            raise
        except Exception as exc:  # noqa: BLE001 - 任何异常都必须落到报告行，绝不让脚本崩
            row["exists"] = "ERROR:%s" % short_reason("%s: %s" % (type(exc).__name__, exc), 80)
            row["flags"].append("unexpected-error:%s" % type(exc).__name__)
        finalize_row(row)
        if not args.quiet:
            detail = ""
            if row["match_confidence"]:
                detail = "  conf=%s" % row["match_confidence"]
            sys.stderr.write("[%d/%d] %-13s %-40s exists=%-10s retracted=%-7s%s%s\n" % (
                index, total, row["kind"], clean_text(row["_query"], 40),
                row["exists"], row["retracted"], detail,
                ("  flags=" + row["flags"]) if row["flags"] else ""))
            sys.stderr.flush()

    summary = summarise(rows)
    write_tsv(args.out, rows)
    if args.json_path:
        write_json(args.json_path, rows, summary)

    sys.stdout.write("== 校验汇总 ==\n")
    if any(row["kind"] == "bibliographic" for row in rows):
        sys.stdout.write(
            "条目 %d | 精确命中 %d | 书目匹配 %d | 待确认 %d | 未找到 %d | 错误 %d | 撤稿 %d | 勘误 %d\n" % (
                summary["total"], summary["exists"], summary["matched"],
                summary["ambiguous"], summary["not_found"], summary["errors"],
                summary["retracted"], summary["corrected"]))
    else:
        sys.stdout.write("条目 %d | 存在 %d | 未找到 %d | 错误 %d | 撤稿 %d | 勘误 %d\n" % (
            summary["total"], summary["exists"], summary["not_found"],
            summary["errors"], summary["retracted"], summary["corrected"]))
    sys.stdout.write("TSV: %s\n" % os.path.abspath(args.out))
    if args.json_path:
        sys.stdout.write("JSON: %s\n" % os.path.abspath(args.json_path))
    if summary["ambiguous"]:
        sys.stdout.write("提示：AMBIGUOUS（%d 条）需要人工确认是否同一篇文献。\n"
                         % summary["ambiguous"])
    if summary["not_found"]:
        sys.stdout.write(
            "未找到 %d 条 = 无法自动核验 %d + 有候选但元数据不符 %d + 确认不存在 %d\n" % (
                summary["not_found"], summary["unverifiable"],
                summary["mismatch"], summary["absent"]))
        sys.stdout.write("提示：NOT_FOUND 不等于造假；中文/非 Crossref 文献常见「未收录」，"
                         "人工核验见 SKILL.md「人工核验路径」。\n")

    if summary["failing"]:
        sys.stdout.write("退出码 1：存在 NOT_FOUND / AMBIGUOUS / ERROR / 撤稿条目，需要人工处理。\n")
        return 1
    sys.stdout.write("退出码 0：全部条目已核实存在且未被撤稿。\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
