# scraper_core.py
import os
import re
import asyncio
import shutil
from datetime import datetime
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

def parse_cookie_header(cookie_str: Optional[str]) -> dict:
    if not cookie_str:
        return {}
    cookies = {}
    for part in cookie_str.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


def safe_name(name: str, default: str = "challenge") -> str:
    if not name:
        name = default
    name = re.sub(r"[^\w\-.]+", "_", name, flags=re.UNICODE)
    return name.strip("._") or default


def get_api_root(url: str) -> str:
    """
    Получить базу API вида https://host/api/v1
    """
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}/api/v1"


async def login_ctfd(
    client: httpx.AsyncClient,
    login_url: str,
    username: str,
    password: str,
) -> None:
    print(f"[+] Пытаюсь залогиниться по адресу: {login_url}")
    r = await client.get(login_url)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    form = soup.find("form")
    if not form:
        raise RuntimeError("Не найден <form> на странице логина")

    action = form.get("action") or login_url
    action_url = urljoin(login_url, action)

    data = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        if not name:
            continue
        value = inp.get("value", "")
        data[name] = value

    username_fields = ["name", "username", "email", "login"]
    password_fields = ["password", "pass", "pwd"]

    form_field_names = set(data.keys())

    username_field_name = next(
        (c for c in username_fields if c in form_field_names), None
    )
    password_field_name = next(
        (c for c in password_fields if c in form_field_names), None
    )

    if not username_field_name or not password_field_name:
        raise RuntimeError(
            f"Не удалось определить имена полей логина/пароля в форме. "
            f"Найденные поля: {form_field_names}"
        )

    data[username_field_name] = username
    data[password_field_name] = password

    print(
        f"[+] Отправляю форму логина на {action_url} "
        f"(user field: {username_field_name}, pass field: {password_field_name})"
    )

    r2 = await client.post(action_url, data=data, follow_redirects=True)
    r2.raise_for_status()

    if "/login" in str(r2.url):
        print(f"[!] Похоже, логин не удался, всё ещё на странице логина: {r2.url}")
    else:
        print(f"[+] Логин вероятно успешен, текущий URL: {r2.url}")


async def api_get_json(client: httpx.AsyncClient, url: str) -> dict:
    """
    GET к CTFd API с JSON-ответом.
    Обязательно ставим Content-Type: application/json (даже для GET),
    иначе некоторые версии CTFd не отдают JSON нормально.
    """
    r = await client.get(url, headers={"Content-Type": "application/json"})
    r.raise_for_status()
    try:
        return r.json()
    except ValueError as e:
        raise RuntimeError(f"Не удалось распарсить JSON с {url}: {e}") from e


async def api_list_challenges(
    client: httpx.AsyncClient,
    any_url_on_site: str,
) -> List[Dict[str, Any]]:
    """
    /api/v1/challenges — основной способ получить список задач.
    """
    api_root = get_api_root(any_url_on_site)
    url = f"{api_root}/challenges"
    print(f"[+] Запрашиваю список задач через API: {url}")
    data = await api_get_json(client, url)
    if not data.get("success", False):
        raise RuntimeError(f"API /challenges вернул success={data.get('success')}")
    challenges = data.get("data") or []
    print(f"[+] Через API найдено задач: {len(challenges)}")
    return challenges



def extract_title(soup: BeautifulSoup) -> str:
    candidates = soup.select(
        '.challenge-name, .challenge-title, h1.challenge-name, h1.challenge-title'
    )
    for el in candidates:
        text = el.get_text(strip=True)
        if text:
            return text

    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)

    if soup.title and soup.title.string:
        return soup.title.string.strip()

    return "challenge"


def extract_description(soup: BeautifulSoup) -> str:
    desc_selectors = [
        ".challenge-desc",
        ".challenge-description",
        ".challenge-description-body",
        ".challenge-text",
        "#challenge-desc",
    ]
    for sel in desc_selectors:
        el = soup.select_one(sel)
        if el:
            text = el.get_text("\n", strip=True)
            if text:
                return text

    paragraphs = soup.find_all(["p", "div"])
    best = ""
    for p in paragraphs:
        text = p.get_text(" ", strip=True)
        if len(text) > len(best) and len(text) > 40:
            best = text
    return best or "Описание не найдено автоматически."




