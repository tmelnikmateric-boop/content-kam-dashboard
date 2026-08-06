import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials

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
    'Причина паузы', 'Источник', 'Дата загрузки'
]

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

        # 1. Завершенные
        is_completed = (
            st_val in ['выполнено', 'выполнен', 'завершен', 'завершена', '✅ выполнен', '✅ Завершена'] or
            'выполнен' in st_grp or 'выполнено' in st_grp or 'заверш' in st_grp or
            bool(date_done and date_done.lower() != 'nan' and date_done != '')
        )
        
        # 2. На паузе
        is_paused = (
            st_val in ['пауза', 'на паузе', '⏸️ на паузе'] or
            'пауз' in st_grp or
            '⏸️' in st_grp or
            '⏸' in st_val or
            bool(pause_reason and pause_reason.lower() != 'nan' and pause_reason != '')
        )
        
        # 3. В работе
        is_in_work = (
            not is_completed and not is_paused and (
                st_val in ['в работе', 'взято в работу', '🔄 в работе'] or
                'в работе' in st_grp or
                '🔄' in st_grp or
                bool(date_take and date_take.lower() != 'nan' and date_take != '')
            )
        )

        if is_completed:
            done_cnt, in_work_cnt, new_cnt, group_status = total, 0, 0, '✅ Завершена'
        elif is_paused:
            done_cnt, in_work_cnt, new_cnt, group_status = 0, 0, total, '⏸️ На паузе'
        elif is_in_work:
            done_cnt, in_work_cnt, new_cnt, group_status = 0, total, 0, '🔄 В работе'
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
            'Причина паузы': pause_reason,
            'Исполнитель': first_row.get('Исполнитель', ''),
            'Дата взятия': date_take,
            'Дата завершения работы': date_done,
            'Дата добавления файла': first_row.get('Дата добавления файла', first_row.get('Дата загрузки', ''))
        })

    return pd.DataFrame(summary_rows)

# ==========================================
# 3. МОДАЛЬНЫЕ ОКНА (DIALOGS)
# ==========================================

@st.dialog("▶️ Взять файлы в работу")
def modal_take_in_work(sheet_name, summary_df, df):
    new_files = summary_df[summary_df['Статус группы'] == '🆕 Новая']['Имя файла'].tolist()

    if not new_files:
        st.info("Нет новых файлов для взятия в работу.")
        return

    st.write("Выберите новые файлы:")
    selected_files = []
    for filename in new_files:
        if st.checkbox(filename, key=f"chk_new_{filename}"):
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

            if save_dept_data(sheet_name, df):
                st.success("Статус обновлен на '🔄 В работе'")
                st.rerun()

@st.dialog("⏸️ Поставить файлы на паузу")
def modal_pause(sheet_name, summary_df, df):
    in_work_files = summary_df[summary_df['Статус группы'] == '🔄 В работе']['Имя файла'].tolist()

    if not in_work_files:
        st.info("Нет файлов в работе для отправки на паузу.")
        return

    st.write("Выберите файлы в работе:")
    selected_files = []
    for filename in in_work_files:
        if st.checkbox(filename, key=f"chk_work_{filename}"):
            selected_files.append(filename)

    pause_reason = st.selectbox(
        "Укажите причину паузы:",
        options=["информация уточняется", "запрошено у поставщика"]
    )

    if st.button("Поставить на паузу"):
        if not selected_files:
            st.warning("Отметьте хотя бы один файл!")
        else:
            source_col = 'Имя файла' if 'Имя файла' in df.columns else 'Источник'
            mask = df[source_col].isin(selected_files)

            df.loc[mask, 'Статус'] = '⏸️ На паузе'
            df.loc[mask, 'Статус группы'] = '⏸️ На паузе'
            df.loc[mask, 'Причина паузы'] = pause_reason

            if save_dept_data(sheet_name, df):
                st.success("Файлы переведены на паузу!")
                st.rerun()

