# web_app.py
import os
from urllib.parse import parse_qs, quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse

from scraper_core import run_scrape  # импортируем нашу логику

app = FastAPI(title="CTFd Scraper Web")


@app.get("/", response_class=HTMLResponse)
async def index():
    return """
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <title>CTFd Scraper</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root {
      color-scheme: dark;
      --bg: #020617;
      --bg-soft: #020617;
      --card-bg: #020617;
      --border-subtle: rgba(148, 163, 184, 0.35);
      --accent: #38bdf8;
      --accent-soft: rgba(56, 189, 248, 0.18);
      --accent-strong: #0ea5e9;
      --text-main: #e5e7eb;
      --text-muted: #94a3b8;
      --danger: #f97373;
      --input-bg: rgba(15, 23, 42, 0.92);
      --radius-lg: 20px;
      --radius-md: 10px;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text-main);
      background:
        radial-gradient(circle at top left, rgba(56, 189, 248, 0.25), transparent 55%),
        radial-gradient(circle at bottom right, rgba(129, 140, 248, 0.25), transparent 50%),
        var(--bg-soft);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }

    .shell {
      width: 100%;
      max-width: 1120px;
    }

    .card {
      position: relative;
      background:
        radial-gradient(circle at top left, rgba(148, 163, 184, 0.12), transparent 60%),
        var(--card-bg);
      border-radius: 22px;
      border: 1px solid var(--border-subtle);
      box-shadow:
        0 22px 80px rgba(15, 23, 42, 0.9),
        0 0 0 1px rgba(15, 23, 42, 0.85);
      padding: 26px 26px 22px;
      backdrop-filter: blur(26px);
      overflow: hidden;
    }

    .card::before {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      border-radius: inherit;
      border: 1px solid rgba(148, 163, 184, 0.3);
      mix-blend-mode: soft-light;
      opacity: 0.7;
    }

    .header {
      margin-bottom: 22px;
    }

    .title-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 10px;
    }

    .logo-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 4px 10px 4px 4px;
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.9);
      border: 1px solid rgba(148, 163, 184, 0.55);
      box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.9);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .06em;
      color: var(--text-muted);
    }

    .logo-dot {
      width: 20px;
      height: 20px;
      border-radius: 999px;
      background: radial-gradient(circle at 30% 30%, #fff, var(--accent-strong));
      box-shadow:
        0 0 0 1px rgba(15, 23, 42, 0.9),
        0 0 22px rgba(56, 189, 248, 0.9);
    }

    .tag {
      font-size: 11px;
      padding: 3px 8px;
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.9);
      border: 1px solid rgba(148, 163, 184, 0.5);
      color: var(--text-muted);
    }

    h1 {
      margin: 0 0 4px;
      font-size: clamp(22px, 3vw, 26px);
      letter-spacing: -.02em;
    }

    .subtitle {
      margin: 0;
      font-size: 13px;
      color: var(--text-muted);
      max-width: 640px;
    }

    .hints {
      display: flex;
      gap: 10px;
      margin-top: 14px;
      flex-wrap: wrap;
      font-size: 11px;
      color: var(--text-muted);
    }

    .pill {
      padding: 4px 9px;
      border-radius: 999px;
      border: 1px dashed rgba(148, 163, 184, 0.55);
      background: rgba(15, 23, 42, 0.85);
      display: inline-flex;
      align-items: center;
      gap: 4px;
      white-space: nowrap;
    }

    .pill strong {
      font-weight: 600;
      color: var(--accent-strong);
    }

    form {
      margin-top: 18px;
    }

    .form-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr);
      gap: 18px 26px;
    }

    .field {
      display: flex;
      flex-direction: column;
      gap: 5px;
      font-size: 13px;
    }

    .field-label {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }

    .field-label span:first-child {
      font-weight: 550;
    }

    .field-label small {
      color: var(--text-muted);
      font-size: 11px;
      opacity: 0.9;
    }

    input[type="text"],
    input[type="password"],
    textarea {
      width: 100%;
      border-radius: var(--radius-md);
      border: 1px solid rgba(51, 65, 85, 0.9);
      background: var(--input-bg);
      padding: 8px 10px;
      font-size: 13px;
      color: var(--text-main);
      outline: none;
      transition: border-color 0.16s ease, box-shadow 0.16s ease, background 0.16s ease, transform 0.06s ease;
      resize: vertical;
      min-height: 38px;
    }

    textarea {
      min-height: 72px;
    }

    input::placeholder,
    textarea::placeholder {
      color: rgba(148, 163, 184, 0.8);
    }

    input:focus,
    textarea:focus {
      border-color: var(--accent-strong);
      box-shadow:
        0 0 0 1px rgba(15,23,42,0.95),
        0 0 0 1px rgba(56, 189, 248, 0.8),
        0 0 26px rgba(56, 189, 248, 0.45);
      background: radial-gradient(circle at top left, rgba(56, 189, 248, 0.12), transparent 60%), var(--input-bg);
      transform: translateY(-0.5px);
    }

    .field-note {
      margin-top: 2px;
      font-size: 11px;
      color: var(--text-muted);
    }

    .checkbox-group {
      margin-top: 4px;
      padding: 9px 10px;
      border-radius: var(--radius-md);
      border: 1px dashed rgba(148, 163, 184, 0.6);
      background: rgba(15, 23, 42, 0.92);
      display: flex;
      flex-direction: column;
      gap: 6px;
      font-size: 12px;
    }

    .checkbox-group-title {
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .11em;
      color: var(--text-muted);
      margin-bottom: 3px;
    }

    .checkbox-row {
      display: flex;
      align-items: flex-start;
      gap: 8px;
    }

    .checkbox-row input[type="checkbox"] {
      margin-top: 2px;
    }

    .checkbox-row span {
      color: var(--text-main);
    }

    button[type="submit"] {
      margin-top: 16px;
      padding: 9px 18px;
      font-size: 13px;
      font-weight: 600;
      border-radius: 999px;
      border: none;
      cursor: pointer;
      background: radial-gradient(circle at 0 0, #e0f2fe, #7dd3fc);
      color: #0f172a;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      box-shadow:
        0 14px 35px rgba(56, 189, 248, 0.55),
        0 0 0 1px rgba(15, 23, 42, 0.9);
      transition: transform 0.09s ease-out, box-shadow 0.09s ease-out, filter 0.08s ease-out;
      white-space: nowrap;
    }

    button[type="submit"]:hover {
      transform: translateY(-1px);
      box-shadow:
        0 18px 40px rgba(56, 189, 248, 0.75),
        0 0 0 1px rgba(15, 23, 42, 0.9);
      filter: brightness(1.02);
    }

    button[type="submit"]:active {
      transform: translateY(0);
      box-shadow:
        0 10px 26px rgba(56, 189, 248, 0.6),
        0 0 0 1px rgba(15, 23, 42, 0.9);
      filter: brightness(0.97);
    }

    button[type="submit"] span.icon {
      font-size: 15px;
    }

    .footer-hint {
      margin-top: 10px;
      font-size: 11px;
      color: var(--text-muted);
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }

    .footer-hint code {
      font-size: 11px;
      padding: 3px 6px;
      border-radius: 6px;
      background: rgba(15, 23, 42, 0.95);
      border: 1px solid rgba(30, 64, 175, 0.8);
      color: #e0f2fe;
    }
    
    .made-by {
      margin-top: 14px;
      font-size: 11px;
      color: var(--text-muted);
      text-align: right;
      opacity: 0.8;
    }

    @media (max-width: 880px) {
      .form-grid {
        grid-template-columns: 1fr;
      }

      .card {
        padding: 22px 18px 18px;
      }

      body {
        padding: 14px;
      }
    }

    @media (max-width: 560px) {
      .title-row {
        flex-direction: column;
        align-items: flex-start;
      }

      h1 {
        font-size: 20px;
        
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <div class="card">
      <header class="header">
        <div class="title-row">
          <div class="logo-pill">
            <span class="logo-dot"></span>
            <span>CTFd Scraper</span>
          </div>
          <span class="tag">web&nbsp;UI</span>
        </div>
        <h1>Снимок CTF-платформы за пару кликов</h1>
        <p class="subtitle">
          Укажи адрес CTFd (вплоть до /challenges или отдельной задачи), при необходимости авторизацию — и получи аккуратный дамп с INDEX.md и ZIP-архивом.
        </p>
        <div class="hints">
          <span class="pill"><strong>✓</strong> Логин/пароль, токен или cookie</span>
          <span class="pill"><strong>✓</strong> Гибкая глубина дампа</span>
          <span class="pill"><strong>✓</strong> Параллельная загрузка задач</span>
        </div>
      </header>

      <form action="/run" method="post">
        <div class="form-grid">
          <div class="left-col">
            <div class="field">
              <div class="field-label">
                <span>CTFd URL</span>
                <small>можно несколько URL через пробел/перенос</small>
              </div>
              <textarea
                name="base_url"
                placeholder="https://ctf.example.com/challenges/
https://ctf.example.com/challenges/web/123"
                required
              ></textarea>
            </div>

            <div class="field">
              <div class="field-label">
                <span>Авторизация</span>
                <small>любая комбинация: логин/пароль, токен, cookie</small>
              </div>
              <div class="field">
                <input type="text" name="username" placeholder="Логин (можно оставить пустым)" />
              </div>
              <div class="field">
                <input type="password" name="password" placeholder="Пароль" />
              </div>
              <div class="field">
                <input type="text" name="api_token" placeholder="API Token (если указан — логин/пароль не нужны)" />
              </div>
              <div class="field">
                <input type="text" name="cookie" placeholder="Cookie, например: session=xxxx; other=yyy" />
              </div>
              <p class="field-note">
                Приоритет обычно за <b>API token</b>, затем cookie, затем логин/пароль (зависит от реализации ядра).
              </p>
            </div>
          </div>

          <div class="right-col">
            <div class="field">
              <div class="field-label">
                <span>Login URL</span>
                <small>опционально</small>
              </div>
              <input type="text" name="login_url" placeholder="по умолчанию: https://host/login" />
            </div>

            <div class="field">
              <div class="field-label">
                <span>Каталог для сохранения</span>
              </div>
              <input type="text" name="out_dir" placeholder="./ctf_dump" />
              <p class="field-note">
                Относительно каталога, из которого запущен сервер. Если пусто — будет <code>./ctf_dump</code>.
              </p>
            </div>

            <div class="field">
              <div class="field-label">
                <span>Параллелизм</span>
                <small>сколько задач качать одновременно</small>
              </div>
              <input type="text" name="concurrency" value="5" />
            </div>

            <div class="field">
              <div class="checkbox-group">
                <div class="checkbox-group-title">опции дампа</div>

                <label class="checkbox-row">
                  <input type="checkbox" name="no_files" />
                  <span>Не скачивать файлы задач (оставить только описания).</span>
                </label>

                <label class="checkbox-row">
                  <input type="checkbox" name="no_desc" />
                  <span>Не сохранять <code>description.txt</code> (только файлы и структура).</span>
                </label>

                <label class="checkbox-row">
                  <input type="checkbox" name="save_html" />
                  <span>Сохранять HTML каждой задачи в <code>page.html</code>.</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        <button type="submit">
          <span class="icon">▶</span>
          <span>Запустить дамп</span>
        </button>

        <div class="footer-hint">
          <span>После завершения будет сгенерирован</span>
          <code>INDEX.md</code>
          <span>и ZIP-архив с дампом, доступный для скачивания.</span>
        </div>
      </form>
        <div class="made-by">
        Made by @Pahihq1
        </div>
    </div>
  </div>
</body>
</html>
    """


