"""Built-in SVG plots for election results.

Hand-written SVG (no plotting dependency), matching the suite convention set
by bewley: deterministic output, embeddable in HTML reports, versionable in
git. All functions take plain data (entities and saved count results) and
return an SVG string.
"""
from __future__ import annotations

import html

GREEN = "#2e6b4f"
DARK = "#214d35"
LIGHT = "#eef5f0"
AMBER = "#b66b13"
MUTED = "#5b665e"
RULE = "#dde5de"
RED = "#a4442f"
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif"

# Sequential greens for rank/stacked shading, best (dark) to worst (pale).
RAMP = ["#214d35", "#2e6b4f", "#4d8a6a", "#71a888", "#97c2a8", "#bcd8c7", "#dcebe2", "#f2f8f4"]


def _svg(width: int, height: int, title: str, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'font-family="{FONT}" role="img" aria-label="{html.escape(title)}">\n'
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>\n'
        f'<text x="20" y="30" font-size="17" font-weight="700" fill="{DARK}">{html.escape(title)}</text>\n'
        f"{body}\n</svg>\n"
    )


def _label(option_id: str, names: dict[str, str] | None) -> str:
    if names and names.get(option_id):
        name = names[option_id]
        return name if len(name) <= 28 else name[:27] + "…"
    return option_id


def scores_svg(result: dict, names: dict[str, str] | None = None) -> str:
    """Horizontal bar chart of a count's per-option totals, winner highlighted."""
    scores = sorted(result.get("scores") or [], key=lambda s: -s["total"])
    if not scores:
        raise ValueError("This result has no per-option scores to plot.")
    winners = set(result.get("winners") or [])
    width, row_h, left, top = 760, 34, 250, 56
    chart_w = width - left - 90
    height = top + row_h * len(scores) + 30
    max_total = max(s["total"] for s in scores) or 1.0
    parts = []
    for i, s in enumerate(scores):
        y = top + i * row_h
        bar = chart_w * s["total"] / max_total
        color = GREEN if s["option_id"] in winners else "#97c2a8"
        parts.append(f'<text x="{left - 10}" y="{y + 21}" font-size="13" text-anchor="end" '
                     f'fill="{DARK}">{html.escape(_label(s["option_id"], names))}</text>')
        parts.append(f'<rect x="{left}" y="{y + 7}" width="{bar:.1f}" height="{row_h - 14}" rx="3" fill="{color}"/>')
        parts.append(f'<text x="{left + bar + 8}" y="{y + 21}" font-size="13" font-weight="700" '
                     f'fill="{MUTED}">{s["total"]:g}</text>')
    method = result.get("method", "")
    title = f"{method} totals — {result.get('election_id', '')}"
    return _svg(width, height, title, "\n".join(parts))


def ranks_svg(ballots: list[dict], options: list[dict]) -> str:
    """Stacked bars: how often each option was ranked 1st, 2nd, ... by voters."""
    option_ids = [o["id"] for o in options]
    names = {o["id"]: o.get("name") or o["id"] for o in options}
    n_positions = len(option_ids)
    counts = {oid: [0] * n_positions for oid in option_ids}
    total = 0
    for ballot in ballots:
        ranking = ballot.get("ranking") or []
        if not ranking:
            continue
        total += 1
        for position, oid in enumerate(ranking):
            if oid in counts and position < n_positions:
                counts[oid][position] += 1
    if not total:
        raise ValueError("No ranked ballots to plot.")
    # Order rows by mean position (best first).
    def mean_pos(oid: str) -> float:
        c = counts[oid]
        n = sum(c) or 1
        return sum((i + 1) * v for i, v in enumerate(c)) / n

    ordered = sorted(option_ids, key=mean_pos)
    width, row_h, left, top = 760, 34, 250, 78
    chart_w = width - left - 40
    height = top + row_h * len(ordered) + 30
    parts = []
    # Legend: first / middle / last shading.
    parts.append(f'<text x="20" y="52" font-size="12" fill="{MUTED}">Each bar spans all {total} ballots; '
                 f'darker = ranked closer to first choice.</text>')
    for i, oid in enumerate(ordered):
        y = top + i * row_h
        parts.append(f'<text x="{left - 10}" y="{y + 21}" font-size="13" text-anchor="end" '
                     f'fill="{DARK}">{html.escape(_label(oid, names))}</text>')
        x = float(left)
        for position, count in enumerate(counts[oid]):
            if not count:
                continue
            seg = chart_w * count / total
            shade = RAMP[min(position, len(RAMP) - 1)]
            parts.append(f'<rect x="{x:.1f}" y="{y + 7}" width="{max(seg, 1.0):.1f}" height="{row_h - 14}" '
                         f'fill="{shade}"><title>{html.escape(names[oid])}: ranked #{position + 1} by {count}</title></rect>')
            if position == 0 and seg > 26:
                parts.append(f'<text x="{x + 6}" y="{y + 21}" font-size="12" font-weight="700" '
                             f'fill="#ffffff">{count}</text>')
            x += seg
    title = "Where voters ranked each option"
    return _svg(width, height, title, "\n".join(parts))


