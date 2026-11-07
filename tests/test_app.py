import io

import pytest
from PIL import Image

import app as app_module


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, 'verify_captcha', lambda token: True)
    app_module.app.config['TESTING'] = True
    return app_module.app.test_client()


def make_png(value=100):
    """Однотонная картинка 20x20 с заданным значением яркости."""
    buf = io.BytesIO()
    Image.new('RGB', (20, 20), (value, value, value)).save(buf, 'PNG')
    buf.seek(0)
    return buf


def send(client, file, brightness):
    return client.post(
        '/process',
        content_type='multipart/form-data',
        data={'image': (file, 'test.png'), 'brightness': brightness},
    )

# Страница открывается
def test_index_page(client):
    r = client.get('/')
    assert r.status_code == 200
    assert 'LUMOS' in r.get_data(as_text=True)

# Запрос без картинки
def test_no_file(client):
    r = client.post('/process', data={'brightness': '1'})
    assert r.status_code == 400

# вместо числа
def test_bad_brightness_value(client):
    assert send(client, make_png(), 'abc').status_code == 400

# Вместо картинки обычный текст
def test_not_an_image(client):
    assert send(client, io.BytesIO(b'just text'), '1').status_code == 400

# Серый цвет 100 с яркостью 2
def test_brightness_x2(client):
    data = send(client, make_png(100), '2.0').get_json()
    assert data['original_stats']['mean'] == 100.0
    assert data['result_stats']['mean'] == 200.0 # средняя стала

# Яркость 1
def test_brightness_unchanged(client):
    data = send(client, make_png(100), '1.0').get_json()
    assert data['result_stats']['mean'] == 100.0 # средние осталось 

# Яркость 0
def test_brightness_zero_is_black(client):
    data = send(client, make_png(100), '0').get_json()
    assert data['result_stats']['max'] == 0 # Макс 0, черная картинка

# Яркость 10/ сервер ограничил её до 4,50×4
def test_brightness_clamped_to_4(client):
    data = send(client, make_png(50), '10').get_json()
    assert data['brightness_applied'] == 4.0
    assert data['result_stats']['mean'] == 200.0

# Структура ответа / что есть все 6 пол
def test_response_has_all_fields(client):
    data = send(client, make_png(), '1.5').get_json()
    for key in ('original_image', 'result_image', 'original_hist',
                'result_hist', 'original_stats', 'result_stats'):
        assert key in data

# Капча не пройдена
def test_captcha_failure_is_rejected(client, monkeypatch):
    monkeypatch.setattr(app_module, 'verify_captcha', lambda token: False)
    assert send(client, make_png(), '1').status_code == 400