@app.post("/run", response_class=HTMLResponse)
async def run(request: Request):
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8", errors="ignore")
    data = parse_qs(body_str)

    def g(key: str, default: str = "") -> str:
        return data.get(key, [default])[0]

    base_url = g("base_url")
    username = g("username")
    password = g("password")
    api_token = g("api_token")
    cookie = g("cookie")
    login_url = g("login_url")
    out_dir = g("out_dir") or "./ctf_dump"
    concurrency_str = g("concurrency", "5")

    no_files = "no_files" in data
    no_desc = "no_desc" in data
    save_html = "save_html" in data

    try:
        concurrency = int(concurrency_str)
        if concurrency <= 0:
            concurrency = 1
    except ValueError:
        concurrency = 5

    urls = [u.strip() for u in base_url.split() if u.strip()]

    # вызываем ядро
    try:
        result = await run_scrape(
            base_urls=urls,
            username=username,
            password=password,
            api_token=api_token,
            cookie=cookie,
            login_url=login_url,
            out_dir=out_dir,
            concurrency=concurrency,
            no_files=no_files,
            no_desc=no_desc,
            save_html=save_html,
        )
    except Exception as e:
        return HTMLResponse(
            f"""
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <title>Ошибка CTFd Scraper</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root {{
      color-scheme: dark;
      --bg: #020617;
      --card-bg: #020617;
      --text-main: #e5e7eb;
      --text-muted: #94a3b8;
      --danger: #f97373;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      min-height: 100vh;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text-main);
      background:
        radial-gradient(circle at top left, rgba(239, 68, 68, 0.24), transparent 55%),
        radial-gradient(circle at bottom right, rgba(15, 23, 42, 1), transparent 45%),
        var(--bg);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }}

    .card {{
      width: 100%;
      max-width: 720px;
      background: var(--card-bg);
      border-radius: 18px;
      border: 1px solid rgba(248, 113, 113, 0.55);
      box-shadow:
        0 22px 80px rgba(15, 23, 42, 0.9),
        0 0 0 1px rgba(15, 23, 42, 0.85);
      padding: 22px 22px 18px;
    }}

    h1 {{
      margin: 0 0 8px;
      font-size: 20px;
      color: var(--danger);
    }}

    p {{
      margin: 0 0 10px;
      font-size: 13px;
      color: var(--text-muted);
    }}

    pre {{
      margin: 0;
      padding: 10px 12px;
      border-radius: 10px;
      background: #020617;
      border: 1px solid rgba(248, 113, 113, 0.5);
      font-size: 12px;
      overflow: auto;
      max-height: 360px;
      white-space: pre-wrap;
      word-break: break-word;
    }}

    a {{
      display: inline-flex;
      margin-top: 14px;
      font-size: 13px;
      text-decoration: none;
      color: #e5e7eb;
      padding: 7px 12px;
      border-radius: 999px;
      background: #020617;
      border: 1px solid rgba(148, 163, 184, 0.6);
    }}

    a:hover {{
      border-color: rgba(248, 250, 252, 0.9);
    }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Ошибка при парсинге</h1>
    <p>Что-то пошло не так во время выполнения дампа. Текст исключения ниже может помочь разобраться:</p>
    <pre>{e}</pre>
    <a href="/">← Назад к форме</a>
  </div>
</body>
</html>
            """,
            status_code=400,
        )

    results = result["results"]
    index_path = result["index_path"]
    zip_path = result["zip_path"]
    zip_url = f"/download?path={quote(zip_path)}"

    rows = []
    for r in sorted(results, key=lambda x: x["title"].lower()):
        rows.append(
            f"<tr>"
            f"<td>{r['title']}</td>"
            f"<td><a href=\"{r['url']}\" target=\"_blank\" rel=\"noopener noreferrer\">{r['url']}</a></td>"
            f"<td><code>{r['dir']}</code></td>"
            f"<td>{r['files_count']}</td>"
            f"</tr>"
        )

    html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <title>Результат CTFd Scraper</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root {{
      color-scheme: dark;
      --bg: #020617;
      --card-bg: #020617;
      --accent: #38bdf8;
      --accent-soft: rgba(56, 189, 248, 0.18);
      --accent-strong: #0ea5e9;
      --text-main: #e5e7eb;
      --text-muted: #94a3b8;
      --border-subtle: rgba(148, 163, 184, 0.4);
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      min-height: 100vh;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text-main);
      background:
        radial-gradient(circle at top left, rgba(56, 189, 248, 0.25), transparent 55%),
        radial-gradient(circle at bottom right, rgba(129, 140, 248, 0.25), transparent 50%),
        var(--bg);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 22px;
    }}

    .shell {{
      width: 100%;
      max-width: 1180px;
    }}

    .card {{
      background:
        radial-gradient(circle at top left, rgba(148, 163, 184, 0.12), transparent 60%),
        var(--card-bg);
      border-radius: 22px;
      border: 1px solid var(--border-subtle);
      box-shadow:
        0 22px 80px rgba(15, 23, 42, 0.9),
        0 0 0 1px rgba(15, 23, 42, 0.85);
      padding: 22px 22px 18px;
      backdrop-filter: blur(24px);
      overflow: hidden;
    }}

    header {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 12px;
    }}

    h1 {{
      margin: 0;
      font-size: 22px;
      letter-spacing: -.02em;
    }}

    .sub {{
      margin: 2px 0 0;
      font-size: 13px;
      color: var(--text-muted);
    }}

    .badge {{
      padding: 4px 9px;
      border-radius: 999px;
      border: 1px solid rgba(148, 163, 184, 0.6);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .12em;
      color: var(--text-muted);
      background: rgba(15, 23, 42, 0.95);
    }}

    .top-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      align-items: stretch;
      margin: 10px 0 14px;
    }}

    .stats {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      flex: 2;
      min-width: 220px;
    }}

    .stat-card {{
      flex: 1;
      min-width: 160px;
      border-radius: 14px;
      border: 1px solid rgba(148, 163, 184, 0.5);
      background: rgba(15, 23, 42, 0.95);
      padding: 8px 10px;
      font-size: 12px;
    }}

    .stat-label {{
      color: var(--text-muted);
      margin-bottom: 3px;
    }}

    .stat-value {{
      font-size: 18px;
      font-weight: 600;
    }}

    .stat-extra {{
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 2px;
    }}

    .download-card {{
      flex: 1.1;
      min-width: 220px;
      border-radius: 16px;
      border: 1px solid rgba(56, 189, 248, 0.75);
      background: radial-gradient(circle at top left, rgba(56, 189, 248, 0.33), transparent 65%), #020617;
      padding: 10px 12px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}

    .download-title {{
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .12em;
      color: #e0f2fe;
      opacity: 0.9;
    }}

    .download-row {{
      display: flex;
      flex-direction: column;
      gap: 3px;
      font-size: 11px;
    }}

    .download-row code {{
      padding: 3px 6px;
      border-radius: 7px;
      background: rgba(15, 23, 42, 0.95);
      border: 1px solid rgba(15, 23, 42, 0.95);
      font-size: 11px;
      color: #e0f2fe;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}

    .download-btn {{
      margin-top: 6px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 11px;
      font-size: 12px;
      border-radius: 999px;
      border: none;
      background: #e0f2fe;
      color: #0f172a;
      text-decoration: none;
      font-weight: 600;
      box-shadow:
        0 10px 30px rgba(56, 189, 248, 0.65),
        0 0 0 1px rgba(15, 23, 42, 0.9);
      white-space: nowrap;
    }}

    .download-btn span.icon {{
      font-size: 14px;
    }}

    .table-wrap {{
      margin-top: 8px;
      border-radius: 14px;
      border: 1px solid rgba(148, 163, 184, 0.55);
      background: rgba(15, 23, 42, 0.92);
      overflow: auto;
      max-height: 540px;
    }}

    table {{
      border-collapse: collapse;
      width: 100%;
      min-width: 600px;
      font-size: 13px;
    }}

    thead tr {{
      background: rgba(15, 23, 42, 0.96);
      position: sticky;
      top: 0;
      z-index: 1;
    }}

    th, td {{
      padding: 7px 10px;
      text-align: left;
      border-bottom: 1px solid rgba(30, 41, 59, 0.95);
    }}

    th {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .09em;
      color: var(--text-muted);
      border-bottom-color: rgba(148, 163, 184, 0.7);
    }}

    tbody tr:nth-child(odd) {{
      background: rgba(15, 23, 42, 0.96);
    }}

    tbody tr:nth-child(even) {{
      background: rgba(15, 23, 42, 0.92);
    }}

    tbody tr:hover {{
      background: radial-gradient(circle at top left, rgba(56, 189, 248, 0.18), transparent 70%), #020617;
    }}

    code {{
      font-size: 12px;
      background: rgba(15, 23, 42, 0.96);
      padding: 2px 5px;
      border-radius: 6px;
      border: 1px solid rgba(30, 64, 175, 0.8);
      color: #e0f2fe;
    }}

    a {{
      color: var(--accent-strong);
      text-decoration: none;
    }}

    a:hover {{
      text-decoration: underline;
    }}

    .bottom-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 10px;
      font-size: 12px;
      color: var(--text-muted);
      gap: 10px;
      flex-wrap: wrap;
    }}

    .back-link {{
      text-decoration: none;
      color: var(--text-muted);
      padding: 5px 9px;
      border-radius: 999px;
      border: 1px solid rgba(148, 163, 184, 0.5);
      background: rgba(15, 23, 42, 0.96);
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}

    .back-link:hover {{
      color: #e5e7eb;
      border-color: rgba(248, 250, 252, 0.9);
    }}

    @media (max-width: 860px) {{
      .card {{
        padding: 20px 16px 16px;
      }}

      body {{
        padding: 14px;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <div class="card">
      <header>
        <div>
          <h1>Дамп CTFd готов 🎉</h1>
          <p class="sub">Все задачи сохранены локально, а архив можно сразу забрать.</p>
        </div>
        <div class="badge">export summary</div>
      </header>

      <div class="top-row">
        <div class="stats">
          <div class="stat-card">
            <div class="stat-label">Всего задач</div>
            <div class="stat-value">{len(results)}</div>
            <div class="stat-extra">Отсортировано по заголовку (A→Я).</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Структура дампа</div>
            <div class="stat-extra">Главный индекс:</div>
            <div class="stat-extra"><code>{index_path}</code></div>
          </div>
        </div>

        <div class="download-card">
          <div class="download-title">ZIP-архив с дампом</div>
          <div class="download-row">
            <span>Локальный путь:</span>
            <code>{zip_path}</code>
          </div>
          <a class="download-btn" href="{zip_url}">
            <span class="icon">⬇</span>
            <span>Скачать архив</span>
          </a>
        </div>
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th style="width: 34%;">Задача</th>
              <th style="width: 34%;">Исходный URL</th>
              <th style="width: 22%;">Локальный путь</th>
              <th style="width: 10%;">Файлы</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows)}
          </tbody>
        </table>
      </div>

      <div class="bottom-row">
        <a class="back-link" href="/">← Новый дамп</a>
        <span>Можно запускать парсер несколько раз — уже сохранённые директории останутся на диске.</span>
      </div>
    </div>
  </div>
</body>
</html>
    """
    return HTMLResponse(html)


@app.get("/download")
async def download(path: str):
    abs_path = os.path.abspath(path)
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="Файл не найден")

    return FileResponse(
        abs_path,
        media_type="application/zip",
        filename=os.path.basename(abs_path),
    )