@st.dialog("▶️ Снять файлы с паузы")
def modal_unpause(sheet_name, summary_df, df):
    paused_files = summary_df[summary_df['Статус группы'] == '⏸️ На паузе']['Имя файла'].tolist()

    if not paused_files:
        st.info("Нет файлов на паузе.")
        return

    st.write("Выберите файлы для возобновления работы:")
    selected_files = []
    for filename in paused_files:
        if st.checkbox(filename, key=f"chk_unpause_{filename}"):
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

            if save_dept_data(sheet_name, df):
                st.success("Файлы успешно возвращены в работу!")
                st.rerun()

@st.dialog("✅ Завершить работу по файлам")
def modal_complete(sheet_name, summary_df, df):
    in_work_files = summary_df[summary_df['Статус группы'] == '🔄 В работе']['Имя файла'].tolist()

    if not in_work_files:
        st.info("Нет файлов в работе для завершения.")
        return

    st.write("Выберите файлы в работе для завершения:")
    selected_files = []
    for filename in in_work_files:
        if st.checkbox(filename, key=f"chk_comp_{filename}"):
            selected_files.append(filename)

    if st.button("Завершить"):
        if not selected_files:
            st.warning("Отметьте хотя бы один файл!")
        else:
            source_col = 'Имя файла' if 'Имя файла' in df.columns else 'Источник'
            now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            mask = df[source_col].isin(selected_files)

            df.loc[mask, 'Статус'] = '✅ Завершена'
            df.loc[mask, 'Статус группы'] = '✅ Завершена'
            df.loc[mask, 'Дата завершения работы'] = now_str
            df.loc[mask, 'Дата выполнения'] = now_str

            if save_dept_data(sheet_name, df):
                st.success("Статус обновлен на '✅ Завершена'")
                st.rerun()

# ==========================================
# 4. ОСНОВНОЙ ИНТЕРФЕЙС STREAMLIT
# ==========================================
st.title("📊 Панель управления Контентом и КАМ")

dept = st.radio("Выберите отдел:", options=['Контент', 'КАМ'], horizontal=True)
sheet_name = SHEET_MAP[dept]

# Загружаем текущие данные
df = load_dept_data(sheet_name)
summary_df = build_summary(df)

col_upload, col_actions = st.columns([1, 2.5])

with col_upload:
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
            uploaded_df['Статус группы'] = '🆕 Новая'

            for col in COLUMNS:
                if col not in uploaded_df.columns:
                    uploaded_df[col] = ''

            new_df = pd.concat([df, uploaded_df], ignore_index=True)
            if save_dept_data(sheet_name, new_df):
                st.success(f"Файл '{uploaded_file.name}' успешно сохранен!")
                st.rerun()

with col_actions:
    st.subheader("2. Управление статусами")
    st.write("Выберите необходимое действие:")
    
    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)

    if btn_col1.button("▶️ В работу", use_container_width=True):
        modal_take_in_work(sheet_name, summary_df, df)

    if btn_col2.button("⏸️ На паузу", use_container_width=True):
        modal_pause(sheet_name, summary_df, df)

    if btn_col3.button("▶️ Снять с паузы", use_container_width=True):
        modal_unpause(sheet_name, summary_df, df)

    if btn_col4.button("✅ Завершить", use_container_width=True):
        modal_complete(sheet_name, summary_df, df)

st.divider()

# ==========================================
# 5. РЕЕСТР АКТИВНЫХ И ЗАВЕРШЕННЫХ ГРУПП
# ==========================================
if summary_df.empty:
    st.info("Нет данных для отображения")
else:
    active_summary = summary_df[~summary_df['Статус группы'].isin(['✅ Выполнен', '✅ Завершена'])].reset_index(drop=True)
    completed_summary = summary_df[summary_df['Статус группы'].isin(['✅ Выполнен', '✅ Завершена'])].reset_index(drop=True)

    if not active_summary.empty:
        active_summary['№'] = range(1, len(active_summary) + 1)

    st.subheader(f"📋 Реестр активных групп — {sheet_name.upper()}")
    
    if active_summary.empty:
        st.info("Все группы завершены или нет активных задач.")
    else:
        st.dataframe(active_summary, use_container_width=True)

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
            completed_summary['№'] = range(1, len(completed_summary) + 1)
            st.dataframe(completed_summary, use_container_width=True)
