import sys
import os
import csv
import smtplib
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header

from dotenv import load_dotenv
from PyQt5 import QtCore, QtGui, QtWidgets, uic

# Загружаем переменные из .env файла (рядом с main.py)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

# Путь по умолчанию для диалога выбора файлов
PATH = os.path.expanduser('~')


# ──────────────────────────────────────────────
# Функции для работы с вложениями
# ──────────────────────────────────────────────
def attach_file(msg, filepath):
    """Добавляет конкретный файл к сообщению."""
    filename = os.path.basename(filepath)
    ctype, encoding = mimetypes.guess_type(filepath)

    if ctype is None or encoding is not None:
        ctype = 'application/octet-stream'

    maintype, subtype = ctype.split('/', 1)

    if maintype == 'text':
        with open(filepath, 'r', encoding='utf-8', errors='replace') as fp:
            file = MIMEText(fp.read(), _subtype=subtype)
    elif maintype == 'image':
        with open(filepath, 'rb') as fp:
            file = MIMEImage(fp.read(), _subtype=subtype)
    elif maintype == 'audio':
        with open(filepath, 'rb') as fp:
            file = MIMEAudio(fp.read(), _subtype=subtype)
    else:
        with open(filepath, 'rb') as fp:
            file = MIMEBase(maintype, subtype)
            file.set_payload(fp.read())
        encoders.encode_base64(file)

    file.add_header('Content-Disposition', 'attachment', filename=filename)
    msg.attach(file)


def process_attachement(msg, files):
    """Обрабатывает список файлов/папок и прикрепляет их к сообщению."""
    for f in files:
        f = f.strip()
        if not f:
            continue
        if os.path.isfile(f):
            attach_file(msg, f)
        elif os.path.exists(f):
            for child in os.listdir(f):
                child_path = os.path.join(f, child)
                if os.path.isfile(child_path):
                    attach_file(msg, child_path)


# ──────────────────────────────────────────────
# Функция отправки email
# ──────────────────────────────────────────────
def send_email(addr_from, password, addr_to, msg_subj, msg_text, files, server_index):
    """Формирует и отправляет email через SMTP с вложениями."""
    msg = MIMEMultipart()
    msg['From'] = addr_from
    msg['To'] = addr_to
    msg['Subject'] = Header(msg_subj, 'utf-8')
    msg.attach(MIMEText(msg_text, 'plain', 'utf-8'))

    # Прикрепляем файлы
    if files:
        process_attachement(msg, files)

    # Выбор SMTP-сервера по индексу ComboBox
    if server_index == 0:       # yandex
        server = smtplib.SMTP_SSL('smtp.yandex.ru', 465)
    elif server_index == 1:     # mail.ru
        server = smtplib.SMTP_SSL('smtp.mail.ru', 465)
    elif server_index == 2:     # gmail
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    else:
        server = smtplib.SMTP_SSL('smtp.yandex.ru', 465)

    server.login(addr_from, password)
    server.sendmail(addr_from, [addr_to], msg.as_string())
    server.quit()


# ──────────────────────────────────────────────
# Главное окно приложения
# ──────────────────────────────────────────────
class Win(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi('email_form.ui', self)

        # Путь к выбранному CSV файлу
        self.path = ''

        # Предзаполняем из .env (если есть)
        env_from = os.getenv('EMAIL_FROM', '')
        env_pass = os.getenv('EMAIL_PASSWORD', '')
        if env_from:
            self.ui.addr_from.setText(env_from)
        if env_pass:
            self.ui.password.setText(env_pass)

        # Обработчики кнопок
        self.ui.sendmail.clicked.connect(self.on_sendmail)
        self.ui.open_file.clicked.connect(self.on_open_file)

        self.ui.show()

    def on_open_file(self):
        """Открывает диалог выбора CSV файла."""
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self,
            caption='Открыть файл',
            directory=PATH,
            filter='CSV (*.csv);;All Files (*)'
        )
        if filename:
            self.path = filename
            self.ui.label_4.setText(os.path.basename(filename))
            self.ui.label_4.setStyleSheet('color: black;')

    def on_sendmail(self):
        """Читает CSV и отправляет письма массово."""
        addr_from = self.ui.addr_from.text()
        password  = self.ui.password.text()

        if not addr_from or not password:
            QtWidgets.QMessageBox.warning(
                self, "Ошибка",
                "Заполните адрес отправителя и пароль!"
            )
            return

        if not self.path:
            QtWidgets.QMessageBox.warning(
                self, "Ошибка", "Выберите CSV файл!"
            )
            return

        msg_subj = self.ui.msg_subj.text()
        msg_text = self.ui.msg_text.toPlainText()
        server_index = self.ui.comboBox.currentIndex()

        # Директория CSV файла — для разрешения относительных путей к вложениям
        csv_dir = os.path.dirname(self.path)

        # Файл логирования
        log_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'send.txt'
        )
        my_file = open(log_path, 'a', encoding='utf-8')

        sent_count = 0
        errors = []

        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if not row or not row[0].strip():
                        continue

                    # Разбираем строку: email;файл1;файл2;...
                    parts = row[0].split(';')
                    addr_to = parts[0].strip()
                    # Файлы — всё после первого элемента (без пустых)
                    files = []
                    for p in parts[1:]:
                        p = p.strip()
                        if p:
                            # Если путь относительный — ищем от папки CSV
                            if not os.path.isabs(p):
                                p = os.path.join(csv_dir, p)
                            files.append(p)

                    try:
                        send_email(
                            addr_from, password, addr_to,
                            msg_subj, msg_text,
                            files, server_index
                        )
                        sent_count += 1
                        my_file.write(
                            "\n Email {0}; тема:{1}; сообщение: {2}".format(
                                addr_to, msg_subj, msg_text
                            )
                        )
                    except Exception as e:
                        errors.append(f"{addr_to}: {e}")

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Ошибка CSV", f"Не удалось прочитать CSV:\n{e}"
            )
            my_file.close()
            return

        my_file.close()

        # Итоговое сообщение
        result = f"Отправлено: {sent_count} писем."
        if errors:
            result += "\n\nОшибки:\n" + "\n".join(errors)
            QtWidgets.QMessageBox.warning(self, "Результат", result)
        else:
            QtWidgets.QMessageBox.information(self, "Успех", result)


# ──────────────────────────────────────────────
# Точка входа
# ──────────────────────────────────────────────
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Win()
    sys.exit(app.exec_())
