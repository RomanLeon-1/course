import psycopg2
import self
from psycopg2 import sql
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import Calendar
from decimal import Decimal
import re
from tkinter import simpledialog
import werkzeug.security
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import os
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
import sys
import subprocess

def connect_db():
    return psycopg2.connect(
        dbname="lab",
        user="postgres",
        password="evybr2004",
        host="localhost",
        port="5432"
    )

COLUMN_TRANSLATIONS = {
    "Order": {
        "order_id": "ID",
        "client_id": "ID Клиента",
        "object_id": "ID Объекта",
        "manager_id": "ID Менеджера",
        "order_startdate": "Дата начала",
        "order_enddate": "Дата завершения",
        "order_total": "Общая стоимость",
        "order_deadlines": "Сроки",
        "order_status": "Статус заказа",
        "order_description": "Краткое описание",
        "client_name": "Имя клиента",
        "object_type": "Тип объекта",
        "manager_name": "Имя менеджера"
    },
    "client": {
        "client_id": "ID клиента",
        "client_phonenumber": "Номер телефона",
        "client_orders": "Количество заказов",
        "client_name": "Имя клиента"
    },
    "Services in order": {
        "servicesorder_id": "ID услуги в заказе",
        "order_id": "ID заказа",
        "service_id": "ID услуги",
        "servicesorder_datestart": "Дата начала услуги",
        "servicesorder_dateend": "Дата завершения услуги"
    },
    "equipment": {
        "equipment_id": "ID оборудования",
        "equipment_name": "Название оборудования",
        "equipment_status": "Стоимость аренды",
        "equipment_usecost": "Статус оборудования"
    },

    "manager": {
        "manager_id": "ID менеджера",
        "manager_phonenumber": "Телефон",
        "manager_name": "Имя менеджера"
    },
    "materials": {
        "material_id": "ID материала",
        "servicesorder_id": "ID услуги в заказе",
        "material_name": "Название материала",
        "material_amount": "Количество материала",
        "material_unit": "Единица измерения",
        "material_costunit": "Стоимость за ед.",
        "total_cost": "Стоимость"
    },

    "object": {
        "object_id": "ID объекта",
        "object_type": "Тип объекта",
        "object_adress": "Адрес объекта"
    },
    "service": {
        "service_id": "ID услуги",
        "service_type": "Тип услуги",
        "service_cost": "Цена"
    },

    "worker": {
        "worker_id": "ID работника",
        "worker_status": "Статус работника",
        "worker_specialization": "Специализация",
        "worker_phonenumber": "Номер телефона"
    },

}


def create_admin_if_not_exists():
    try:
        conn = connect_db()
        cursor = conn.cursor()

        # Проверяем, есть ли уже администраторы
        cursor.execute("SELECT 1 FROM manager WHERE is_admin = TRUE")
        if not cursor.fetchone():
            # Создаем администратора по умолчанию
            hashed_password = generate_password_hash("admin123")
            cursor.execute("""
                INSERT INTO manager (manager_phonenumber, manager_name, password, is_admin)
                VALUES (%s, %s, %s, TRUE)
            """, ("+11111111111", "Администратор", hashed_password))
            conn.commit()

    except Exception as e:
        print(f"Ошибка при создании администратора: {str(e)}")
    finally:
        conn.close()
def get_column_translations(table_name):
    """Получить переводы для столбцов указанной таблицы."""
    return COLUMN_TRANSLATIONS.get(table_name, {})

# Получение всех таблиц из базы данных
def get_tables():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables

# Получение данных из выбранной таблицы с сортировкой по первому столбцу
def get_data(table_name, current_user=None, sort_columns=None):
    conn = connect_db()
    cursor = conn.cursor()

    # Без авторизации
    if not current_user:
        return [], []

    # Список колонок, которые нужно исключить
    excluded_columns = ['password', 'is_admin', 'is_master']

    if current_user.role == 'worker':
        if table_name == "Order":
            query = """
                SELECT ord.order_id, c.client_name, o.object_type, m.manager_name, 
                       ord.order_startdate, ord.order_enddate, ord.order_total, 
                       ord.order_deadlines, ord.order_status, ord.order_description
                FROM "Order" ord
                JOIN client c ON ord.client_id = c.client_id
                JOIN object o ON ord.object_id = o.object_id
                JOIN manager m ON ord.manager_id = m.manager_id
            """
            cursor.execute(query)

        elif table_name in ("materials", "equipment"):
            query = sql.SQL("SELECT * FROM {}").format(sql.Identifier(table_name))
            cursor.execute(query)
        else:
            return [], []  # worker не имеет доступа к другим таблицам
    elif table_name == "Order":
        if current_user.role == 'client' and not current_user.is_admin:
            query = """
                SELECT ord.order_id, c.client_name, o.object_type, m.manager_name, 
                       ord.order_startdate, ord.order_enddate, ord.order_total, 
                       ord.order_deadlines, ord.order_status, ord.order_description
                FROM "Order" ord
                JOIN client c ON ord.client_id = c.client_id
                JOIN object o ON ord.object_id = o.object_id
                JOIN manager m ON ord.manager_id = m.manager_id
                WHERE ord.client_id = %s 
            """
            cursor.execute(query, (current_user.user_id,))  # Передаем ID текущего клиента
        else:
            # Для менеджеров и админов показываем все заказы
            query = """
                SELECT ord.order_id, c.client_name, o.object_type, m.manager_name, 
                       ord.order_startdate, ord.order_enddate, ord.order_total, 
                       ord.order_deadlines, ord.order_status, ord.order_description
                FROM "Order" ord
                JOIN client c ON ord.client_id = c.client_id
                JOIN object o ON ord.object_id = o.object_id
                JOIN manager m ON ord.manager_id = m.manager_id
            """
            cursor.execute(query)
    else:
        # Для других таблиц
        if current_user.role == 'client' and not current_user.is_admin:
            return [], []  # Клиенты видят только таблицу Order
        elif table_name in ['client', 'manager']:
            # Получаем все колонки таблицы, исключая sensitive данные
            cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'")
            all_columns = [col[0] for col in cursor.fetchall()]
            selected_columns = [col for col in all_columns if col not in excluded_columns]
            query = sql.SQL("SELECT {} FROM {}").format(
                sql.SQL(', ').join(map(sql.Identifier, selected_columns)),
                sql.Identifier(table_name)
            )
            cursor.execute(query)
        else:
            query = sql.SQL("SELECT * FROM {}").format(sql.Identifier(table_name))
            cursor.execute(query)

    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    conn.close()
    return columns, rows

