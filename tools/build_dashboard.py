"""docs/dashboard.md を、ブラウザで見るための 1 枚の HTML にする（GitHub Pages の /dashboard/）。

  python3 tools/build_dashboard.py [出力フォルダ]     既定：site/dashboard

外部のライブラリは使わない（CI でそのまま動くように）。dashboard.md で使っている書き方だけを扱う：
見出し、表、箇条書き、引用、コードブロック（コピーのボタンを付ける）、**太字**、`コード`。
`...md`・`...jpg` などのファイル名の `コード` は、GitHub のそのファイルへのリンクにする。
"""
from __future__ import annotations

import html
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC = os.path.join(REPO, 'docs', 'dashboard.md')
BLOB = 'https://github.com/hassy0511/project-relic/blob/claude/busy-bell-oagnck/'
FILE_RE = re.compile(r'^[\w./\-ぁ-んァ-ヶ一-龠ー]+\.(md|jpg|png|py|gd|json)$')


def link_code(code: str) -> str:
    """ファイル名らしい `コード` を GitHub へのリンクにする（docs/ からの相対とみなす）"""
    esc = html.escape(code)
    if FILE_RE.match(code) and not code.startswith('http'):
        path = code if code.startswith(('docs/', 'tools/', 'godot/', '.claude/')) or code == 'CLAUDE.md' else 'docs/' + code
        return f'<a href="{BLOB}{html.escape(path)}"><code>{esc}</code></a>'
    return f'<code>{esc}</code>'


def inline(text: str) -> str:
    parts = re.split(r'(`[^`]+`)', text)
    out = []
    for p in parts:
        if p.startswith('`') and p.endswith('`') and len(p) > 1:
            out.append(link_code(p[1:-1]))
            continue
        t = html.escape(p)
        t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
        t = re.sub(r'(https?://[^\s<）)]+)', r'<a href="\1">\1</a>', t)
        out.append(t)
    return ''.join(out)


def convert(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    n_code = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('```'):
            body = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                body.append(lines[i])
                i += 1
            i += 1
            n_code += 1
            cid = f'code{n_code}'
            out.append(f'<div class="code"><button onclick="copyCode(\'{cid}\', this)">コピー</button>'
                       f'<pre id="{cid}">{html.escape(chr(10).join(body))}</pre></div>')
            continue
        m = re.match(r'^(#{1,4}) (.*)', line)
        if m:
            lv = len(m.group(1))
            out.append(f'<h{lv}>{inline(m.group(2))}</h{lv}>')
            i += 1
            continue
        if line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                rows.append(lines[i])
                i += 1
            cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows]
            head, body = cells[0], [r for r in cells[1:] if not all(re.fullmatch(r':?-+:?', c or '-') for c in r)]
            t = ['<div class="table"><table><thead><tr>'] + [f'<th>{inline(c)}</th>' for c in head] + ['</tr></thead><tbody>']
            for r in body:
                t.append('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>')
            t.append('</tbody></table></div>')
            out.append(''.join(t))
            continue
        if line.startswith('>'):
            quote = []
            while i < len(lines) and lines[i].startswith('>'):
                quote.append(inline(lines[i].lstrip('>').strip()))
                i += 1
            out.append('<blockquote>' + '<br>'.join(quote) + '</blockquote>')
            continue
        if re.match(r'^\s*[-*] ', line):
            items = []
            while i < len(lines) and re.match(r'^\s*[-*] ', lines[i]):
                item = re.sub(r'^\s*[-*] ', '', lines[i])
                items.append(f'<li>{inline(item)}</li>')
                i += 1
            out.append('<ul>' + ''.join(items) + '</ul>')
            continue
        if line.strip() == '---':
            out.append('<hr>')
        elif line.strip():
            out.append(f'<p>{inline(line)}</p>')
        i += 1
    return '\n'.join(out)


PAGE = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>アークウォーカー 開発ダッシュボード</title>
<style>
:root {{ --bg:#f7f4ee; --fg:#26221d; --muted:#6b6358; --line:#ddd5c8; --card:#fff; --accent:#b75b43; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#1c1a17; --fg:#ece6dc; --muted:#a59b8c; --line:#3a352e; --card:#26231f; --accent:#e08a6f; }} }}
p, li, td, blockquote, h1, h2, h3 {{ overflow-wrap:anywhere; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:15px/1.6 system-ui, "Hiragino Sans", "Noto Sans JP", sans-serif; }}
main {{ max-width:1100px; margin:0 auto; padding:16px; }}
h1 {{ font-size:1.5em; margin:.4em 0; }} h2 {{ font-size:1.2em; margin:1.6em 0 .5em; border-bottom:2px solid var(--accent); padding-bottom:.2em; }}
h3 {{ font-size:1.02em; margin:1.2em 0 .4em; }}
blockquote {{ margin:0 0 1em; padding:.4em .8em; border-left:3px solid var(--line); color:var(--muted); }}
.table {{ overflow-x:auto; }} table {{ border-collapse:collapse; width:100%; background:var(--card); }}
th, td {{ border:1px solid var(--line); padding:.35em .5em; text-align:left; vertical-align:top; }} th {{ white-space:nowrap; }}
code {{ font-size:.9em; background:rgba(128,128,128,.15); padding:0 .25em; border-radius:3px; }}
a {{ color:var(--accent); }}
.code {{ position:relative; margin:.4em 0 1em; }}
.code pre {{ background:var(--card); border:1px solid var(--line); padding:.8em; padding-top:2.2em; white-space:pre-wrap; word-break:break-all; margin:0; font-size:.85em; }}
.code button {{ position:absolute; top:.4em; right:.4em; padding:.3em .9em; border:1px solid var(--accent); background:var(--accent); color:#fff; border-radius:4px; font-size:.9em; }}
hr {{ border:none; border-top:1px solid var(--line); margin:1.5em 0; }}
.foot {{ color:var(--muted); font-size:.85em; margin-top:2em; }}
</style></head>
<body><main>
{body}
<p class="foot">docs/dashboard.md から自動で作ったページ（push のたびに更新）。</p>
</main>
<script>
function copyCode(id, btn) {{
  const text = document.getElementById(id).innerText;
  const done = () => {{ btn.textContent = 'コピーしました'; setTimeout(() => btn.textContent = 'コピー', 1500); }};
  if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, () => fallback(text, done));
  else fallback(text, done);
}}
function fallback(text, done) {{
  const t = document.createElement('textarea'); t.value = text; document.body.appendChild(t); t.select();
  try {{ document.execCommand('copy'); done(); }} catch (e) {{}} document.body.removeChild(t);
}}
</script></body></html>
"""


def main() -> None:
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, 'site', 'dashboard')
    os.makedirs(out_dir, exist_ok=True)
    with open(SRC, encoding='utf-8') as f:
        body = convert(f.read())
    with open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(PAGE.format(body=body))
    print('できた：', os.path.join(out_dir, 'index.html'))


if __name__ == '__main__':
    main()
