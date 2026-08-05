import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials

# Загрузка из secrets
credentials = st.secrets["gcp_service_account"]
gc = gspread.service_account_from_dict(credentials)

# Настройка страницы Streamlit
st.set_page_config(page_title="Панель управления Контентом и КАМ", layout="wide")

# ==========================================
# 1. ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS
# ==========================================
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1vCZQgzBPv8uahr8ckRI1f-TA_QS6Afz2B9NP_ZMj6ek/edit?gid=59376984#gid=59376984"

SHEET_MAP = {
    'Контент': '📥 Загруженные данные контента',
    'КАМ': '📥 Загруженные данные КАМ'
}

COLUMNS = [
    'ID', 'Внешний код', 'Группа 3', 'Наименование',
    'Статус', 'Исполнитель', 'Дата взятия', 
    'Дата выполнения', 'Дата завершения работы', 
    'Источник', 'Дата загрузки'
]

@st.cache_resource
def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    # Авторизация через Secrets в Streamlit Cloud
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
            for col in COLUMNS:
                if col not in df.columns:
                    df[col] = ''
            return df
        return pd.DataFrame(columns=COLUMNS)
    except Exception as e:
        st.error(f"Ошибка загрузки листа {sheet_name}: {e}")
        return pd.DataFrame(columns=COLUMNS)

def save_dept_data(sheet_name, df):
    try:
        gc = get_gspread_client()
        sh = gc.open_by_url(SPREADSHEET_URL)
        try:
            worksheet = sh.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=sheet_name, rows="1000", cols="20")

        df_to_save = df.fillna('')
        data_to_write = [df_to_save.columns.tolist()] + df_to_save.values.tolist()
        
        worksheet.clear()
        worksheet.update('A1', data_to_write)
        return True
    except Exception as e:
        st.error(f"Ошибка сохранения: {e}")
        return False

# ==========================================
# 2. РАСЧЕТ СВОДНОЙ ТАБЛИЦЫ
# ==========================================
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

        st_val = str(first_row.get('Статус', '')).strip().lower()
        st_grp = str(first_row.get('Статус группы', '')).strip().lower()
        date_done = str(first_row.get('Дата завершения работы', '')).strip()
        date_take = str(first_row.get('Дата взятия', '')).strip()
        pause_reason = str(first_row.get('Причина паузы', '')).strip()

        is_completed = (
            st_val in ['выполнено', 'выполнен', 'завершен', 'завершена'] or
            'выполнено' in st_grp or 'заверш' in st_grp or
            bool(date_done and date_done.lower() != 'nan' and date_done != '')
        )
        is_paused = (
            st_val in ['пауза', 'на паузе'] or
            'пауз' in st_grp or
            bool(pause_reason and pause_reason.lower() != 'nan' and pause_reason != '')
        )
        is_in_work = (
            st_val in ['в работе', 'взято в работу'] or
            'в работе' in st_grp or
            bool(date_take and date_take.lower() != 'nan' and date_take != '')
        )

        if is_completed:
            done_cnt, in_work_cnt, new_cnt, group_status = total, 0, 0, '✅ Завершена'
        elif is_paused:
            done_cnt, in_work_cnt, new_cnt, group_status = 0, 0, total, '⏸️ На паузе'
        elif is_in_work:
            done_cnt, in_work_cnt, new_cnt, group_status = 0, total, 0, '⏳ В работе'
        else:
            done_cnt, in_work_cnt, new_cnt, group_status = 0, 0, total, '🆕 Новая'

        summary_rows.append({
            '№': idx,
            'Имя файла': filename,
            'Группа 3': first_row.get('Группа 3', ''),
            'Количество товаров': total,
            'Новых': new_cnt,
            'В работе': in_work_cnt,
            'Выполнено': done_cnt,
            'Статус группы': group_status,
            'Исполнитель': first_row.get('Исполнитель', ''),
            'Дата взятия': date_take,
            'Дата завершения работы': date_done,
            'Дата добавления файла': first_row.get('Дата добавления файла', first_row.get('Дата загрузки', ''))
        })

    return pd.DataFrame(summary_rows)

