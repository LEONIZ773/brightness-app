"""Веб-приложение на Flask: изменение яркости изображения.

Лабораторная работа №3, вариант 3.
Пользователь загружает картинку, выбирает коэффициент яркости,
сервер возвращает результат, гистограммы RGB и статистику.
"""
import io
import os
import base64

import numpy as np
import requests
from flask import Flask, request, jsonify, render_template
from matplotlib.figure import Figure
from PIL import Image, ImageEnhance

app = Flask(__name__)
# Ограничение размера загружаемого файла: 10 МБ
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

# Ключи reCAPTCHA берутся из переменных окружения (в код их не пишем!).
# Если ключи не заданы, капча отключена - так удобно запускать локально.
RECAPTCHA_SITE_KEY = os.environ.get('RECAPTCHA_SITE_KEY', '')
RECAPTCHA_SECRET = os.environ.get('RECAPTCHA_SECRET', '')
CAPTCHA_ENABLED = bool(RECAPTCHA_SITE_KEY and RECAPTCHA_SECRET)


def verify_captcha(token: str) -> bool:
    """Проверяет ответ капчи на сервере Google."""
    if not CAPTCHA_ENABLED:
        return True
    if not token:
        return False
    try:
        r = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={'secret': RECAPTCHA_SECRET, 'response': token},
            timeout=5,
        )
        return bool(r.json().get('success'))
    except (requests.RequestException, ValueError):
        return False


def image_to_base64(img: Image.Image, fmt="PNG") -> str:
    """Картинка -> строка base64 (для передачи в JSON, без файлов на диске)."""
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode('utf-8')


def generate_histogram(img: Image.Image, title: str) -> str:
    """Гистограмма RGB в виде PNG (base64).

    Для каждого канала R, G, B считаем, сколько пикселей имеют
    каждое значение яркости от 0 до 255.
    """
    arr = np.array(img.convert("RGB"))

    # Figure вместо pyplot: не хранит глобальное состояние,
    # безопасно при нескольких запросах одновременно.
    fig = Figure(figsize=(6, 3))
    fig.patch.set_facecolor('#0d0d0d')
    ax = fig.subplots()
    ax.set_facecolor('#111111')

    colors = [('#e05c5c', 'R'), ('#5ce07a', 'G'), ('#5c9ae0', 'B')]
    for i, (color, label) in enumerate(colors):
        channel = arr[:, :, i].flatten()
        ax.hist(channel, bins=128, range=(0, 256), color=color,
                alpha=0.75, label=label, histtype='stepfilled', linewidth=0)

    ax.set_xlim(0, 255)
    ax.set_title(title, color='#cccccc', fontsize=11, pad=8)
    ax.tick_params(colors='#555555', labelsize=8)
    ax.spines['bottom'].set_color('#333333')
    ax.spines['left'].set_color('#333333')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_xlabel('Значение пикселя', color='#777777', fontsize=8)
    ax.set_ylabel('Частота', color='#777777', fontsize=8)
    ax.legend(framealpha=0, labelcolor='#aaaaaa', fontsize=8)
    fig.tight_layout(pad=0.5)

    buf = io.BytesIO()
    fig.savefig(buf, format='PNG', dpi=120, facecolor=fig.get_facecolor())
    return base64.b64encode(buf.getvalue()).decode('utf-8')


def stats(arr) -> dict:
    """Среднее, минимум, максимум и стандартное отклонение пикселей."""
    return {
        'mean': round(float(arr.mean()), 2),
        'min': int(arr.min()),
        'max': int(arr.max()),
        'std': round(float(arr.std()), 2),
    }


@app.route('/')
def index():
    return render_template(
        'index.html',
        site_key=RECAPTCHA_SITE_KEY,
        captcha_enabled=CAPTCHA_ENABLED,
    )


@app.errorhandler(413)
def too_large(_):
    return jsonify({'error': 'Файл слишком большой (максимум 10 МБ)'}), 413


@app.route('/process', methods=['POST'])
def process():
    if not verify_captcha(request.form.get('g-recaptcha-response', '')):
        return jsonify({'error': 'Подтвердите, что вы не робот'}), 400

    if 'image' not in request.files:
        return jsonify({'error': 'Файл не передан'}), 400

    try:
        brightness = float(request.form.get('brightness', 1.0))
    except ValueError:
        return jsonify({'error': 'Некорректное значение яркости'}), 400

    # Коэффициент ограничиваем диапазоном 0..4
    brightness = max(0.0, min(4.0, brightness))

    try:
        original = Image.open(request.files['image'].stream)
        original.load()
    except Exception:
        return jsonify({'error': 'Не удалось открыть изображение'}), 400

    # Есть ли у картинки прозрачность (альфа-канал)?
    has_alpha = 'A' in original.getbands() or 'transparency' in original.info
    original = original.convert("RGBA") if has_alpha else original.convert("RGB")

    # Яркость: ImageEnhance умножает каждый пиксель на коэффициент
    # (0 - чёрное, 1 - без изменений, 2 - вдвое ярче).
    rgb = original.convert("RGB")
    enhanced_rgb = ImageEnhance.Brightness(rgb).enhance(brightness)

    # Прозрачность берём из оригинала и склеиваем обратно
    if has_alpha:
        r, g, b = enhanced_rgb.split()
        a = original.split()[3]
        result = Image.merge("RGBA", (r, g, b, a))
    else:
        result = enhanced_rgb

    return jsonify({
        'original_image': image_to_base64(original),
        'result_image': image_to_base64(result),
        'original_hist': generate_histogram(rgb, 'Оригинал - гистограмма RGB'),
        'result_hist': generate_histogram(
            enhanced_rgb, f'Яркость x{brightness:.2f} - гистограмма RGB'),
        'original_stats': stats(np.array(rgb)),
        'result_stats': stats(np.array(enhanced_rgb)),
        'brightness_applied': brightness,
    })


if __name__ == '__main__':
    # Локальный запуск: python app.py
    app.run(host='127.0.0.1', port=5000, debug=False)
