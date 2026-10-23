"""Выгрузка проекта на PythonAnywhere через их API и перезагрузка сайта.

Запускается из GitHub Actions ТОЛЬКО после успешных тестов.
Нужные переменные окружения (берутся из GitHub Secrets):
  PA_USERNAME - логин на PythonAnywhere
  PA_TOKEN    - API-токен (вкладка Account -> API token)
  PA_DOMAIN   - адрес сайта, например ivan.pythonanywhere.com
"""
import os
import sys
from pathlib import Path

import requests

USER = os.environ["PA_USERNAME"].strip()
TOKEN = os.environ["PA_TOKEN"].strip()
DOMAIN = os.environ["PA_DOMAIN"].strip().replace("https://", "").rstrip("/")

# Аккаунты в ЕС живут на другом адресе API
HOST = ("eu.pythonanywhere.com" if DOMAIN.endswith(".eu.pythonanywhere.com")
        else "www.pythonanywhere.com")
API = f"https://{HOST}/api/v0/user/{USER}"
REMOTE_DIR = f"/home/{USER}/brightness-app"
HEADERS = {"Authorization": f"Token {TOKEN}"}


def files_to_upload():
    """Что именно выгружаем на сервер (тесты и служебные файлы - нет)."""
    result = [Path("app.py"), Path("requirements.txt")]
    for folder in ("templates", "static"):
        result += sorted(p for p in Path(folder).rglob("*") if p.is_file())
    return result


def main() -> int:
    for path in files_to_upload():
        remote = f"{REMOTE_DIR}/{path.as_posix()}"
        r = requests.post(
            f"{API}/files/path{remote}",
            headers=HEADERS,
            files={"content": (path.name, path.read_bytes())},
            timeout=60,
        )
        if r.status_code not in (200, 201):
            print(f"ОШИБКА загрузки {path}: HTTP {r.status_code} {r.text[:300]}")
            return 1
        print(f"загружен: {path}")

    r = requests.post(f"{API}/webapps/{DOMAIN}/reload/", headers=HEADERS, timeout=60)
    if r.status_code != 200:
        print(f"ОШИБКА перезагрузки сайта: HTTP {r.status_code} {r.text[:300]}")
        return 1
    print(f"сайт {DOMAIN} перезагружен")
    return 0


if __name__ == "__main__":
    sys.exit(main())
