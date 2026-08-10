import streamlit as st
import pandas as pd
import numpy as np
import datetime
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 1.1 ОБНОВЛЕННАЯ ЛОГИКА ДЛЯ "НОВЫХ ТОВАРОВ"
# ==========================================
NEW_PRODUCTS_SHEET_NAME = 'Новые товары'
MANAGERS_SHEET_NAME = 'Менеджеры'

# Исключили столбец 'Выгружено в файл'
NEW_PRODUCTS_COLUMNS = [
    'Внешний код', 'Наименование', 'Дата создания', 
    'Цифровой код менеджера', 'Название раздела', 'Менеджер', 
    'Контент'
]

def load_managers_mapping():
    """Загружает словарь соответствия цифрового кода менеджеру из листа 'Менеджеры'"""
    try:
        gc = get_gspread_client()
        sh = gc.open_by_url(SPREADSHEET_URL)
        try:
            worksheet = sh.worksheet(MANAGERS_SHEET_NAME)
        except gspread.WorksheetNotFound:
            return {}

        records = worksheet.get_all_records()
        if not records:
            return {}

        m_df = pd.DataFrame(records).astype(str)
        m_df.columns = m_df.columns.astype(str).str.strip()

        code_col = next((c for c in m_df.columns if 'код' in c.lower()), m_df.columns[0])
        name_col = next((c for c in m_df.columns if any(k in c.lower() for k in ['менеджер', 'фамили', 'фио', 'имя'])), 
                        m_df.columns[1] if len(m_df.columns) > 1 else m_df.columns[0])

        return dict(zip(m_df[code_col].str.strip(), m_df[name_col].str.strip()))
    except Exception as e:
        st.error(f"Ошибка загрузки листа менеджеров: {e}")
        return {}

def load_raw_new_products():
    """Загружает все строки листа 'Новые товары' списком списков для разбора разделителей"""
    try:
        gc = get_gspread_client()
        sh = gc.open_by_url(SPREADSHEET_URL)
        try:
            worksheet = sh.worksheet(NEW_PRODUCTS_SHEET_NAME)
        except gspread.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=NEW_PRODUCTS_SHEET_NAME, rows="1000", cols="10")
            worksheet.append_row(NEW_PRODUCTS_COLUMNS)
            return []

        return worksheet.get_all_values()
    except Exception as e:
        st.error(f"Ошибка загрузки листа 'Новые товары': {e}")
        return []

def parse_new_products_by_batches():
    """
    Разбирает выгрузку из Google Sheets на блоки по датам загрузки.
    Возвращает словарь { "Дата загрузки": DataFrame_товаров }
    """
    raw_data = load_raw_new_products()
    if not raw_data:
        return {}

    batches = {}
    current_date = "Без даты"
    current_rows = []

    # Заголовок таблицы (первая строка)
    header = raw_data[0] if raw_data else NEW_PRODUCTS_COLUMNS

    for row in raw_data[1:]:
        if not row or not any(row):
            continue
        
        # Проверяем, является ли строка разделителем с датой
        first_cell = str(row[0]).strip()
        if "📅 Загрузка от" in first_cell:
            if current_rows:
                df_batch = pd.DataFrame(current_rows, columns=header)
                # Оставляем только нужные колонки
                for col in NEW_PRODUCTS_COLUMNS:
                    if col not in df_batch.columns:
                        df_batch[col] = ''
                batches[current_date] = df_batch[NEW_PRODUCTS_COLUMNS]
                current_rows = []
            current_date = first_cell.replace("📅 Загрузка от", "").strip()
        else:
            # Выравниваем длину строки под заголовок
            padded_row = row + [''] * (len(header) - len(row))
            current_rows.append(padded_row[:len(header)])

    if current_rows:
        df_batch = pd.DataFrame(current_rows, columns=header)
        for col in NEW_PRODUCTS_COLUMNS:
            if col not in df_batch.columns:
                df_batch[col] = ''
        batches[current_date] = df_batch[NEW_PRODUCTS_COLUMNS]

    return batches

