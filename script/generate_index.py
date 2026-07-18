import os
import html as html_lib
from datetime import datetime, timezone

try:
    import markdown as md_lib
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

HIDDEN_ALWAYS = {'.git', '.github', 'links'}
EXCLUDE_DIRS = {'__pycache__', 'node_modules'}
EXCLUDE_FILES = {'index.html'}
EXCLUDE_FILE_EXTS = set()
MD_EXTS = ('.md', '.markdown')

COPY_ICON_SVG = (
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="9" y="9" width="13" height="13" rx="2"></rect>'
    '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>'
)

FOLDER_ICON_SVG = (
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z"></path></svg>'
)

STYLE = '''
  @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
  :root {
    --bg: #f7f8fa;
    --card: #ffffff;
    --border: #e6e8ee;
    --text: #1e222b;
    --muted: #7a8194;
    --accent: #3562e0;
    --accent-soft: #eef2fd;
    --shadow: 0 1px 2px rgba(20, 24, 33, 0.04), 0 1px 8px rgba(20, 24, 33, 0.03);
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    padding: 44px 18px 90px;
    font-size: 15px;
    line-height: 1.5;
  }
  a { color: inherit; }
  .wrap { max-width: 780px; margin: 0 auto; }
  .crumb { font-size: 13px; color: var(--muted); margin-bottom: 14px; }
  .crumb a { color: var(--accent); text-decoration: none; }
  .crumb a:hover { text-decoration: underline; }
  .crumb .sep { margin: 0 6px; color: var(--border); }
  h1 { font-size: 21px; margin: 0 0 20px; font-weight: 700; word-break: break-all; }
  .stats { display: flex; gap: 20px; margin-bottom: 22px; font-size: 13px; color: var(--muted); }
  .stats b { color: var(--text); font-weight: 600; }

  .folder-grid { display: flex; flex-direction: column; gap: 10px; margin-bottom: 22px; }
  .folder-card {
    display: flex; align-items: center; gap: 14px; text-decoration: none;
    background: var(--card); border: 1px solid var(--border); border-radius: 12px;
    padding: 16px 18px; box-shadow: var(--shadow); color: var(--text);
    transition: border-color .12s, transform .12s;
  }
  .folder-card:hover { border-color: var(--accent); transform: translateY(-1px); }
  .folder-card .icon { color: var(--accent); flex-shrink: 0; }
  .folder-card .name { font-weight: 600; font-size: 15px; flex: 1; }
  .folder-card .meta { color: var(--muted); font-size: 12.5px; }

  .table-card {
    background: var(--card); border: 1px solid var(--border); border-radius: 12px;
    box-shadow: var(--shadow); overflow: hidden;
  }
  .table-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }
  table { width: 100%; border-collapse: collapse; min-width: 100%; }
  thead th {
    text-align: left; color: var(--muted); font-weight: 400; font-size: 11px;
    padding: 10px 14px; border-bottom: 1px solid var(--border);
  }
  tbody tr { border-top: 1px solid var(--border); }
  tbody tr:first-child { border-top: none; }
  tbody tr:hover { background: var(--accent-soft); }
  tbody td { padding: 9px 14px; font-size: 13px; white-space: nowrap; }
  td.fname-cell { max-width: 0; width: 100%; overflow: hidden; text-overflow: ellipsis; }
  a.fname {
    text-decoration: none; color: var(--text); font-weight: 500;
    font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  }
  a.fname:hover { color: var(--accent); text-decoration: underline; }
  .ftype { color: var(--muted); }
  .fsize { color: var(--muted); text-align: right; }
  .op { text-align: right; width: 44px; padding-right: 14px !important; }

  .copy-btn {
    background: transparent; border: 1px solid var(--border); color: var(--muted);
    border-radius: 6px; width: 30px; height: 30px; cursor: pointer;
    display: inline-flex; align-items: center; justify-content: center;
    transition: color .12s, border-color .12s, background .12s;
    flex-shrink: 0;
  }
  .copy-btn:hover { color: var(--accent); border-color: var(--accent); background: var(--accent-soft); }
  .copy-btn.copied { color: #0f9d78; border-color: #0f9d78; background: #e6f7f1; }

  .empty { color: var(--muted); font-size: 13px; }

  footer { margin-top: 32px; color: var(--muted); font-size: 12px; text-align: center; }
  footer a { color: var(--accent); text-decoration: none; }
  footer a:hover { text-decoration: underline; }
'''

