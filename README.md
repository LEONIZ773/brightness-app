# LUMOS — изменение яркости изображения

Лабораторная работа №3 «Разработка веб-приложения на python», вариант 3.

Веб-приложение на Flask: пользователь загружает изображение и выбирает
коэффициент яркости (0–4). Сервер возвращает результат, гистограммы RGB
исходной и новой картинки и статистику пикселей (среднее, min, max, std).

- Защита формы: Google reCAPTCHA v2
- Тесты: pytest (10 тестов)
- CI: GitHub Actions (тесты при каждом push)
- Деплой: PythonAnywhere (через API), запускается только после успешных тестов

## Структура

```
app.py                  - приложение Flask
templates/index.html    - страница
static/styles.css       - стили
tests/test_app.py       - тесты
.github/workflows/ci.yml - тесты + деплой
deploy_pythonanywhere.py - выгрузка на PythonAnywhere
requirements.txt        - зависимости
```

## Локальный запуск

```
pip install -r requirements.txt
python app.py
```

Откройте http://127.0.0.1:5000. Без ключей капчи приложение работает
с отключённой капчей (удобно для отладки).

Чтобы включить капчу локально, задайте переменные окружения:

- Windows (cmd): `set RECAPTCHA_SITE_KEY=...` и `set RECAPTCHA_SECRET=...`
- Linux/Mac: `export RECAPTCHA_SITE_KEY=...` и `export RECAPTCHA_SECRET=...`

## Тесты

```
python -m pytest -v
```