def get_orders_report(start_date, end_date):
    conn = connect_db()
    cursor = conn.cursor()
    query = """
  SELECT 
    o.object_type AS object_type,
    c.client_name AS client_name,
    ord.order_total AS total_cost,
    ord.order_startDate AS start_date,
    ord.order_endDate AS end_date
FROM 
    "Order" ord
JOIN 
    Client c ON ord.client_id = c.client_id
JOIN 
    Object o ON ord.object_id = o.object_id
WHERE 
    ord.order_startDate >= %s 
    AND ord.order_endDate <= %s;

    """
    cursor.execute(query, (start_date, end_date))
    rows = cursor.fetchall()
    conn.close()
    return rows


class User:
    def __init__(self, user_id, phone, name, role, is_admin=False):
        self.user_id = user_id
        self.phone = phone
        self.name = name
        self.role = role  # 'client' или 'manager'
        self.is_admin = is_admin


# Добавим окно авторизации
class LoginWindow(tk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("Авторизация")
        self.callback = callback

        tk.Label(self, text="Номер телефона:").grid(row=0, column=0, padx=5, pady=5)
        self.phone_entry = tk.Entry(self)
        self.phone_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(self, text="Пароль:").grid(row=1, column=0, padx=5, pady=5)
        self.password_entry = tk.Entry(self, show="*")
        self.password_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Button(self, text="Войти", command=self.authenticate).grid(row=2, columnspan=2, pady=10)

    def authenticate(self):
        phone = self.phone_entry.get()
        password = self.password_entry.get()

        try:
            conn = connect_db()
            cursor = conn.cursor()

            # 1. Проверяем менеджера
            cursor.execute("""
                SELECT manager_id, manager_phonenumber, manager_name, password, is_admin 
                FROM manager 
                WHERE manager_phonenumber = %s
            """, (phone,))
            manager = cursor.fetchone()

            if manager:
                manager_id, phone, name, hashed_password, is_admin = manager
                if check_password_hash(hashed_password, password):
                    self.callback(User(manager_id, phone, name, 'manager', is_admin))
                    self.destroy()
                    return
                else:
                    messagebox.showerror("Ошибка", "Неверный пароль менеджера")
                    return

            # 2. Проверяем клиента
            cursor.execute("""
                SELECT client_id, client_phonenumber, client_name, password, is_admin 
                FROM client 
                WHERE client_phonenumber = %s
            """, (phone,))
            client = cursor.fetchone()

            if client:
                client_id, phone, name, hashed_password, is_admin = client
                if check_password_hash(hashed_password, password):
                    self.callback(User(client_id, phone, name, 'client', is_admin))
                    self.destroy()
                    return
                else:
                    messagebox.showerror("Ошибка", "Неверный пароль клиента")
                    return

            # 3. Проверяем мастера
            cursor.execute("""
                SELECT worker_id, worker_phonenumber, worker_specialization, password 
                FROM worker 
                WHERE worker_phonenumber = %s AND is_master = TRUE
            """, (phone,))
            worker = cursor.fetchone()

            if worker:
                worker_id, phone, name, hashed_password = worker
                if check_password_hash(hashed_password, password):
                    self.callback(User(worker_id, phone, name, 'worker'))
                    self.destroy()
                    return
                else:
                    messagebox.showerror("Ошибка", "Неверный пароль мастера")
                    return

            # Если ни один пользователь не найден
            messagebox.showerror("Ошибка", "Пользователь не найден")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при авторизации: {str(e)}")
        finally:
            conn.close()


# Интерфейс приложения
class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.hidden_data = {}
        self.title("Приложение для работы с БД PostgreSQL")
        self.geometry("1000x700")

        # Сначала показываем окно авторизации
        self.withdraw()
        LoginWindow(self, self.on_login_success)

    def generate_pdf_report(self, report_text, start_date, end_date):
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            # Регистрируем шрифт с поддержкой кириллицы
            try:
                # Попробуем использовать стандартный шрифт Arial
                pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
                font_name = 'Arial'
            except:
                try:
                    # Если Arial не найден, попробуем DejaVu Sans
                    pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
                    font_name = 'DejaVuSans'
                except:
                    # Если ничего не найдено, используем стандартный шрифт (может не поддерживать кириллицу)
                    font_name = 'Helvetica'

            filename = f"Отчет_с_{start_date}_по_{end_date}.pdf"
            doc = SimpleDocTemplate(filename, pagesize=letter)

            # Создаем стиль с русским шрифтом
            styles = getSampleStyleSheet()
            styles['Normal'].fontName = font_name
            styles['Title'].fontName = font_name

            report_lines = report_text.split('\n')
            data = []

            # Добавляем заголовок
            title = Paragraph(f"<b>Отчет по заказам с {start_date} по {end_date}</b>", styles['Title'])
            data.append(title)
            data.append(Paragraph("<br/><br/>", styles['Normal']))  # Добавляем отступ

            # Парсим данные для таблицы
            table_data = []
            headers_added = False
            for line in report_lines:
                if '|' in line:  # Это строка таблицы
                    cells = [x.strip() for x in line.split('|')]
                    if not headers_added and any(cell in ['Объект', 'Имя клиента'] for cell in cells):
                        # Это заголовок таблицы
                        table_data.append([Paragraph(cell, styles['Normal']) for cell in cells])
                        headers_added = True
                    else:
                        table_data.append(cells)
                elif line.strip() and not line.startswith('-') and 'Общее количество' not in line:
                    data.append(Paragraph(line, styles['Normal']))

            # Создаем таблицу
            if table_data:
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), font_name),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), font_name),  # Шрифт для содержимого таблицы
                ]))
                data.append(table)

            # Добавляем итоговую информацию
            for line in report_lines:
                if 'Общее количество' in line or 'Общая сумма' in line:
                    data.append(Paragraph("<br/>" + line, styles['Normal']))

            # Собираем документ
            doc.build(data)

            # Открываем PDF файл
            if os.name == 'nt':  # Для Windows
                os.startfile(filename)
            else:  # Для Mac и Linux
                opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
                subprocess.call([opener, filename])

            messagebox.showinfo("Успех", f"PDF отчет сохранен как {filename}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать PDF: {str(e)}")
    def on_login_success(self, user):
        self.current_user = user
        self.deiconify()

        self.current_table = None
        self.column_names = []
        self.create_widgets()  # Сначала создаем все виджеты
        self.load_tables()
        self.tree.bind("<Double-1>", self.on_cell_double_click)

        # Только после создания виджетов настраиваем интерфейс
        self.configure_ui_for_user()

    def configure_ui_for_user(self):
        if not hasattr(self, 'sidebar'):
            return

        # Очищаем sidebar перед повторным заполнением
        for widget in self.sidebar.winfo_children():
            if widget.winfo_class() == 'Button':
                widget.destroy()

        # Для клиентов показываем только таблицу Order
        if self.current_user.role == 'client' and not self.current_user.is_admin:
            # Клиентам только заказы
            btn = tk.Button(self.sidebar, text="Order", command=lambda: self.switch_table("Order"))
            btn.pack(fill=tk.X, pady=5, padx=10)
        elif self.current_user.role == 'worker':
            # Мастерам только нужные таблицы
            allowed_tables = ["Order", "materials", "equipment"]
            for table in get_tables():
                if table in allowed_tables:
                    btn = tk.Button(self.sidebar, text=table, command=lambda t=table: self.switch_table(t))
                    btn.pack(fill=tk.X, pady=5, padx=10)
        else:
            # Админы и менеджеры видят всё
            for table in get_tables():
                btn = tk.Button(self.sidebar, text=table, command=lambda t=table: self.switch_table(t))
                btn.pack(fill=tk.X, pady=5, padx=10)


        # Настраиваем видимость кнопок
        if hasattr(self, 'button_frame'):
            for widget in self.button_frame.winfo_children():
                if widget.winfo_class() == 'Button':
                    if self.current_user.role == 'client' and not self.current_user.is_admin:
                        # Клиентам оставляем только кнопку фильтра
                        if widget["text"] not in ["Фильтровать"]:
                            widget.pack_forget()
                        else:
                            widget.pack(side=tk.LEFT, padx=5)
                    else:
                        # Показываем все кнопки
                        widget.pack(side=tk.LEFT, padx=5)
        elif self.current_user.role == 'worker':
            # Мастерам только ограниченный список
            allowed_tables = ["Order", "materials", "equipment"]
            for table in get_tables():
                if table in allowed_tables:
                    btn = tk.Button(self.sidebar, text=table, command=lambda t=table: self.switch_table(t))
                    btn.pack(fill=tk.X, pady=5, padx=10)
    def on_cell_double_click(self, event):
        """Обработчик двойного клика по ячейке для редактирования."""
        # Определяем выбранную строку и колонку
        row_id = self.tree.identify_row(event.y)
        column_id = self.tree.identify_column(event.x)
        if not row_id or not column_id:
            return

        # Получаем текущее значение
        item = self.tree.item(row_id)
        current_value = item["values"][int(column_id[1:]) - 1]  # Учитываем, что колонка начинается с #1

        # Создаем окно для редактирования
        edit_window = tk.Toplevel(self)
        edit_window.title("Редактировать значение")
        edit_window.geometry("300x150")
        edit_window.transient(self)  # Окно поверх родительского

        tk.Label(edit_window, text="Новое значение:").pack(pady=10)
        new_value_entry = tk.Entry(edit_window)
        new_value_entry.pack(pady=10)
        new_value_entry.insert(0, current_value)

        def save_edit():
            new_value = new_value_entry.get()
            if new_value != current_value:
                # Обновляем значение в Treeview
                column_index = int(column_id[1:]) - 1
                self.tree.set(row_id, column=column_id, value=new_value)

                # Обновляем значение в базе данных
                primary_key = item["values"][0]  # Предполагаем, что первичный ключ в первой колонке
                column_name = self.column_names[column_index]
                self.update_database(primary_key, column_name, new_value)

            edit_window.destroy()

        tk.Button(edit_window, text="Сохранить", command=save_edit).pack(pady=10)

    def update_database(self, primary_key, column_name, new_value):
        """Обновляет значение в базе данных."""
        try:
            conn = connect_db()
            cursor = conn.cursor()

            # Формируем запрос
            query = sql.SQL("UPDATE {} SET {} = %s WHERE {} = %s").format(
                sql.Identifier(self.current_table),
                sql.Identifier(column_name),
                sql.Identifier(self.column_names[0])  # Первичный ключ
            )

            cursor.execute(query, (new_value, primary_key))
            conn.commit()
            conn.close()
            messagebox.showinfo("Успех", "Запись успешно обновлена.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось обновить запись: {e}")

    def get_services(self):
        """Получить список типов услуг из базы данных."""
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT service_id, service_type FROM service")  # Замените на вашу таблицу и столбцы
        services = cursor.fetchall()
        conn.close()
        return services

    def get_order_id_by_date(self, order_startdate):
        """Получить order_id по дате начала заказа (order_startdate)."""
        try:
            conn = connect_db()
            cursor = conn.cursor()
            query = sql.SQL("SELECT order_id FROM \"Order\" WHERE order_startdate = %s")
            cursor.execute(query, (order_startdate,))
            result = cursor.fetchone()  # Получаем первую строку результата
            conn.close()

            return result[0] if result else None  # Возвращаем order_id или None, если не найден
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось получить order_id: {e}")
            return None

    def create_widgets(self):
        # Боковая панель
        self.sidebar = tk.Frame(self, bg="lightgray", width=200)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(self.sidebar, text="Таблицы", bg="lightgray", font=("Arial", 14)).pack(pady=10)

        for table in get_tables():
            btn = tk.Button(self.sidebar, text=table, command=lambda t=table: self.switch_table(t))
            btn.pack(fill=tk.X, pady=5, padx=10)

        # Основной контент
        content_frame = tk.Frame(self)
        content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(content_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Вкладка "Основные данные"
        self.tab_data = tk.Frame(notebook)
        notebook.add(self.tab_data, text="Основные данные")

        # Вкладка "Отчет"
        self.tab_report = tk.Frame(notebook)
        notebook.add(self.tab_report, text="Отчет")

        # Вкладка "Основные данные" - Верхний фрейм
        top_frame = tk.Frame(self.tab_data, bg="lightgray")
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        # Средний фрейм с таблицей и чекбоксами
        middle_frame = tk.Frame(self.tab_data)
        middle_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Чекбоксы для выбора колонок
        self.checkbox_frame = tk.Frame(middle_frame)
        self.checkbox_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10)

        # Фрейм для таблицы
        table_frame = tk.Frame(middle_frame)
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Прокрутка для таблицы
        scroll_y = tk.Scrollbar(table_frame, orient=tk.VERTICAL)
        scroll_x = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)

        self.tree = ttk.Treeview(
            table_frame,
            show="headings",
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )

        # Привязка скроллбаров к Treeview
        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)

        # Упаковываем элементы с grid для лучшего позиционирования
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

        # Позволяет table_frame растягивать дерево
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Нижний фрейм для кнопок
        self.button_frame = tk.Frame(self.tab_data)  # Делаем атрибутом класса с self.
        self.button_frame.pack(fill=tk.X, padx=10, pady=5)

        # Добавление кнопок
        for text, command in [
            ("Добавить", self.add_record),
            ("Изменить", self.edit_record),
            ("Удалить", self.delete_record),
            ("Выполнить процедуру", self.show_input_dialog),
            ("Фильтровать", self.filter_data),
        ]:
            tk.Button(self.button_frame, text=text, command=command).pack(side=tk.LEFT, padx=5)

        # Поля для фильтрации
        self.filter_column_label = tk.Label(self.button_frame, text="Колонка:")
        self.filter_column_label.pack(side=tk.LEFT, padx=5)

        self.filter_column_selector = ttk.Combobox(self.button_frame, state="readonly")
        self.filter_column_selector.pack(side=tk.LEFT, padx=5)

        self.filter_value_label = tk.Label(self.button_frame, text="Значение:")
        self.filter_value_label.pack(side=tk.LEFT, padx=5)

        self.filter_value_entry = tk.Entry(self.button_frame)
        self.filter_value_entry.pack(side=tk.LEFT, padx=5)

        # Вкладка "Отчет"
        report_label = tk.Label(self.tab_report, text="Отчет по заказам", font=("Arial", 16))
        report_label.pack(padx=10, pady=10)

        # Фрейм для календарей
        calendar_frame = tk.Frame(self.tab_report)
        calendar_frame.pack(padx=10, pady=5)

        self.start_date_label = tk.Label(calendar_frame, text="Начальная дата:")
        self.start_date_label.pack(side=tk.LEFT, padx=5)

        self.start_date_calendar = Calendar(calendar_frame, selectmode="day", date_pattern="yyyy-mm-dd")
        self.start_date_calendar.pack(side=tk.LEFT, padx=5)

        self.end_date_label = tk.Label(calendar_frame, text="Конечная дата:")
        self.end_date_label.pack(side=tk.LEFT, padx=5)

        self.end_date_calendar = Calendar(calendar_frame, selectmode="day", date_pattern="yyyy-mm-dd")
        self.end_date_calendar.pack(side=tk.LEFT, padx=5)

        self.generate_report_button = tk.Button(self.tab_report, text="Сгенерировать отчет",
                                                command=self.generate_report)
        self.generate_report_button.pack(padx=10, pady=10)
        self.generate_pdf_button = tk.Button(self.tab_report, text="Сохранить в PDF",
                                             command=lambda: self.generate_pdf_report(
                                                 self.report_text.get("1.0", tk.END),
                                                 self.start_date_calendar.get_date(),
                                                 self.end_date_calendar.get_date()
                                             ))
        self.generate_pdf_button.pack(padx=10, pady=10)
        # Текстовое поле для вывода отчета с прокруткой
        report_frame = tk.Frame(self.tab_report)
        report_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scroll_report = tk.Scrollbar(report_frame)
        scroll_report.pack(side=tk.RIGHT, fill=tk.Y)

        self.report_text = tk.Text(report_frame, height=20, wrap=tk.WORD, yscrollcommand=scroll_report.set)
        self.report_text.pack(fill=tk.BOTH, expand=True)
        scroll_report.config(command=self.report_text.yview)

    def load_tables(self):
        tables = get_tables()

    def switch_table(self, table_name):
        if (self.current_user.role == 'client' and not self.current_user.is_admin
                and table_name != "Order"):
            messagebox.showwarning("Ограничение", "У вас нет доступа к этой таблице")
            return

        self.current_table = table_name
        self.load_data()

        if (self.current_user.role == 'worker' and
                table_name not in ["Order", "materials", "equipment"]):
            messagebox.showwarning("Ограничение", "У вас нет доступа к этой таблице")
            return

    def toggle_column(self, column, var):
        """Управление видимостью колонок."""
        if var.get():
            # Показываем колонку
            if column not in self.visible_columns:
                self.visible_columns.append(column)
                self.hidden_columns.remove(column)

            # Обновляем Treeview: добавляем колонку
            self.tree["columns"] = self.visible_columns
            self.tree.heading(column, text=self.column_translations.get(column, column))
            self.tree.column(column, width=150, anchor=tk.W)
        else:
            # Скрываем колонку
            if column in self.visible_columns:
                self.visible_columns.remove(column)
                self.hidden_columns.append(column)

            # Обновляем Treeview: убираем колонку
            self.tree["columns"] = self.visible_columns

    def load_data(self):
        if not self.current_table:
            return

        self.tree.delete(*self.tree.get_children())

        # Загружаем данные из выбранной таблицы
        self.column_names, rows = get_data(self.current_table, self.current_user)

        # Фильтруем колонки, которые не хотим показывать
        excluded_columns = ['password', 'is_admin']
        filtered_columns = [col for col in self.column_names if col not in excluded_columns]
        filtered_rows = []

        for row in rows:
            filtered_row = [val for col, val in zip(self.column_names, row) if col not in excluded_columns]
            filtered_rows.append(filtered_row)

        self.column_names = filtered_columns
        rows = filtered_rows

        # Получаем переводы колонок
        self.column_translations = get_column_translations(self.current_table)

        # Остальной код функции остается без изменений...
        # Создаем переведенные названия столбцов
        translated_columns = [self.column_translations.get(col, col) for col in self.column_names]

        # Обновляем доступные колонки для фильтрации
        self.filter_column_selector["values"] = self.column_names

        # Устанавливаем переведенные названия колонок
        self.tree["columns"] = self.column_names
        for col, translated_name in zip(self.column_names, translated_columns):
            self.tree.heading(col, text=translated_name, command=lambda c=col: self.sort_table(c))
            self.tree.column(col, anchor=tk.W)

        for col in self.column_names:
            self.tree.column(col, width=150, anchor=tk.W)

        # Вставляем строки в таблицу
        for row in rows:
            self.tree.insert("", tk.END, values=row)

        # Обновляем чекбоксы для отображения/скрытия колонок
        for widget in self.checkbox_frame.winfo_children():
            widget.destroy()

        for col, translated_name in zip(self.column_names, translated_columns):
            var = tk.BooleanVar(value=False if "id" in col.lower() else True)
            check = tk.Checkbutton(
                self.checkbox_frame,
                text=translated_name,
                variable=var,
                command=lambda col=col, var=var: self.toggle_column(col, var)
            )
            check.pack(anchor=tk.W)

            # Изначально скрываем столбцы с ID
            if not var.get():
                self.toggle_column(col, var)

    def filter_data(self):
        """Фильтрует данные по выбранной колонке и значению."""
        filter_column = self.filter_column_selector.get()
        filter_value = self.filter_value_entry.get()

        if not filter_column or not filter_value:
            messagebox.showwarning("Ошибка", "Выберите колонку и укажите значение для фильтрации.")
            return

        # Проверка, является ли фильтруемое значение числом
        try:
            # Преобразуем значение в число, если это возможно
            float(filter_value)
            is_numeric = True
        except ValueError:
            is_numeric = False

        # Список колонок типа money (замените на реальные имена колонок)
        money_columns = ['order_total', 'material_unit', 'material_costunit', 'total_cost', 'service_cost']  # Замените на реальные названия

        # Если фильтруем по одной из колонок money
        if filter_column in money_columns:
            if is_numeric:
                # Для числовых значений фильтруем как число (первоначально преобразуем money в numeric)
                query = sql.SQL("SELECT * FROM {} WHERE {}::numeric = %s").format(
                    sql.Identifier(self.current_table),
                    sql.Identifier(filter_column)
                )
                filter_value = float(filter_value)  # Преобразуем в число
            else:
                # Для строковых значений фильтруем как строку
                query = sql.SQL("SELECT * FROM {} WHERE {}::text LIKE %s").format(
                    sql.Identifier(self.current_table),
                    sql.Identifier(filter_column)
                )
                filter_value = f"%{filter_value}%"
        else:
            # Если фильтруемая колонка не из типа money, просто используем LIKE
            if is_numeric:
                query = sql.SQL("SELECT * FROM {} WHERE {} = %s").format(
                    sql.Identifier(self.current_table),
                    sql.Identifier(filter_column)
                )
                filter_value = float(filter_value)
            else:
                query = sql.SQL("SELECT * FROM {} WHERE {}::text LIKE %s").format(
                    sql.Identifier(self.current_table),
                    sql.Identifier(filter_column)
                )
                filter_value = f"%{filter_value}%"

        # Подключаемся к базе данных и выполняем запрос
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(query, (filter_value,))
        rows = cursor.fetchall()
        conn.close()

        # Обновляем таблицу с отфильтрованными данными
        self.update_table(rows)

    def sort_table(self, col):
        """Функция сортировки таблицы по выбранной колонке."""
        rows = self.tree.get_children()  # Получаем все строки
        rows = [self.tree.item(row)['values'] for row in rows]  # Извлекаем данные из строк

        # Сортируем данные по выбранной колонке (используем индекс колонки)
        sorted_rows = sorted(rows, key=lambda row: row[self.column_names.index(col)])

        # Очистим таблицу и вставим отсортированные строки
        self.tree.delete(*self.tree.get_children())
        for row in sorted_rows:
            self.tree.insert("", tk.END, values=row)

    def update_table(self, rows):
        """Обновление данных в таблице."""
        self.tree.delete(*self.tree.get_children())  # Очищаем текущие данные в таблице
        for row in rows:
            self.tree.insert("", tk.END, values=row)  # Вставляем новые строки

    def toggle_column(self, column, var):
        column_index = self.column_names.index(column)

        if var.get():
            # Включаем колонку (делаем её видимой)
            self.tree.heading(column, text=column)  # Восстанавливаем текст заголовка
            self.tree.column(column, width=100, anchor=tk.W)  # Восстанавливаем ширину

            # Восстанавливаем данные из сохраненного состояния
            if column in self.hidden_data:
                for item_id, original_value in zip(self.tree.get_children(), self.hidden_data[column]):
                    current_values = list(self.tree.item(item_id, "values"))
                    current_values[column_index] = original_value  # Восстанавливаем значение
                    self.tree.item(item_id, values=current_values)

            # Удаляем сохраненные данные после восстановления
            self.hidden_data.pop(column, None)

        else:
            # Скрываем колонку
            self.tree.heading(column, text="")  # Убираем текст заголовка
            self.tree.column(column, width=0)  # Устанавливаем ширину в 0, чтобы скрыть колонку

            # Сохраняем текущие данные для этой колонки
            self.hidden_data[column] = [
                self.tree.item(item_id, "values")[column_index]
                for item_id in self.tree.get_children()
            ]

            # Заменяем данные пустыми строками
            for item_id in self.tree.get_children():
                current_values = list(self.tree.item(item_id, "values"))
                current_values[column_index] = ""  # Убираем значение
                self.tree.item(item_id, values=current_values)

    def get_clients(self):
        """Получить список клиентов (ID и имя) из базы данных."""
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT client_id, client_name FROM client")
        clients = cursor.fetchall()
        conn.close()
        return clients

    def get_managers(self):
        """Получить список менеджеров (ID и имя) из базы данных."""
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT manager_id, manager_name FROM manager")
        managers = cursor.fetchall()
        conn.close()
        return managers

    def get_objects(self):
        """Получить список объектов (ID и тип объекта) из базы данных."""
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT object_id, object_type FROM object")
        objects = cursor.fetchall()
        conn.close()
        return objects

    def get_orders(self):
        """Получить список заказов (ID и имя заказа) из базы данных."""
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT order_id, order_name FROM Orders")  # Или используйте любой другой нужный критерий
        orders = cursor.fetchall()
        conn.close()
        return orders

    def get_order_id(self, order_name):
        """Получить order_id по имени заказа (или другому критерию)."""
        conn = connect_db()
        cursor = conn.cursor()

        # Здесь предполагается, что у вас есть таблица с заказами, например, "Orders",
        # и вы можете получить order_id по какому-то уникальному критерию, например, по имени заказа.
        cursor.execute("SELECT order_id FROM Orders WHERE order_name = %s", (order_name,))
        result = cursor.fetchone()  # Получаем одну строку результата

        conn.close()

        if result:  # Если результат есть, возвращаем order_id
            return result[0]
        else:
            return None  # Если заказа нет в базе, возвращаем None

    def add_record(self):
        self.open_edit_window("Добавить запись")

    def edit_record(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Ошибка", "Выберите запись для изменения")
            return

        values = self.tree.item(selected_item, "values")
        self.open_edit_window("Изменить запись", values)

    def delete_record(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Ошибка", "Выберите запись для удаления")
            return

        record_id = self.tree.item(selected_item)["values"][0]
        id_column = self.column_names[0]
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(sql.SQL("DELETE FROM {} WHERE {} = %s").format(
            sql.Identifier(self.current_table),
            sql.Identifier(id_column)
        ), (record_id,))
        conn.commit()
        conn.close()

        self.load_data()

    def update_database(self, item_id, column_name, new_value):
        """Обновляет данные в базе данных."""
        primary_key_value = self.tree.item(item_id, "values")[0]  # Предполагаем, что первичный ключ в первом столбце
        query = sql.SQL("UPDATE {} SET {} = %s WHERE {} = %s").format(
            sql.Identifier(self.current_table),
            sql.Identifier(column_name),
            sql.Identifier(self.column_names[0])  # Предполагается, что первичный ключ — первый столбец
        )
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(query, (new_value, primary_key_value))
        conn.commit()
        conn.close()

    def open_edit_window(self, title, values=None):
        """Открыть окно для добавления или редактирования записи."""
        edit_window = tk.Toplevel(self)
        edit_window.title(title)
        edit_window.geometry("400x300")

        entries = []
        value_dict = dict(zip(self.column_names, values)) if values else {}

        for idx, col in enumerate(self.column_names):
            # Исключаем колонку 'total_cost' из модального окна
            if col == "total_cost":
                continue  # Пропускаем создание поля для 'total_cost'
            translated_name = self.column_translations.get(col, col)
            tk.Label(edit_window, text=translated_name).grid(row=idx, column=0, padx=5, pady=5)

            if self.current_table == "Order" and col in ["client_name", "object_type", "manager_name"]:
                # Для client_name, object_type, manager_name используем выпадающий список
                combobox = ttk.Combobox(edit_window, state="readonly")
                combobox.grid(row=idx, column=1, padx=5, pady=5)

                # Заполняем выпадающий список значениями
                if col == "client_name":
                    client_data = self.get_clients()
                    combobox["values"] = [f"{row[1]} ({row[0]})" for row in client_data]  # Имя + ID
                    combobox.data_map = {row[1]: row[0] for row in client_data}  # Имя -> ID
                elif col == "object_type":
                    object_data = self.get_objects()
                    combobox["values"] = [f"{row[1]} ({row[0]})" for row in object_data]  # Тип + ID
                    combobox.data_map = {row[1]: row[0] for row in object_data}  # Тип -> ID
                elif col == "manager_name":
                    manager_data = self.get_managers()
                    combobox["values"] = [f"{row[1]} ({row[0]})" for row in manager_data]  # Имя + ID
                    combobox.data_map = {row[1]: row[0] for row in manager_data}  # Имя -> ID

                # Устанавливаем текущее значение, если оно передано
                if col in value_dict:
                    current_name = value_dict[col]
                    # Для редактирования выбираем соответствующий ID
                    combobox.set(next((val for val in combobox["values"] if val.startswith(current_name)), ""))

                entries.append((col, combobox))
            else:
                # Для других полей используем текстовые поля
                entry = tk.Entry(edit_window)
                entry.grid(row=idx, column=1, padx=5, pady=5)
                if col in value_dict:
                    entry.insert(0, value_dict[col])
                entries.append((col, entry))

                def save():
                    new_values = []
                    columns_to_update = []

                    for col, widget in entries:
                        if self.current_table == "Order" and col == "client_name":
                            # Извлекаем ID из выпадающего списка для client_name
                            selected_name = widget.get()
                            name_part = selected_name.split(" (")[0]  # Извлекаем только имя
                            new_values.append(widget.data_map.get(name_part))  # Получаем ID
                            columns_to_update.append("client_id")  # Используем client_id в запросе
                        elif self.current_table == "Order" and col == "object_type":
                            # Извлекаем ID из выпадающего списка для object_type
                            selected_name = widget.get()
                            name_part = selected_name.split(" (")[0]  # Извлекаем только тип
                            new_values.append(widget.data_map.get(name_part))  # Получаем ID
                            columns_to_update.append("object_id")  # Используем object_id в запросе
                        elif self.current_table == "Order" and col == "manager_name":
                            # Извлекаем ID из выпадающего списка для manager_name
                            selected_name = widget.get()
                            name_part = selected_name.split(" (")[0]  # Извлекаем только имя
                            new_values.append(widget.data_map.get(name_part))  # Получаем ID
                            columns_to_update.append("manager_id")  # Используем manager_id в запросе
                        else:
                            # Для остальных полей сохраняем текстовое значение
                            new_values.append(widget.get())
                            columns_to_update.append(col)  # Добавляем имя колонки, как оно есть

                    conn = connect_db()
                    cursor = conn.cursor()

                    if values:
                        # Обновление записи
                        query = sql.SQL("UPDATE {} SET {} WHERE {} = %s").format(
                            sql.Identifier(self.current_table),
                            sql.SQL(", ").join([sql.Identifier(col) + sql.SQL(" = %s") for col in columns_to_update]),
                            sql.Identifier(self.column_names[0])  # Предполагается, что первое поле — это ID
                        )
                        cursor.execute(query, (*new_values, values[0]))  # values[0] предполагается ID записи
                    else:
                        columns_to_update = [col for col in columns_to_update if
                                             col != "total_cost"]  # Исключаем колонку
                        query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                            sql.Identifier(self.current_table),
                            sql.SQL(", ").join([sql.Identifier(col) for col in columns_to_update]),
                            # Используем новые имена колонок (с ID)
                            sql.SQL(", ").join([sql.Placeholder()] * len(new_values))
                        )
                        cursor.execute(query, new_values)  # Передаем ID в запрос

                    conn.commit()
                    conn.close()
                    edit_window.destroy()
                    self.load_data()

        tk.Button(edit_window, text="Сохранить", command=save).grid(row=len(self.column_names), columnspan=2, pady=10)

    def generate_report(self):
        # Получаем выбранные даты
        start_date = self.start_date_calendar.get_date()
        end_date = self.end_date_calendar.get_date()

        # Получаем данные по заказам за выбранный период
        orders = get_orders_report(start_date, end_date)

        if not orders:
            self.report_text.delete(1.0, tk.END)
            self.report_text.insert(tk.END, "Нет заказов за выбранный период.")
            return

        # Формируем отчет
        report = f"Отчет по заказам с {start_date} по {end_date}:\n\n"
        report += "Объект | Имя клиента | Стоимость | Дата начала | Дата окончания\n"
        report += "-" * 80 + "\n"

        total_orders = 0  # Счетчик заказов
        total_sum = Decimal(0)  # Сумма всех заказов (используем Decimal)

        for order in orders:
            order_id, client_id, order_total, order_startdate, order_enddate = order

            # Очистка строки и преобразование в Decimal
            try:
                # Преобразуем запятую в точку, убираем все символы кроме цифр и точки
                cleaned_order_total = re.sub(r'[^\d,]', '', str(order_total))
                cleaned_order_total = cleaned_order_total.replace(',', '.')  # Меняем запятую на точку
                order_total = Decimal(cleaned_order_total)  # Преобразуем в Decimal
            except (ValueError, InvalidOperation):
                order_total = Decimal(0)  # Если не удается преобразовать, ставим 0

            report += f"{order_id} | {client_id} | {order_total} | {order_startdate} | {order_enddate}\n"
            total_orders += 1
            total_sum += order_total

        # Добавляем итоговую информацию
        report += "-" * 80 + "\n"
        report += f"Общее количество заказов: {total_orders}\n"
        report += f"Общая сумма заказов: {total_sum}\n"

        self.report_text.delete(1.0, tk.END)
        self.report_text.insert(tk.END, report)

        # Генерируем PDF
        self.generate_pdf_report(report, start_date, end_date)
    def show_input_dialog(self):
        form = tk.Toplevel(self)
        form.title("Добавление комплексного заказа")
        form.geometry("500x600")
        form.grab_set()  # Модальное поведение

        fields = {}

        labels = [
            ("ID клиента:", "client_id"),
            ("Имя клиента:", "client_name"),
            ("Телефон клиента:", "client_phone"),
            ("ID объекта:", "object_id"),
            ("Адрес объекта:", "object_address"),
            ("ID заказа:", "order_id"),
            ("ID менеджера:", "manager_id"),
            ("Сумма заказа:", "order_total"),
            ("Название материала:", "material_name"),
            ("Кол-во материала:", "material_amount"),
            ("Ед. изм. материала:", "material_unit"),
            ("Цена за ед. материала:", "material_costunit"),
            ("ID услуги:", "service_id"),
            ("Дата начала услуги (YYYY-MM-DD):", "service_start_date"),
            ("Дата окончания услуги (YYYY-MM-DD):", "service_end_date"),
        ]

        for i, (label_text, field_key) in enumerate(labels):
            tk.Label(form, text=label_text).grid(row=i, column=0, sticky="w", padx=10, pady=5)
            entry = tk.Entry(form, width=30)
            entry.grid(row=i, column=1, padx=10, pady=5)
            fields[field_key] = entry

        def submit():
            try:
                values = {key: entry.get() for key, entry in fields.items()}

                # Преобразуем типы
                self.execute_sql(
                    client_id=int(values["client_id"]),
                    client_name=values["client_name"],
                    client_phone=values["client_phone"],
                    object_id=int(values["object_id"]),
                    object_address=values["object_address"],
                    order_id=int(values["order_id"]),
                    manager_id=int(values["manager_id"]),
                    order_total=float(values["order_total"]),
                    material_name=values["material_name"],
                    material_amount=int(values["material_amount"]),
                    material_unit=values["material_unit"],
                    material_costunit=float(values["material_costunit"]),
                    service_id=int(values["service_id"]),
                    service_start_date=values["service_start_date"],
                    service_end_date=values["service_end_date"]
                )
                form.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Проверьте ввод: {e}")

        tk.Button(form, text="Выполнить", command=submit).grid(row=len(labels), columnspan=2, pady=20)

    def execute_sql(self, client_id, client_name, client_phone, object_id, object_address,
                    order_id, manager_id, order_total, material_name, material_amount,
                    material_unit, material_costunit, service_id, service_start_date, service_end_date):
        """Функция для выполнения SQL запроса с переданными данными"""
        try:
            # Соединение с базой данных (необходимо заменить параметры на свои)
            conn = psycopg2.connect(
                dbname="lab",
                user="postgres",
                password="evybr2004",
                host="localhost",
                port="5432"
            )

            cur = conn.cursor()

            # SQL запрос, который будет выполняться на сервере
            sql_query = f"""
              BEGIN;
              DO $$ 
              BEGIN
                  IF NOT EXISTS (SELECT 1 FROM client WHERE client_id = {client_id}) THEN
                      INSERT INTO client (client_id, client_phonenumber, client_orders, client_name)
                      VALUES ({client_id}, '{client_phone}', 0, '{client_name}');
                  END IF;
              END;
              $$;
              DO $$ 
              BEGIN
                  IF NOT EXISTS (SELECT 1 FROM object WHERE object_id = {object_id}) THEN
                      INSERT INTO object (object_id, object_type, object_adress)
                      VALUES ({object_id}, 'квартира', '{object_address}');
                  END IF;
              END;
              $$;
              DO $$ 
              BEGIN
                  INSERT INTO "order" (order_id, client_id, object_id, manager_id, order_startdate, order_enddate, order_total, order_status)
                  VALUES ({order_id}, {client_id}, {object_id}, {manager_id}, CURRENT_DATE, NULL, {order_total}, 'новый');
              EXCEPTION
                  WHEN OTHERS THEN
                      RAISE NOTICE 'ошибка при создании заказа: %', SQLERRM;
                      ROLLBACK;
              END;
              $$;
              INSERT INTO materials (material_id, servicesorder_id, material_name, material_amount, material_unit, material_costunit)
              VALUES ({order_id}, {order_id}, '{material_name}', {material_amount}, '{material_unit}', {material_costunit});

              INSERT INTO "services in order" (servicesorder_id, order_id, service_id, servicesorder_datestart, servicesorder_dateend)
              VALUES ({order_id + 1}, {order_id}, {service_id}, '{service_start_date}', '{service_end_date}');
              COMMIT;
              """

            # Выполнение SQL запроса
            cur.execute(sql_query)
            conn.commit()
            messagebox.showinfo("Успех", "Процедура успешно выполнена!")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка: {str(e)}")
        finally:
            if conn:
                cur.close()
                conn.close()


if __name__ == "__main__":
    app = Application()
    app.mainloop()
