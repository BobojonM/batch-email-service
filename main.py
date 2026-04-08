import sys
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header

from dotenv import load_dotenv
from PyQt5 import QtCore, QtGui, QtWidgets, uic

# Загружаем переменные из .env файла (рядом с main.py)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))


# ──────────────────────────────────────────────
# Функция отправки email
# ──────────────────────────────────────────────
def send_email(addr_from, password, addr_to, msg_subj, msg_text):
    """
    Формирует и отправляет email через SMTP.
    Пример использует Яндекс SMTP (smtp.yandex.ru:465).
    """
    msg = MIMEMultipart()
    msg['From'] = addr_from                          # Адресат (отправитель)
    msg['To'] = addr_to                              # Получатель
    msg['Subject'] = Header(msg_subj, 'utf-8')       # Тема сообщения
    msg.attach(MIMEText(msg_text, 'plain', 'utf-8')) # Текст письма

    # Подключение к SMTP-серверу (Яндекс)
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
        # Загружаем UI-форму, созданную в Qt Designer
        self.ui = uic.loadUi('email_form.ui', self)

        # Обработчик нажатия кнопки «Отправить»
        self.ui.sendmail.clicked.connect(self.on_sendmail)

        self.ui.show()

    def on_sendmail(self):
        """Собирает данные с формы и вызывает отправку."""
        # Данные отправителя берутся из .env файла
        addr_from = os.getenv('EMAIL_FROM')
        password  = os.getenv('EMAIL_PASSWORD')

        if not addr_from or not password:
            QtWidgets.QMessageBox.warning(
                self, "Ошибка конфигурации",
                "Не заданы EMAIL_FROM и/или EMAIL_PASSWORD в файле .env"
            )
            return

        addr_to  = self.ui.addr_to.text()
        msg_subj = self.ui.msg_subj.text()
        msg_text = self.ui.msg_text.toPlainText()

        try:
            send_email(addr_from, password, addr_to, msg_subj, msg_text)
            QtWidgets.QMessageBox.information(
                self, "Успех", "Письмо успешно отправлено!"
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Ошибка", f"Не удалось отправить письмо:\n{e}"
            )


# ──────────────────────────────────────────────
# Точка входа
# ──────────────────────────────────────────────
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Win()
    sys.exit(app.exec_())
