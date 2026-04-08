import sys
import os
from PyQt5 import QtCore, QtGui, QtWidgets, uic


# ──────────────────────────────────────────────
# Главное окно — Текстовый редактор
# ──────────────────────────────────────────────
class Win(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi('editor_form.ui', self)

        # Текущий путь к файлу
        self.current_file = None

        # Заполняем список шрифтов
        font_db = QtGui.QFontDatabase()
        for family in font_db.families():
            self.ui.font_family.addItem(family)
        # Устанавливаем шрифт по умолчанию
        default_font = self.ui.textBrowser.currentFont().family()
        index = self.ui.font_family.findText(default_font)
        if index >= 0:
            self.ui.font_family.setCurrentIndex(index)

        # ── Обработчики кнопок ──
        self.ui.btn_open.clicked.connect(self.on_open)
        self.ui.btn_save.clicked.connect(self.on_save)
        self.ui.btn_bold.clicked.connect(self.on_bold)
        self.ui.btn_italic.clicked.connect(self.on_italic)
        self.ui.btn_underline.clicked.connect(self.on_underline)
        self.ui.btn_color.clicked.connect(self.on_color)
        self.ui.font_size.valueChanged.connect(self.on_font_size)
        self.ui.font_family.currentTextChanged.connect(self.on_font_family)

        self.ui.show()

    # ── Открыть файл ──
    def on_open(self):
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Открыть файл', os.path.expanduser('~'),
            'Текстовые файлы (*.txt *.html *.htm);;Все файлы (*)'
        )
        if filepath:
            self.current_file = filepath
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            # Если HTML — загружаем как HTML, иначе как текст
            if filepath.lower().endswith(('.html', '.htm')):
                self.ui.textBrowser.setHtml(content)
            else:
                self.ui.textBrowser.setPlainText(content)

            self.setWindowTitle(f"Текстовый редактор — {os.path.basename(filepath)}")
            self.statusBar().showMessage(f"Открыт: {filepath}", 3000)

    # ── Сохранить файл ──
    def on_save(self):
        if not self.current_file:
            filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, 'Сохранить файл', os.path.expanduser('~'),
                'HTML (*.html);;Текстовые файлы (*.txt);;Все файлы (*)'
            )
            if not filepath:
                return
            self.current_file = filepath

        # Сохраняем как HTML (сохраняет форматирование)
        with open(self.current_file, 'w', encoding='utf-8') as f:
            if self.current_file.lower().endswith('.txt'):
                f.write(self.ui.textBrowser.toPlainText())
            else:
                f.write(self.ui.textBrowser.toHtml())

        self.setWindowTitle(
            f"Текстовый редактор — {os.path.basename(self.current_file)}"
        )
        self.statusBar().showMessage(f"Сохранено: {self.current_file}", 3000)

    # ── Жирный ──
    def on_bold(self):
        if self.ui.btn_bold.isChecked():
            self.ui.textBrowser.setFontWeight(QtGui.QFont.Bold)
        else:
            self.ui.textBrowser.setFontWeight(QtGui.QFont.Normal)

    # ── Курсив ──
    def on_italic(self):
        self.ui.textBrowser.setFontItalic(self.ui.btn_italic.isChecked())

    # ── Подчёркивание ──
    def on_underline(self):
        self.ui.textBrowser.setFontUnderline(self.ui.btn_underline.isChecked())

    # ── Цвет текста ──
    def on_color(self):
        color = QtWidgets.QColorDialog.getColor(
            self.ui.textBrowser.textColor(), self, "Выберите цвет текста"
        )
        if color.isValid():
            self.ui.textBrowser.setTextColor(color)

    # ── Размер шрифта ──
    def on_font_size(self, size):
        self.ui.textBrowser.setFontPointSize(size)

    # ── Семейство шрифта ──
    def on_font_family(self, family):
        self.ui.textBrowser.setFontFamily(family)


# ──────────────────────────────────────────────
# Точка входа
# ──────────────────────────────────────────────
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Win()
    sys.exit(app.exec_())
