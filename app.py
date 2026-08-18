import base64
import datetime
import gspread
from google.oauth2.service_account import Credentials
import numpy as np
import pandas as pd
import streamlit as st
from urllib.parse import quote


# ==========================================
# 0. НАСТРОЙКА СТРАНИЦЫ И СТИЛЕЙ
# ==========================================
st.set_page_config(
    page_title="Панель управления отдела контента", layout="wide"
)

st.markdown(
    """
    <style>
    .custom-header {
        text-align: center;
        font-size: 1.8rem !important;
        font-weight: 600;
        margin-bottom: 25px;
    }
    
    /* Стили для переключателя отделов: слева, мелкий шрифт */
    div[data-testid="stRadio"] > label {
        display: none;
    }
    div[data-testid="stRadio"] > div {
        justify-content: flex-start !important;
        gap: 15px;
    }
    div[data-testid="stRadio"] label p {
        font-size: 0.95rem !important;
        font-weight: 500 !important;
    }

    /* 1. ГЛАВНЫЕ (ВЕРХНИЕ) ВКЛАДКИ: по центру, размер 1.25rem */
    div[data-testid="stTabs"] [data-baseweb="tab-list"] {
        justify-content: center !important;
        gap: 30px;
    }
    div[data-testid="stTabs"] [data-baseweb="tab"] p {
        font-size: 1.25rem !important;
        font-weight: 600 !important;
    }

    /* 2. ВЛОЖЕННЫЕ ПОДВКЛАДКИ (Новые, В работе, Завершенные): слева, размер 1rem */
    div[data-testid="stTabs"] div[data-testid="stTabs"] [data-baseweb="tab-list"] {
        justify-content: flex-start !important;
        gap: 15px !important;
    }
    div[data-testid="stTabs"] div[data-testid="stTabs"] [data-baseweb="tab"] p {
        font-size: 1rem !important;
        font-weight: 500 !important;
    }

    div[role="dialog"], div[data-testid="stDialog"] > div:nth-child(2) {
        max-height: 88vh !important;
        width: 85vw !important;
        max-width: 85vw !important;
        overflow-y: auto !important;
    }

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

    .urgent-badge {
        background-color: #ffebe9;
        color: #cf222e;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.8rem;
        display: inline-block;
    }
    .normal-badge {
        background-color: #f0f2f5;
        color: #57606a;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 500;
        font-size: 0.8rem;
        display: inline-block;
    }

    /* СТИЛИ ДЛЯ БАБЛОВ (ТЕГОВ) ИСПОЛНИТЕЛЕЙ */
    .executors-container {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        align-items: center;
        margin-top: 4px;
        margin-bottom: 8px;
    }
    .executor-bubble {
        background-color: #e1f5fe;
        color: #0288d1;
        border: 1px solid #b3e5fc;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.82rem;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
    }
    /* СТИЛИ ДЛЯ ВЫВОДА ГРУПП С ПЕРЕНОСОМ ТЕКСТА И ФИКСИРОВАННЫМИ СТОЛБЦАМИ */
    .groups-table-container {
        max-height: 650px;
        overflow: auto;
        border: 1px solid #e6e8eb;
        border-radius: 8px;
    }
    .groups-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-size: 0.78rem;
    }
    .groups-table th {
        position: sticky;
        top: 0;
        background: #f8f9fa;
        z-index: 10;
        padding: 6px 6px;
        white-space: normal !important;
        word-wrap: break-word;
        text-align: center;
        vertical-align: middle;
        font-weight: 600;
        border-bottom: 2px solid #d0d7de;
        border-right: 1px solid #e6e8eb;
        line-height: 1.2;
    }
    .groups-table td {
        padding: 6px 8px;
        border-bottom: 1px solid #f0f2f5;
        border-right: 1px solid #f0f2f5;
        white-space: normal !important;
        word-break: break-word;
        background-color: #ffffff;
        text-align: center;
        vertical-align: middle;
    }

    /* Фиксирование первых трех столбцов (Группа 1, Группа 2, Группа 3) */
    .groups-table th:nth-child(2), .groups-table td:nth-child(2) {
        position: sticky; left: 0; width: 130px; min-width: 130px; max-width: 130px;
    }
    .groups-table th:nth-child(3), .groups-table td:nth-child(3) {
        position: sticky; left: 130px; width: 130px; min-width: 130px; max-width: 130px;
    }
    .groups-table th:nth-child(4), .groups-table td:nth-child(4) {
        position: sticky; left: 260px; width: 140px; min-width: 140px; max-width: 140px; border-right: 2px solid #d0d7de;
    }

    .groups-table td:nth-child(2), .groups-table td:nth-child(3), .groups-table td:nth-child(4) {
        background-color: #fcfcfd;
        text-align: left;
        z-index: 5;
    }
    .groups-table th:nth-child(2), .groups-table th:nth-child(3), .groups-table th:nth-child(4) {
        z-index: 15;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 1. КОНСТАНТЫ И ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS
# ==========================================
SPREADSHEET_URL = 'https://docs.google.com/spreadsheets/d/1vCZQgzBPv8uahr8ckRI1f-TA_QS6Afz2B9NP_ZMj6ek/edit?gid=59376984#gid=59376984'

SHEET_MAP = {
    'Отдел контента': {
        'data': '📥 Загруженные данные контента',
        'workgroups': '👥 Рабочие группы контента',
    },
    'Коммерческий отдел': {
        'data': '📥 Загруженные данные КАМ',
        'workgroups': '👥 Рабочие группы КАМ',
    },
}

COLUMNS = [
    'ID',                      # A - Номер по-порядку
    'Внешний код',             # B - Внешний код (из файла)
    'Группа 3',                # C - Группа 3 (из файла)
    'Наименование',            # D - Наименование (из файла)
    'Статус',                  # E - Статус (🆕 Новый)
    'Причина паузы',           # F - Причина паузы
    'Дата паузы',              # G - Дата паузы
    'Исполнитель',             # H - Исполнитель
    'Дата взятия',             # I - Дата взятия
    'Дата выполнения',         # J - Дата выполнения
    'Дата завершения работы',  # K - Дата завершения работы
    'Источник',                # L - Источник (название файла)
    'Дата загрузки',           # M - Дата загрузки (время загрузки)
]

CONTACTS_SHEET_NAME = '📇 Контакты поставщиков'
CONTACT_COLUMNS = [
    'Производитель',
    'Оф.сайт',
    'Контакт',
    'Имя',
    'Группы товаров',
    'Примечание',
]

NEW_PRODUCTS_SHEET_NAME = 'Новые товары'
MANAGERS_SHEET_NAME = 'Менеджеры'

NEW_PRODUCTS_COLUMNS = [
    'Внешний код',
    'Наименование',
    'Дата создания',
    'Цифровой код менеджера (служебное св-во) [MAIN_MNG_CODE]',
    'Название раздела',
    'Менеджер',
    'Контент',
]

TASKS_SHEET_NAME = '🎯 Задачи'
TASK_COLUMNS = [
    'ID',
    'Тема',
    'Описание',
    'Исполнители',
    'Статус',
    'Срочность',
    'Изображения Base64',
    'Дата создания',
    'Дата обновления',
]

MONTH_NAMES = {
    1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
    5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
    9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь',
}


@st.cache_resource
def get_gspread_client():
  scopes = ['https://www.googleapis.com/auth/spreadsheets']
  creds_dict = dict(st.secrets['gcp_service_account'])
  creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
  return gspread.authorize(creds)


def load_dept_data(sheet_name):
  """Загрузка данных из Google Таблицы с устранением дубликатов колонок."""
  try:
    gc = get_gspread_client()
    sh = gc.open_by_url(SPREADSHEET_URL)
    worksheet = sh.worksheet(sheet_name)
    vals = worksheet.get_all_values()

    if len(vals) > 1:
      headers = [str(h).strip() for h in vals[0]]
      df = pd.DataFrame(vals[1:], columns=headers).astype(str)
      df = df.loc[:, ~df.columns.duplicated()].copy()
      df = df.replace({'nan': '', 'NaN': '', 'None': '', '<NA>': '', 'NaT': ''})
      for col in COLUMNS:
        if col not in df.columns:
          df[col] = ''
      return df[COLUMNS]
    return pd.DataFrame(columns=COLUMNS)
  except Exception as e:
    st.error(f'Ошибка загрузки листа {sheet_name}: {e}')
    return pd.DataFrame(columns=COLUMNS)


def save_dept_data(dept_info, df):
  """Сохранение данных и автоматическая сквозная нумерация (ID / № п/п)."""
  data_sheet_name = dept_info['data']
  workgroup_sheet_name = dept_info['workgroups']

  try:
    gc = get_gspread_client()
    sh = gc.open_by_url(SPREADSHEET_URL)

    try:
      worksheet = sh.worksheet(data_sheet_name)
      existing_vals = worksheet.get_all_values()
    except gspread.WorksheetNotFound:
      worksheet = sh.add_worksheet(title=data_sheet_name, rows='2000', cols='25')
      existing_vals = []

    if existing_vals and len(existing_vals) > 1:
      old_headers = [str(h).strip() for h in existing_vals[0]]
      old_data_df = pd.DataFrame(existing_vals[1:], columns=old_headers).astype(str)
      old_data_df = old_data_df.loc[:, ~old_data_df.columns.duplicated()].copy()

      for col in COLUMNS:
        if col not in old_data_df.columns:
          old_data_df[col] = ''
        if col not in df.columns:
          df[col] = ''

      updated_sources = df['Источник'].replace('', np.nan).dropna().unique()
      old_sources = old_data_df['Источник'].replace('', np.nan).fillna('')

      old_filtered = old_data_df[~old_sources.isin(updated_sources)]
      full_df = pd.concat([old_filtered[COLUMNS], df[COLUMNS]], ignore_index=True)
    else:
      full_df = df[COLUMNS].copy()

    full_df = full_df.fillna('').astype(str)
    full_df['ID'] = [str(i + 1) for i in range(len(full_df))]

    data_to_write = [COLUMNS] + full_df.values.tolist()

    worksheet.clear()
    worksheet.update(range_name='A1', values=data_to_write)

    try:
      try:
        wg_worksheet = sh.worksheet(workgroup_sheet_name)
      except gspread.WorksheetNotFound:
        wg_worksheet = sh.add_worksheet(title=workgroup_sheet_name, rows='1000', cols='20')

      full_summary_df = build_summary(full_df)

      if not full_summary_df.empty:
        wg_data = [full_summary_df.columns.tolist()] + (
            full_summary_df.fillna('').astype(str).values.tolist()
        )
        wg_worksheet.clear()
        wg_worksheet.update(range_name='A1', values=wg_data)

    except Exception as wg_err:
      st.warning(f"Основные данные сохранены, но не обновлен лист '{workgroup_sheet_name}': {wg_err}")

    return True
  except Exception as e:
    st.error(f'Ошибка сохранения: {e}')
    return False


def load_contacts_data():
  try:
    gc = get_gspread_client()
    sh = gc.open_by_url(SPREADSHEET_URL)
    try:
      worksheet = sh.worksheet(CONTACTS_SHEET_NAME)
    except gspread.WorksheetNotFound:
      worksheet = sh.add_worksheet(title=CONTACTS_SHEET_NAME, rows='1000', cols='10')
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
    st.error(f'Ошибка загрузки контактов: {e}')
    return pd.DataFrame(columns=CONTACT_COLUMNS)


def add_contact_row(new_row_dict):
  try:
    gc = get_gspread_client()
    sh = gc.open_by_url(SPREADSHEET_URL)
    try:
      worksheet = sh.worksheet(CONTACTS_SHEET_NAME)
    except gspread.WorksheetNotFound:
      worksheet = sh.add_worksheet(title=CONTACTS_SHEET_NAME, rows='1000', cols='10')
      worksheet.append_row(CONTACT_COLUMNS)

    row_values = [str(new_row_dict.get(col, '')).strip() for col in CONTACT_COLUMNS]
    worksheet.append_row(row_values)
    return True
  except Exception as e:
    st.error(f'Ошибка сохранения контакта: {e}')
    return False


def load_managers_mapping():
  """Загрузка маппинга менеджеров и их цифровых кодов из листа 'Менеджеры'."""
  try:
    gc = get_gspread_client()
    sh = gc.open_by_url(SPREADSHEET_URL)
    try:
      ws = sh.worksheet(MANAGERS_SHEET_NAME)
      records = ws.get_all_records()
      mapping_code = {}
      mapping_name = {}
      for r in records:
        m_name = str(r.get('Менеджер', '') or r.get('ФИО', '')).strip()
        m_code = str(r.get('Цифровой код', '') or r.get('Код', '') or r.get('MAIN_MNG_CODE', '')).strip()
        if m_name and m_code:
          mapping_code[m_name.lower()] = m_code
          mapping_name[m_code] = m_name
      return mapping_code, mapping_name
    except Exception:
      return {}, {}
  except Exception:
    return {}, {}


def load_raw_new_products():
  try:
    gc = get_gspread_client()
    sh = gc.open_by_url(SPREADSHEET_URL)
    try:
      worksheet = sh.worksheet(NEW_PRODUCTS_SHEET_NAME)
    except gspread.WorksheetNotFound:
      worksheet = sh.add_worksheet(title=NEW_PRODUCTS_SHEET_NAME, rows='1000', cols='10')
      worksheet.append_row(NEW_PRODUCTS_COLUMNS)
      return []

    return worksheet.get_all_values()
  except Exception as e:
    st.error(f"Ошибка загрузки листа 'Новые товары': {e}")
    return []


def parse_new_products_by_batches():
  raw_data = load_raw_new_products()
  if not raw_data:
    return {}

  batches = {}
  current_date = 'Без даты'
  current_rows = []
  header = NEW_PRODUCTS_COLUMNS

  for row in raw_data[1:]:
    if not row or not any(row):
      continue

    first_cell = str(row[0]).strip()
    if '📅 Загрузка от' in first_cell:
      if current_rows:
        df_batch = pd.DataFrame(current_rows, columns=header)
        batches[current_date] = df_batch
        current_rows = []
      current_date = first_cell.replace('📅 Загрузка от', '').strip()
    else:
      padded_row = row + [''] * (len(header) - len(row))
      current_rows.append(padded_row[: len(header)])

  if current_rows:
    df_batch = pd.DataFrame(current_rows, columns=header)
    batches[current_date] = df_batch

  return batches


def map_excel_columns(uploaded_df):
  """Разбор столбцов из Excel с фильтрацией пустых строк по первому столбцу и удалением .0."""
  uploaded_df = uploaded_df.loc[:, ~uploaded_df.columns.duplicated()].copy()

  if not uploaded_df.empty and len(uploaded_df.columns) > 0:
    first_col_str = uploaded_df.iloc[:, 0].astype(str).str.strip().str.lower()
    uploaded_df = uploaded_df[
        ~first_col_str.isin(['', 'nan', 'none', '<na>', 'nat', 'null'])
        & uploaded_df.iloc[:, 0].notna()
    ].copy()

  cols = list(uploaded_df.columns)

  def get_column_values(keywords, default_idx=None, clean_code=False):
    series = None
    for idx, c in enumerate(cols):
      c_str = str(c).strip().lower()
      if any(k in c_str for k in keywords):
        series = uploaded_df.iloc[:, idx]
        break
    
    if series is None and default_idx is not None and len(cols) > default_idx:
      series = uploaded_df.iloc[:, default_idx]

    if series is None:
      return [""] * len(uploaded_df)

    res = series.astype(str).str.strip()
    if clean_code:
      res = res.str.replace(r'\.0$', '', regex=True)

    return res.values

  return {
      'Внешний код': get_column_values(['внешний', 'артикул', 'код товара', 'идентификатор', 'код'], default_idx=0, clean_code=True),
      'Группа 3': get_column_values(['группа 3', 'раздел', 'категория', 'группа'], default_idx=None),
      'Наименование': get_column_values(['наименование', 'название', 'номенклатура', 'товар'], default_idx=1),
      'Менеджер': get_column_values(['менеджер', 'ответственный', 'кам', 'фио'], default_idx=None),
      'Код менеджера': get_column_values(['цифровой код', 'код менеджера', 'main_mng_code'], default_idx=None, clean_code=True),
  }


def append_new_products_batch(uploaded_files, progress_bar=None, status_text=None):
  try:
    gc = get_gspread_client()
    sh = gc.open_by_url(SPREADSHEET_URL)
    try:
      worksheet = sh.worksheet(NEW_PRODUCTS_SHEET_NAME)
    except gspread.WorksheetNotFound:
      worksheet = sh.add_worksheet(title=NEW_PRODUCTS_SHEET_NAME, rows='1000', cols='10')
      worksheet.append_row(NEW_PRODUCTS_COLUMNS)

    now_dt = datetime.datetime.now()
    now_str = now_dt.strftime('%d.%m.%Y %H:%M')
    today_date_str = now_dt.strftime('%d.%m.%Y')

    mng_map_code, mng_map_name = load_managers_mapping()

    all_rows_to_append = []
    total_files = len(uploaded_files)

    for idx, u_file in enumerate(uploaded_files):
      if status_text:
        status_text.info(f'Чтение файла {idx + 1} из {total_files}: **{u_file.name}**')

      u_file.seek(0)
      raw_df = pd.read_excel(u_file, dtype=str)
      mapped_data = map_excel_columns(raw_df)

      managers_input = mapped_data.get('Менеджер', [""] * len(raw_df))
      codes_input = mapped_data.get('Код менеджера', [""] * len(raw_df))

      final_mng_codes = []
      final_managers = []

      for m_val, c_val in zip(managers_input, codes_input):
        m_str = str(m_val).strip()
        c_str = str(c_val).strip()

        if c_str and not m_str:
          m_str = mng_map_name.get(c_str, "")
        elif m_str and not c_str:
          c_str = mng_map_code.get(m_str.lower(), "")

        final_managers.append(m_str)
        final_mng_codes.append(c_str)

      formatted_df = pd.DataFrame({
          'Внешний код': mapped_data['Внешний код'],
          'Наименование': mapped_data['Наименование'],
          'Дата создания': today_date_str,
          'Цифровой код менеджера (служебное св-во) [MAIN_MNG_CODE]': final_mng_codes,
          'Название раздела': mapped_data['Группа 3'],
          'Менеджер': final_managers,
          'Контент': '',
      })

      formatted_df = formatted_df.astype(str).replace({'nan': '', 'NaN': '', 'None': '', '<NA>': '', 'NaT': ''})
      formatted_df = formatted_df[NEW_PRODUCTS_COLUMNS]

      if not formatted_df.empty:
        date_header_row = [f'📅 Загрузка от {now_str} ({u_file.name})'] + [''] * (len(NEW_PRODUCTS_COLUMNS) - 1)
        all_rows_to_append.append(date_header_row)
        all_rows_to_append.extend(formatted_df.values.tolist())

      if progress_bar:
        progress_bar.progress(int(((idx + 1) / total_files) * 75))

    if all_rows_to_append:
      if status_text:
        status_text.info('Запись данных в Google Таблицу...')
      worksheet.append_rows(all_rows_to_append)
      if progress_bar:
        progress_bar.progress(100)

    return True
  except Exception as e:
    st.error(f'Ошибка сохранения новых товаров: {e}')
    return False


# ==========================================
# 2. РАБОТА С ЛИСТОМ ЗАДАЧ
# ==========================================
def load_tasks_data():
  """Загрузка списка задач из Google Таблицы."""
  try:
    gc = get_gspread_client()
    sh = gc.open_by_url(SPREADSHEET_URL)
    try:
      worksheet = sh.worksheet(TASKS_SHEET_NAME)
    except gspread.WorksheetNotFound:
      worksheet = sh.add_worksheet(title=TASKS_SHEET_NAME, rows='1000', cols='15')
      worksheet.append_row(TASK_COLUMNS)
      return pd.DataFrame(columns=TASK_COLUMNS)

    vals = worksheet.get_all_values()
    if len(vals) > 1:
      headers = [str(h).strip() for h in vals[0]]
      df = pd.DataFrame(vals[1:], columns=headers).astype(str)
      df = df.replace({'nan': '', 'NaN': '', 'None': '', '<NA>': '', 'NaT': ''})
      for col in TASK_COLUMNS:
        if col not in df.columns:
          df[col] = ''
      return df[TASK_COLUMNS]
    return pd.DataFrame(columns=TASK_COLUMNS)
  except Exception as e:
    st.error(f'Ошибка загрузки задач: {e}')
    return pd.DataFrame(columns=TASK_COLUMNS)


def save_all_tasks(df):
  """Сохранение и перезапись списка задач."""
  try:
    gc = get_gspread_client()
    sh = gc.open_by_url(SPREADSHEET_URL)
    try:
      worksheet = sh.worksheet(TASKS_SHEET_NAME)
    except gspread.WorksheetNotFound:
      worksheet = sh.add_worksheet(title=TASKS_SHEET_NAME, rows='1000', cols='15')

    df_to_save = df[TASK_COLUMNS].fillna('').astype(str)
    data_to_write = [TASK_COLUMNS] + df_to_save.values.tolist()

    worksheet.clear()
    worksheet.update(range_name='A1', values=data_to_write)
    return True
  except Exception as e:
    st.error(f'Ошибка сохранения списка задач: {e}')
    return False


# ==========================================
# 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ И СВОДКА
# ==========================================
def calculate_business_days(date_str):
  if not date_str or str(date_str).lower() in ['nan', 'none', '']:
    return 0
  try:
    clean_date_str = str(date_str).split(' ')[0]
    start_date = datetime.datetime.strptime(clean_date_str, '%d.%m.%Y').date()
    today = datetime.date.today()
    if start_date >= today:
      return 0
    return int(np.busday_count(start_date, today))
  except Exception:
    return 0


def build_summary(df):
  if df.empty:
    return pd.DataFrame()

  temp_df = df.copy()

  if 'Источник' in temp_df.columns:
    source_series = temp_df['Источник'].astype(str).str.strip()
  else:
    source_series = pd.Series('Без названия', index=temp_df.index)

  group_keys = source_series.replace('', 'Без названия').fillna('Без названия')
  temp_df['Группа_Ключ'] = group_keys

  summary_rows = []
  grouped = temp_df.groupby('Группа_Ключ', sort=False)

  for group_name, group in grouped:
    total = len(group)
    first_row = group.iloc[0]

    def get_clean_val(col_names):
      for c in col_names:
        if c in group.columns:
          s = group[c].astype(str).str.strip()
          valid = s[~s.isin(['', 'nan', 'NaN', 'None', '<NA>', 'NaT'])]
          if not valid.empty:
            return valid.iloc[0]
      return ''

    st_val = str(first_row.get('Статус', '')).strip().lower()

    date_done = get_clean_val(['Дата завершения работы', 'Дата выполнения'])
    date_take = get_clean_val(['Дата взятия'])
    pause_reason = get_clean_val(['Причина паузы', 'Причина'])
    date_pause = get_clean_val(['Дата паузы'])
    date_added = get_clean_val(['Дата загрузки'])

    is_completed = st_val in ['выполнено', 'выполнен', 'завершен', '✅ выполнен', '✅ завершена']
    is_paused = st_val in ['пауза', 'на паузе', '⏸️ на паузе'] or '⏸' in st_val
    is_in_work = st_val in ['в работе', 'взято в работу', '🔄 в работе'] or (bool(date_take) and not is_completed and not is_paused)

    if is_completed:
      done_cnt, in_work_cnt, new_cnt, group_status = total, 0, 0, '✅ Выполнен'
    elif is_paused:
      done_cnt, in_work_cnt, new_cnt, group_status = 0, 0, total, '⏸️ На паузе'
    elif is_in_work:
      done_cnt, in_work_cnt, new_cnt, group_status = 0, total, 0, '🔄 В работе'
    else:
      done_cnt, in_work_cnt, new_cnt, group_status = 0, 0, total, '🆕 Новый'

    days_passed = calculate_business_days(date_added)

    summary_rows.append({
        'Имя файла': group_name,
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
        'Дней с добавления': days_passed,
    })

  return pd.DataFrame(summary_rows)


def render_grouped_html_table(df, group_col, cols_order, headers):
  if df.empty:
    return ''

  html = """
    <div class="custom-table-container">
    <table class="custom-table"><thead><tr>
    """
  for h in headers:
    html += f'<th>{h}</th>'
  html += '</tr></thead><tbody>'

  seen = set()
  unique_ordered = [x for x in df[group_col] if not (x in seen or seen.add(x))]

  for val in unique_ordered:
    sub_df = df[df[group_col] == val]
    rowspan = len(sub_df)
    first_row = True

    for _, row in sub_df.iterrows():
      html += '<tr>'
      if first_row:
        html += f"<td rowspan='{rowspan}' class='grouped-cell'>{row[group_col]}</td>"
        first_row = False

      for col in cols_order:
        if col != group_col:
          html += f'<td>{row[col]}</td>'
      html += '</tr>'

  html += '</tbody></table></div>'
  return html


def render_executor_bubbles(executors_str):
  """Форматирует строку с исполнителями в HTML-баблы."""
  if not executors_str or not executors_str.strip():
    return "<span style='color: #888;'>Не назначены</span>"
  
  names = [n.strip() for n in executors_str.split(',') if n.strip()]
  bubbles_html = "".join([f"<span class='executor-bubble'>👤 {name}</span>" for name in names])
  return f"<div class='executors-container'>{bubbles_html}</div>"


# ==========================================
# 4. МОДАЛЬНЫЕ ОКНА (DIALOGS)
# ==========================================

@st.dialog('▶️ Взять файлы в работу')
def modal_take_in_work(dept_info, summary_df, df):
  new_df = summary_df[summary_df['Статус группы'] == '🆕 Новый']
  if new_df.empty:
    st.info('Нет новых файлов для взятия в работу.')
    return

  st.write('Выберите новые файлы:')
  selected_files = []

  with st.container(height=350):
    for _, row in new_df.iterrows():
      filename = row['Имя файла']
      count = row['Количество товаров']
      if st.checkbox(f'{filename} — {count} SKU', key=f'chk_new_{filename}'):
        selected_files.append(filename)

  executor_name = st.text_input('Имя исполнителя:')

  if st.button('В работу'):
    if not selected_files:
      st.warning('Отметьте хотя бы один файл!')
    elif not executor_name.strip():
      st.warning('Укажите имя исполнителя!')
    else:
      now_str = datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')
      mask = df['Источник'].isin(selected_files)

      df.loc[mask, 'Статус'] = 'В работе'
      df.loc[mask, 'Исполнитель'] = executor_name.strip()
      df.loc[mask, 'Дата взятия'] = now_str
      df.loc[mask, 'Дата завершения работы'] = ''
      df.loc[mask, 'Дата выполнения'] = ''
      df.loc[mask, 'Причина паузы'] = ''
      df.loc[mask, 'Дата паузы'] = ''

      if save_dept_data(dept_info, df):
        st.success("Статус обновлен на 'В работе'")
        st.rerun()


@st.dialog('⏸️ Поставить файлы на паузу')
def modal_pause(dept_info, summary_df, df):
  in_work_df = summary_df[summary_df['Статус группы'] == '🔄 В работе']
  if in_work_df.empty:
    st.info('Нет файлов в работе для отправки на паузу.')
    return

  st.write('Выберите файлы в работе:')
  selected_files = []

  with st.container(height=350):
    for _, row in in_work_df.iterrows():
      filename = row['Имя файла']
      count = row['Количество товаров']
      if st.checkbox(f'{filename} — {count} SKU', key=f'chk_work_{filename}'):
        selected_files.append(filename)

  pause_reason = st.selectbox(
      'Укажите причину паузы:',
      options=['информация уточняется', 'запрошено у поставщика'],
  )

  if st.button('Поставить на паузу'):
    if not selected_files:
      st.warning('Отметьте хотя бы один файл!')
    else:
      now_str = datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')
      mask = df['Источник'].isin(selected_files)

      df.loc[mask, 'Статус'] = 'Пауза'
      df.loc[mask, 'Причина паузы'] = pause_reason
      df.loc[mask, 'Дата паузы'] = now_str

      if save_dept_data(dept_info, df):
        st.success('Файлы переведены на паузу!')
        st.rerun()


@st.dialog('▶️ Снять файлы с паузы')
def modal_unpause(dept_info, summary_df, df):
  paused_df = summary_df[summary_df['Статус группы'] == '⏸️ На паузе']
  if paused_df.empty:
    st.info('Нет файлов на паузе.')
    return

  st.write('Выберите файлы для возобновления работы:')
  selected_files = []

  with st.container(height=350):
    for _, row in paused_df.iterrows():
      filename = row['Имя файла']
      count = row['Количество товаров']
      if st.checkbox(f'{filename} — {count} SKU', key=f'chk_unpause_{filename}'):
        selected_files.append(filename)

  if st.button('Вернуть в работу'):
    if not selected_files:
      st.warning('Отметьте хотя бы один файл!')
    else:
      mask = df['Источник'].isin(selected_files)

      df.loc[mask, 'Статус'] = 'В работе'
      df.loc[mask, 'Причина паузы'] = ''
      df.loc[mask, 'Дата паузы'] = ''

      if save_dept_data(dept_info, df):
        st.success('Файлы успешно возвращены в работу!')
        st.rerun()


@st.dialog('✅ Завершить работу по файлам')
def modal_complete(dept_info, summary_df, df):
  in_work_df = summary_df[summary_df['Статус группы'] == '🔄 В работе']
  if in_work_df.empty:
    st.info('Нет файлов в работе для завершения.')
    return

  st.write('Выберите файлы в работе для завершения:')
  selected_files = []

  with st.container(height=350):
    for _, row in in_work_df.iterrows():
      filename = row['Имя файла']
      count = row['Количество товаров']
      if st.checkbox(f'{filename} — {count} SKU', key=f'chk_comp_{filename}'):
        selected_files.append(filename)

  if st.button('Завершить'):
    if not selected_files:
      st.warning('Отметьте хотя бы один файл!')
    else:
      now_str = datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')
      mask = df['Источник'].isin(selected_files)

      df.loc[mask, 'Статус'] = 'Выполнено'
      df.loc[mask, 'Дата завершения работы'] = now_str
      df.loc[mask, 'Дата выполнения'] = now_str

      if save_dept_data(dept_info, df):
        st.success("Статус обновлен на 'Выполнено'")
        st.rerun()


@st.dialog('📊 Аналитика и статистика')
def modal_analytics():
  with st.spinner('Сбор статистики...'):
    df_content = load_dept_data(SHEET_MAP['Отдел контента']['data'])
    df_comm = load_dept_data(SHEET_MAP['Коммерческий отдел']['data'])

    summary_content = build_summary(df_content)
    summary_comm = build_summary(df_comm)

    with st.container(height=650):
      new_content_sku = (
          summary_content[summary_content['Статус группы'] == '🆕 Новый']['Количество товаров'].sum()
          if not summary_content.empty else 0
      )
      new_comm_sku = (
          summary_comm[summary_comm['Статус группы'] == '🆕 Новый']['Количество товаров'].sum()
          if not summary_comm.empty else 0
      )

      st.markdown("<h4 style='font-weight: 500; font-size: 1.05rem; margin-bottom: 12px;'>🆕 Новые SKU на добавление</h4>", unsafe_allow_html=True)
      
      c1, c2, c3 = st.columns(3)
      c1.metric('Отдел контента', f'{new_content_sku} SKU')
      c2.metric('Коммерческий отдел', f'{new_comm_sku} SKU')
      c3.metric('Всего новых SKU', f'{new_content_sku + new_comm_sku} SKU')

      st.divider()

      all_work = []
      if not summary_content.empty:
        cw = summary_content[summary_content['Статус группы'] == '🔄 В работе'].copy()
        if not cw.empty:
          cw['Отдел'] = 'Отдел контента'
          all_work.append(cw)

      if not summary_comm.empty:
        kw = summary_comm[summary_comm['Статус группы'] == '🔄 В работе'].copy()
        if not kw.empty:
          kw['Отдел'] = 'Коммерческий отдел'
          all_work.append(kw)

      st.markdown("<h4 style='font-weight: 500; font-size: 1.05rem; margin-bottom: 12px;'>⚙️ SKU в работе по исполнителям</h4>", unsafe_allow_html=True)

      if all_work:
        df_work_all = pd.concat(all_work, ignore_index=True)
        exec_summary = (
            df_work_all.groupby(['Исполнитель', 'Отдел'])['Количество товаров']
            .sum()
            .reset_index()
            .rename(columns={'Количество товаров': 'SKU в работе'})
        )
        exec_summary = exec_summary[exec_summary['Исполнитель'].str.strip() != '']

        if not exec_summary.empty:
          html_table_work = render_grouped_html_table(
              exec_summary,
              group_col='Исполнитель',
              cols_order=['Исполнитель', 'Отдел', 'SKU в работе'],
              headers=['Исполнитель', 'Отдел', 'SKU в работе'],
          )
          st.markdown(html_table_work, unsafe_allow_html=True)
        else:
          st.info('В данный момент нет SKU в работе.')
      else:
        st.info('Данные отсутствуют.')


@st.dialog('📇 Контакты поставщиков')
def modal_contacts():
  with st.expander('➕ Добавить новый контакт поставщика', expanded=False):
    with st.form('add_contact_form', clear_on_submit=True):
      f_col1, f_col2, f_col3, f_col4, f_col5, f_col6 = st.columns([1.2, 1.2, 1.2, 1.2, 1.5, 2.0])
      with f_col1:
        producer = st.text_input('Производитель', placeholder='Название')
      with f_col2:
        site = st.text_input('Оф.сайт', placeholder='URL / сайт')
      with f_col3:
        contact_info = st.text_input('Контакт', placeholder='Тел / Email')
      with f_col4:
        name = st.text_input('Имя', placeholder='Контактное лицо')
      with f_col5:
        product_groups = st.text_input('Группы товаров', placeholder='Перечень')
      with f_col6:
        note = st.text_input('Примечание', placeholder='Заметки')

      submit_contact = st.form_submit_button('💾 Сохранить контакт', use_container_width=True)

      if submit_contact:
        if not producer.strip():
          st.warning('Укажите наименование производителя!')
        else:
          new_contact_data = {
              'Производитель': producer.strip(),
              'Оф.сайт': site.strip(),
              'Контакт': contact_info.strip(),
              'Имя': name.strip(),
              'Группы товаров': product_groups.strip(),
              'Примечание': note.strip(),
          }
          if add_contact_row(new_contact_data):
            st.success('Контакт успешно сохранен!')
            st.rerun()

  st.divider()

  contacts_df = load_contacts_data()
  if not contacts_df.empty:
    search_q = st.text_input('🔍 Поиск по контактам:', placeholder='Введите производителя, имя или категорию...').strip().lower()
    if search_q:
      mask = contacts_df.apply(lambda r: r.astype(str).str.lower().str.contains(search_q).any(), axis=1)
      filtered_contacts = contacts_df[mask]
    else:
      filtered_contacts = contacts_df

    st.dataframe(filtered_contacts, use_container_width=True, hide_index=True)
  else:
    st.info('База контактов пока пуста.')


@st.dialog('📦 Новые товары')
def modal_new_products():
  tab_upload, tab_view, tab_summary = st.tabs([
      '📥 Загрузить партии из Excel',
      '📋 Просмотр загруженных партий',
      '📊 Сводная (Менеджер + Название раздела)'
  ])

  with tab_upload:
    st.subheader('Загрузка Excel-файлов')
    uploaded_files = st.file_uploader(
        'Выберите один или несколько Excel файлов:',
        type=['xlsx', 'xls'],
        accept_multiple_files=True,
    )

    if uploaded_files:
      st.info(f'Выбрано файлов: {len(uploaded_files)}')
      if st.button('💾 Добавить товары в таблицу', type='primary'):
        prog_bar = st.progress(0)
        stat_text = st.empty()

        success = append_new_products_batch(uploaded_files, prog_bar, stat_text)
        if success:
          stat_text.empty()
          prog_bar.empty()
          st.success('Все партии успешно добавлены в лист "Новые товары"!')
          st.rerun()

  with tab_view:
    batches = parse_new_products_by_batches()
    if not batches:
      st.info('Нет загруженных партий новых товаров.')
    else:
      selected_batch_date = st.selectbox('Выберите партию для просмотра:', options=list(batches.keys()))
      if selected_batch_date:
        batch_df = batches[selected_batch_date]
        st.write(f'Всего SKU в партии: **{len(batch_df)}**')
        st.dataframe(batch_df, use_container_width=True, hide_index=True)

  with tab_summary:
    st.subheader('📊 Сводная аналитика: Менеджер + Название раздела (по датам)')
    
    batches = parse_new_products_by_batches()
    if not batches:
      st.info('Нет загруженных товаров для формирования сводной таблицы.')
    else:
      all_batches_list = []
      for b_name, b_df in batches.items():
        temp_df = b_df.copy()
        temp_df['Партия'] = b_name
        all_batches_list.append(temp_df)
      
      full_new_df = pd.concat(all_batches_list, ignore_index=True)
      
      col_mng = 'Менеджер'
      col_sec = 'Название раздела'
      col_date = 'Дата создания'
      
      full_new_df[col_mng] = full_new_df[col_mng].replace({'': 'Не указан'})
      full_new_df[col_sec] = full_new_df[col_sec].replace({'': 'Не указан'})
      full_new_df[col_date] = full_new_df[col_date].replace({'': 'Без даты'})

      c_f1, c_f2 = st.columns(2)
      with c_f1:
        mng_list = sorted(full_new_df[col_mng].unique().tolist())
        sel_mngs = st.multiselect('Фильтр по менеджерам:', options=mng_list, default=mng_list)
      with c_f2:
        dates_list = sorted(full_new_df[col_date].unique().tolist())
        sel_dates = st.multiselect('Фильтр по датам создания:', options=dates_list, default=dates_list)

      filtered_summary_df = full_new_df[
          (full_new_df[col_mng].isin(sel_mngs)) & 
          (full_new_df[col_date].isin(sel_dates))
      ]

      if not filtered_summary_df.empty:
        pivot_df = pd.pivot_table(
            filtered_summary_df,
            index=[col_mng, col_sec],
            columns=[col_date],
            values='Внешний код',
            aggfunc='count',
            fill_value=0
        )
        
        pivot_df['Итого'] = pivot_df.sum(axis=1)
        st.dataframe(pivot_df, use_container_width=True)
      else:
        st.info('По выбранным фильтрам данные отсутствуют.')


# ==========================================
# 5. ОСНОВНОЙ ИНТЕРФЕЙС ПРИЛОЖЕНИЯ
# ==========================================
def main():
  st.markdown("<h1 class='custom-header'>📋 Панель управления обработкой файлов</h1>", unsafe_allow_html=True)

  main_tab1, main_tab2 = st.tabs(['🗂️ Обработка файлов по отделам', '🎯 Центр Задач'])

  with main_tab1:
    dept = st.radio(
        'Выберите отдел:',
        options=list(SHEET_MAP.keys()),
        horizontal=True,
        key='radio_dept_select',
    )

    dept_info = SHEET_MAP[dept]

    with st.spinner(f'Загрузка данных ({dept})...'):
      df = load_dept_data(dept_info['data'])
      summary_df = build_summary(df)

    st.subheader('⚡ Управление файлами')

    col_actions, col_extra = st.columns([1.5, 1.0])

    with col_actions:
      st.subheader('1-2. Операции с файлами')
      st.write('Изменение статусов выбранных файлов:')

      btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)

      if btn_col1.button('▶️ В работу', use_container_width=True):
        modal_take_in_work(dept_info, summary_df, df)

      if btn_col2.button('⏸️ На паузу', use_container_width=True):
        modal_pause(dept_info, summary_df, df)

      if btn_col3.button('▶️ Снять с паузы', use_container_width=True):
        modal_unpause(dept_info, summary_df, df)

      if btn_col4.button('✅ Завершить', use_container_width=True):
        modal_complete(dept_info, summary_df, df)

    with col_extra:
      st.subheader('3. Дополнительная информация')
      st.write('Просмотр отчетов, контактов и выгрузок:')

      btn_ex1, btn_ex2, btn_ex3 = st.columns(3)

      if btn_ex1.button('📊 Аналитика', use_container_width=True):
        modal_analytics()

      if btn_ex2.button('📇 Контакты', use_container_width=True):
        modal_contacts()

      if btn_ex3.button('📦 Новые товары', use_container_width=True):
        modal_new_products()

    st.divider()

    # РЕЕСТР АКТИВНЫХ И ЗАВЕРШЕННЫХ ГРУПП
    if summary_df.empty:
      st.info('Нет данных для отображения')
    else:
      st.subheader(f'📋 Реестр групп — {dept.upper()}')

      new_df = summary_df[summary_df['Статус группы'] == '🆕 Новый'].copy().reset_index(drop=True)
      paused_df = summary_df[summary_df['Статус группы'] == '⏸️ На паузе'].copy().reset_index(drop=True)
      work_df = summary_df[summary_df['Статус группы'] == '🔄 В работе'].copy().reset_index(drop=True)
      completed_summary = summary_df[summary_df['Статус группы'] == '✅ Выполнен'].copy().reset_index(drop=True)

      tab_new, tab_paused, tab_work = st.tabs([
          f'🆕 Новые ({len(new_df)})',
          f'⏸️ На паузе ({len(paused_df)})',
          f'🔄 В работе ({len(work_df)})',
      ])

      with tab_new:
        if new_df.empty:
          st.info('Нет новых файлов.')
        else:
          cols_show = ['Имя файла', 'Группа 3', 'Количество товаров', 'Дата добавления', 'Дней с добавления']
          st.dataframe(new_df[cols_show], use_container_width=True, hide_index=True)

      with tab_paused:
        if paused_df.empty:
          st.info('Нет файлов на паузе.')
        else:
          cols_show = ['Имя файла', 'Группа 3', 'Количество товаров', 'Причина паузы', 'Дата паузы', 'Исполнитель']
          st.dataframe(paused_df[cols_show], use_container_width=True, hide_index=True)

      with tab_work:
        if work_df.empty:
          st.info('Нет файлов в работе.')
        else:
          cols_show = ['Имя файла', 'Группа 3', 'Количество товаров', 'Исполнитель', 'Дата начала работы']
          st.dataframe(work_df[cols_show], use_container_width=True, hide_index=True)

      st.divider()

      with st.expander(f'✅ Выполненные файлы ({len(completed_summary)})', expanded=False):
        if completed_summary.empty:
          st.info('Нет выполненных файлов.')
        else:
          cols_show = ['Имя файла', 'Группа 3', 'Количество товаров', 'Исполнитель', 'Дата начала работы', 'Дата завершения работы']
          st.dataframe(completed_summary[cols_show], use_container_width=True, hide_index=True)

  with main_tab2:
    st.subheader('🎯 Центр управления задачами')

    tasks_df = load_tasks_data()

    with st.expander('➕ Создать новую задачу', expanded=False):
      with st.form('create_task_form', clear_on_submit=True):
        t_title = st.text_input('Тема задачи *')
        t_desc = st.text_area('Описание задачи')
        t_execs = st.text_input('Исполнители (через запятую)')
        t_urgency = st.selectbox('Срочность', options=['Обычная', 'Срочно'])
        
        uploaded_imgs = st.file_uploader('Прикрепить изображения', type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

        submit_task = st.form_submit_button('💾 Сохранить задачу')

        if submit_task:
          if not t_title.strip():
            st.warning('Заполните тему задачи!')
          else:
            img_b64_list = []
            if uploaded_imgs:
              for img_file in uploaded_imgs:
                bytes_data = img_file.read()
                b64_str = base64.b64encode(bytes_data).decode('utf-8')
                img_b64_list.append(b64_str)

            now_str = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')
            new_id = str(len(tasks_df) + 1)

            new_task_row = {
                'ID': new_id,
                'Тема': t_title.strip(),
                'Описание': t_desc.strip(),
                'Исполнители': t_execs.strip(),
                'Статус': '🆕 Новая',
                'Срочность': t_urgency,
                'Изображения Base64': '||'.join(img_b64_list),
                'Дата создания': now_str,
                'Дата обновления': now_str,
            }

            new_tasks_df = pd.concat([tasks_df, pd.DataFrame([new_task_row])], ignore_index=True)
            if save_all_tasks(new_tasks_df):
              st.success('Задача успешно создана!')
              st.rerun()

    st.divider()

    if tasks_df.empty:
      st.info('Список задач пуст.')
    else:
      new_tasks = tasks_df[tasks_df['Статус'] == '🆕 Новая']
      work_tasks = tasks_df[tasks_df['Статус'] == '🔄 В работе']
      done_tasks = tasks_df[tasks_df['Статус'] == '✅ Завершена']

      t_tab1, t_tab2, t_tab3 = st.tabs([
          f'🆕 Новые ({len(new_tasks)})',
          f'🔄 В работе ({len(work_tasks)})',
          f'✅ Завершенные ({len(done_tasks)})',
      ])

      def render_task_card(row):
        t_id = row['ID']
        t_title = row['Тема']
        t_desc = row['Описание']
        t_execs = row['Исполнители']
        t_status = row['Статус']
        t_urgency = row['Срочность']
        t_img = row['Изображения Base64']
        t_date = row['Дата создания']

        is_urgent = t_urgency == 'Срочно'
        badge_html = f"<span class='urgent-badge'>🔥 {t_urgency}</span>" if is_urgent else f"<span class='normal-badge'>📌 {t_urgency}</span>"
        bubbles_html = render_executor_bubbles(t_execs)

        with st.container(border=True):
          c1, c2 = st.columns([3, 1])
          with c1:
            st.markdown(f"### #{t_id} {t_title}")
            st.markdown(f"**Создана:** {t_date} | {badge_html}", unsafe_allow_html=True)
            st.markdown(f"**Исполнители:**", unsafe_allow_html=True)
            st.markdown(bubbles_html, unsafe_allow_html=True)
            if t_desc:
              st.markdown(f"**Описание:**\n{t_desc}")

            if t_img:
              images = t_img.split('||')
              st.markdown("**Прикрепленные изображения:**")
              img_cols = st.columns(min(len(images), 4))
              for i_idx, img_b64 in enumerate(images):
                if img_b64.strip():
                  with img_cols[i_idx % 4]:
                    st.image(f"data:image/png;base64,{img_b64}")

          with c2:
            st.markdown(f"**Текущий статус:** {t_status}")
            new_status = st.selectbox('Изменить статус:', options=['🆕 Новая', '🔄 В работе', '✅ Завершена'], index=['🆕 Новая', '🔄 В работе', '✅ Завершена'].index(t_status) if t_status in ['🆕 Новая', '🔄 В работе', '✅ Завершена'] else 0, key=f"sel_status_{t_id}")
            
            if new_status != t_status:
              if st.button('Сохранить', key=f"btn_save_st_{t_id}"):
                tasks_df.loc[tasks_df['ID'] == t_id, 'Статус'] = new_status
                tasks_df.loc[tasks_df['ID'] == t_id, 'Дата обновления'] = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')
                if save_all_tasks(tasks_df):
                  st.success('Статус обновлен!')
                  st.rerun()

      with t_tab1:
        if new_tasks.empty:
          st.info('Нет новых задач.')
        else:
          for _, row in new_tasks.iterrows():
            render_task_card(row)

      with t_tab2:
        if work_tasks.empty:
          st.info('Нет задач в работе.')
        else:
          for _, row in work_tasks.iterrows():
            render_task_card(row)

      with t_tab3:
        if done_tasks.empty:
          st.info('Нет завершенных задач.')
        else:
          for _, row in done_tasks.iterrows():
            render_task_card(row)


if __name__ == '__main__':
  main()
