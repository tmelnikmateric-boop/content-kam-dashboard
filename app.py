import base64
import datetime
import gspread
from google.oauth2.service_account import Credentials
import numpy as np
import pandas as pd
import streamlit as st

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
    
    /* Стили для переключателя отделов: слева, размер 0.95rem */
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

    /* 1. ГЛАВНЫЕ ВКТАДКИ (самый верхний блок st.tabs): по центру, размер 1.25rem */
    div[data-testid="stMainBlockContainer"] > div:nth-of-type(1) div[data-testid="stTabs"] [data-baseweb="tab-list"] {
        justify-content: center !important;
        gap: 30px;
    }
    div[data-testid="stMainBlockContainer"] > div:nth-of-type(1) div[data-testid="stTabs"] [data-baseweb="tab"] p {
        font-size: 1.25rem !important;
        font-weight: 600 !important;
    }

    /* 2. ВЛОЖЕННЫЕ ПОДВКЛАДКИ (Новые, В работе, Завершенные): слева, размер 1rem */
    div[data-testid="stTabs"] [data-baseweb="tab-list"] {
        justify-content: flex-start !important;
        gap: 15px;
    }
    div[data-testid="stTabs"] [data-baseweb="tab"] p {
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
    'Исполнитель',             # F - Исполнитель (пустое)
    'Дата взятия',             # G - Дата взятия (пустое)
    'Дата выполнения',         # H - Дата выполнения (пустое)
    'Дата завершения работы',  # I - Дата завершения работы (пустое)
    'Источник',                # J - Источник (название файла)
    'Дата загрузки',           # K - Дата загрузки (время загрузки)
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
    'Цифровой код менеджера',
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

    now_str = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')

    all_rows_to_append = []
    total_files = len(uploaded_files)

    for idx, u_file in enumerate(uploaded_files):
      if status_text:
        status_text.info(f'Чтение файла {idx + 1} из {total_files}: **{u_file.name}**')

      u_file.seek(0)
      raw_df = pd.read_excel(u_file, dtype=str)
      mapped_data = map_excel_columns(raw_df)

      formatted_df = pd.DataFrame({
          'Внешний код': mapped_data['Внешний код'],
          'Наименование': mapped_data['Наименование'],
          'Дата создания': '',
          'Цифровой код менеджера': '',
          'Название раздела': mapped_data['Группа 3'],
          'Менеджер': '',
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

    is_completed = st_val in ['выполнено', 'выполнен', 'завершен', '✅ выполнен', '✅ завершена'] or bool(date_done)
    is_paused = st_val in ['пауза', 'на паузе', '⏸️ на паузе'] or '⏸' in st_val
    is_in_work = not is_completed and not is_paused and (st_val in ['в работе', 'взято в работу', '🔄 в работе'] or bool(date_take))

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
      if 'Причина паузы' in df.columns:
        df.loc[mask, 'Причина паузы'] = pause_reason
      if 'Дата паузы' in df.columns:
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
      if 'Причина паузы' in df.columns:
        df.loc[mask, 'Причина паузы'] = ''
      if 'Дата паузы' in df.columns:
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
    col_m1, col_m2 = st.columns(2)
    col_m1.metric('Отдел контента', f'{new_content_sku} SKU')
    col_m2.metric('Коммерческий отдел', f'{new_comm_sku} SKU')

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
            dt = datetime.datetime.strptime(clean_date, '%d.%m.%Y')
            month_str = f'{MONTH_NAMES[dt.month]} {dt.year}'
            sort_key = dt.strftime('%Y-%m')
            return pd.Series([month_str, sort_key])
          except Exception:
            return pd.Series(['Неизвестно', '9999-99'])
        return pd.Series(['Неизвестно', '9999-99'])

      all_summary[['Месяц', 'Месяц_сорт']] = all_summary.apply(parse_date_and_month, axis=1)
      exec_df = all_summary[all_summary['Исполнитель'].str.strip() != ''].copy()

      if not exec_df.empty:
        perf_df = (
            exec_df.groupby(['Месяц_сорт', 'Месяц', 'Исполнитель'])['Количество товаров']
            .sum().reset_index()
        )
        perf_df.sort_values(by=['Месяц_сорт', 'Исполнитель'], inplace=True)
        perf_df.rename(columns={'Количество товаров': 'Количество SKU'}, inplace=True)

        html_table_perf = render_grouped_html_table(
            df=perf_df,
            group_col='Месяц',
            cols_order=['Месяц', 'Исполнитель', 'Количество SKU'],
            headers=['Месяц', 'Исполнитель', 'Количество SKU'],
        )
        st.markdown(html_table_perf, unsafe_allow_html=True)
      else:
        st.info('Нет данных о выполненных файлах.')

      st.divider()

      st.markdown("<h4 style='font-weight: 500; font-size: 1.05rem; margin-bottom: 12px;'>🔄 В работе на данный момент</h4>", unsafe_allow_html=True)
      in_work_summary = all_summary[all_summary['Статус группы'] == '🔄 В работе'].copy()

      if not in_work_summary.empty:
        work_by_exec = (
            in_work_summary.groupby(['Исполнитель', 'Отдел'])['Количество товаров']
            .sum().reset_index()
        )
        work_by_exec.sort_values(by=['Исполнитель', 'Отдел'], inplace=True)
        work_by_exec.rename(columns={'Количество товаров': 'SKU в работе'}, inplace=True)

        html_table_work = render_grouped_html_table(
            df=work_by_exec,
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
        groups = st.text_input('Группы товаров', placeholder='Категории')
      with f_col6:
        note = st.text_input('Примечание', placeholder='Доп. информация')

      btn_submit = st.form_submit_button('Сохранить контакт', use_container_width=True)

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
              'Примечание': note,
          }
          if add_contact_row(new_contact):
            st.success('Контакт сохранен!')
            st.rerun()

  contacts_df = load_contacts_data()

  col_search, _ = st.columns([2, 1])
  with col_search:
    search_query = st.text_input('🔍 Быстрый поиск:', '', placeholder='Введите текст для фильтрации...')

  if not contacts_df.empty:
    if search_query.strip():
      q = search_query.lower()
      mask = contacts_df.apply(lambda row: row.astype(str).str.lower().str.contains(q).any(), axis=1)
      filtered_contacts = contacts_df[mask]
    else:
      filtered_contacts = contacts_df

    column_configuration = {
        'Производитель': st.column_config.TextColumn('Производитель', width='medium'),
        'Оф.сайт': st.column_config.TextColumn('Оф.сайт', width='small'),
        'Контакт': st.column_config.TextColumn('Контакт', width='small'),
        'Имя': st.column_config.TextColumn('Имя', width='small'),
        'Группы товаров': st.column_config.TextColumn('Группы товаров', width='medium'),
        'Примечание': st.column_config.TextColumn('Примечание', width='large'),
    }

    st.dataframe(
        filtered_contacts,
        use_container_width=True,
        hide_index=True,
        column_config=column_configuration,
        height=480,
    )
  else:
    st.info('Контакты пока не добавлены.')


@st.dialog('📦 Новые товары (Еженедельная загрузка)')
def modal_new_products():
  st.markdown("<h4 style='font-weight: 500; font-size: 1.05rem; margin-top: 5px; margin-bottom: 12px;'>📥 Загрузить файлы (пакетно)</h4>", unsafe_allow_html=True)

  uploaded_files = st.file_uploader(
      'Выберите .xlsx / .xls файлы',
      type=['xlsx', 'xls'],
      accept_multiple_files=True,
      key='new_prod_file',
  )

  if uploaded_files:
    if st.button(f'🚀 Добавить выгрузки в таблицу ({len(uploaded_files)})', use_container_width=True):
      progress_bar = st.progress(0)
      status_text = st.empty()
      try:
        if append_new_products_batch(uploaded_files, progress_bar, status_text):
          status_text.success(f'Успешно добавлено файлов: {len(uploaded_files)}!')
          st.rerun()
      except Exception as e:
        status_text.empty()
        progress_bar.empty()
        st.error(f'Ошибка обработки файлов: {e}')

  st.divider()

  st.markdown("<h4 style='font-weight: 500; font-size: 1.05rem; margin-bottom: 12px;'>📋 Реестр выгрузок по датам</h4>", unsafe_allow_html=True)

  batches = parse_new_products_by_batches()

  if batches:
    dates_list = list(batches.keys())
    dates_list.reverse()

    selected_date = st.selectbox('📅 Выберите дату загрузки:', options=dates_list, key='select_batch_date')
    selected_df = batches[selected_date]

    st.caption(f'Всего товаров в выгрузке: **{len(selected_df)}** | Кликните по заголовку любого столбца для сортировки')

    np_column_config = {
        'Внешний код': st.column_config.TextColumn('Внешний код', width='small'),
        'Наименование': st.column_config.TextColumn('Наименование', width='large'),
        'Дата создания': st.column_config.TextColumn('Дата создания', width='small'),
        'Цифровой код менеджера': st.column_config.TextColumn('Код менеджера', width='small'),
        'Название раздела': st.column_config.TextColumn('Название раздела', width='medium'),
        'Менеджер': st.column_config.TextColumn('Менеджер', width='medium'),
        'Контент': st.column_config.TextColumn('Контент', width='small'),
    }

    st.dataframe(
        selected_df,
        use_container_width=True,
        hide_index=True,
        column_config=np_column_config,
        height=450,
    )
  else:
    st.info('Данные по новым товарам пока отсутствуют.')


@st.dialog('➕ Создать новую задачу')
def modal_add_task():
  with st.form('create_task_form', clear_on_submit=True):
    task_title = st.text_input('Тема задачи *', placeholder='Введите краткое название задачи')
    
    col1, col2 = st.columns(2)
    with col1:
      task_urgency = st.selectbox('Срочность:', ['Текущая задача', 'Срочно'])
    with col2:
      task_status = st.selectbox('Начальный статус:', ['Новая', 'В работе', 'Завершена'])

    executors_input = st.text_input(
        'Исполнитель(и) *',
        placeholder='Укажите одного или нескольких через запятую (напр.: Анна, Иван)',
    )

    st.caption('Описание поддерживает Markdown (списки `- [ ] пункт` для чек-боксов)')
    task_desc = st.text_area(
        'Описание задачи',
        placeholder='- [ ] Подготовить отчет\n- [ ] Проверить фото\nПодробности...',
        height=150,
    )

    uploaded_img = st.file_uploader(
        'Прикрепить изображение',
        type=['png', 'jpg', 'jpeg', 'webp'],
        accept_multiple_files=False,
    )

    btn_create = st.form_submit_button('Создать задачу', use_container_width=True)

    if btn_create:
      if not task_title.strip():
        st.warning('Заполните поле "Тема задачи"!')
      elif not executors_input.strip():
        st.warning('Укажите хотя бы одного исполнителя!')
      else:
        tasks_df = load_tasks_data()
        next_id = str(len(tasks_df) + 1)
        now_str = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')

        img_b64 = ''
        if uploaded_img is not None:
          bytes_data = uploaded_img.getvalue()
          b64_str = base64.b64encode(bytes_data).decode('utf-8')
          mime_type = uploaded_img.type
          img_b64 = f'data:{mime_type};base64,{b64_str}'

        execs_clean = ', '.join([e.strip() for e in executors_input.split(',') if e.strip()])

        new_task = pd.DataFrame([{
            'ID': next_id,
            'Тема': task_title.strip(),
            'Описание': task_desc.strip(),
            'Исполнители': execs_clean,
            'Статус': task_status,
            'Срочность': task_urgency,
            'Изображения Base64': img_b64,
            'Дата создания': now_str,
            'Дата обновления': now_str,
        }])

        updated_tasks = pd.concat([tasks_df, new_task], ignore_index=True)
        if save_all_tasks(updated_tasks):
          st.success('Задача успешно создана!')
          st.rerun()


@st.dialog('✏️ Редактировать задачу')
def modal_edit_task(task_row):
  """Модальное окно для полного редактирования выбранной задачи."""
  t_id = task_row['ID']

  with st.form(f'edit_task_form_{t_id}'):
    edit_title = st.text_input('Тема задачи *', value=task_row['Тема'])

    col1, col2 = st.columns(2)
    with col1:
      urg_options = ['Текущая задача', 'Срочно']
      urg_index = urg_options.index(task_row['Срочность']) if task_row['Срочность'] in urg_options else 0
      edit_urgency = st.selectbox('Срочность:', urg_options, index=urg_index)
    with col2:
      st_options = ['Новая', 'В работе', 'Завершена']
      st_index = st_options.index(task_row['Статус']) if task_row['Статус'] in st_options else 0
      edit_status = st.selectbox('Статус:', st_options, index=st_index)

    edit_executors = st.text_input(
        'Исполнитель(и) *',
        value=task_row['Исполнители'],
        help='Указывайте имена через запятую',
    )

    edit_desc = st.text_area(
        'Описание задачи',
        value=task_row['Описание'],
        height=150,
    )

    if task_row['Изображения Base64']:
      st.markdown('**Текущее изображение:**')
      st.image(task_row['Изображения Base64'], width=250)

    uploaded_img = st.file_uploader(
        'Заменить / прикрепить новое изображение',
        type=['png', 'jpg', 'jpeg', 'webp'],
        accept_multiple_files=False,
        key=f'edit_img_{t_id}',
    )

    btn_update = st.form_submit_button('Сохранить изменения', use_container_width=True)

    if btn_update:
      if not edit_title.strip():
        st.warning('Заполните поле "Тема задачи"!')
      elif not edit_executors.strip():
        st.warning('Укажите хотя бы одного исполнителя!')
      else:
        tasks_df = load_tasks_data()
        now_str = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')

        # Обработка картинки
        img_b64 = task_row['Изображения Base64']
        if uploaded_img is not None:
          bytes_data = uploaded_img.getvalue()
          b64_str = base64.b64encode(bytes_data).decode('utf-8')
          mime_type = uploaded_img.type
          img_b64 = f'data:{mime_type};base64,{b64_str}'

        execs_clean = ', '.join([e.strip() for e in edit_executors.split(',') if e.strip()])

        mask = tasks_df['ID'] == t_id
        tasks_df.loc[mask, 'Тема'] = edit_title.strip()
        tasks_df.loc[mask, 'Описание'] = edit_desc.strip()
        tasks_df.loc[mask, 'Исполнители'] = execs_clean
        tasks_df.loc[mask, 'Статус'] = edit_status
        tasks_df.loc[mask, 'Срочность'] = edit_urgency
        tasks_df.loc[mask, 'Изображения Base64'] = img_b64
        tasks_df.loc[mask, 'Дата обновления'] = now_str

        if save_all_tasks(tasks_df):
          st.success('Задача успешно обновлена!')
          st.rerun()


# ==========================================
# 5. ОСНОВНОЙ ИНТЕРФЕЙС STREAMLIT
# ==========================================

# 1. Заголовок
st.markdown("<h2 class='custom-header'>Панель управления отдела контента</h2>", unsafe_allow_html=True)

# 2. Три главные вкладки
main_tab1, main_tab2, main_tab3 = st.tabs([
    "📥 Добавление товаров",
    "📂 Открытие новых групп",
    "🎯 Задачи"
])

# ------------------------------------------
# ВКЛАДКА 1: ДОБАВЛЕНИЕ ТОВАРОВ
# ------------------------------------------
with main_tab1:
    dept = st.radio(
        'Выберите отдел:',
        options=['Отдел контента', 'Коммерческий отдел'],
        horizontal=True,
        label_visibility='collapsed',
    )

    dept_info = SHEET_MAP[dept]

    # Загружаем сырые данные из Гугл Таблицы
    df = load_dept_data(dept_info['data'])

    # Динамически рассчитываем сводку
    summary_df = build_summary(df)

    st.divider()

    col_upload, col_actions, col_extra = st.columns([1.2, 1.8, 1.3])

    with col_upload:
      st.subheader(f'1. Загрузка файлов ({dept.lower()})')
      uploaded_files = st.file_uploader(
          f'Выберите .xlsx / .xls файлы для {dept.lower()}',
          type=['xlsx', 'xls'],
          accept_multiple_files=True,
      )
      if uploaded_files:
        if st.button(f'Загрузить файлы ({len(uploaded_files)})', use_container_width=True):
          now_str = datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')
          all_dfs = []
          total_files = len(uploaded_files)

          progress_bar = st.progress(0)
          status_text = st.empty()

          try:
            for idx, u_file in enumerate(uploaded_files):
              status_text.info(f'Чтение файла {idx + 1} из {total_files}: **{u_file.name}**')

              u_file.seek(0)
              raw_uploaded_df = pd.read_excel(u_file, dtype=str)

              mapped_data = map_excel_columns(raw_uploaded_df)
              num_rows = len(mapped_data['Внешний код'])

              if num_rows > 0:
                uploaded_df = pd.DataFrame({
                    'ID': [''] * num_rows,
                    'Внешний код': mapped_data['Внешний код'],
                    'Группа 3': mapped_data['Группа 3'],
                    'Наименование': mapped_data['Наименование'],
                    'Статус': ['🆕 Новый'] * num_rows,
                    'Исполнитель': [''] * num_rows,
                    'Дата взятия': [''] * num_rows,
                    'Дата выполнения': [''] * num_rows,
                    'Дата завершения работы': [''] * num_rows,
                    'Источник': [u_file.name] * num_rows,
                    'Дата загрузки': [now_str] * num_rows,
                })

                all_dfs.append(uploaded_df[COLUMNS])
              progress_bar.progress(int(((idx + 1) / total_files) * 60))

            if all_dfs:
              status_text.info('Сохранение и запись данных в Google Таблицу...')
              combined_df = pd.concat(all_dfs, ignore_index=True)

              progress_bar.progress(80)
              if save_dept_data(dept_info, combined_df):
                progress_bar.progress(100)
                status_text.success(f'Успешно загружено файлов: {total_files}!')
                st.rerun()

          except Exception as e:
            status_text.empty()
            progress_bar.empty()
            st.error(f'Ошибка обработки файлов: {e}')

    with col_actions:
      st.subheader('2. Управление статусами')
      st.write('Выберите действие по файлам:')

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
          st.info('Нет новых групп.')
        else:
          cols_new = [c for c in ['Имя файла', 'Группа 3', 'Количество товаров', 'Дата добавления', 'Дней с добавления'] if c in new_df.columns]
          st.dataframe(new_df[cols_new], use_container_width=True, hide_index=True)

      with tab_paused:
        if paused_df.empty:
          st.info('Нет групп на паузе.')
        else:
          cols_paused = [c for c in ['Имя файла', 'Группа 3', 'Количество товаров', 'Исполнитель', 'Дата паузы', 'Причина паузы'] if c in paused_df.columns]
          st.dataframe(paused_df[cols_paused], use_container_width=True, hide_index=True)

      with tab_work:
        if work_df.empty:
          st.info('Нет групп в работе.')
        else:
          cols_work = [c for c in ['Имя файла', 'Группа 3', 'Количество товаров', 'Исполнитель', 'Дата начала работы'] if c in work_df.columns]
          st.dataframe(work_df[cols_work], use_container_width=True, hide_index=True)

      st.write('')

      if 'show_completed' not in st.session_state:
        st.session_state.show_completed = False

      btn_label = (
          '🙈 Скрыть завершенные группы'
          if st.session_state.show_completed
          else f'📂 Посмотреть завершенные группы ({len(completed_summary)})'
      )

      if st.button(btn_label):
        st.session_state.show_completed = not st.session_state.show_completed
        st.rerun()

      if st.session_state.show_completed:
        st.markdown('---')
        st.subheader(f'✅ Завершенные группы ({len(completed_summary)})')
        if completed_summary.empty:
          st.info('Завершенных групп пока нет.')
        else:
          cols_completed = [c for c in ['Имя файла', 'Группа 3', 'Количество товаров', 'Исполнитель', 'Дата начала работы', 'Дата завершения работы'] if c in completed_summary.columns]
          st.dataframe(completed_summary[cols_completed], use_container_width=True, hide_index=True)

# ------------------------------------------
# ВКЛАДКА 2: ОТКРЫТИЕ НОВЫХ ГРУПП (ПУСТО)
# ------------------------------------------
with main_tab2:
    st.info("Раздел 'Открытие новых групп' находится в разработке.")

# ------------------------------------------
# ВКЛАДКА 3: ЗАДАЧИ
# ------------------------------------------
with main_tab3:
    col_t_title, col_t_btn = st.columns([3, 1])
    with col_t_title:
      st.subheader('🎯 Менеджер задач')
    with col_t_btn:
      if st.button('➕ Добавить задачу', use_container_width=True):
        modal_add_task()

    st.divider()

    tasks_df = load_tasks_data()

    if tasks_df.empty:
      st.info('Задач пока нет. Нажмите «Добавить задачу», чтобы создать первую.')
    else:
      # Фильтрация по статусам
      new_tasks = tasks_df[tasks_df['Статус'] == 'Новая']
      work_tasks = tasks_df[tasks_df['Статус'] == 'В работе']
      done_tasks = tasks_df[tasks_df['Статус'] == 'Завершена']

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
        badge_html = (
            f"<span class='urgent-badge'>🔥 {t_urgency}</span>"
            if is_urgent
            else f"<span class='normal-badge'>📌 {t_urgency}</span>"
        )
        bubbles_html = render_executor_bubbles(t_execs)

        with st.expander(f"#{t_id} | {t_title}", expanded=False):
          col_info, col_edit_btn = st.columns([3, 1])

          with col_info:
            st.markdown(f"**Срочность:** {badge_html}", unsafe_allow_html=True)
            st.markdown("**Исполнители:**", unsafe_allow_html=True)
            st.markdown(bubbles_html, unsafe_allow_html=True)
            st.caption(f"Дата создания: {t_date}")

          with col_edit_btn:
            if st.button('✏️ Редактировать', key=f'btn_modal_edit_{t_id}', use_container_width=True):
              modal_edit_task(row)

          st.divider()

          if t_desc:
            st.markdown("**Описание:**")
            st.markdown(t_desc)

          if t_img:
            st.write('')
            st.image(t_img, caption='Прикрепленное изображение', width=350)

          st.divider()

          # Быстрое изменение статуса задачи
          c_sel, c_sav = st.columns([2, 1])
          with c_sel:
            new_st = st.selectbox(
                'Быстрая смена статуса:',
                ['Новая', 'В работе', 'Завершена'],
                index=['Новая', 'В работе', 'Завершена'].index(t_status) if t_status in ['Новая', 'В работе', 'Завершена'] else 0,
                key=f'status_sel_{t_id}',
            )
          with c_sav:
            st.write('')
            st.write('')
            if st.button('Сохранить статус', key=f'btn_save_status_{t_id}'):
              tasks_df.loc[tasks_df['ID'] == t_id, 'Статус'] = new_st
              tasks_df.loc[tasks_df['ID'] == t_id, 'Дата обновления'] = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')
              if save_all_tasks(tasks_df):
                st.success('Статус задачи сохранен!')
                st.rerun()

      with t_tab1:
        if new_tasks.empty:
          st.info('Новых задач нет.')
        else:
          for _, task_row in new_tasks.iterrows():
            render_task_card(task_row)

      with t_tab2:
        if work_tasks.empty:
          st.info('Задач в работе нет.')
        else:
          for _, task_row in work_tasks.iterrows():
            render_task_card(task_row)

      with t_tab3:
        if done_tasks.empty:
          st.info('Завершенных задач нет.')
        else:
          for _, task_row in done_tasks.iterrows():
            render_task_card(task_row)
