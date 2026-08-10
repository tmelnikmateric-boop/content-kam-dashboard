import streamlit as st
import pandas as pd
import numpy as np
import datetime
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 0. НАСТРОЙКА СТРАНИЦЫ И СТИЛЕЙ
# ==========================================
st.set_page_config(page_title="Панель управления отдела контента", layout="wide")

st.markdown("""
    <style>
    /* Центрирование и уменьшение главного заголовка */
    .custom-header {
        text-align: center;
        font-size: 1.8rem !important;
        font-weight: 600;
        margin-bottom: 25px;
    }
    
    /* Переключатель отделов */
    div[data-testid="stRadio"] > label {
        display: none;
    }
    div[data-testid="stRadio"] > div {
        justify-content: center;
        gap: 20px;
    }
    div[data-testid="stRadio"] label p {
        font-size: 1.25rem !important;
        font-weight: 600 !important;
    }

    /* Увеличение модальных окон до 85% экрана */
    div[role="dialog"], div[data-testid="stDialog"] > div:nth-child(2) {
        max-height: 88vh !important;
        width: 85vw !important;
        max-width: 85vw !important;
        overflow-y: auto !important;
    }

    /* Стили для HTML таблиц */
    .custom-table-container {
        border: 1px solid #e6e8eb;
        border-radius: 10px;
        overflow: hidden;
        margin-bottom: 24px;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.03);
    }
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 0.88rem;
    }
    .custom-table th {
        background-color: #f8f9fa;
        color: #555e6d;
        font-weight: 500;
        font-size: 0.8rem;
        letter-spacing: 0.02em;
        padding: 10px 14px;
        border-bottom: 1px solid #e6e8eb;
        border-right: 1px solid #f0f2f5;
        text-align: left;
    }
    .custom-table th:last-child {
        border-right: none;
    }
    .custom-table td {
        border-bottom: 1px solid #f0f2f5;
        border-right: 1px solid #f0f2f5;
        padding: 9px 14px;
        color: #31333f;
        font-weight: 400;
        background-color: #ffffff;
    }
    .custom-table tr:last-child td {
        border-bottom: none;
    }
    .custom-table td:last-child {
        border-right: none;
    }
    .grouped-cell {
        background-color: #fcfcfd !important;
        font-weight: 500 !important;
        color: #2c3e50 !important;
        vertical-align: middle !important;
    }

    /* Компактные формы */
    .compact-form label {
        font-size: 0.78rem !important;
        margin-bottom: -4px !important;
    }
    .compact-form input {
        padding: 4px 8px !important;
        font-size: 0.85rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. КОНСТАНТЫ И ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS
# ==========================================
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1vCZQgzBPv8uahr8ckRI1f-TA_QS6Afz2B9NP_ZMj6ek/edit?gid=59376984#gid=59376984"

SHEET_MAP = {
    'Отдел контента': {
        'data': '📥 Загруженные данные контента',
        'workgroups': '👥 Рабочие группы контента'
    },
    'Коммерческий отдел': {
        'data': '📥 Загруженные данные КАМ',
        'workgroups': '👥 Рабочие группы КАМ'
    }
}

COLUMNS = [
    'ID', 'Внешний код', 'Группа 3', 'Наименование',
    'Статус', 'Исполнитель', 'Дата взятия', 
    'Дата выполнения', 'Дата завершения работы', 
    'Причина паузы', 'Источник', 'Дата загрузки', 'Дата паузы'
]

CONTACTS_SHEET_NAME = '📇 Контакты поставщиков'
CONTACT_COLUMNS = ['Производитель', 'Оф.сайт', 'Контакт', 'Имя', 'Группы товаров', 'Примечание']

NEW_PRODUCTS_SHEET_NAME = 'Новые товары'
MANAGERS_SHEET_NAME = 'Менеджеры'

# Исключен столбец "Выгружено в файл"
NEW_PRODUCTS_COLUMNS = [
    'Внешний код', 'Наименование', 'Дата создания', 
    'Цифровой код менеджера', 'Название раздела', 'Менеджер', 
    'Контент'
]

MONTH_NAMES = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
}

@st.cache_resource
def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def load_dept_data(sheet_name):
    try:
        gc = get_gspread_client()
        sh = gc.open_by_url(SPREADSHEET_URL)
        worksheet = sh.worksheet(sheet_name)
        records = worksheet.get_all_records()
        if records:
            df = pd.DataFrame(records).astype(str)
            df.columns = df.columns.astype(str).str.strip()
            df = df.replace({'nan': '', 'NaN': '', 'None': '', '<NA>': '', 'NaT': ''})
            for col in COLUMNS:
                if col not in df.columns:
                    df[col] = ''
            return df
        return pd.DataFrame(columns=COLUMNS)
    except Exception as e:
        st.error(f"Ошибка загрузки листа {sheet_name}: {e}")
        return pd.DataFrame(columns=COLUMNS)

def save_dept_data(dept_info, df):
    data_sheet_name = dept_info['data']
    workgroup_sheet_name = dept_info['workgroups']

    try:
        gc = get_gspread_client()
        sh = gc.open_by_url(SPREADSHEET_URL)

        try:
            worksheet = sh.worksheet(data_sheet_name)
        except gspread.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=data_sheet_name, rows="1000", cols="20")

        df_to_save = df.fillna('')
        data_to_write = [df_to_save.columns.tolist()] + df_to_save.values.tolist()

        worksheet.clear()
        worksheet.update('A1', data_to_write)

        try:
            wg_worksheet = sh.worksheet(workgroup_sheet_name)
            wg_records = wg_worksheet.get_all_records()

            if wg_records:
                wg_df = pd.DataFrame(wg_records)
                wg_df.columns = wg_df.columns.astype(str).str.strip()
                summary_df = build_summary(df)

                if not summary_df.empty:
                    group_col = None
                    for c in ['Имя файла', 'Источник', 'Файл', 'Группа']:
                        if c in wg_df.columns:
                            group_col = c
                            break

                    if group_col:
                        status_map = dict(zip(summary_df['Имя файла'], summary_df['Статус группы']))
                        pause_map = dict(zip(summary_df['Имя файла'], summary_df['Причина паузы']))
                        date_pause_map = dict(zip(summary_df['Имя файла'], summary_df['Дата паузы']))

                        if 'Статус группы' not in wg_df.columns:
                            wg_df['Статус группы'] = ''
                        if 'Причина паузы' not in wg_df.columns:
                            wg_df['Причина паузы'] = ''
                        if 'Дата паузы' not in wg_df.columns:
                            wg_df['Дата паузы'] = ''

                        for idx, row in wg_df.iterrows():
                            filename = str(row.get(group_col, '')).strip()
                            if filename in status_map:
                                wg_df.at[idx, 'Статус группы'] = status_map[filename]
                                wg_df.at[idx, 'Причина паузы'] = pause_map.get(filename, '')
                                wg_df.at[idx, 'Дата паузы'] = date_pause_map.get(filename, '')

                        wg_data = [wg_df.columns.tolist()] + wg_df.fillna('').values.tolist()
                        wg_worksheet.clear()
                        wg_worksheet.update('A1', wg_data)

        except Exception as wg_err:
            st.warning(f"Данные сохранены, но не удалось обновить рабочий лист '{workgroup_sheet_name}': {wg_err}")

        return True
    except Exception as e:
        st.error(f"Ошибка сохранения: {e}")
        return False

def load_contacts_data():
    try:
        gc = get_gspread_client()
        sh = gc.open_by_url(SPREADSHEET_URL)
        try:
            worksheet = sh.worksheet(CONTACTS_SHEET_NAME)
        except gspread.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=CONTACTS_SHEET_NAME, rows="1000", cols="10")
            worksheet.append_row(CONTACT_COLUMNS)
            return pd.DataFrame(columns=CONTACT_COLUMNS)

        records = worksheet.get_all_records()
        if records:
            df = pd.DataFrame(records).astype(str)
            df.columns = df.columns.astype(str).str.strip()
            for col in CONTACT_COLUMNS:
                if col not in df.columns:
                    df[col] = ''
            return df[CONTACT_COLUMNS]
        return pd.DataFrame(columns=CONTACT_COLUMNS)
    except Exception as e:
        st.error(f"Ошибка загрузки контактов: {e}")
        return pd.DataFrame(columns=CONTACT_COLUMNS)

def add_contact_row(new_row_dict):
    try:
        gc = get_gspread_client()
        sh = gc.open_by_url(SPREADSHEET_URL)
        try:
            worksheet = sh.worksheet(CONTACTS_SHEET_NAME)
        except gspread.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=CONTACTS_SHEET_NAME, rows="1000", cols="10")
            worksheet.append_row(CONTACT_COLUMNS)

        row_values = [str(new_row_dict.get(col, '')).strip() for col in CONTACT_COLUMNS]
        worksheet.append_row(row_values)
        return True
    except Exception as e:
        st.error(f"Ошибка сохранения контакта: {e}")
        return False

# ==========================================
# 1.1 ЛОГИКА ДЛЯ "НОВЫХ ТОВАРОВ" И "МЕНЕДЖЕРОВ"
# ==========================================
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
    """Загружает все строки листа 'Новые товары' списком списков"""
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

    header = raw_data[0] if raw_data else NEW_PRODUCTS_COLUMNS

    for row in raw_data[1:]:
        if not row or not any(row):
            continue
        
        first_cell = str(row[0]).strip()
        if "📅 Загрузка от" in first_cell:
            if current_rows:
                df_batch = pd.DataFrame(current_rows, columns=header[:len(current_rows[0])])
                for col in NEW_PRODUCTS_COLUMNS:
                    if col not in df_batch.columns:
                        df_batch[col] = ''
                batches[current_date] = df_batch[NEW_PRODUCTS_COLUMNS]
                current_rows = []
            current_date = first_cell.replace("📅 Загрузка от", "").strip()
        else:
            padded_row = row + [''] * (len(header) - len(row))
            current_rows.append(padded_row[:len(header)])

    if current_rows:
        df_batch = pd.DataFrame(current_rows, columns=header[:len(current_rows[0])])
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
        
        # Автозаполнение Менеджера по Цифровому коду (аналог ВПР)
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
# 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================
def calculate_business_days(date_str):
    if not date_str or str(date_str).lower() in ['nan', 'none', '']:
        return 0
    try:
        clean_date_str = str(date_str).split(' ')[0]
        start_date = datetime.datetime.strptime(clean_date_str, "%d.%m.%Y").date()
        today = datetime.date.today()
        if start_date >= today:
            return 0
        return int(np.busday_count(start_date, today))
    except Exception:
        return 0

def build_summary(df):
    source_col = None
    for col in ['Имя файла', 'Источник', 'Файл']:
        if col in df.columns:
            source_col = col
            break

    if df.empty or not source_col:
        return pd.DataFrame()

    summary_rows = []
    grouped = df.groupby(source_col, sort=False)

    for idx, (filename, group) in enumerate(grouped, start=1):
        if not str(filename).strip():
            continue

        total = len(group)
        first_row = group.iloc[0]

        def get_group_val(possible_cols):
            for col in possible_cols:
                matching_cols = [c for c in group.columns if c.strip().lower() == col.strip().lower()]
                for m_col in matching_cols:
                    s = group[m_col].astype(str).str.strip()
                    valid = s[~s.isin(['', 'nan', 'NaN', 'None', '<NA>', 'NaT'])]
                    if not valid.empty:
                        return valid.iloc[0]
            return ''

        st_val = str(first_row.get('Статус', '')).strip().lower()
        st_grp = str(first_row.get('Статус группы', '')).strip().lower()
        
        date_done = get_group_val(['Дата завершения работы', 'Дата выполнения'])
        date_take = get_group_val(['Дата взятия', 'Дата начала работы'])
        pause_reason = get_group_val(['Причина паузы', 'Причина'])
        date_pause = get_group_val(['Дата паузы', 'Дата постановки на паузу'])
        date_added = get_group_val(['Дата добавления файла', 'Дата загрузки', 'Дата добавления'])

        is_completed = (
            st_val in ['выполнено', 'выполнен', 'завершен', 'завершена', '✅ выполнен', '✅ завершена'] or
            'выполнен' in st_grp or 'выполнено' in st_grp or 'заверш' in st_grp or bool(date_done)
        )
        is_paused = (
            st_val in ['пауза', 'на паузе', '⏸️ на паузе'] or 'пауз' in st_grp or '⏸️' in st_grp or '⏸' in st_val or bool(pause_reason)
        )
        is_in_work = (
            not is_completed and not is_paused and (
                st_val in ['в работе', 'взято в работу', '🔄 в работе'] or 'в работе' in st_grp or '🔄' in st_grp or bool(date_take)
            )
        )

        if is_completed:
            done_cnt, in_work_cnt, new_cnt, group_status = total, 0, 0, '✅ Выполнен'
        elif is_paused:
            done_cnt, in_work_cnt, new_cnt, group_status = 0, 0, total, '⏸️ На паузе'
        elif is_in_work:
            done_cnt, in_work_cnt, new_cnt, group_status = 0, total, 0, '🔄 В работе'
        else:
            done_cnt, in_work_cnt, new_cnt, group_status = 0, 0, total, '🆕 Новая'

        days_passed = calculate_business_days(date_added)

        summary_rows.append({
            'Имя файла': filename,
            'Группа 3': first_row.get('Группа 3', ''),
            'Количество товаров': total,
            'Новых': new_cnt,
            'В работе': in_work_cnt,
            'Выполнено': done_cnt,
            'Статус группы': group_status,
            'Причина паузы': pause_reason,
            'Дата паузы': date_pause,
            'Исполнитель': first_row.get('Исполнитель', ''),
            'Дата начала работы': date_take,
            'Дата завершения работы': date_done,
            'Дата добавления': date_added,
            'Дней с добавления': days_passed
        })

    return pd.DataFrame(summary_rows)

def render_grouped_html_table(df, group_col, cols_order, headers):
    if df.empty:
        return ""
    
    html = """
    <div class="custom-table-container">
    <table class="custom-table"><thead><tr>
    """
    for h in headers:
        html += f"<th>{h}</th>"
    html += "</tr></thead><tbody>"

    seen = set()
    unique_ordered = [x for x in df[group_col] if not (x in seen or seen.add(x))]

    for val in unique_ordered:
        sub_df = df[df[group_col] == val]
        rowspan = len(sub_df)
        first_row = True

        for _, row in sub_df.iterrows():
            html += "<tr>"
            if first_row:
                html += f"<td rowspan='{rowspan}' class='grouped-cell'>{row[group_col]}</td>"
                first_row = False
            
            for col in cols_order:
                if col != group_col:
                    html += f"<td>{row[col]}</td>"
            html += "</tr>"

    html += "</tbody></table></div>"
    return html

# ==========================================
# 3. МОДАЛЬНЫЕ ОКНА (DIALOGS)
# ==========================================

@st.dialog("▶️ Взять файлы в работу")
def modal_take_in_work(dept_info, summary_df, df):
    new_df = summary_df[summary_df['Статус группы'] == '🆕 Новая']
    if new_df.empty:
        st.info("Нет новых файлов для взятия в работу.")
        return

    st.write("Выберите новые файлы:")
    selected_files = []
    
    with st.container(height=350):
        for _, row in new_df.iterrows():
            filename = row['Имя файла']
            count = row['Количество товаров']
            if st.checkbox(f"{filename} — {count} SKU", key=f"chk_new_{filename}"):
                selected_files.append(filename)

    executor_name = st.text_input("Имя исполнителя:")

    if st.button("В работу"):
        if not selected_files:
            st.warning("Отметьте хотя бы один файл!")
        elif not executor_name.strip():
            st.warning("Укажите имя исполнителя!")
        else:
            source_col = 'Имя файла' if 'Имя файла' in df.columns else 'Источник'
            now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            mask = df[source_col].isin(selected_files)

            df.loc[mask, 'Статус'] = 'В работе'
            df.loc[mask, 'Статус группы'] = '🔄 В работе'
            df.loc[mask, 'Исполнитель'] = executor_name.strip()
            df.loc[mask, 'Дата взятия'] = now_str
            df.loc[mask, 'Причина паузы'] = ''
            df.loc[mask, 'Дата паузы'] = ''

            if save_dept_data(dept_info, df):
                st.success("Статус обновлен на '🔄 В работе'")
                st.rerun()

@st.dialog("⏸️ Поставить файлы на паузу")
def modal_pause(dept_info, summary_df, df):
    in_work_df = summary_df[summary_df['Статус группы'] == '🔄 В работе']
    if in_work_df.empty:
        st.info("Нет файлов в работе для отправки на паузу.")
        return

    st.write("Выберите файлы в работе:")
    selected_files = []
    
    with st.container(height=350):
        for _, row in in_work_df.iterrows():
            filename = row['Имя файла']
            count = row['Количество товаров']
            if st.checkbox(f"{filename} — {count} SKU", key=f"chk_work_{filename}"):
                selected_files.append(filename)

    pause_reason = st.selectbox("Укажите причину паузы:", options=["информация уточняется", "запрошено у поставщика"])

    if st.button("Поставить на паузу"):
        if not selected_files:
            st.warning("Отметьте хотя бы один файл!")
        else:
            source_col = 'Имя файла' if 'Имя файла' in df.columns else 'Источник'
            now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            mask = df[source_col].isin(selected_files)

            df.loc[mask, 'Статус'] = '⏸️ На паузе'
            df.loc[mask, 'Статус группы'] = '⏸️ На паузе'
            df.loc[mask, 'Причина паузы'] = pause_reason
            df.loc[mask, 'Дата паузы'] = now_str

            if save_dept_data(dept_info, df):
                st.success("Файлы переведены на паузу!")
                st.rerun()

@st.dialog("▶️ Снять файлы с паузы")
def modal_unpause(dept_info, summary_df, df):
    paused_df = summary_df[summary_df['Статус группы'] == '⏸️ На паузе']
    if paused_df.empty:
        st.info("Нет файлов на паузе.")
        return

    st.write("Выберите файлы для возобновления работы:")
    selected_files = []
    
    with st.container(height=350):
        for _, row in paused_df.iterrows():
            filename = row['Имя файла']
            count = row['Количество товаров']
            if st.checkbox(f"{filename} — {count} SKU", key=f"chk_unpause_{filename}"):
                selected_files.append(filename)

    if st.button("Вернуть в работу"):
        if not selected_files:
            st.warning("Отметьте хотя бы один файл!")
        else:
            source_col = 'Имя файла' if 'Имя файла' in df.columns else 'Источник'
            mask = df[source_col].isin(selected_files)

            df.loc[mask, 'Статус'] = 'В работе'
            df.loc[mask, 'Статус группы'] = '🔄 В работе'
            df.loc[mask, 'Причина паузы'] = ''
            df.loc[mask, 'Дата паузы'] = ''

            if save_dept_data(dept_info, df):
                st.success("Файлы успешно возвращены в работу!")
                st.rerun()

@st.dialog("✅ Завершить работу по файлам")
def modal_complete(dept_info, summary_df, df):
    in_work_df = summary_df[summary_df['Статус группы'] == '🔄 В работе']
    if in_work_df.empty:
        st.info("Нет файлов в работе для завершения.")
        return

    st.write("Выберите файлы в работе для завершения:")
    selected_files = []
    
    with st.container(height=350):
        for _, row in in_work_df.iterrows():
            filename = row['Имя файла']
            count = row['Количество товаров']
            if st.checkbox(f"{filename} — {count} SKU", key=f"chk_comp_{filename}"):
                selected_files.append(filename)

    if st.button("Завершить"):
        if not selected_files:
            st.warning("Отметьте хотя бы один файл!")
        else:
            source_col = 'Имя файла' if 'Имя файла' in df.columns else 'Источник'
            now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            mask = df[source_col].isin(selected_files)

            df.loc[mask, 'Статус'] = '✅ Выполнен'
            df.loc[mask, 'Статус группы'] = '✅ Выполнен'
            df.loc[mask, 'Дата завершения работы'] = now_str
            df.loc[mask, 'Дата выполнения'] = now_str

            if save_dept_data(dept_info, df):
                st.success("Статус обновлен на '✅ Выполнен'")
                st.rerun()

@st.dialog("📊 Аналитика и статистика")
def modal_analytics():
    with st.spinner("Сбор статистики..."):
        df_content = load_dept_data(SHEET_MAP['Отдел контента']['data'])
        df_comm = load_dept_data(SHEET_MAP['Коммерческий отдел']['data'])

        summary_content = build_summary(df_content)
        summary_comm = build_summary(df_comm)

    with st.container(height=650):
        new_content_sku = summary_content[summary_content['Статус группы'] == '🆕 Новая']['Количество товаров'].sum() if not summary_content.empty else 0
        new_comm_sku = summary_comm[summary_comm['Статус группы'] == '🆕 Новая']['Количество товаров'].sum() if not summary_comm.empty else 0

        st.markdown("<h4 style='font-weight: 500; font-size: 1.05rem; margin-bottom: 12px;'>🆕 Новые SKU на добавление</h4>", unsafe_allow_html=True)
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Отдел контента", f"{new_content_sku} SKU")
        col_m2.metric("Коммерческий отдел", f"{new_comm_sku} SKU")

        st.divider()

        combined_summaries = []
        if not summary_content.empty:
            summary_content['Отдел'] = 'Отдел контента'
            combined_summaries.append(summary_content)
        if not summary_comm.empty:
            summary_comm['Отдел'] = 'Коммерческий отдел'
            combined_summaries.append(summary_comm)

        if combined_summaries:
            all_summary = pd.concat(combined_summaries, ignore_index=True)
            
            st.markdown("<h4 style='font-weight: 500; font-size: 1.05rem; margin-bottom: 12px;'>👤 Статистика по месяцам</h4>", unsafe_allow_html=True)
            
            def parse_date_and_month(row):
                date_str = str(row['Дата завершения работы']) or str(row['Дата начала работы'])
                if date_str and len(date_str) >= 10:
                    try:
                        clean_date = date_str.split(' ')[0]
                        dt = datetime.datetime.strptime(clean_date, "%d.%m.%Y")
                        month_str = f"{MONTH_NAMES[dt.month]} {dt.year}"
                        sort_key = dt.strftime("%Y-%m")
                        return pd.Series([month_str, sort_key])
                    except Exception:
                        return pd.Series(["Неизвестно", "9999-99"])
                return pd.Series(["Неизвестно", "9999-99"])

            all_summary[['Месяц', 'Месяц_сорт']] = all_summary.apply(parse_date_and_month, axis=1)
            exec_df = all_summary[all_summary['Исполнитель'].str.strip() != ''].copy()
            
            if not exec_df.empty:
                perf_df = exec_df.groupby(['Месяц_сорт', 'Месяц', 'Исполнитель'])['Количество товаров'].sum().reset_index()
                perf_df.sort_values(by=['Месяц_сорт', 'Исполнитель'], inplace=True)
                perf_df.rename(columns={'Количество товаров': 'Количество SKU'}, inplace=True)
                
                html_table_perf = render_grouped_html_table(
                    df=perf_df,
                    group_col='Месяц',
                    cols_order=['Месяц', 'Исполнитель', 'Количество SKU'],
                    headers=['Месяц', 'Исполнитель', 'Количество SKU']
                )
                st.markdown(html_table_perf, unsafe_allow_html=True)
            else:
                st.info("Нет данных о выполненных файлах.")

            st.divider()

            st.markdown("<h4 style='font-weight: 500; font-size: 1.05rem; margin-bottom: 12px;'>🔄 В работе на данный момент</h4>", unsafe_allow_html=True)
            in_work_summary = all_summary[all_summary['Статус группы'] == '🔄 В работе'].copy()
            
            if not in_work_summary.empty:
                work_by_exec = in_work_summary.groupby(['Исполнитель', 'Отдел'])['Количество товаров'].sum().reset_index()
                work_by_exec.sort_values(by=['Исполнитель', 'Отдел'], inplace=True)
                work_by_exec.rename(columns={'Количество товаров': 'SKU в работе'}, inplace=True)

                html_table_work = render_grouped_html_table(
                    df=work_by_exec,
                    group_col='Исполнитель',
                    cols_order=['Исполнитель', 'Отдел', 'SKU в работе'],
                    headers=['Исполнитель', 'Отдел', 'SKU в работе']
                )
                st.markdown(html_table_work, unsafe_allow_html=True)
            else:
                st.info("В данный момент нет SKU в работе.")
        else:
            st.info("Данные отсутствуют.")

@st.dialog("📇 Контакты поставщиков")
def modal_contacts():
    with st.expander("➕ Добавить новый контакт поставщика", expanded=False):
        with st.form("add_contact_form", clear_on_submit=True):
            f_col1, f_col2, f_col3, f_col4, f_col5, f_col6 = st.columns([1.2, 1.2, 1.2, 1.2, 1.5, 2.0])
            with f_col1:
                producer = st.text_input("Производитель", placeholder="Название")
            with f_col2:
                site = st.text_input("Оф.сайт", placeholder="URL / сайт")
            with f_col3:
                contact_info = st.text_input("Контакт", placeholder="Тел / Email")
            with f_col4:
                name = st.text_input("Имя", placeholder="Контактное лицо")
            with f_col5:
                groups = st.text_input("Группы товаров", placeholder="Категории")
            with f_col6:
                note = st.text_input("Примечание", placeholder="Доп. информация")

            btn_submit = st.form_submit_button("Сохранить контакт", use_container_width=True)

            if btn_submit:
                if not producer.strip() and not name.strip():
                    st.warning("Укажите хотя бы 'Производитель' или 'Имя'!")
                else:
                    new_contact = {
                        'Производитель': producer,
                        'Оф.сайт': site,
                        'Контакт': contact_info,
                        'Имя': name,
                        'Группы товаров': groups,
                        'Примечание': note
                    }
                    if add_contact_row(new_contact):
                        st.success("Контакт сохранен!")
                        st.rerun()

    contacts_df = load_contacts_data()

    col_search, _ = st.columns([2, 1])
    with col_search:
        search_query = st.text_input("🔍 Быстрый поиск:", "", placeholder="Введите текст для фильтрации...")

    if not contacts_df.empty:
        if search_query.strip():
            q = search_query.lower()
            mask = contacts_df.apply(lambda row: row.astype(str).str.lower().str.contains(q).any(), axis=1)
            filtered_contacts = contacts_df[mask]
        else:
            filtered_contacts = contacts_df

        column_configuration = {
            "Производитель": st.column_config.TextColumn("Производитель", width="medium"),
            "Оф.сайт": st.column_config.TextColumn("Оф.сайт", width="small"),
            "Контакт": st.column_config.TextColumn("Контакт", width="small"),
            "Имя": st.column_config.TextColumn("Имя", width="small"),
            "Группы товаров": st.column_config.TextColumn("Группы товаров", width="medium"),
            "Примечание": st.column_config.TextColumn("Примечание", width="large")
        }

        st.dataframe(
            filtered_contacts,
            use_container_width=True,
            hide_index=True,
            column_config=column_configuration,
            height=480
        )
    else:
        st.info("Контакты пока не добавлены.")

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
        dates_list.reverse()

        selected_date = st.selectbox(
            "📅 Выберите дату загрузки:",
            options=dates_list,
            key="select_batch_date"
        )

        selected_df = batches[selected_date]

        st.caption(f"Всего товаров в выгрузке: **{len(selected_df)}** | Кликните по заголовку любого столбца для сортировки")

        np_column_config = {
            "Внешний код": st.column_config.TextColumn("Внешний код", width="small"),
            "Наименование": st.column_config.TextColumn("Наименование", width="large"),
            "Дата создания": st.column_config.TextColumn("Дата создания", width="small"),
            "Цифровой код менеджера": st.column_config.TextColumn("Код менеджера", width="small"),
            "Название раздела": st.column_config.TextColumn("Название раздела", width="medium"),
            "Менеджер": st.column_config.TextColumn("Менеджер", width="medium"),
            "Контент": st.column_config.TextColumn("Контент", width="small")
        }

        st.dataframe(
            selected_df,
            use_container_width=True,
            hide_index=True,
            column_config=np_column_config,
            height=450
        )
    else:
        st.info("Данные по новым товарам пока отсутствуют.")

# ==========================================
# 4. ОСНОВНОЙ ИНТЕРФЕЙС STREAMLIT
# ==========================================

st.markdown("<h2 class='custom-header'>Панель управления отдела контента</h2>", unsafe_allow_html=True)

dept = st.radio(
    "Выберите отдел:", 
    options=['Отдел контента', 'Коммерческий отдел'], 
    horizontal=True,
    label_visibility="collapsed"
)

dept_info = SHEET_MAP[dept]

df = load_dept_data(dept_info['data'])
summary_df = build_summary(df)

st.divider()

col_upload, col_actions, col_extra = st.columns([1.2, 1.8, 1.3])

with col_upload:
    st.subheader(f"1. Загрузка файла ({dept.lower()})")
    uploaded_file = st.file_uploader(f"Выберите .xlsx / .xls файл для {dept.lower()}", type=['xlsx', 'xls'])
    if uploaded_file is not None:
        if st.button(f"Загрузить файл {dept.lower()}", use_container_width=True):
            uploaded_df = pd.read_excel(uploaded_file)
            now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

            uploaded_df['Имя файла'] = uploaded_file.name
            uploaded_df['Источник'] = uploaded_file.name
            uploaded_df['Дата добавления файла'] = now_str
            uploaded_df['Статус'] = 'Новый'
            uploaded_df['Статус группы'] = '🆕 Новая'

            for col in COLUMNS:
                if col not in uploaded_df.columns:
                    uploaded_df[col] = ''

            new_df = pd.concat([df, uploaded_df], ignore_index=True)
            if save_dept_data(dept_info, new_df):
                st.success(f"Файл '{uploaded_file.name}' успешно сохранен!")
                st.rerun()

with col_actions:
    st.subheader("2. Управление статусами")
    st.write("Выберите действие по файлам:")

    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)

    if btn_col1.button("▶️ В работу", use_container_width=True):
        modal_take_in_work(dept_info, summary_df, df)

    if btn_col2.button("⏸️ На паузу", use_container_width=True):
        modal_pause(dept_info, summary_df, df)

    if btn_col3.button("▶️ Снять с паузы", use_container_width=True):
        modal_unpause(dept_info, summary_df, df)

    if btn_col4.button("✅ Завершить", use_container_width=True):
        modal_complete(dept_info, summary_df, df)

with col_extra:
    st.subheader("3. Дополнительная информация")
    st.write("Просмотр отчетов, контактов и выгрузок:")

    btn_ex1, btn_ex2, btn_ex3 = st.columns(3)

    if btn_ex1.button("📊 Аналитика", use_container_width=True):
        modal_analytics()

    if btn_ex2.button("📇 Контакты", use_container_width=True):
        modal_contacts()

    if btn_ex3.button("📦 Новые товары", use_container_width=True):
        modal_new_products()

st.divider()

# ==========================================
# 5. РЕЕСТР АКТИВНЫХ И ЗАВЕРШЕННЫХ ГРУПП
# ==========================================
if summary_df.empty:
    st.info("Нет данных для отображения")
else:
    st.subheader(f"📋 Реестр групп — {dept.upper()}")

    new_df = summary_df[summary_df['Статус группы'] == '🆕 Новая'].copy().reset_index(drop=True)
    paused_df = summary_df[summary_df['Статус группы'] == '⏸️ На паузе'].copy().reset_index(drop=True)
    work_df = summary_df[summary_df['Статус группы'] == '🔄 В работе'].copy().reset_index(drop=True)
    completed_summary = summary_df[summary_df['Статус группы'].isin(['✅ Выполнен', '✅ Завершена'])].copy().reset_index(drop=True)

    tab_new, tab_paused, tab_work = st.tabs([
        f"🆕 Новые ({len(new_df)})", 
        f"⏸️ На паузе ({len(paused_df)})", 
        f"🔄 В работе ({len(work_df)})"
    ])

    with tab_new:
        if new_df.empty:
            st.info("Нет новых групп.")
        else:
            cols_new = ['Имя файла', 'Группа 3', 'Количество товаров', 'Дата добавления', 'Дней с добавления']
            st.dataframe(new_df[cols_new], use_container_width=True, hide_index=True)

    with tab_paused:
        if paused_df.empty:
            st.info("Нет групп на паузе.")
        else:
            cols_paused = ['Имя файла', 'Группа 3', 'Количество товаров', 'Исполнитель', 'Дата паузы', 'Причина паузы']
            st.dataframe(paused_df[cols_paused], use_container_width=True, hide_index=True)

    with tab_work:
        if work_df.empty:
            st.info("Нет групп в работе.")
        else:
            cols_work = ['Имя файла', 'Группа 3', 'Количество товаров', 'Исполнитель', 'Дата начала работы']
            st.dataframe(work_df[cols_work], use_container_width=True, hide_index=True)

    st.write("")

    if 'show_completed' not in st.session_state:
        st.session_state.show_completed = False

    btn_label = "🙈 Скрыть завершенные группы" if st.session_state.show_completed else f"📂 Посмотреть завершенные группы ({len(completed_summary)})"

    if st.button(btn_label):
        st.session_state.show_completed = not st.session_state.show_completed
        st.rerun()

    if st.session_state.show_completed:
        st.markdown("---")
        st.subheader(f"✅ Завершенные группы ({len(completed_summary)})")
        if completed_summary.empty:
            st.info("Завершенных групп пока нет.")
        else:
            cols_completed = ['Имя файла', 'Группа 3', 'Количество товаров', 'Исполнитель', 'Дата начала работы', 'Дата завершения работы']
            st.dataframe(completed_summary[cols_completed], use_container_width=True, hide_index=True)