def pairwise_svg(result: dict, names: dict[str, str] | None = None) -> str:
    """Head-to-head matrix: row option's margin over column option."""
    pairwise = result.get("pairwise") or []
    if not pairwise:
        raise ValueError("This result has no pairwise data (run a Condorcet method such as schulze).")
    option_ids: list[str] = []
    margins: dict[tuple[str, str], float] = {}
    for pair in pairwise:
        a, b = pair["a"], pair["b"]
        for oid in (a, b):
            if oid not in option_ids:
                option_ids.append(oid)
        margins[(a, b)] = pair["a_over_b"] - pair["b_over_a"]
        margins[(b, a)] = pair["b_over_a"] - pair["a_over_b"]
    ranking = {row["option_id"]: row.get("rank", 99) for row in result.get("ranking", [])}
    option_ids.sort(key=lambda oid: ranking.get(oid, 99))
    cell, left, top = 52, 210, 120
    width = left + cell * len(option_ids) + 40
    height = top + cell * len(option_ids) + 40
    max_margin = max(abs(m) for m in margins.values()) or 1.0
    parts = [f'<text x="20" y="52" font-size="12" fill="{MUTED}">Green: row beats column (darker = larger margin). '
             f'Red: row loses. Grey: tie.</text>']
    for j, col in enumerate(option_ids):
        x = left + j * cell + cell / 2
        parts.append(f'<g transform="translate({x},{top - 8}) rotate(-45)">'
                     f'<text font-size="11" fill="{DARK}">{html.escape(_label(col, names)[:14])}</text></g>')
    for i, row in enumerate(option_ids):
        y = top + i * cell
        parts.append(f'<text x="{left - 10}" y="{y + cell / 2 + 4}" font-size="12" text-anchor="end" '
                     f'fill="{DARK}">{html.escape(_label(row, names)[:24])}</text>')
        for j, col in enumerate(option_ids):
            x = left + j * cell
            if row == col:
                parts.append(f'<rect x="{x}" y="{y}" width="{cell - 3}" height="{cell - 3}" fill="{LIGHT}"/>')
                continue
            margin = margins.get((row, col), 0.0)
            if margin > 0:
                opacity = 0.25 + 0.75 * margin / max_margin
                fill, text_fill = GREEN, "#ffffff" if opacity > 0.55 else DARK
            elif margin < 0:
                opacity = 0.25 + 0.75 * -margin / max_margin
                fill, text_fill = RED, "#ffffff" if opacity > 0.55 else DARK
            else:
                opacity, fill, text_fill = 1.0, "#c9d4cc", DARK
            parts.append(f'<rect x="{x}" y="{y}" width="{cell - 3}" height="{cell - 3}" '
                         f'fill="{fill}" fill-opacity="{opacity:.2f}">'
                         f'<title>{html.escape(_label(row, names))} vs {html.escape(_label(col, names))}: '
                         f'{margin:+g}</title></rect>')
            parts.append(f'<text x="{x + (cell - 3) / 2}" y="{y + cell / 2 + 3}" font-size="12" '
                         f'text-anchor="middle" fill="{text_fill}">{margin:+g}</text>')
    title = f"Head-to-head margins — {result.get('election_id', '')}"
    return _svg(width, height, title, "\n".join(parts))


def methods_svg(results: list[dict], names: dict[str, str] | None = None) -> str:
    """Option x method grid of finishing positions across saved counts."""
    if not results:
        raise ValueError("No saved count results to compare (run voting count run first).")
    methods: list[str] = []
    positions: dict[str, dict[str, int]] = {}
    no_winner: set[str] = set()
    for result in results:
        method = result.get("method", "?")
        if method not in methods:
            methods.append(method)
        if not result.get("winners"):
            no_winner.add(method)
        else:
            no_winner.discard(method)
        for row in result.get("ranking", []):
            positions.setdefault(row["option_id"], {})[method] = row.get("rank", 0)
    option_ids = sorted(positions, key=lambda oid: sum(positions[oid].values()) / max(len(positions[oid]), 1))
    cell_w, cell_h, left, top = (88 if len(methods) <= 8 else 70), 40, 250, 118
    width = left + cell_w * len(methods) + 60
    height = top + cell_h * len(option_ids) + (56 if no_winner else 40)
    n_options = len(option_ids)
    parts = [f'<text x="20" y="52" font-size="12" fill="{MUTED}">Cell = finishing position under that method '
             f'(1 = winner). A solid top row means the method does not change the outcome.</text>']
    rotate = len(methods) > 8
    for j, method in enumerate(methods):
        label = html.escape(method + ("*" if method in no_winner else ""))
        if rotate:
            parts.append(f'<g transform="translate({left + j * cell_w + 10},{top - 10}) rotate(-32)">'
                         f'<text font-size="11" font-weight="700" fill="{DARK}">{label}</text></g>')
        else:
            parts.append(f'<text x="{left + j * cell_w + cell_w / 2}" y="{top - 12}" font-size="12" font-weight="700" '
                         f'text-anchor="middle" fill="{DARK}">{label}</text>')
    if no_winner:
        parts.append(f'<text x="{left}" y="{top + cell_h * n_options + 30}" font-size="12" fill="{AMBER}">'
                     f'* declared no winner (its ranking is shown for comparison)</text>')
    for i, oid in enumerate(option_ids):
        y = top + i * cell_h
        parts.append(f'<text x="{left - 10}" y="{y + cell_h / 2 + 4}" font-size="13" text-anchor="end" '
                     f'fill="{DARK}">{html.escape(_label(oid, names))}</text>')
        for j, method in enumerate(methods):
            x = left + j * cell_w
            rank = positions[oid].get(method)
            if rank is None:
                continue
            shade = RAMP[min(rank - 1, len(RAMP) - 1)] if n_options > 1 else RAMP[0]
            text_fill = "#ffffff" if rank <= max(2, n_options // 3) else DARK
            parts.append(f'<rect x="{x}" y="{y}" width="{cell_w - 4}" height="{cell_h - 4}" rx="4" fill="{shade}"/>')
            parts.append(f'<text x="{x + (cell_w - 4) / 2}" y="{y + cell_h / 2 + 4}" font-size="14" '
                         f'font-weight="700" text-anchor="middle" fill="{text_fill}">{rank}</text>')
    title = "Finishing positions across counting methods"
    return _svg(width, height, title, "\n".join(parts))
