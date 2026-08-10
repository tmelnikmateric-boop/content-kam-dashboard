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
    page_title="Панель управления отдела контента!!!", layout="wide"
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

# Точный список столбцов под вашу Гугл Таблицу
COLUMNS = [
    'ID',
    'Внешний код',
    'Группа 3',
    'Наименование',
    'Статус',
    'Исполнитель',
    'Дата взятия',
    'Дата выполнения',
    'Дата завершения работы',
    'Источник',
    'Дата загрузки',
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

MONTH_NAMES = {
    1: 'Январь',
    2: 'Февраль',
    3: 'Март',
    4: 'Апрель',
    5: 'Май',
    6: 'Июнь',
    7: 'Июль',
    8: 'Август',
    9: 'Сентябрь',
    10: 'Октябрь',
    11: 'Ноябрь',
    12: 'Декабрь',
}


@st.cache_resource
def get_gspread_client():
  scopes = ['https://www.googleapis.com/auth/spreadsheets']
  creds_dict = dict(st.secrets['gcp_service_account'])
  creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
  return gspread.authorize(creds)


def load_dept_data(sheet_name):
  """Загрузка сырых данных напрямую из Google Таблицы."""
  try:
    gc = get_gspread_client()
    sh = gc.open_by_url(SPREADSHEET_URL)
    worksheet = sh.worksheet(sheet_name)
    vals = worksheet.get_all_values()

    if len(vals) > 1:
      headers = [str(h).strip() for h in vals[0]]
      df = pd.DataFrame(vals[1:], columns=headers).astype(str)
      df = df.replace(
          {'nan': '', 'NaN': '', 'None': '', '<NA>': '', 'NaT': ''}
      )
      for col in COLUMNS:
        if col not in df.columns:
          df[col] = ''
      return df
    return pd.DataFrame(columns=COLUMNS)
  except Exception as e:
    st.error(f'Ошибка загрузки листа {sheet_name}: {e}')
    return pd.DataFrame(columns=COLUMNS)


def save_dept_data(dept_info, df):
  """Сохранение сырых данных и обновление сводного реестра."""
  data_sheet_name = dept_info['data']
  workgroup_sheet_name = dept_info['workgroups']

  try:
    gc = get_gspread_client()
    sh = gc.open_by_url(SPREADSHEET_URL)

    try:
      worksheet = sh.worksheet(data_sheet_name)
      existing_vals = worksheet.get_all_values()
    except gspread.WorksheetNotFound:
      worksheet = sh.add_worksheet(
          title=data_sheet_name, rows='2000', cols='25'
      )
      existing_vals = []

    if existing_vals and len(existing_vals) > 1:
      old_headers = [str(h).strip() for h in existing_vals[0]]
      old_data_df = pd.DataFrame(existing_vals[1:], columns=old_headers).astype(
          str
      )

      for col in COLUMNS:
        if col not in old_data_df.columns:
          old_data_df[col] = ''
        if col not in df.columns:
          df[col] = ''

      # Группируем по полю "Источник"
      updated_sources = (
          df['Источник']
          .replace('', np.nan)
          .fillna(df.get('Имя файла', ''))
          .unique()
      )
      old_sources = old_data_df['Источник'].replace('', np.nan).fillna('')

      old_filtered = old_data_df[~old_sources.isin(updated_sources)]
      full_df = pd.concat([old_filtered, df[COLUMNS]], ignore_index=True)
    else:
      full_df = df[COLUMNS]

    full_df = full_df.fillna('').astype(str)
    data_to_write = [COLUMNS] + full_df.values.tolist()

    worksheet.clear()
    worksheet.update(range_name='A1', values=data_to_write)

    # Перерасчет и обновление сводной таблицы групп
    try:
      try:
        wg_worksheet = sh.worksheet(workgroup_sheet_name)
      except gspread.WorksheetNotFound:
        wg_worksheet = sh.add_worksheet(
            title=workgroup_sheet_name, rows='1000', cols='20'
        )

      full_summary_df = build_summary(full_df)

      if not full_summary_df.empty:
        wg_data = [full_summary_df.columns.tolist()] + (
            full_summary_df.fillna('').astype(str).values.tolist()
        )
        wg_worksheet.clear()
        wg_worksheet.update(range_name='A1', values=wg_data)

    except Exception as wg_err:
      st.warning(
          f"Основные данные сохранены, но не удалось обновить лист"
          f" '{workgroup_sheet_name}': {wg_err}"
      )

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
      worksheet = sh.add_worksheet(
          title=CONTACTS_SHEET_NAME, rows='1000', cols='10'
      )
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
      worksheet = sh.add_worksheet(
          title=CONTACTS_SHEET_NAME, rows='1000', cols='10'
      )
      worksheet.append_row(CONTACT_COLUMNS)

    row_values = [
        str(new_row_dict.get(col, '')).strip() for col in CONTACT_COLUMNS
    ]
    worksheet.append_row(row_values)
    return True
  except Exception as e:
    st.error(f'Ошибка сохранения контакта: {e}')
    return False


def load_managers_mapping():
  try:
    gc = get_gspread_client()
    sh = gc.open_by_url(SPREADSHEET_URL)
    try:
      worksheet = sh.worksheet(MANAGERS_SHEET_NAME)
    except gspread.WorksheetNotFound:
      return {}

    vals = worksheet.get_all_values()
    if not vals or len(vals) < 2:
      return {}

    m_df = pd.DataFrame(vals[1:], columns=vals[0]).astype(str)
    m_df.columns = m_df.columns.astype(str).str.strip()

    code_col = next(
        (
            c
            for c in m_df.columns
            if any(k in c.lower() for k in ['код', 'цифровой', 'id'])
        ),
        m_df.columns[0],
    )
    name_col = next(
        (
            c
            for c in m_df.columns
            if any(k in c.lower() for k in ['менеджер', 'фамили', 'фио', 'имя'])
        ),
        m_df.columns[1] if len(m_df.columns) > 1 else m_df.columns[0],
    )

    keys = m_df[code_col].str.strip().str.replace(r'\.0$', '', regex=True)
    values = m_df[name_col].str.strip()

    return dict(zip(keys, values))
  except Exception as e:
    st.error(f'Ошибка загрузки листа менеджеров: {e}')
    return {}


def load_raw_new_products():
  try:
    gc = get_gspread_client()
    sh = gc.open_by_url(SPREADSHEET_URL)
    try:
      worksheet = sh.worksheet(NEW_PRODUCTS_SHEET_NAME)
    except gspread.WorksheetNotFound:
      worksheet = sh.add_worksheet(
          title=NEW_PRODUCTS_SHEET_NAME, rows='1000', cols='10'
      )
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
  mapped_df = pd.DataFrame()
  cols = list(uploaded_df.columns)

  def find_col(keywords):
    for c in cols:
      c_str = str(c).strip().lower()
      if any(k in c_str for k in keywords):
        return c
    return None

  col_code = find_col(['внешний', 'артикул', 'код товара', 'идентификатор'])
  mapped_df['Внешний код'] = (
      uploaded_df[col_code]
      if col_code
      else (uploaded_df.iloc[:, 0] if len(cols) > 0 else '')
  )

  col_name = find_col(['наименование', 'название', 'номенклатура', 'товар'])
  mapped_df['Наименование'] = (
      uploaded_df[col_name]
      if col_name
      else (uploaded_df.iloc[:, 1] if len(cols) > 1 else '')
  )

  col_sec = find_col(['группа 3', 'раздел', 'категория', 'группа'])
  mapped_df['Группа 3'] = uploaded_df[col_sec] if col_sec else ''

  col_date = find_col(['дата созд', 'создан', 'дата'])
  mapped_df['Дата создания'] = uploaded_df[col_date] if col_date else ''

  col_mgr_code = find_col(
      ['цифровой', 'код менеджер', 'код отд', 'код кадра', 'менеджер код']
  )
  mapped_df['Цифровой код менеджера'] = (
      uploaded_df[col_mgr_code] if col_mgr_code else ''
  )

  col_cnt = find_col(['контент', 'описание', 'статус контент'])
  mapped_df['Контент'] = uploaded_df[col_cnt] if col_cnt else ''
  mapped_df['Менеджер'] = ''

  return mapped_df


def append_new_products(uploaded_df):
  try:
    gc = get_gspread_client()
    sh = gc.open_by_url(SPREADSHEET_URL)
    try:
      worksheet = sh.worksheet(NEW_PRODUCTS_SHEET_NAME)
    except gspread.WorksheetNotFound:
      worksheet = sh.add_worksheet(
          title=NEW_PRODUCTS_SHEET_NAME, rows='1000', cols='10'
      )
      worksheet.append_row(NEW_PRODUCTS_COLUMNS)

    formatted_df = map_excel_columns(uploaded_df)
    formatted_df = formatted_df.astype(str).replace(
        {'nan': '', 'NaN': '', 'None': '', '<NA>': '', 'NaT': ''}
    )
    formatted_df['Цифровой код менеджера'] = (
        formatted_df['Цифровой код менеджера']
        .str.strip()
        .str.replace(r'\.0$', '', regex=True)
    )

    managers_map = load_managers_mapping()
    formatted_df['Менеджер'] = (
        formatted_df['Цифровой код менеджера'].map(managers_map).fillna('')
    )
    formatted_df = formatted_df[NEW_PRODUCTS_COLUMNS]

    now_str = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')
    date_header_row = [f'📅 Загрузка от {now_str}'] + [''] * (
        len(NEW_PRODUCTS_COLUMNS) - 1
    )

    rows_to_append = [date_header_row] + formatted_df.values.tolist()
    worksheet.append_rows(rows_to_append)

    return True
  except Exception as e:
    st.error(f'Ошибка сохранения новых товаров: {e}')
    return False


# ==========================================
# 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ И СВОДКА
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
  """Построение группы на базе колонки 'Источник' и даты 'Дата загрузки'."""
  if df.empty:
    return pd.DataFrame()

  temp_df = df.copy()

  # Выделяем ключевое поле для группировки — Источник
  if 'Источник' in temp_df.columns:
    source_series = temp_df['Источник'].astype(str).str.strip()
  elif 'Имя файла' in temp_df.columns:
    source_series = temp_df['Имя файла'].astype(str).str.strip()
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
    st_grp = str(first_row.get('Статус группы', '')).strip().lower()

    date_done = get_clean_val(['Дата завершения работы', 'Дата выполнения'])
    date_take = get_clean_val(['Дата взятия', 'Дата начала работы'])
    pause_reason = get_clean_val(['Причина паузы', 'Причина'])
    date_pause = get_clean_val(['Дата паузы'])
    date_added = get_clean_val(
        ['Дата загрузки', 'Дата добавления файла', 'Дата добавления']
    )

    is_completed = (
        st_val
        in [
            'выполнено',
            'выполнен',
            'завершен',
            'завершена',
            '✅ выполнен',
            '✅ завершена',
        ]
        or 'выполнен' in st_grp
        or 'выполнено' in st_grp
        or bool(date_done)
    )

    is_paused = (
        st_val in ['пауза', 'на паузе', '⏸️ на паузе']
        or 'пауз' in st_grp
        or '⏸' in st_val
    )

    is_in_work = (
        not is_completed
        and not is_paused
        and (
            st_val
            in [
                'в работе',
                'взято в работу',
                'взята в работу',
                '🔄 в работе',
            ]
            or 'в работе' in st_grp
            or bool(date_take)
        )
    )

    if is_completed:
      done_cnt, in_work_cnt, new_cnt, group_status = total, 0, 0, '✅ Выполнен'
    elif is_paused:
      done_cnt, in_work_cnt, new_cnt, group_status = 0, 0, total, '⏸️ На паузе'
    elif is_in_work:
      done_cnt, in_work_cnt, new_cnt, group_status = 0, total, 0, '🔄 В работе'
    else:
      # По умолчанию статус «новый» или любой другой относим к «🆕 Новый»
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
        html += (
            f"<td rowspan='{rowspan}'"
            f" class='grouped-cell'>{row[group_col]}</td>"
        )
        first_row = False

      for col in cols_order:
        if col != group_col:
          html += f'<td>{row[col]}</td>'
      html += '</tr>'

  html += '</tbody></table></div>'
  return html


# ==========================================
# 3. МОДАЛЬНЫЕ ОКНА (DIALOGS)
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
      if 'Имя файла' in df.columns:
        mask = mask | df['Имя файла'].isin(selected_files)

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
      if 'Имя файла' in df.columns:
        mask = mask | df['Имя файла'].isin(selected_files)

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
      if st.checkbox(
          f'{filename} — {count} SKU', key=f'chk_unpause_{filename}'
      ):
        selected_files.append(filename)

  if st.button('Вернуть в работу'):
    if not selected_files:
      st.warning('Отметьте хотя бы один файл!')
    else:
      mask = df['Источник'].isin(selected_files)
      if 'Имя файла' in df.columns:
        mask = mask | df['Имя файла'].isin(selected_files)

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
      if 'Имя файла' in df.columns:
        mask = mask | df['Имя файла'].isin(selected_files)

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
        summary_content[summary_content['Статус группы'] == '🆕 Новый'][
            'Количество товаров'
        ].sum()
        if not summary_content.empty
        else 0
    )
    new_comm_sku = (
        summary_comm[summary_comm['Статус группы'] == '🆕 Новый'][
            'Количество товаров'
        ].sum()
        if not summary_comm.empty
        else 0
    )

    st.markdown(
        "<h4 style='font-weight: 500; font-size: 1.05rem; margin-bottom:"
        " 12px;'>🆕 Новые SKU на добавление</h4>",
        unsafe_allow_html=True,
    )
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

      st.markdown(
          "<h4 style='font-weight: 500; font-size: 1.05rem; margin-bottom:"
          " 12px;'>👤 Статистика по месяцам</h4>",
          unsafe_allow_html=True,
      )

      def parse_date_and_month(row):
        date_str = str(row['Дата завершения работы']) or str(
            row['Дата начала работы']
        )
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

      all_summary[['Месяц', 'Месяц_сорт']] = all_summary.apply(
          parse_date_and_month, axis=1
      )
      exec_df = all_summary[all_summary['Исполнитель'].str.strip() != ''].copy()

      if not exec_df.empty:
        perf_df = (
            exec_df.groupby(['Месяц_сорт', 'Месяц', 'Исполнитель'])[
                'Количество товаров'
            ]
            .sum()
            .reset_index()
        )
        perf_df.sort_values(by=['Месяц_сорт', 'Исполнитель'], inplace=True)
        perf_df.rename(
            columns={'Количество товаров': 'Количество SKU'}, inplace=True
        )

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

      st.markdown(
          "<h4 style='font-weight: 500; font-size: 1.05rem; margin-bottom:"
          " 12px;'>🔄 В работе на данный момент</h4>",
          unsafe_allow_html=True,
      )
      in_work_summary = all_summary[
          all_summary['Статус группы'] == '🔄 В работе'
      ].copy()

      if not in_work_summary.empty:
        work_by_exec = (
            in_work_summary.groupby(['Исполнитель', 'Отдел'])[
                'Количество товаров'
            ]
            .sum()
            .reset_index()
        )
        work_by_exec.sort_values(by=['Исполнитель', 'Отдел'], inplace=True)
        work_by_exec.rename(
            columns={'Количество товаров': 'SKU в работе'}, inplace=True
        )

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
      f_col1, f_col2, f_col3, f_col4, f_col5, f_col6 = st.columns(
          [1.2, 1.2, 1.2, 1.2, 1.5, 2.0]
      )
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

      btn_submit = st.form_submit_button(
          'Сохранить контакт', use_container_width=True
      )

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
    search_query = st.text_input(
        '🔍 Быстрый поиск:', "", placeholder='Введите текст для фильтрации...'
    )

  if not contacts_df.empty:
    if search_query.strip():
      q = search_query.lower()
      mask = contacts_df.apply(
          lambda row: row.astype(str).str.lower().str.contains(q).any(),
          axis=1,
      )
      filtered_contacts = contacts_df[mask]
    else:
      filtered_contacts = contacts_df

    column_configuration = {
        'Производитель': st.column_config.TextColumn(
            'Производитель', width='medium'
        ),
        'Оф.сайт': st.column_config.TextColumn('Оф.сайт', width='small'),
        'Контакт': st.column_config.TextColumn('Контакт', width='small'),
        'Имя': st.column_config.TextColumn('Имя', width='small'),
        'Группы товаров': st.column_config.TextColumn(
            'Группы товаров', width='medium'
        ),
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
  st.markdown(
      "<h4 style='font-weight: 500; font-size: 1.05rem; margin-top: 5px;"
      " margin-bottom: 12px;'>📥 Загрузить новый файл</h4>",
      unsafe_allow_html=True,
  )

  uploaded_file = st.file_uploader(
      'Выберите .xlsx / .xls файл', type=['xlsx', 'xls'], key='new_prod_file'
  )

  if uploaded_file is not None:
    if st.button('🚀 Добавить выгрузку в таблицу', use_container_width=True):
      try:
        new_products_df = pd.read_excel(uploaded_file)
        if append_new_products(new_products_df):
          st.success(f"Выгрузка '{uploaded_file.name}' успешно добавлена!")
          st.rerun()
      except Exception as e:
        st.error(f'Ошибка чтения файла: {e}')

  st.divider()

  st.markdown(
      "<h4 style='font-weight: 500; font-size: 1.05rem; margin-bottom:"
      " 12px;'>📋 Реестр выгрузок по датам</h4>",
      unsafe_allow_html=True,
  )

  batches = parse_new_products_by_batches()

  if batches:
    dates_list = list(batches.keys())
    dates_list.reverse()

    selected_date = st.selectbox(
        '📅 Выберите дату загрузки:',
        options=dates_list,
        key='select_batch_date',
    )

    selected_df = batches[selected_date]

    st.caption(
        f'Всего товаров в выгрузке: **{len(selected_df)}** | Кликните по'
        ' заголовку любого столбца для сортировки'
    )

    np_column_config = {
        'Внешний код': st.column_config.TextColumn(
            'Внешний код', width='small'
        ),
        'Наименование': st.column_config.TextColumn(
            'Наименование', width='large'
        ),
        'Дата создания': st.column_config.TextColumn(
            'Дата создания', width='small'
        ),
        'Цифровой код менеджера': st.column_config.TextColumn(
            'Код менеджера', width='small'
        ),
        'Название раздела': st.column_config.TextColumn(
            'Название раздела', width='medium'
        ),
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


# ==========================================
# 4. ОСНОВНОЙ ИНТЕРФЕЙС STREAMLIT
# ==========================================

st.markdown(
    "<h2 class='custom-header'>Панель управления отдела контента!!!</h2>",
    unsafe_allow_html=True,
)

dept = st.radio(
    'Выберите отдел:',
    options=['Отдел контента', 'Коммерческий отдел'],
    horizontal=True,
    label_visibility='collapsed',
)

dept_info = SHEET_MAP[dept]

# 1. Загружаем сырые данные из Гугл Таблицы
df = load_dept_data(dept_info['data'])

# 2. Динамически рассчитываем сводку
summary_df = build_summary(df)
# --- ВРЕМЕННАЯ ДИАГНОСТИКА ---
with st.expander('🔍 Отладка загрузки данных', expanded=True):
  st.write(f'**Текущий отдел:** {dept}')
  st.write(f'**Имя листа:** {dept_info["data"]}')
  st.write(f'**Загружено строк из таблицы (df):** {len(df)}')
  st.write(f'**Названия колонок в df:** {list(df.columns)}')
  if not df.empty:
    st.write('**Первые 3 строки сырых данных:**')
    st.dataframe(df.head(3))
    st.write(f'**Уникальные значения в "Источник":** {df["Источник"].unique()}')
    st.write(f'**Уникальные значения в "Статус":** {df["Статус"].unique()}')
# ------------------------------
st.divider()

col_upload, col_actions, col_extra = st.columns([1.2, 1.8, 1.3])

with col_upload:
  st.subheader(f'1. Загрузка файла ({dept.lower()})')
  uploaded_file = st.file_uploader(
      f'Выберите .xlsx / .xls файл для {dept.lower()}', type=['xlsx', 'xls']
  )
  if uploaded_file is not None:
    if st.button(f'Загрузить файл {dept.lower()}', use_container_width=True):
      raw_uploaded_df = pd.read_excel(uploaded_file)

      # Формируем структуру с использованием Источник и Дата загрузки
      uploaded_df = map_excel_columns(raw_uploaded_df)
      now_str = datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')

      uploaded_df['Источник'] = uploaded_file.name
      uploaded_df['Дата загрузки'] = now_str
      uploaded_df['Статус'] = 'Новый'

      for col in COLUMNS:
        if col not in uploaded_df.columns:
          uploaded_df[col] = ''

      if save_dept_data(dept_info, uploaded_df):
        st.success(f"Файл '{uploaded_file.name}' успешно сохранен!")
        st.rerun()

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

# ==========================================
# 5. РЕЕСТР АКТИВНЫХ И ЗАВЕРШЕННЫХ ГРУПП
# ==========================================
if summary_df.empty:
  st.info('Нет данных для отображения')
else:
  st.subheader(f'📋 Реестр групп — {dept.upper()}')

  new_df = (
      summary_df[summary_df['Статус группы'] == '🆕 Новый']
      .copy()
      .reset_index(drop=True)
  )
  paused_df = (
      summary_df[summary_df['Статус группы'] == '⏸️ На паузе']
      .copy()
      .reset_index(drop=True)
  )
  work_df = (
      summary_df[summary_df['Статус группы'] == '🔄 В работе']
      .copy()
      .reset_index(drop=True)
  )
  completed_summary = (
      summary_df[summary_df['Статус группы'] == '✅ Выполнен']
      .copy()
      .reset_index(drop=True)
  )

  tab_new, tab_paused, tab_work = st.tabs([
      f'🆕 Новые ({len(new_df)})',
      f'⏸️ На паузе ({len(paused_df)})',
      f'🔄 В работе ({len(work_df)})',
  ])

  with tab_new:
    if new_df.empty:
      st.info('Нет новых групп.')
    else:
      cols_new = [
          c
          for c in [
              'Имя файла',
              'Группа 3',
              'Количество товаров',
              'Дата добавления',
              'Дней с добавления',
          ]
          if c in new_df.columns
      ]
      st.dataframe(
          new_df[cols_new], use_container_width=True, hide_index=True
      )

  with tab_paused:
    if paused_df.empty:
      st.info('Нет групп на паузе.')
    else:
      cols_paused = [
          c
          for c in [
              'Имя файла',
              'Группа 3',
              'Количество товаров',
              'Исполнитель',
              'Дата паузы',
              'Причина паузы',
          ]
          if c in paused_df.columns
      ]
      st.dataframe(
          paused_df[cols_paused], use_container_width=True, hide_index=True
      )

  with tab_work:
    if work_df.empty:
      st.info('Нет групп в работе.')
    else:
      cols_work = [
          c
          for c in [
              'Имя файла',
              'Группа 3',
              'Количество товаров',
              'Исполнитель',
              'Дата начала работы',
          ]
          if c in work_df.columns
      ]
      st.dataframe(
          work_df[cols_work], use_container_width=True, hide_index=True
      )

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
      cols_completed = [
          c
          for c in [
              'Имя файла',
              'Группа 3',
              'Количество товаров',
              'Исполнитель',
              'Дата начала работы',
              'Дата завершения работы',
          ]
          if c in completed_summary.columns
      ]
      st.dataframe(
          completed_summary[cols_completed],
          use_container_width=True,
          hide_index=True,
      )
