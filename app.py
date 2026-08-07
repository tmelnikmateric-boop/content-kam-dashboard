import streamlit as st
import pandas as pd
import numpy as np
import datetime
import gspread
from google.oauth2.service_account import Credentials

# Настройка страницы Streamlit
st.set_page_config(page_title="Панель управления отдела контента", layout="wide")

# Дополнительные CSS стили
st.markdown("""
    <style>
    /* Центрирование и уменьшение главного заголовка */
    .custom-header {
        text-align: center;
        font-size: 1.8rem !important;
        font-weight: 600;
        margin-bottom: 25px;
    }
    
    /* Увеличение текста в переключателе отделов и центрирование */
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

    /* Ограничение высоты модального окна и прокрутка */
    div[role="dialog"], div[data-testid="stDialog"] > div:nth-child(2) {
        max-height: 85vh !important;
        overflow-y: auto !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS
# ==========================================
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1vCZQgzBPv8uahr8ckRI1f-TA_QS6Afz2B9NP_ZMj6ek/edit?gid=59376984#gid=59376984"

SHEET_MAP = {
    'Отдел контента': {
        'data': '📥 Загруженные данные контента',
        'workgroups': '👥 Рабочие группы контента'
    },
    'Отдел маркетинга': {
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

        # 1. Сохранение основного листа с загруженными данными
        try:
            worksheet = sh.worksheet(data_sheet_name)
        except gspread.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=data_sheet_name, rows="1000", cols="20")

        df_to_save = df.fillna('')
        data_to_write = [df_to_save.columns.tolist()] + df_to_save.values.tolist()

        worksheet.clear()
        worksheet.update('A1', data_to_write)

        # 2. Синхронизация статусов, причин и дат паузы с листом "👥 Рабочие группы..."
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

# ==========================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ: РАСЧЕТ РАБОЧИХ ДНЕЙ
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
            
        bus_days = np.busday_count(start_date, today)
        return int(bus_days)
    except Exception:
        return 0

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

        # 1. Завершенные
        is_completed = (
            st_val in ['выполнено', 'выполнен', 'завершен', 'завершена', '✅ выполнен', '✅ завершена'] or
            'выполнен' in st_grp or 'выполнено' in st_grp or 'заверш' in st_grp or
            bool(date_done)
        )

        # 2. На паузе
        is_paused = (
            st_val in ['пауза', 'на паузе', '⏸️ на паузе'] or
            'пауз' in st_grp or
            '⏸️' in st_grp or
            '⏸' in st_val or
            bool(pause_reason)
        )

        # 3. В работе
        is_in_work = (
            not is_completed and not is_paused and (
                st_val in ['в работе', 'взято в работу', '🔄 в работе'] or
                'в работе' in st_grp or
                '🔄' in st_grp or
                bool(date_take)
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
    
    with st.container(height=300):
        for _, row in new_df.iterrows():
            filename = row['Имя файла']
            count = row['Количество товаров']
            label = f"{filename} — {count} SKU"
            if st.checkbox(label, key=f"chk_new_{filename}"):
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
    
    with st.container(height=300):
        for _, row in in_work_df.iterrows():
            filename = row['Имя файла']
            count = row['Количество товаров']
            label = f"{filename} — {count} SKU"
            if st.checkbox(label, key=f"chk_work_{filename}"):
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
    
    with st.container(height=300):
        for _, row in paused_df.iterrows():
            filename = row['Имя файла']
            count = row['Количество товаров']
            label = f"{filename} — {count} SKU"
            if st.checkbox(label, key=f"chk_unpause_{filename}"):
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
    
    with st.container(height=300):
        for _, row in in_work_df.iterrows():
            filename = row['Имя файла']
            count = row['Количество товаров']
            label = f"{filename} — {count} SKU"
            if st.checkbox(label, key=f"chk_comp_{filename}"):
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
        df_marketing = load_dept_data(SHEET_MAP['Отдел маркетинга']['data'])

        summary_content = build_summary(df_content)
        summary_marketing = build_summary(df_marketing)

    with st.container(height=400):
        # 1. Сводные метрики по новым SKU
        new_content_sku = summary_content[summary_content['Статус группы'] == '🆕 Новая']['Количество товаров'].sum() if not summary_content.empty else 0
        new_marketing_sku = summary_marketing[summary_marketing['Статус группы'] == '🆕 Новая']['Количество товаров'].sum() if not summary_marketing.empty else 0

        st.markdown("### 🆕 Новые SKU на добавление")
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Отдел контента", f"{new_content_sku} SKU")
        col_m2.metric("Отдел маркетинга", f"{new_marketing_sku} SKU")

        st.divider()

        # Объединение сводок для общей аналитики по исполнителям
        combined_summaries = []
        if not summary_content.empty:
            summary_content['Отдел'] = 'Контент'
            combined_summaries.append(summary_content)
        if not summary_marketing.empty:
            summary_marketing['Отдел'] = 'Маркетинг'
            combined_summaries.append(summary_marketing)

        if combined_summaries:
            all_summary = pd.concat(combined_summaries, ignore_index=True)
            
            # 2. Исполнитель — Месяц — Количество SKU
            st.markdown("### 👤 Статистика: Исполнитель / Месяц / SKU")
            
            def extract_month(row):
                date_str = str(row['Дата завершения работы']) or str(row['Дата начала работы'])
                if date_str and len(date_str) >= 10:
                    try:
                        clean_date = date_str.split(' ')[0]
                        dt = datetime.datetime.strptime(clean_date, "%d.%m.%Y")
                        return dt.strftime("%Y-%m (%B)")
                    except Exception:
                        return "Неизвестно"
                return "Неизвестно"

            all_summary['Месяц'] = all_summary.apply(extract_month, axis=1)
            
            # Фильтруем файлы с назначенным исполнителем
            exec_df = all_summary[all_summary['Исполнитель'].str.strip() != ''].copy()
            
            if not exec_df.empty:
                perf_df = exec_df.groupby(['Исполнитель', 'Месяц'])['Количество товаров'].sum().reset_index()
                perf_df.rename(columns={'Количество товаров': 'Всего SKU'}, inplace=True)
                st.dataframe(perf_df, use_container_width=True, hide_index=True)
            else:
                st.info("Нет данных о выполненных или находящихся в работе файлах с указанием исполнителя.")

            st.divider()

            # 3. Количество SKU у каждого исполнителя в работе на данный момент
            st.markdown("### 🔄 В работе на данный момент")
            in_work_summary = all_summary[all_summary['Статус группы'] == '🔄 В работе'].copy()
            
            if not in_work_summary.empty:
                work_by_exec = in_work_summary.groupby(['Исполнитель', 'Отдел'])['Количество товаров'].sum().reset_index()
                work_by_exec.rename(columns={'Количество товаров': 'SKU в работе'}, inplace=True)
                st.dataframe(work_by_exec, use_container_width=True, hide_index=True)
            else:
                st.info("В данный момент нет SKU в работе.")
        else:
            st.info("Данные в разделах отсутствуют.")

# ==========================================
# 4. ОСНОВНОЙ ИНТЕРФЕЙС STREAMLIT
# ==========================================

st.markdown("<h2 class='custom-header'>Панель управления отдела контента</h2>", unsafe_allow_html=True)

dept = st.radio(
    "Выберите отдел:", 
    options=['Отдел контента', 'Отдел маркетинга'], 
    horizontal=True,
    label_visibility="collapsed"
)

dept_info = SHEET_MAP[dept]

df = load_dept_data(dept_info['data'])
summary_df = build_summary(df)

st.divider()

col_upload, col_actions = st.columns([1, 2.5])

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
    st.subheader("2. Управление статусами и аналитикой")
    st.write("Выберите необходимое действие:")

    btn_col1, btn_col2, btn_col3, btn_col4, btn_col5 = st.columns(5)

    if btn_col1.button("▶️ В работу", use_container_width=True):
        modal_take_in_work(dept_info, summary_df, df)

    if btn_col2.button("⏸️ На паузу", use_container_width=True):
        modal_pause(dept_info, summary_df, df)

    if btn_col3.button("▶️ Снять с паузы", use_container_width=True):
        modal_unpause(dept_info, summary_df, df)

    if btn_col4.button("✅ Завершить", use_container_width=True):
        modal_complete(dept_info, summary_df, df)

    if btn_col5.button("📊 Аналитика", use_container_width=True):
        modal_analytics()

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

    # 1. Вкладка "Новые"
    with tab_new:
        if new_df.empty:
            st.info("Нет новых групп.")
        else:
            cols_new = ['Имя файла', 'Группа 3', 'Количество товаров', 'Дата добавления', 'Дней с добавления']
            st.dataframe(new_df[cols_new], use_container_width=True, hide_index=True)

    # 2. Вкладка "На паузе"
    with tab_paused:
        if paused_df.empty:
            st.info("Нет групп на паузе.")
        else:
            cols_paused = ['Имя файла', 'Группа 3', 'Количество товаров', 'Исполнитель', 'Дата паузы', 'Причина паузы']
            st.dataframe(paused_df[cols_paused], use_container_width=True, hide_index=True)

    # 3. Вкладка "В работе"
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
