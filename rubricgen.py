"""rubricgen —— 把评分标准写成机器能查的规则。

设计原则：
1. **诚实地区分**。能机械判定的和必须人读的，明确分开，
   不假装全自动——假装全自动的评分系统比没有评分更危险。
2. **规则要能落地**。每条机器规则都得说清：检查什么、什么算通过。
3. **不评价标准本身好不好**，只负责把它变成可执行的检查。

仅依赖 Python 标准库。

用法:
    python rubricgen.py --help
    python rubricgen.py --file rubric.md
    python rubricgen.py --file rubric.md --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys

# ---------------------------------------------------------------------------
# 判定规则
# ---------------------------------------------------------------------------

# 机器可判定的信号：规则文本里出现这些词，说明标准本身自带判定依据
MACHINE_SIGNALS = [
    (re.compile(r"(必须|应当|不得|禁止)\s*[^\n]{0,20}(包含|含有|以\s*[`*\[]?\w+[`*\]]?\s*开头|"
                r"以\s*\w+结尾|不少于|不超过|等于|为空|非空)"), "keyword_or_count"),
    (re.compile(r"(长度|字数|字符数|行数|条数)\s*(不超过|不少于|至少|最多|等于|应为)"), "count"),
    (re.compile(r"(格式|结构)\s*(为|是|应为)\s*(JSON|XML|YAML|CSV|Markdown|列表|表格)"), "format"),
    (re.compile(r"(包含|含有)\s*(关键词|词|字面量)\s*[「\"'\[]"), "keyword_or_count"),
    (re.compile(r"(不含|不得包含|没有|无)\s*(关键词|词|敏感词|禁用词)"), "keyword_or_count"),
    (re.compile(r"(以|用)\s*(英文|中文|繁体|简体)"), "language"),
    (re.compile(r"(句数|段落数)\s*(等于|不超过|不少于)"), "count"),
]

# 必须人判断的信号
HUMAN_SIGNALS = [
    (re.compile(r"(是否|有没有|合理|恰当|准确|贴切|自然|通顺|流畅|优雅|"
                r"有说服力|贴切度|深度|创意|新颖)"),
     "subjective"),
    (re.compile(r"(风格|语气|口吻|表达方式)", re.I), "subjective"),
    (re.compile(r"(相关性|相关性|相关性)"), "subjective"),
    (re.compile(r"(逻辑|推理|论证)", re.I), "subjective"),
    (re.compile(r"(可读性|易读)", re.I), "subjective"),
]

# 规则切分：编号项、列表项、表格行
ITEM_RE = re.compile(
    r"^\s*(?:[-*+]\s+|\d+[.)]\s+|\(?[a-z]\)\s+)(?P<text>.+)$", re.I)
TABLE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")


def split_criteria(text: str) -> list[dict]:
    """把评分标准切成一条条。"""
    items: list[dict] = []
    current_section = ""
    raw_lines = text.splitlines()

    # 表头行：紧跟着分隔行（|---|---|）的那一行不是标准，是列名，跳过
    header_idx: set[int] = set()
    for idx, ln in enumerate(raw_lines):
        s = ln.strip()
        if not s.startswith("|") or not s.endswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if cells and all(set(c) <= set("-: ") and c for c in cells):
            header_idx.add(idx)
            if idx - 1 >= 0:
                header_idx.add(idx - 1)

    for lineno, raw in enumerate(raw_lines):
        if lineno in header_idx:
            continue
        line = raw.rstrip()
        if not line.strip():
            continue

        # 标题
        if re.match(r"^\s*#{1,6}\s+", line):
            current_section = re.sub(r"^\s*#{1,6}\s+", "", line).strip()
            continue

        # 表格行：| 判据 | 通过标准 |
        m = TABLE_ROW_RE.match(line)
        if m:
            cells = [c.strip() for c in m.group(1).split("|")]
            if len(cells) >= 2 and not all(
                    set(c) <= set("-: ") for c in cells):
                items.append({
                    "text": cells[0],
                    "criterion": cells[1],
                    "section": current_section,
                    "source": "table",
                })
            continue

        # 编号 / 列表项
        m = ITEM_RE.match(line)
        if m:
            body = m.group("text").strip()
            # 「标题：说明」的形式
            if "：" in body or ":" in body:
                sep = "：" if "：" in body else ":"
                head, _, tail = body.partition(sep)
                items.append({
                    "text": head.strip(),
                    "criterion": tail.strip(),
                    "section": current_section,
                    "source": "item",
                })
            else:
                items.append({
                    "text": body,
                    "criterion": "",
                    "section": current_section,
                    "source": "item",
                })
            continue

        # 普通段落：并入上一条
        if items and not TABLE_ROW_RE.match(line):
            items[-1]["criterion"] = (items[-1]["criterion"] + " " + line.strip()).strip()

    return items


def classify(item: dict) -> dict:
    """判断一条标准能否机械判定。"""
    text = f"{item['text']} {item['criterion']}"

    machine_hit = None
    for pat, kind in MACHINE_SIGNALS:
        if pat.search(text):
            machine_hit = kind
            break

    human_hit = None
    for pat, kind in HUMAN_SIGNALS:
        if pat.search(text):
            human_hit = kind
            break

    # 人判断信号优先：如果一条标准既有主观词也有机械条件，
    # 归为「部分可判定」，需要人确认边界。
    if machine_hit and human_hit:
        return {"mode": "partial", "machine_kind": machine_hit,
                "human_reason": "含主观判断词与机械条件，边界需人确认",
                "action": "拆成机械部分与人判部分"}
    if machine_hit:
        return {"mode": "machine", "machine_kind": machine_hit,
                "human_reason": "", "action": "写成可执行的检查"}
    if human_hit:
        return {"mode": "human", "machine_kind": "",
                "human_reason": "标准本身要求主观判断",
                "action": "留在人工队列"}
    return {"mode": "unknown", "machine_kind": "",
            "human_reason": "看不出判定依据",
            "action": "补写通过标准"}


# ---------------------------------------------------------------------------
# 规则模板
# ---------------------------------------------------------------------------

RULE_TEMPLATES = {
    "keyword_or_count": "检查输出是否{op}指定内容：{detail}",
    "count": "检查数量是否满足约束：{detail}",
    "format": "检查输出格式是否为指定形式：{detail}",
    "language": "检查输出语言：{detail}",
}


def build_rule(item: dict, info: dict) -> str:
    """给一条可机械判定的标准写出一句可执行的规则。"""
    kind = info["machine_kind"]
    criterion = item["criterion"] or item["text"]
    tmpl = RULE_TEMPLATES.get(kind, "按标准原文检查：{detail}")
    return tmpl.format(op="包含", detail=criterion)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def generate(text: str) -> dict:
    items = split_criteria(text)
    rows: list[dict] = []
    for idx, item in enumerate(items):
        info = classify(item)
        rows.append({
            "index": idx,
            "criterion": item["text"],
            "standard": item["criterion"],
            "section": item["section"],
            "mode": info["mode"],
            "machine_kind": info["machine_kind"],
            "human_reason": info["human_reason"],
            "action": info["action"],
            "rule": (build_rule(item, info)
                     if info["mode"] in ("machine", "partial") else ""),
        })

    machine = [r for r in rows if r["mode"] == "machine"]
    partial = [r for r in rows if r["mode"] == "partial"]
    human = [r for r in rows if r["mode"] == "human"]
    unknown = [r for r in rows if r["mode"] == "unknown"]

    return {
        "total": len(rows),
        "rows": rows,
        "machine": machine,
        "partial": partial,
        "human": human,
        "unknown": unknown,
        "coverage": {
            "machine": len(machine),
            "partial": len(partial),
            "human": len(human),
            "unknown": len(unknown),
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def render(result: dict) -> str:
    out: list[str] = []
    c = result["coverage"]
    out.append("评分标准可判定化报告")
    out.append("=" * 60)
    out.append(f"共 {result['total']} 条标准｜"
               f"可机器判定 {c['machine']} ｜ 部分可判定 {c['partial']} ｜ "
               f"必须人判 {c['human']} ｜ 判据不明 {c['unknown']}")
    out.append("")

    groups = [
        ("可机械判定", result["machine"]),
        ("部分可判定（需拆）", result["partial"]),
        ("必须人判断", result["human"]),
        ("判据不明（需补写）", result["unknown"]),
    ]
    for title, rows in groups:
        if not rows:
            continue
        out.append(f"{title}（{len(rows)} 条）：")
        for r in rows:
            out.append(f"  · {r['criterion']}")
            if r["standard"]:
                out.append(f"    通过标准：{r['standard']}")
            if r["rule"]:
                out.append(f"    可执行规则：{r['rule']}")
            if r["human_reason"]:
                out.append(f"    原因：{r['human_reason']}")
            out.append(f"    处置：{r['action']}")
        out.append("")

    out.append("人工队列里剩下的，都是机器确实判不了的——这部分不建议硬自动化。")
    return "\n".join(out).rstrip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="rubricgen",
        description="把评分标准写成机器能查的规则（仅依赖标准库）",
        epilog=(
            "示例:\n"
            "  python rubricgen.py --file rubric.md\n"
            "  python rubricgen.py --file rubric.md --json\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--file", required=True, help="评分标准文件")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args(argv)

    try:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"读不了文件：{e}", file=sys.stderr)
        return 2

    if not text.strip():
        print("文件是空的。", file=sys.stderr)
        return 2

    result = generate(text)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(render(result))
    # 有判据不明的标准时退出码 1
    return 1 if result["unknown"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