# ==========================================
# 3. ВЕБ-ИНТЕРФЕЙС (STREAMLIT)
# ==========================================
st.title("📊 Панель управления Контентом и КАМ")

dept = st.radio("Выберите отдел:", options=['Контент', 'КАМ'], horizontal=True)
sheet_name = SHEET_MAP[dept]

# Загружаем текущие данные
df = load_dept_data(sheet_name)

col_left, col_right = st.columns([1, 2])

with col_left:
    st.subheader("1. Загрузка Excel")
    uploaded_file = st.file_uploader("Выберите .xlsx / .xls файл", type=['xlsx', 'xls'])
    if uploaded_file is not None:
        if st.button("Загрузить файл в систему"):
            uploaded_df = pd.read_excel(uploaded_file)
            now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

            uploaded_df['Имя файла'] = uploaded_file.name
            uploaded_df['Источник'] = uploaded_file.name
            uploaded_df['Дата добавления файла'] = now_str
            uploaded_df['Статус'] = 'Новый'
            uploaded_df['Статус группы'] = 'Новая'

            for col in COLUMNS:
                if col not in uploaded_df.columns:
                    uploaded_df[col] = ''

            new_df = pd.concat([df, uploaded_df], ignore_index=True)
            if save_dept_data(sheet_name, new_df):
                st.success(f"Файл '{uploaded_file.name}' успешно сохранен!")
                st.rerun()

with col_right:
    st.subheader("2. Фильтр и управление статусами")
    source_col = 'Имя файла' if 'Имя файла' in df.columns else 'Источник'
    all_files = df[source_col].unique().tolist() if not df.empty and source_col in df.columns else []
    
    selected_files = st.multiselect("Выберите файл(ы):", options=all_files)
    executor_name = st.text_input("Имя исполнителя:")

    btn_col1, btn_col2, btn_col3 = st.columns(3)

    now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    mask = df[source_col].isin(selected_files) if source_col in df.columns else []

    if btn_col1.button("▶️ Взять в работу"):
        if not selected_files:
            st.warning("Выберите файлы!")
        elif not executor_name.strip():
            st.warning("Укажите имя исполнителя!")
        else:
            df.loc[mask, 'Статус'] = 'В работе'
            df.loc[mask, 'Статус группы'] = '⏳ В работе'
            df.loc[mask, 'Исполнитель'] = executor_name.strip()
            df.loc[mask, 'Дата взятия'] = now_str
            save_dept_data(sheet_name, df)
            st.success("Статус обновлен на 'В работе'")
            st.rerun()

    if btn_col2.button("⏸️ На паузу"):
        if not selected_files:
            st.warning("Выберите файлы!")
        else:
            df.loc[mask, 'Статус'] = 'Пауза'
            df.loc[mask, 'Статус группы'] = '⏸️ На паузе'
            save_dept_data(sheet_name, df)
            st.success("Статус обновлен на 'На паузе'")
            st.rerun()

    if btn_col3.button("✅ Завершить"):
        if not selected_files:
            st.warning("Выберите файлы!")
        else:
            df.loc[mask, 'Статус'] = 'выполнено'
            df.loc[mask, 'Статус группы'] = '✅ Завершена'
            df.loc[mask, 'Дата завершения работы'] = now_str
            df.loc[mask, 'Дата выполнения'] = now_str
            save_dept_data(sheet_name, df)
            st.success("Статус обновлен на 'Выполнено'")
            st.rerun()

st.divider()
st.subheader(f"📋 Реестр групп / файлов — {sheet_name.upper()}")

summary_df = build_summary(df)
if summary_df.empty:
    st.info("Нет данных для отображения")
else:
    st.dataframe(summary_df, use_container_width=True)
