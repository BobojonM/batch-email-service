import sys
import os
import sqlite3
from PyQt5 import QtCore, QtGui, QtWidgets, uic


class Win(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi('db_form.ui', self)

        # Соединение с БД
        self.conn = None
        self.db_path = None

        # ── Вкладка 1: База данных ──
        self.ui.btn_connect.clicked.connect(self.on_connect)
        self.ui.btn_query.clicked.connect(self.on_query)
        self.ui.btn_close_db.clicked.connect(self.on_close_db)
        self.ui.btn_delete_record.clicked.connect(self.on_delete_record)

        # ── Вкладка 2: DML SQL ──
        self.ui.btn_add_col.clicked.connect(self.on_add_column)
        self.ui.btn_del_col.clicked.connect(self.on_del_column)
        self.ui.btn_create_table.clicked.connect(self.on_create_table)
        self.ui.btn_drop_table.clicked.connect(self.on_drop_table)

        # ── Вкладка 3: Вставка значений ──
        self.ui.btn_get_tables.clicked.connect(self.on_get_tables_insert)
        self.ui.comboBox_tables.currentTextChanged.connect(self.on_table_selected)
        self.ui.btn_insert_values.clicked.connect(self.on_insert_values)

        # ── Вкладка 4: Управление ──
        self.ui.btn_get_tables_manage.clicked.connect(self.on_get_tables_manage)
        self.ui.btn_execute.clicked.connect(self.on_execute)
        self.ui.comboBox_actions.currentIndexChanged.connect(self.on_action_changed)
        self.ui.comboBox_manage.currentTextChanged.connect(self.on_action_changed)

        self.ui.show()

    # ════════════════════════════════════════════
    # Проверка подключения
    # ════════════════════════════════════════════
    def check_connection(self):
        if self.conn is None:
            QtWidgets.QMessageBox.warning(
                self, "Ошибка", "Сначала подключитесь к БД!"
            )
            return False
        return True

    # ════════════════════════════════════════════
    # Вкладка 1: База данных
    # ════════════════════════════════════════════
    def on_connect(self):
        """Подключение к БД SQLite (выбор или создание файла)."""
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Выбрать БД', os.path.expanduser('~'),
            'SQLite (*.db *.sqlite);;Все файлы (*)'
        )
        if filepath:
            try:
                if self.conn:
                    self.conn.close()
                self.conn = sqlite3.connect(filepath)
                self.db_path = filepath
                self.ui.db_status_label.setText(
                    f"Подключено: {os.path.basename(filepath)}"
                )
                self.ui.db_status_label.setStyleSheet("color: green;")
                self.statusBar().showMessage(f"БД: {filepath}", 3000)
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self, "Ошибка подключения", str(e)
                )

    def on_query(self):
        """Выполнить SQL запрос из поля ввода."""
        if not self.check_connection():
            return

        sql = self.ui.query_input.text().strip()
        if not sql:
            return

        self.execute_and_display(sql, self.ui.result_table)

    def on_close_db(self):
        """Закрыть соединение с БД."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.db_path = None
            self.ui.db_status_label.setText("БД не подключена")
            self.ui.db_status_label.setStyleSheet("color: gray;")
            self.ui.result_table.clear()
            self.ui.result_table.setRowCount(0)
            self.ui.result_table.setColumnCount(0)
            self.statusBar().showMessage("БД закрыта", 3000)

    def on_delete_record(self):
        """Удалить выбранную строку (нужно знать таблицу и rowid)."""
        if not self.check_connection():
            return
        row = self.ui.result_table.currentRow()
        if row < 0:
            QtWidgets.QMessageBox.warning(
                self, "Ошибка", "Выберите строку для удаления!"
            )
            return
        # Используем данные из текущего запроса
        sql = self.ui.query_input.text().strip()
        QtWidgets.QMessageBox.information(
            self, "Подсказка",
            "Для удаления записи используйте SQL:\n"
            "DELETE FROM таблица WHERE условие;\n\n"
            "Введите запрос в поле и нажмите «Запрос»."
        )

    # ════════════════════════════════════════════
    # Вкладка 2: DML SQL — Создание/удаление таблиц
    # ════════════════════════════════════════════
    def on_add_column(self):
        """Добавить строку в таблицу столбцов."""
        row = self.ui.columns_table.rowCount()
        self.ui.columns_table.setRowCount(row + 1)
        self.ui.columns_table.setItem(row, 0, QtWidgets.QTableWidgetItem(""))
        # ComboBox с типами данных
        combo = QtWidgets.QComboBox()
        combo.addItems(["TEXT", "INTEGER", "REAL", "BLOB"])
        self.ui.columns_table.setCellWidget(row, 1, combo)

    def on_del_column(self):
        """Удалить выбранную строку из таблицы столбцов."""
        row = self.ui.columns_table.currentRow()
        if row >= 0:
            self.ui.columns_table.removeRow(row)

    def on_create_table(self):
        """Создать таблицу из описания столбцов."""
        if not self.check_connection():
            return

        table_name = self.ui.table_name_input.text().strip()
        if not table_name:
            QtWidgets.QMessageBox.warning(
                self, "Ошибка", "Введите имя таблицы!"
            )
            return

        cols = []
        for i in range(self.ui.columns_table.rowCount()):
            name_item = self.ui.columns_table.item(i, 0)
            type_widget = self.ui.columns_table.cellWidget(i, 1)

            col_name = name_item.text().strip() if name_item else ""
            if not col_name:
                continue

            if isinstance(type_widget, QtWidgets.QComboBox):
                col_type = type_widget.currentText()
            else:
                type_item = self.ui.columns_table.item(i, 1)
                col_type = type_item.text().strip() if type_item else "TEXT"

            cols.append(f'"{col_name}" {col_type}')

        if not cols:
            QtWidgets.QMessageBox.warning(
                self, "Ошибка", "Добавьте хотя бы один столбец!"
            )
            return

        sql = f'CREATE TABLE "{table_name}" ({", ".join(cols)})'
        try:
            self.conn.execute(sql)
            self.conn.commit()
            self.ui.dml_status_label.setText(f"Таблица «{table_name}» создана")
            self.ui.dml_status_label.setStyleSheet("color: green;")
        except Exception as e:
            self.ui.dml_status_label.setText(f"Ошибка: {e}")
            self.ui.dml_status_label.setStyleSheet("color: red;")

    def on_drop_table(self):
        """Удалить таблицу."""
        if not self.check_connection():
            return

        table_name = self.ui.table_name_input.text().strip()
        if not table_name:
            QtWidgets.QMessageBox.warning(
                self, "Ошибка", "Введите имя таблицы!"
            )
            return

        reply = QtWidgets.QMessageBox.question(
            self, "Подтверждение",
            f"Удалить таблицу «{table_name}»?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            try:
                self.conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                self.conn.commit()
                self.ui.dml_status_label.setText(f"Таблица «{table_name}» удалена")
                self.ui.dml_status_label.setStyleSheet("color: green;")
            except Exception as e:
                self.ui.dml_status_label.setText(f"Ошибка: {e}")
                self.ui.dml_status_label.setStyleSheet("color: red;")

    # ════════════════════════════════════════════
    # Вкладка 3: Вставка значений
    # ════════════════════════════════════════════
    def on_get_tables_insert(self):
        """Загрузить список таблиц в comboBox."""
        if not self.check_connection():
            return
        self.load_tables_into(self.ui.comboBox_tables)

    def on_table_selected(self, table_name):
        """При выборе таблицы — показать её столбцы для вставки."""
        if not self.conn or not table_name:
            return
        try:
            cursor = self.conn.execute(f'PRAGMA table_info("{table_name}")')
            columns = cursor.fetchall()

            self.ui.insert_table.setRowCount(len(columns))
            for i, col in enumerate(columns):
                # col: (cid, name, type, notnull, default, pk)
                name_item = QtWidgets.QTableWidgetItem(col[1])
                name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.ui.insert_table.setItem(i, 0, name_item)

                self.ui.insert_table.setItem(
                    i, 1, QtWidgets.QTableWidgetItem("")
                )

                type_item = QtWidgets.QTableWidgetItem(col[2])
                type_item.setFlags(type_item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.ui.insert_table.setItem(i, 2, type_item)

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))

    def on_insert_values(self):
        """Вставить значения в выбранную таблицу."""
        if not self.check_connection():
            return

        table_name = self.ui.comboBox_tables.currentText()
        if not table_name:
            return

        col_names = []
        values = []
        for i in range(self.ui.insert_table.rowCount()):
            name_item = self.ui.insert_table.item(i, 0)
            val_item = self.ui.insert_table.item(i, 1)
            if name_item and val_item:
                col_names.append(f'"{name_item.text()}"')
                values.append(val_item.text())

        if not values:
            return

        placeholders = ", ".join(["?"] * len(values))
        sql = f'INSERT INTO "{table_name}" ({", ".join(col_names)}) VALUES ({placeholders})'

        try:
            self.conn.execute(sql, values)
            self.conn.commit()
            QtWidgets.QMessageBox.information(
                self, "Успех", "Запись добавлена!"
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))

    # ════════════════════════════════════════════
    # Вкладка 4: Управление
    # ════════════════════════════════════════════
    def on_get_tables_manage(self):
        """Загрузить таблицы в comboBox управления."""
        if not self.check_connection():
            return
        self.load_tables_into(self.ui.comboBox_manage)

    def on_action_changed(self):
        """Генерировать SQL при смене действия или таблицы."""
        table = self.ui.comboBox_manage.currentText()
        action = self.ui.comboBox_actions.currentIndex()
        if not table:
            return
        if action == 0:  # Удалить таблицу
            self.ui.sql_text.setPlainText(f'DROP TABLE IF EXISTS "{table}"')
        elif action == 1:  # Показать данные
            self.ui.sql_text.setPlainText(f'SELECT * FROM "{table}"')

    def on_execute(self):
        """Выполнить SQL из текстового поля управления."""
        if not self.check_connection():
            return

        sql = self.ui.sql_text.toPlainText().strip()
        if not sql:
            return

        self.execute_and_display(sql, self.ui.manage_result_table)
        # Обновляем списки таблиц
        self.load_tables_into(self.ui.comboBox_manage)

    # ════════════════════════════════════════════
    # Утилиты
    # ════════════════════════════════════════════
    def load_tables_into(self, combobox):
        """Загрузить список таблиц БД в comboBox."""
        combobox.clear()
        try:
            cursor = self.conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' ORDER BY name"
            )
            for row in cursor.fetchall():
                combobox.addItem(row[0])
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))

    def execute_and_display(self, sql, table_widget):
        """Выполнить SQL и показать результат в QTableWidget."""
        try:
            cursor = self.conn.execute(sql)

            # Для SELECT — показать результаты
            if sql.strip().upper().startswith("SELECT") or \
               sql.strip().upper().startswith("PRAGMA"):
                rows = cursor.fetchall()
                cols = [desc[0] for desc in cursor.description] \
                    if cursor.description else []

                table_widget.setColumnCount(len(cols))
                table_widget.setHorizontalHeaderLabels(cols)
                table_widget.setRowCount(len(rows))

                for i, row in enumerate(rows):
                    for j, val in enumerate(row):
                        table_widget.setItem(
                            i, j, QtWidgets.QTableWidgetItem(str(val))
                        )

                self.statusBar().showMessage(
                    f"Получено строк: {len(rows)}", 3000
                )
            else:
                self.conn.commit()
                table_widget.clear()
                table_widget.setRowCount(0)
                table_widget.setColumnCount(0)
                self.statusBar().showMessage("Запрос выполнен", 3000)

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка SQL", str(e))


# ──────────────────────────────────────────────
# Точка входа
# ──────────────────────────────────────────────
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Win()
    sys.exit(app.exec_())
