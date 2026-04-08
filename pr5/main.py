import sys
import re
from PyQt5 import QtCore, QtGui, QtWidgets, uic


# ──────────────────────────────────────────────
# Алгоритм вычисления выражений
# (рекурсивный спуск — поддержка +, -, *, /, скобок)
# ──────────────────────────────────────────────
class Parser:
    """
    Парсер математических выражений.
    Поддерживает: числа (целые и дробные), +, -, *, /, скобки ().
    Пример: (2+3)*4 - 10/(2+3)
    """

    def __init__(self, expression):
        # Убираем пробелы
        self.text = expression.replace(' ', '')
        self.pos = 0

    def parse(self):
        result = self.parse_expression()
        if self.pos < len(self.text):
            raise ValueError(
                f"Неожиданный символ '{self.text[self.pos]}' "
                f"на позиции {self.pos + 1}"
            )
        return result

    def parse_expression(self):
        """Обрабатывает сложение и вычитание."""
        result = self.parse_term()
        while self.pos < len(self.text) and self.text[self.pos] in '+-':
            op = self.text[self.pos]
            self.pos += 1
            right = self.parse_term()
            if op == '+':
                result += right
            else:
                result -= right
        return result

    def parse_term(self):
        """Обрабатывает умножение и деление."""
        result = self.parse_factor()
        while self.pos < len(self.text) and self.text[self.pos] in '*/':
            op = self.text[self.pos]
            self.pos += 1
            right = self.parse_factor()
            if op == '*':
                result *= right
            else:
                if right == 0:
                    raise ValueError("Деление на ноль!")
                result /= right
        return result

    def parse_factor(self):
        """Обрабатывает унарный минус, скобки и числа."""
        # Унарный минус
        if self.pos < len(self.text) and self.text[self.pos] == '-':
            self.pos += 1
            return -self.parse_factor()

        # Унарный плюс
        if self.pos < len(self.text) and self.text[self.pos] == '+':
            self.pos += 1
            return self.parse_factor()

        # Скобки
        if self.pos < len(self.text) and self.text[self.pos] == '(':
            self.pos += 1  # пропускаем '('
            result = self.parse_expression()
            if self.pos >= len(self.text) or self.text[self.pos] != ')':
                raise ValueError("Не найдена закрывающая скобка ')'")
            self.pos += 1  # пропускаем ')'
            return result

        # Число
        return self.parse_number()

    def parse_number(self):
        """Считывает число (целое или дробное)."""
        start = self.pos
        while self.pos < len(self.text) and (
            self.text[self.pos].isdigit() or self.text[self.pos] == '.'
        ):
            self.pos += 1

        if self.pos == start:
            if self.pos < len(self.text):
                raise ValueError(
                    f"Ожидалось число, получен '{self.text[self.pos]}' "
                    f"на позиции {self.pos + 1}"
                )
            else:
                raise ValueError("Неожиданный конец выражения")

        number_str = self.text[start:self.pos]
        return float(number_str)


def calculate(expression):
    """Вычисляет математическое выражение и возвращает результат."""
    parser = Parser(expression)
    result = parser.parse()
    # Если результат целый — показываем без .0
    if result == int(result):
        return int(result)
    return round(result, 10)


# ──────────────────────────────────────────────
# Главное окно приложения
# ──────────────────────────────────────────────
class Win(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi('calc_form.ui', self)

        # Обработчик нажатия кнопки «Рассчитать»
        self.ui.calc.clicked.connect(self.on_calc)

        # Также считаем по Enter
        self.ui.expression.returnPressed.connect(self.on_calc)

        self.ui.show()

    def on_calc(self):
        """Считывает выражение и вычисляет результат."""
        expr = self.ui.expression.text().strip()
        if not expr:
            self.ui.result_label.setText("Результат:")
            return

        try:
            result = calculate(expr)
            self.ui.result_label.setText(f"Результат: {result}")
        except Exception as e:
            self.ui.result_label.setText(f"Ошибка: {e}")


# ──────────────────────────────────────────────
# Точка входа
# ──────────────────────────────────────────────
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Win()
    sys.exit(app.exec_())
