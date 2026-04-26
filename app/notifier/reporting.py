from __future__ import annotations

import os
import re
import uuid
from datetime import datetime
from typing import Optional


def generate_html_report(title: str, markdown_content: str) -> str:
    import markdown

    html_body = markdown.markdown(markdown_content, extensions=["extra", "toc", "tables"])
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} - LazyTube Research</title>
  <style>
    :root {{
      --primary-color: #1a73e8;
      --bg-color: #f8f9fa;
      --text-color: #202124;
      --card-bg: #ffffff;
      --border-color: #dadce0;
    }}
    body {{
      margin: 0;
      background: var(--bg-color);
      color: var(--text-color);
      font-family: "Segoe UI", Roboto, Arial, "PingFang TC", sans-serif;
      line-height: 1.6;
    }}
    .container {{
      max-width: 900px;
      margin: 40px auto;
      padding: 0 20px;
    }}
    header {{
      margin-bottom: 32px;
      padding-bottom: 16px;
      text-align: center;
      border-bottom: 2px solid var(--primary-color);
    }}
    .card {{
      padding: 40px;
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }}
    h1 {{
      margin: 0;
      color: var(--primary-color);
    }}
    h2 {{
      margin-top: 28px;
      padding-left: 12px;
      color: #174ea6;
      border-left: 4px solid var(--primary-color);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      padding: 12px;
      border: 1px solid var(--border-color);
      text-align: left;
    }}
    blockquote {{
      margin: 20px 0;
      padding: 12px 16px;
      background: #e8f0fe;
      border-left: 4px solid var(--primary-color);
    }}
    footer {{
      margin-top: 32px;
      text-align: center;
      font-size: 0.85rem;
      color: #70757a;
    }}
    @media (max-width: 600px) {{
      .container {{
        margin: 12px auto;
      }}
      .card {{
        padding: 20px;
      }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>{title}</h1>
      <div>產生時間：{generated_at}</div>
    </header>
    <div class="card">{html_body}</div>
    <footer>&copy; {datetime.now().year} LazyTube-Assistant</footer>
  </div>
</body>
</html>"""


def generate_pdf_report(html_content: str) -> Optional[str]:
    try:
        import pdfkit

        pdf_path = os.path.join("/tmp", f"report_{uuid.uuid4().hex[:8]}.pdf")
        pdfkit.from_string(
            html_content,
            pdf_path,
            options={
                "page-size": "A4",
                "margin-top": "0.75in",
                "margin-right": "0.75in",
                "margin-bottom": "0.75in",
                "margin-left": "0.75in",
                "encoding": "UTF-8",
                "no-outline": None,
                "quiet": "",
            },
        )
        return pdf_path
    except Exception:
        return None


def generate_podcast_html_report(
    ep_title: str,
    ep_date: str,
    channel_label: str,
    analysis: str,
) -> str:
    """
    Podcast 財經分析專屬精美 HTML 報告。
    analysis 預期格式：
      【文字紀錄】...
      【投資倒數小結】...
    """
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    def extract_section(text: str, header: str) -> str:
        m = re.search(rf"【{re.escape(header)}】\s*(.*?)(?=【|$)", text, re.DOTALL)
        return m.group(1).strip() if m else ""

    transcript = extract_section(analysis, "文字紀錄")
    summary    = extract_section(analysis, "投資倒數小結")
    if not transcript and not summary:
        transcript = analysis.strip()

    def nl2p(text: str) -> str:
        return "".join(f"<p>{p.strip()}</p>" for p in text.split("\n") if p.strip())

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{ep_title} — Podcast 財經分析</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap');
    :root{{--bg:#0f1117;--surface:#1a1d27;--accent:#4f9cf9;--gold:#f5c842;--text:#e2e8f0;--muted:#8892a4;--border:rgba(255,255,255,0.08);}}
    *{{box-sizing:border-box;margin:0;padding:0;}}
    body{{background:var(--bg);color:var(--text);font-family:'Noto Sans TC',system-ui,sans-serif;line-height:1.8;}}
    .hero{{background:linear-gradient(135deg,#1a1d27 0%,#0f1117 60%);border-bottom:1px solid var(--border);padding:40px 24px 32px;text-align:center;}}
    .badge{{display:inline-block;background:rgba(79,156,249,0.15);border:1px solid rgba(79,156,249,0.4);color:var(--accent);font-size:.75rem;padding:3px 12px;border-radius:99px;margin-bottom:14px;letter-spacing:.08em;}}
    h1{{font-size:clamp(1.15rem,4vw,1.75rem);font-weight:700;color:#fff;margin-bottom:8px;}}
    .meta{{font-size:.82rem;color:var(--muted);}}
    .container{{max-width:900px;margin:0 auto;padding:28px 18px 60px;display:grid;gap:22px;}}
    .card{{background:var(--surface);border:1px solid var(--border);border-radius:14px;overflow:hidden;}}
    .card-header{{display:flex;align-items:center;gap:10px;padding:14px 22px;border-bottom:1px solid var(--border);font-weight:700;font-size:.92rem;}}
    .card-header.tr{{color:#a3c4f3;}} .card-header.sm{{color:var(--gold);}}
    .card-body{{padding:22px;font-size:.93rem;}}
    .card-body p{{margin-bottom:13px;}} .card-body p:last-child{{margin-bottom:0;}}
    footer{{text-align:center;color:var(--muted);font-size:.78rem;padding-top:8px;}}
  </style>
</head>
<body>
  <div class="hero">
    <div class="badge">🎙️ PODCAST 財經分析</div>
    <h1>{ep_title}</h1>
    <div class="meta">📻 {channel_label} &nbsp;·&nbsp; 📅 {ep_date} &nbsp;·&nbsp; 產生：{generated_at}</div>
  </div>
  <div class="container">
    <div class="card">
      <div class="card-header tr"><span>📝</span> 文字紀錄</div>
      <div class="card-body">{nl2p(transcript) if transcript else "<p><em>（無文字紀錄）</em></p>"}</div>
    </div>
    <div class="card">
      <div class="card-header sm"><span>📊</span> 投資倒數小結</div>
      <div class="card-body">{nl2p(summary) if summary else "<p><em>（無投資小結）</em></p>"}</div>
    </div>
    <footer>© {datetime.now().year} LazyTube-Assistant &nbsp;·&nbsp; 此頁面 30 分鐘後失效</footer>
  </div>
</body>
</html>"""

