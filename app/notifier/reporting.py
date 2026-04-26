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
    Podcast 財經分析 — 專業 Bloomberg 風格 HTML 報告。

    analysis 預期格式：
      【文字紀錄】 ... 
      【投資倒數小結】
        1. 台美股焦點標的：...
        2. 本集結論：...
    """
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ── 解析分段 ──────────────────────────────────────────────────────
    def extract_section(text: str, header: str) -> str:
        m = re.search(rf"【{re.escape(header)}】\s*(.*?)(?=【|$)", text, re.DOTALL)
        return m.group(1).strip() if m else ""

    transcript = extract_section(analysis, "文字紀錄")
    summary_raw = extract_section(analysis, "投資倒數小結")

    if not transcript and not summary_raw:
        transcript = analysis.strip()

    # ── 解析股票標的與結論 ─────────────────────────────────────────────
    stocks_text = ""
    conclusion_text = ""
    if summary_raw:
        sm = re.search(r"台美股焦點標的[：:]\s*(.*?)(?=本集結論|$)", summary_raw, re.DOTALL)
        cm = re.search(r"本集結論[：:]\s*(.*?)$", summary_raw, re.DOTALL)
        stocks_text = sm.group(1).strip() if sm else summary_raw
        conclusion_text = cm.group(1).strip() if cm else ""

    # 把股票標的每行轉為 HTML 卡片
    def render_stocks(text: str) -> str:
        lines = [l.strip().lstrip("-•·1234567890.） ") for l in text.split("\n") if l.strip()]
        cards = []
        for line in lines:
            # 嘗試拆出 ticker：「NVDA - 看好」 or「台積電（2330）— xxx」
            ticker_m = re.match(r"^([A-Z0-9]{2,6}|[\u4e00-\u9fff]{2,6}(?:（\w+）)?)\s*[-—–]\s*(.*)", line)
            if ticker_m:
                ticker = ticker_m.group(1)
                comment = ticker_m.group(2)
                is_us = bool(re.match(r"^[A-Z]{2,5}$", ticker))
                flag = "🇺🇸" if is_us else "🇹🇼"
                cards.append(
                    f'<div class="stock-card">'
                    f'<div class="stock-header"><span class="stock-flag">{flag}</span>'
                    f'<span class="stock-ticker">{ticker}</span></div>'
                    f'<div class="stock-comment">{comment}</div>'
                    f'</div>'
                )
            else:
                cards.append(f'<div class="stock-item"><span class="bullet">▸</span>{line}</div>')
        return "\n".join(cards) if cards else f"<p class='muted'>{text}</p>"

    def nl2p(text: str) -> str:
        paras = [p.strip() for p in text.split("\n") if p.strip()]
        return "".join(f"<p>{p}</p>" for p in paras)

    stocks_html = render_stocks(stocks_text) if stocks_text else "<p class='muted'>本集未提及特定標的</p>"
    conclusion_html = nl2p(conclusion_text) if conclusion_text else ""
    transcript_html = nl2p(transcript) if transcript else "<p class='muted'>（無文字紀錄）</p>"

    # 若沒有拆出結論，把整段 summary 放進結論
    if not conclusion_html and summary_raw and not stocks_text:
        conclusion_html = nl2p(summary_raw)

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{ep_title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    /* ── Reset & Base ─────────────────────────────────────── */
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --navy:     #060d1f;
      --surface:  #0c1428;
      --card:     #111827;
      --card2:    #1a2236;
      --border:   rgba(255,255,255,0.07);
      --blue:     #3b82f6;
      --blue-dim: rgba(59,130,246,0.12);
      --gold:     #f59e0b;
      --gold-dim: rgba(245,158,11,0.12);
      --green:    #10b981;
      --red:      #ef4444;
      --text:     #e2e8f0;
      --muted:    #64748b;
      --radius:   12px;
    }}
    html {{ scroll-behavior: smooth; }}
    body {{
      background: var(--navy);
      color: var(--text);
      font-family: 'Inter', 'Noto Sans TC', system-ui, sans-serif;
      font-size: 15px;
      line-height: 1.8;
      min-height: 100vh;
    }}

    /* ── Top Bar ──────────────────────────────────────────── */
    .topbar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 28px;
      height: 48px;
      background: rgba(6,13,31,0.95);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 100;
      backdrop-filter: blur(12px);
    }}
    .topbar-brand {{
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      color: var(--blue);
      text-transform: uppercase;
    }}
    .topbar-meta {{
      font-size: 0.72rem;
      color: var(--muted);
    }}
    .live-dot {{
      display: inline-block;
      width: 6px; height: 6px;
      background: var(--green);
      border-radius: 50%;
      margin-right: 6px;
      animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
      0%,100% {{ opacity:1; transform:scale(1); }}
      50%  {{ opacity:.5; transform:scale(1.3); }}
    }}

    /* ── Hero ─────────────────────────────────────────────── */
    .hero {{
      position: relative;
      overflow: hidden;
      padding: 56px 32px 48px;
      background:
        radial-gradient(ellipse 80% 60% at 50% -10%, rgba(59,130,246,0.18) 0%, transparent 70%),
        var(--surface);
      border-bottom: 1px solid var(--border);
      text-align: center;
    }}
    /* Waveform decoration */
    .hero::before {{
      content: '';
      position: absolute;
      bottom: 0; left: 0; right: 0;
      height: 40px;
      background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 40'%3E%3Cpath d='M0,20 Q50,5 100,20 T200,20 T300,20 T400,20 T500,20 T600,20 T700,20 T800,20' stroke='rgba(59,130,246,0.25)' stroke-width='1.5' fill='none'/%3E%3Cpath d='M0,20 Q25,2 50,20 T100,20 T150,20 T200,20 T250,20 T300,20 T350,20 T400,20 T450,20 T500,20 T550,20 T600,20 T650,20 T700,20 T750,20 T800,20' stroke='rgba(59,130,246,0.12)' stroke-width='1' fill='none'/%3E%3C/svg%3E") center/cover no-repeat;
      pointer-events: none;
    }}
    .hero-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--blue-dim);
      border: 1px solid rgba(59,130,246,0.3);
      color: var(--blue);
      font-size: 0.72rem;
      font-weight: 600;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      padding: 4px 14px;
      border-radius: 99px;
      margin-bottom: 20px;
    }}
    .hero h1 {{
      font-size: clamp(1.25rem, 3.5vw, 2rem);
      font-weight: 700;
      color: #fff;
      line-height: 1.35;
      max-width: 760px;
      margin: 0 auto 20px;
      letter-spacing: -0.01em;
    }}
    .hero-meta {{
      display: flex;
      align-items: center;
      justify-content: center;
      flex-wrap: wrap;
      gap: 20px;
      font-size: 0.8rem;
      color: var(--muted);
    }}
    .hero-meta-item {{
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .hero-meta-item span {{ color: var(--text); font-weight: 500; }}

    /* ── Layout ───────────────────────────────────────────── */
    .page {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 32px 20px 80px;
      display: grid;
      grid-template-columns: 1fr 360px;
      gap: 24px;
      align-items: start;
    }}
    @media (max-width: 860px) {{
      .page {{ grid-template-columns: 1fr; }}
    }}

    /* ── Cards ────────────────────────────────────────────── */
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
    }}
    .card-header {{
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 14px 22px;
      border-bottom: 1px solid var(--border);
      font-size: 0.8rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}
    .card-header .icon {{ font-size: 1rem; }}
    .card-header.blue {{ color: #93c5fd; }}
    .card-header.gold {{ color: var(--gold); }}
    .card-header.green {{ color: #6ee7b7; }}
    .card-body {{ padding: 22px; }}
    .card-body p {{ margin-bottom: 14px; color: #cbd5e1; font-size: 0.93rem; }}
    .card-body p:last-child {{ margin-bottom: 0; }}

    /* ── Sidebar sticky ───────────────────────────────────── */
    .sidebar {{
      display: flex;
      flex-direction: column;
      gap: 20px;
      position: sticky;
      top: 64px;
    }}

    /* ── Stock Cards ──────────────────────────────────────── */
    .stock-card {{
      background: var(--card2);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px 16px;
      margin-bottom: 10px;
      transition: border-color .2s;
    }}
    .stock-card:last-child {{ margin-bottom: 0; }}
    .stock-card:hover {{ border-color: rgba(59,130,246,0.35); }}
    .stock-header {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;
    }}
    .stock-flag {{ font-size: 1rem; }}
    .stock-ticker {{
      font-family: 'Inter', monospace;
      font-size: 0.88rem;
      font-weight: 700;
      color: #fff;
      background: rgba(59,130,246,0.15);
      border: 1px solid rgba(59,130,246,0.25);
      padding: 2px 10px;
      border-radius: 6px;
      letter-spacing: 0.04em;
    }}
    .stock-comment {{
      font-size: 0.83rem;
      color: #94a3b8;
      line-height: 1.55;
    }}
    .stock-item {{
      display: flex;
      gap: 8px;
      font-size: 0.85rem;
      color: #94a3b8;
      padding: 6px 0;
      border-bottom: 1px solid var(--border);
      line-height: 1.5;
    }}
    .stock-item:last-child {{ border-bottom: none; }}
    .bullet {{ color: var(--blue); flex-shrink: 0; }}

    /* ── Conclusion Quote ─────────────────────────────────── */
    .conclusion-quote {{
      position: relative;
      background: linear-gradient(135deg, var(--gold-dim) 0%, transparent 100%);
      border: 1px solid rgba(245,158,11,0.25);
      border-left: 3px solid var(--gold);
      border-radius: 10px;
      padding: 18px 20px;
    }}
    .conclusion-quote::before {{
      content: '"';
      position: absolute;
      top: -8px; left: 14px;
      font-size: 2.5rem;
      color: var(--gold);
      opacity: 0.5;
      line-height: 1;
      font-family: Georgia, serif;
    }}
    .conclusion-quote p {{
      font-size: 0.88rem;
      color: #fef3c7;
      margin-bottom: 10px;
      line-height: 1.65;
    }}
    .conclusion-quote p:last-child {{ margin-bottom: 0; }}

    /* ── Divider ──────────────────────────────────────────── */
    .section-divider {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin: 22px 0 18px;
      color: var(--muted);
      font-size: 0.72rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .section-divider::before, .section-divider::after {{
      content: '';
      flex: 1;
      height: 1px;
      background: var(--border);
    }}

    /* ── Footer ───────────────────────────────────────────── */
    footer {{
      grid-column: 1 / -1;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 4px 0;
      border-top: 1px solid var(--border);
      font-size: 0.75rem;
      color: var(--muted);
      flex-wrap: wrap;
      gap: 8px;
    }}

    /* ── Scrollbar ────────────────────────────────────────── */
    ::-webkit-scrollbar {{ width: 6px; }}
    ::-webkit-scrollbar-track {{ background: var(--navy); }}
    ::-webkit-scrollbar-thumb {{ background: #1e2d4a; border-radius: 3px; }}

    /* ── Muted helper ─────────────────────────────────────── */
    .muted {{ color: var(--muted); font-style: italic; }}
  </style>
</head>
<body>

  <!-- Top Bar -->
  <nav class="topbar">
    <div class="topbar-brand">🎙 Podcast 財經分析</div>
    <div class="topbar-meta">
      <span class="live-dot"></span>報告產生：{generated_at}
    </div>
  </nav>

  <!-- Hero -->
  <header class="hero">
    <div class="hero-badge">
      <span>🎙</span> {channel_label}
    </div>
    <h1>{ep_title}</h1>
    <div class="hero-meta">
      <div class="hero-meta-item">📅 <span>{ep_date}</span></div>
      <div class="hero-meta-item">📻 <span>{channel_label}</span></div>
      <div class="hero-meta-item">🤖 <span>AI 財經分析</span></div>
    </div>
  </header>

  <!-- Main Layout -->
  <div class="page">

    <!-- Left: Transcript -->
    <main>
      <div class="card">
        <div class="card-header blue">
          <span class="icon">📝</span> 文字紀錄
        </div>
        <div class="card-body">
          {transcript_html}
        </div>
      </div>
    </main>

    <!-- Right Sidebar -->
    <aside class="sidebar">

      <!-- Stock Picks -->
      <div class="card">
        <div class="card-header gold">
          <span class="icon">📊</span> 台美股焦點標的
        </div>
        <div class="card-body">
          {stocks_html}
        </div>
      </div>

      <!-- Conclusion -->
      {"" if not conclusion_html else f'''
      <div class="card">
        <div class="card-header green">
          <span class="icon">💡</span> 本集結論
        </div>
        <div class="card-body">
          <div class="conclusion-quote">
            {conclusion_html}
          </div>
        </div>
      </div>
      '''}

    </aside>

    <!-- Footer -->
    <footer>
      <span>© {datetime.now().year} LazyTube-Assistant · AI 分析僅供參考，不構成投資建議</span>
      <span>此頁面將於 30 分鐘後失效</span>
    </footer>

  </div>

</body>
</html>"""


