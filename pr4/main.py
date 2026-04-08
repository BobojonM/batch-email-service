import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header

from flask import Flask, request, render_template_string
from waitress import serve

app = Flask(__name__)


# ──────────────────────────────────────────────
# HTML-шаблон формы
# ──────────────────────────────────────────────
HTML_FORM = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Веб-сервис отправки Email</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 { color: #333; }
        form {
            background: #fff;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        label {
            display: block;
            margin-top: 12px;
            font-weight: bold;
            color: #555;
        }
        input, textarea, select {
            width: 100%;
            padding: 8px;
            margin-top: 4px;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-sizing: border-box;
        }
        textarea { height: 120px; resize: vertical; }
        button {
            margin-top: 18px;
            padding: 10px 30px;
            background: #4CAF50;
            color: #fff;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover { background: #45a049; }
        .msg-ok  { color: green; font-weight: bold; }
        .msg-err { color: red;   font-weight: bold; }
    </style>
</head>
<body>
    <h1>Отправка Email</h1>
    {% if message %}
        <p class="{{ msg_class }}">{{ message }}</p>
    {% endif %}
    <form method="POST">
        <label>Сервер</label>
        <select name="server">
            <option value="yandex">yandex</option>
            <option value="mail">mail</option>
            <option value="gmail">gmail</option>
        </select>

        <label>Адрес отправителя</label>
        <input type="email" name="addr_from" placeholder="your_email@yandex.ru" required>

        <label>Пароль</label>
        <input type="password" name="password" required>

        <label>Адрес получателя</label>
        <input type="email" name="addr_to" placeholder="recipient@mail.ru" required>

        <label>Тема</label>
        <input type="text" name="subject" placeholder="Тема письма">

        <label>Текст сообщения</label>
        <textarea name="text" placeholder="Введите текст письма..."></textarea>

        <button type="submit">Отправить</button>
    </form>
</body>
</html>
"""


# ──────────────────────────────────────────────
# Функция отправки email
# ──────────────────────────────────────────────
def send_email(addr_from, password, addr_to, msg_subj, msg_text, server_name):
    """Формирует и отправляет email через SMTP."""
    msg = MIMEMultipart()
    msg['From'] = addr_from
    msg['To'] = addr_to
    msg['Subject'] = Header(msg_subj, 'utf-8')
    msg.attach(MIMEText(msg_text, 'plain', 'utf-8'))

    # Выбор SMTP-сервера
    if server_name == 'mail':
        server = smtplib.SMTP_SSL('smtp.mail.ru', 465)
    elif server_name == 'gmail':
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    else:  # yandex по умолчанию
        server = smtplib.SMTP_SSL('smtp.yandex.ru', 465)

    server.login(addr_from, password)
    server.sendmail(addr_from, [addr_to], msg.as_string())
    server.quit()


# ──────────────────────────────────────────────
# Обработчик GET и POST запросов
# ──────────────────────────────────────────────
@app.route("/", methods=['GET', 'POST'])
def index():
    message = None
    msg_class = ''

    if request.method == 'POST':
        addr_from   = request.form['addr_from']
        password    = request.form['password']
        addr_to     = request.form['addr_to']
        msg_subj    = request.form['subject']
        msg_text    = request.form['text']
        server_name = request.form['server']

        try:
            send_email(addr_from, password, addr_to, msg_subj, msg_text, server_name)
            message = "Письмо успешно отправлено!"
            msg_class = 'msg-ok'
        except Exception as e:
            message = f"Ошибка отправки: {e}"
            msg_class = 'msg-err'

    return render_template_string(HTML_FORM, message=message, msg_class=msg_class)


# ──────────────────────────────────────────────
# Запуск веб-сервера
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("Сервер запущен: http://0.0.0.0:1516")
    serve(app, host='0.0.0.0', port=1516)