def append_new_products(uploaded_df):
    """
    Добавляет новую партию с автоподстановкой Фамилии менеджера (ВПР)
    """
    try:
        gc = get_gspread_client()
        sh = gc.open_by_url(SPREADSHEET_URL)
        try:
            worksheet = sh.worksheet(NEW_PRODUCTS_SHEET_NAME)
        except gspread.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=NEW_PRODUCTS_SHEET_NAME, rows="1000", cols="10")
            worksheet.append_row(NEW_PRODUCTS_COLUMNS)

        managers_map = load_managers_mapping()

        uploaded_df = uploaded_df.astype(str).replace({'nan': '', 'NaN': '', 'None': '', '<NA>': '', 'NaT': ''})
        
        # Автозаполнение Менеджера по Цифровому коду
        if 'Цифровой код менеджера' in uploaded_df.columns:
            uploaded_df['Менеджер'] = uploaded_df['Цифровой код менеджера'].astype(str).str.strip().map(managers_map).fillna('')

        for col in NEW_PRODUCTS_COLUMNS:
            if col not in uploaded_df.columns:
                uploaded_df[col] = ''

        uploaded_df = uploaded_df[NEW_PRODUCTS_COLUMNS]

        now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        date_header_row = [f"📅 Загрузка от {now_str}"] + [''] * (len(NEW_PRODUCTS_COLUMNS) - 1)

        rows_to_append = [date_header_row] + uploaded_df.values.tolist()
        worksheet.append_rows(rows_to_append)

        return True
    except Exception as e:
        st.error(f"Ошибка сохранения новых товаров: {e}")
        return False

# ==========================================
# 3. ОБНОВЛЕННОЕ МОДАЛЬНОЕ ОКНО
# ==========================================
@st.dialog("📦 Новые товары (Еженедельная загрузка)")
def modal_new_products():
    st.markdown("<h4 style='font-weight: 500; font-size: 1.05rem; margin-top: 5px; margin-bottom: 12px;'>📥 Загрузить новый файл</h4>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Выберите .xlsx / .xls файл", type=['xlsx', 'xls'], key="new_prod_file")

    if uploaded_file is not None:
        if st.button("🚀 Добавить выгрузку в таблицу", use_container_width=True):
            try:
                new_products_df = pd.read_excel(uploaded_file)
                if append_new_products(new_products_df):
                    st.success(f"Выгрузка '{uploaded_file.name}' успешно добавлена!")
                    st.rerun()
            except Exception as e:
                st.error(f"Ошибка чтения файла: {e}")

    st.divider()

    st.markdown("<h4 style='font-weight: 500; font-size: 1.05rem; margin-bottom: 12px;'>📋 Реестр выгрузок по датам</h4>", unsafe_allow_html=True)
    
    batches = parse_new_products_by_batches()

    if batches:
        dates_list = list(batches.keys())
        # Сортируем даты (последние загрузки сверху)
        dates_list.reverse()

        selected_date = st.selectbox(
            "📅 Выберите дату загрузки:",
            options=dates_list,
            key="select_batch_date"
        )

        selected_df = batches[selected_date]

        st.caption(f"Всего товаров в выгрузке: **{len(selected_df)}** | Кликните по названию колонки для сортировки")

        np_column_config = {
            "Внешний код": st.column_config.TextColumn("Внешний код", width="small"),
            "Наименование": st.column_config.TextColumn("Наименование", width="large"),
            "Дата создания": st.column_config.TextColumn("Дата создания", width="small"),
            "Цифровой код менеджера": st.column_config.TextColumn("Код менеджера", width="small"),
            "Название раздела": st.column_config.TextColumn("Название раздела", width="medium"),
            "Менеджер": st.column_config.TextColumn("Менеджер", width="medium"),
            "Контент": st.column_config.TextColumn("Контент", width="small")
        }

        # Встроенный st.dataframe поддерживает интерактивную сортировку по клику на заголовки
        st.dataframe(
            selected_df,
            use_container_width=True,
            hide_index=True,
            column_config=np_column_config,
            height=450
        )
    else:
        st.info("Данные по новым товарам пока отсутствуют.")
