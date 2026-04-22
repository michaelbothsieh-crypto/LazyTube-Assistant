from __future__ import annotations

import os
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