SCRIPT = '''
  var CHECK_ICON = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';
  function copyLink(btn) {
    var text = location.origin + '/' + btn.dataset.path;
    var original = btn.innerHTML;
    navigator.clipboard.writeText(text).then(function () {
      btn.innerHTML = CHECK_ICON;
      btn.classList.add('copied');
      setTimeout(function () {
        btn.innerHTML = original;
        btn.classList.remove('copied');
      }, 1200);
    });
  }
'''


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def render_markdown_preview(src_path, title):
    try:
        with open(src_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception:
        return None

    if HAS_MARKDOWN:
        body_html = md_lib.markdown(
            text, extensions=['fenced_code', 'tables', 'toc', 'sane_lists']
        )
    else:
        body_html = f'<pre style="white-space:pre-wrap;">{html_lib.escape(text)}</pre>'

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html_lib.escape(title)}</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.0/github-markdown-light.min.css">
<style>
  body {{
    margin: 0; background: #f7f8fa; padding: 24px 16px 60px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }}
  .back {{ max-width: 780px; margin: 0 auto 14px; font-size: 13px; }}
  .back a {{ color: #3562e0; text-decoration: none; }}
  .back a:hover {{ text-decoration: underline; }}
  .markdown-body {{
    max-width: 780px; margin: 0 auto; background: #fff; border: 1px solid #e6e8ee;
    border-radius: 12px; padding: 32px; box-sizing: border-box;
  }}
  @media (max-width: 600px) {{ .markdown-body {{ padding: 20px; }} }}
</style>
</head>
<body>
<div class="back"><a href="./">← 返回上级目录</a></div>
<article class="markdown-body">
{body_html}
</article>
</body>
</html>'''


def collect_entries(dir_path):
    dirs, files = [], []
    if not os.path.isdir(dir_path):
        return dirs, files
    for name in sorted(os.listdir(dir_path)):
        if name in HIDDEN_ALWAYS:
            continue
        full = os.path.join(dir_path, name)
        if os.path.isdir(full):
            if name in EXCLUDE_DIRS:
                continue
            dirs.append(name)
        elif os.path.isfile(full):
            if name in EXCLUDE_FILES:
                continue
            if os.path.splitext(name)[1].lower() in EXCLUDE_FILE_EXTS:
                continue
            if name.lower().endswith(tuple(ext + '.html' for ext in MD_EXTS)):
                continue
            files.append((name, os.path.getsize(full)))
    return dirs, files


def count_files_recursive(dir_path):
    total = 0
    dirs, files = collect_entries(dir_path)
    total += len(files)
    for d in dirs:
        total += count_files_recursive(os.path.join(dir_path, d))
    return total


def breadcrumb_html(rel_parts):
    segs = ['<a href="/">𝘙𝘶𝘭𝘦 𝘍𝘦𝘦𝘥</a>' if rel_parts else '<span>𝘙𝘶𝘭𝘦 𝘍𝘦𝘦𝘥</span>']
    acc = ""
    for i, part in enumerate(rel_parts):
        acc += part + "/"
        if i == len(rel_parts) - 1:
            segs.append(f'<span>{html_lib.escape(part)}</span>')
        else:
            segs.append(f'<a href="/{acc}">{html_lib.escape(part)}</a>')
    sep = '<span class="sep">/</span>'
    return f'<div class="crumb">{sep.join(segs)}</div>'


def page_shell(title, crumb, body):
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html_lib.escape(title)}</title>
<style>{STYLE}</style>
</head>
<body>
<div class="wrap">
{crumb}
<h1>{html_lib.escape(title)}</h1>
{body}
<footer><a href="https://github.com/XiaoHaiSly" target="_blank" rel="noopener noreferrer">𝑋𝑖𝑎𝑜𝐻𝑎𝑖𝑆𝑙𝑦</a></footer>
</div>
<script>{SCRIPT}</script>
</body>
</html>'''


def render_dir(dir_path, rel_parts):
    dirs, files = collect_entries(dir_path)
    title = rel_parts[-1] if rel_parts else "Rule Feed"
    crumb = breadcrumb_html(rel_parts)
    rel_dir = "/".join(rel_parts)

    body_parts = []

    if dirs:
        cards = []
        for d in dirs:
            cnt = count_files_recursive(os.path.join(dir_path, d))
            cards.append(f'''
<a class="folder-card" href="{html_lib.escape(d)}/">
<span class="icon">{FOLDER_ICON_SVG}</span>
<span class="name">{html_lib.escape(d)}/</span>
<span class="meta">{cnt} 个文件</span>
</a>''')
        body_parts.append(f'<div class="folder-grid">{"".join(cards)}</div>')

    if files:
        rows = []
        for fname, size in files:
            ext = fname.rsplit('.', 1)[-1] if '.' in fname else ''
            relpath = f"{rel_dir}/{fname}" if rel_dir else fname
            is_md = fname.lower().endswith(MD_EXTS)
            open_href = f"{html_lib.escape(fname)}.html" if is_md else html_lib.escape(fname)
            rows.append(f'''
<tr>
<td class="fname-cell"><a class="fname" href="{open_href}">{html_lib.escape(fname)}</a></td>
<td class="ftype">.{ext}</td>
<td class="fsize">{human_size(size)}</td>
<td class="op"><button class="copy-btn" data-path="{html_lib.escape(relpath)}" onclick="copyLink(this)">{COPY_ICON_SVG}</button></td>
</tr>''')
        table_html = f'''
<div class="table-card">
<div class="table-scroll">
<table>
<thead><tr><th>文件</th><th>类型</th><th>大小</th><th></th></tr></thead>
<tbody>{"".join(rows)}</tbody>
</table>
</div>
</div>'''
        body_parts.append(f'<div class="stats"><span><b>{len(files)}</b> 个文件</span></div>{table_html}')

    if not dirs and not files:
        body_parts.append('<p class="empty">-- 这里还没有文件，先运行构建任务 --</p>')

    write(os.path.join(dir_path, "index.html"), page_shell(title, crumb, "".join(body_parts)))

    for fname, _size in files:
        if fname.lower().endswith(MD_EXTS):
            preview_html = render_markdown_preview(os.path.join(dir_path, fname), fname)
            if preview_html:
                write(os.path.join(dir_path, f"{fname}.html"), preview_html)

    for d in dirs:
        render_dir(os.path.join(dir_path, d), rel_parts + [d])


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    render_dir(ROOT_DIR, [])
    total_files = count_files_recursive(ROOT_DIR)
    print(f"生成完毕，共 {total_files} 个文件，构建时间 {now}")


if __name__ == '__main__':
    main()