def extract_file_links(soup: BeautifulSoup, base_url: str):
    file_links = []

    file_containers = soup.select(
        ".challenge-files, .challenge-file, .files, .attachments"
    )
    if not file_containers:
        candidates = soup.find_all("a", attrs={"download": True})
        if not candidates:
            candidates = soup.find_all("a", href=True)
        links = candidates
    else:
        links = []
        for cont in file_containers:
            links.extend(cont.find_all("a", href=True))

    seen = set()
    for a in links:
        href = a.get("href")
        if not href:
            continue
        abs_url = urljoin(base_url, href).split("#", 1)[0]
        if abs_url in seen:
            continue
        seen.add(abs_url)

        fname = (
            a.get("download")
            or a.get_text(strip=True)
            or os.path.basename(urlparse(abs_url).path)
        )
        fname = safe_name(
            fname, default=os.path.basename(urlparse(abs_url).path) or "file"
        )
        if not fname:
            continue
        file_links.append((fname, abs_url))

    return file_links


async def scrape_ctfd_challenge(
    client: httpx.AsyncClient,
    url: str,
    out_root: Optional[str],
    save_files: bool = True,
    save_desc: bool = True,
    save_html: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Скачивает одну задачу:
      - ID берём из фрагмента #...-<id> или из пути /challenges/<id>
      - по ID идём в /api/v1/challenges/<id>
      - при проблемах с API падаем на HTML-разбор.
    """
    print(f"[+] GET {url} (страница задачи)")
    # это будет /challenges#-id — сервер всё равно вернёт /challenges
    resp = await client.get(url)
    resp.raise_for_status()

    html_text = resp.text
    soup = BeautifulSoup(html_text, "html.parser")

    p = urlparse(url)
    site_root = f"{p.scheme}://{p.netloc}"

    # ---- достаём ID задачи ----
    challenge_id: Optional[int] = None

    # 1) сначала пробуем из фрагмента #...-<id>, например "#-23" или "#Скоростные-Пазлы-1-23"
    frag = p.fragment or ""
    if frag:
        nums = re.findall(r"\d+", frag)
        if nums:
            try:
                challenge_id = int(nums[-1])
            except ValueError:
                challenge_id = None

    # 2) если с фрагментом не получилось — пробуем из пути /challenges/<id>
    if challenge_id is None:
        path_parts = [seg for seg in p.path.split("/") if seg]
        if len(path_parts) >= 2 and path_parts[0] == "challenges" and path_parts[1].isdigit():
            challenge_id = int(path_parts[1])

    api_data: Optional[Dict[str, Any]] = None

    # ---- пробуем достать данные через API ----
    if challenge_id is not None:
        api_root = get_api_root(url)
        api_url = f"{api_root}/challenges/{challenge_id}"
        try:
            data = await api_get_json(client, api_url)
            if data.get("success", False):
                api_data = data.get("data") or {}
                print(f"[+] Получены данные задачи через API: id={challenge_id}")
            else:
                print(
                    f"[!] API /challenges/{challenge_id} вернул success={data.get('success')}, "
                    f"использую HTML."
                )
        except Exception as e:
            print(f"[!] Не удалось получить задачу {challenge_id} через API: {e}")

    # ---- формируем title/description/files ----
    if api_data:
        title_core = api_data.get("name") or extract_title(soup)
        category = api_data.get("category") or ""
        value = api_data.get("value")

        if category:
            title = f"[{category}] {title_core}"
        else:
            title = title_core

        desc_html = api_data.get("description") or ""
        if desc_html:
            desc = BeautifulSoup(desc_html, "html.parser").get_text("\n", strip=True)
        else:
            desc = extract_description(soup)

        files: List[tuple[str, str]] = []
        for rel in api_data.get("files") or []:
            if not rel:
                continue
            f_url = urljoin(site_root, rel)
            fname = os.path.basename(urlparse(rel).path) or "file"
            fname = safe_name(fname)
            files.append((fname, f_url))

        extra_meta_lines = []
        if category:
            extra_meta_lines.append(f"Category: {category}")
        if value is not None:
            extra_meta_lines.append(f"Points: {value}")
        meta_header = "\n".join(extra_meta_lines)
    else:
        # API не сработал — пробуем выжать максимум из HTML
        title = extract_title(soup)
        desc = extract_description(soup)
        files = extract_file_links(soup, url)
        meta_header = ""

    # ---- сохраняем на диск ----
    base_name = safe_name(title)

    # подпапка категории
    category_dir_name: Optional[str] = None
    if category:
        category_dir_name = safe_name(category, default="Uncategorized")

    if out_root:
        if category_dir_name:
            challenge_dir = os.path.join(out_root, category_dir_name, base_name)
        else:
            challenge_dir = os.path.join(out_root, base_name)
    else:
        if category_dir_name:
            challenge_dir = os.path.join(category_dir_name, base_name)
        else:
            challenge_dir = base_name


    os.makedirs(challenge_dir, exist_ok=True)

    # HTML
    if save_html:
        html_path = os.path.join(challenge_dir, "page.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_text)

    # Описание
    if save_desc:
        desc_path = os.path.join(challenge_dir, "description.txt")
        with open(desc_path, "w", encoding="utf-8") as f:
            f.write(f"URL: {url}\n")
            if challenge_id is not None:
                f.write(f"Challenge ID: {challenge_id}\n")
            if api_data:
                f.write(f"Title: {api_data.get('name') or title}\n")
            else:
                f.write(f"Title: {title}\n")
            if meta_header:
                f.write(meta_header + "\n")
            f.write("\n")
            f.write(desc or "Описание не найдено.")

    # Файлы
    saved_files_count = 0
    if save_files and files:
        files_dir = os.path.join(challenge_dir, "files")
        os.makedirs(files_dir, exist_ok=True)

        for fname, f_url in files:
            print(f"[+]   Скачиваю файл: {f_url}")
            r = await client.get(f_url)
            r.raise_for_status()
            out_path = os.path.join(files_dir, fname)
            with open(out_path, "wb") as out_f:
                out_f.write(r.content)
            saved_files_count += 1

    return {
        "url": url,
        "title": title,
        "dir": os.path.abspath(challenge_dir),
        "files_count": saved_files_count,
        "category": category or "",
    }


async def discover_challenge_urls_from_list(
    client: httpx.AsyncClient,
    list_url: str,
) -> List[str]:
    """
    Пытается найти задачи:
      1) сначала через /api/v1/challenges (JS вообще не нужен),
      2) если API не сработал — разбираем HTML-верстку /challenges как fallback.

    ВАЖНО: "красивые" ссылки делаем вида:
      https://host/challenges#-<id>
    """
    p = urlparse(list_url)
    base_root = f"{p.scheme}://{p.netloc}"
    urls: List[str] = []

    # ---------- 1) Пробуем API ----------
    try:
        chals = await api_list_challenges(client, list_url)
        for chal in chals:
            cid = chal.get("id")
            if isinstance(cid, int) or (isinstance(cid, str) and cid.isdigit()):
                cid_str = str(cid)
                # вот тут и делаем нужный формат
                urls.append(f"{base_root}/challenges#-{cid_str}")
        urls = sorted(set(urls))
        if urls:
            print(f"[+] Через API найдено задач: {len(urls)}")
            for u in urls:
                print(f"    - {u}")
            return urls
        else:
            print("[!] API /challenges вернул пустой список, пробую HTML-разбор…")
    except Exception as e:
        print(f"[!] Ошибка при получении списка задач через API: {e}")
        print("[!] Пытаюсь разобрать HTML-страницу /challenges…")

    # ---------- 2) Fallback: HTML /challenges ----------
    print(f"[+] Открываю страницу списка задач: {list_url}")
    resp = await client.get(list_url)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    base_host = p.netloc

    url_set: set[str] = set()

    # Вариант 0: фрагмент с "-<id>" в anchor (#имя-23)
    if p.fragment:
        frag = p.fragment
        last_part = frag.rsplit("-", 1)[-1].strip()
        last_part = last_part.replace("–", "").strip()
        last_digits = "".join(ch for ch in last_part if ch.isdigit())
        if last_digits.isdigit():
            cid = last_digits
            candidate = f"{p.scheme}://{p.netloc}/challenges#-{cid}"
            url_set.add(candidate)

    # Вариант 1: <a href=...>
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.lower().startswith("javascript:"):
            continue

        abs_url = urljoin(list_url, href)
        pp = urlparse(abs_url)

        if pp.netloc != base_host:
            continue

        path = pp.path
        segments = [seg for seg in path.split("/") if seg]
        fragment = pp.fragment.strip()

        candidate: Optional[str] = None

        if segments and segments[0] == "challenges":
            if len(segments) >= 2:
                cid = segments[1]
                if cid.isdigit():
                    candidate = f"{pp.scheme}://{pp.netloc}/challenges#-{cid}"
            else:
                if fragment:
                    last_part = fragment.rsplit("-", 1)[-1].strip()
                    last_part = last_part.replace("–", "").strip()
                    last_digits = "".join(ch for ch in last_part if ch.isdigit())
                    if last_digits.isdigit():
                        candidate = f"{pp.scheme}://{pp.netloc}/challenges#-{last_digits}"

        if candidate:
            url_set.add(candidate)

    # Вариант 2: кнопки challenge-button[value="id"]
    for btn in soup.select("button.challenge-button[value]"):
        cid = btn.get("value", "").strip()
        if cid.isdigit():
            candidate = f"{p.scheme}://{p.netloc}/challenges#-{cid}"
            url_set.add(candidate)

    urls = sorted(url_set)
    print(f"[+] Найдено задач на странице (HTML): {len(urls)}")
    for u in urls:
        print(f"    - {u}")
    return urls


def is_challenge_list_url(url: str) -> bool:
    p = urlparse(url)
    path = p.path.rstrip("/")
    return path.endswith("/challenges") or path == "/challenges"



def write_index_md(results: List[Dict[str, Any]], out_root: Optional[str]) -> str:
    if not results:
        return ""

    root = out_root or "."
    os.makedirs(root, exist_ok=True)
    index_path = os.path.join(root, "INDEX.md")

    results_sorted = sorted(results, key=lambda r: r["title"].lower())

    lines = []
    lines.append("# CTF Dump Index\n")
    lines.append("")
    lines.append("| # | Category | Title | URL | Local path | Files |")
    lines.append("|---|----------|-------|-----|-----------|-------|")


    for i, info in enumerate(results_sorted, start=1):
        rel_path = os.path.relpath(info["dir"], root)
        title = info["title"].replace("|", "\\|")
        category = (info.get("category") or "").replace("|", "\\|")
        url = info["url"]
        files_count = info["files_count"]
        lines.append(
            f"| {i} | {category} | {title} | {url} | `{rel_path}` | {files_count} |"
        )


    content = "\n".join(lines) + "\n"

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(content)

    return index_path



def make_zip_archive(root: str) -> str:
    root = os.path.abspath(root)
    base_dir = os.path.dirname(root)
    base_name = os.path.basename(root)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_base = os.path.join(base_dir, f"{base_name}_{ts}")
    archive_path = shutil.make_archive(archive_base, "zip", root_dir=root)
    return archive_path



async def run_scrape(
    base_urls: List[str],
    username: str = "",
    password: str = "",
    api_token: str = "",
    cookie: str = "",
    login_url: str = "",
    out_dir: str = "./ctf_dump",
    concurrency: int = 5,
    no_files: bool = False,
    no_desc: bool = False,
    save_html: bool = False,
) -> Dict[str, Any]:
    """
    Главная функция: делает всё и возвращает результат для веба.
    """
    cookie_str = cookie or None
    cookies = parse_cookie_header(cookie_str)

    headers = {
        "User-Agent": "ctfd-async-scraper-httpx/web",
        "Accept-Language": "ru,en;q=0.8",
    }
    if api_token:
        headers["Authorization"] = f"Token {api_token.strip()}"

    urls = [u.strip() for u in base_urls if u.strip()]
    effective_out_dir = out_dir or "./ctf_dump"

    async with httpx.AsyncClient(
        cookies=cookies,
        headers=headers,
        follow_redirects=True,
        timeout=20.0,
    ) as client:

        # логин по форме, если надо
        if username and password and urls:
            if login_url:
                login_url_eff = login_url
            else:
                p = urlparse(urls[0])
                login_url_eff = f"{p.scheme}://{p.netloc}/login"
            await login_ctfd(client, login_url_eff, username, password)

        # получаем список URL задач
        challenge_urls: List[str] = []
        for u in urls:
            if is_challenge_list_url(u):
                discovered = await discover_challenge_urls_from_list(client, u)
                challenge_urls.extend(discovered)
            else:
                challenge_urls.append(u)

        # unique
        seen = set()
        uniq_challenge_urls: List[str] = []
        for u in challenge_urls:
            if u not in seen:
                seen.add(u)
                uniq_challenge_urls.append(u)

        if not uniq_challenge_urls:
            return {
                "results": [],
                "index_path": "",
                "zip_path": "",
            }

        semaphore = asyncio.Semaphore(concurrency)
        results: List[Dict[str, Any]] = []

        async def worker(ch_url: str):
            async with semaphore:
                try:
                    info = await scrape_ctfd_challenge(
                        client=client,
                        url=ch_url,
                        out_root=effective_out_dir,
                        save_files=not no_files,
                        save_desc=not no_desc,
                        save_html=save_html,
                    )
                    if info:
                        results.append(info)
                except Exception as e:
                    print(f"[!] Ошибка при обработке {ch_url}: {e}")

        tasks = [asyncio.create_task(worker(u)) for u in uniq_challenge_urls]
        await asyncio.gather(*tasks)

    index_path = write_index_md(results, effective_out_dir)
    zip_path = make_zip_archive(effective_out_dir)

    return {
        "results": results,
        "index_path": index_path,
        "zip_path": zip_path,
    }
