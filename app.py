import datetime
import pandas as pd
import streamlit as st

# ==========================================
# КОНСТАНТЫ СТАТУСОВ
# ==========================================
# Для отдельных товаров (Загруженные данные контента)
STATUS_ITEM_NEW = "🆕 Новый"

# Для таблицы "👥 Рабочие группы контента"
STATUS_GROUP_AVAILABLE = "🆕 Доступна"
STATUS_IN_WORK = "🔄 В работе"
STATUS_PAUSED = "⏸ На паузе"
STATUS_COMPLETED = "✅ Готово"


# ==========================================
# ПРЕДВАРИТЕЛЬНАЯ ПОДГОТОВКА ДАННЫХ
# ==========================================
def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Заполняет пропуски (NaN) в ключевых столбцах.
    Гарантирует, что группы с пустыми статусами или исполнителями не выпадут.
    """
    if df.empty:
        return df

    df = df.copy()

    # Список текстовых колонок для нормализации
    cols_to_clean = [
        'ID группы', 'Группа', 'Наименование группы', 
        'Статус', 'Статус группы', 'Исполнитель', 
        'Дата взятия', 'Причина паузы', 'Дата паузы'
    ]

    for col in cols_to_clean:
        if col in df.columns:
            # Заменяем NaN и None на пустые строки и убираем лишние пробелы
            df[col] = df[col].fillna('').astype(str).str.strip()

    return df


# ==========================================
# 1. МОДАЛЬНОЕ ОКНО: ВЗЯТЬ В РАБОТУ
# ==========================================
def modal_take_in_work(df: pd.DataFrame, target_ids: list, executor_name: str) -> pd.DataFrame:
    """
    Присваивает выделенным группам/товарам статус '🔄 В работе'
    и проставляет имя исполнителя с текущей датой.
    """
    if not executor_name or not executor_name.strip():
        st.error("Пожалуйста, укажите имя исполнителя.")
        return df

    df = prepare_dataframe(df)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Поиск по ID группы или по индексу
    group_col = 'ID группы' if 'ID группы' in df.columns else 'Группа'
    if group_col in df.columns:
        mask = df[group_col].isin([str(x).strip() for x in target_ids])
    else:
        mask = df.index.isin(target_ids)

    # Гарантированное присвоение статуса "🔄 В работе"
    df.loc[mask, 'Статус'] = STATUS_IN_WORK
    if 'Статус группы' in df.columns:
        df.loc[mask, 'Статус группы'] = STATUS_IN_WORK

    df.loc[mask, 'Исполнитель'] = executor_name.strip()
    df.loc[mask, 'Дата взятия'] = now_str

    # Очистка полей паузы
    if 'Причина паузы' in df.columns:
        df.loc[mask, 'Причина паузы'] = ''
    if 'Дата паузы' in df.columns:
        df.loc[mask, 'Дата паузы'] = ''

    return df


# ==========================================
# 2. МОДАЛЬНОЕ ОКНО: СНЯТЬ С ПАУЗЫ
# ==========================================
def modal_unpause(df: pd.DataFrame, target_ids: list) -> pd.DataFrame:
    """
    Возвращает статус группы/товаров из паузы обратно в '🔄 В работе'.
    """
    df = prepare_dataframe(df)

    group_col = 'ID группы' if 'ID группы' in df.columns else 'Группа'
    if group_col in df.columns:
        mask = df[group_col].isin([str(x).strip() for x in target_ids])
    else:
        mask = df.index.isin(target_ids)

    # Возврат статуса "🔄 В работе"
    df.loc[mask, 'Статус'] = STATUS_IN_WORK
    if 'Статус группы' in df.columns:
        df.loc[mask, 'Статус группы'] = STATUS_IN_WORK

    if 'Причина паузы' in df.columns:
        df.loc[mask, 'Причина паузы'] = ''
    if 'Дата паузы' in df.columns:
        df.loc[mask, 'Дата паузы'] = ''

    return df


# ==========================================
# 3. ФУНКЦИЯ СБОРКИ СВОДКИ (BUILD_SUMMARY)
# ==========================================
def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Формирует сводный реестр '👥 Рабочие группы контента'.
    Не теряет новые группы со статусом '🆕 Доступна'.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    # 1. Очищаем датафрейм от NaN и пробелов
    clean_df = prepare_dataframe(df)

    summary_rows = []
    group_col = 'ID группы' if 'ID группы' in clean_df.columns else 'Группа'

    if group_col not in clean_df.columns:
        st.warning(f"Колонка '{group_col}' не найдена в исходных данных.")
        return pd.DataFrame()

    # 2. dropna=False гарантирует, что ни одна группа не потеряется при группировке
    grouped = clean_df.groupby(group_col, sort=False, dropna=False)

    for group_id, group_df in grouped:
        str_group_id = str(group_id).strip()
        
        # Пропускаем только полностью пустые идентификаторы
        if not str_group_id or str_group_id.lower() in ['nan', 'none']:
            continue

        first_row = group_df.iloc[0]

        st_val = str(first_row.get('Статус', '')).lower()
        st_grp = str(first_row.get('Статус группы', '')).lower()
        date_take = str(first_row.get('Дата взятия', '')).lower()
        executor = str(first_row.get('Исполнитель', '')).lower()

        # --- ЛОГИКА ОПРЕДЕЛЕНИЯ СТАТУСА ---
        
        # A. Завершенная группа
        is_completed = (
            st_val in ['готово', 'завершено', '✅ готово'] or 
            'готово' in st_grp or '✅' in st_grp
        )

        # B. На паузе
        is_paused = (
            st_val in ['на паузе', 'пауза', '⏸ на паузе'] or 
            'пауза' in st_grp or '⏸' in st_grp
        )

        # C. В работе (есть исполнитель/дата взятия или соответствующий статус)
        is_in_work = (
            not is_completed and not is_paused and (
                st_val in ['в работе', 'взято в работу', '🔄 в работе'] or 
                'в работе' in st_grp or '🔄' in st_grp or 
                (bool(date_take) and date_take not in ['', 'nan', 'none']) or
                (bool(executor) and executor not in ['', 'nan', 'none'])
            )
        )

        # D. Выбор итогового статуса группы
        if is_completed:
            final_status = STATUS_COMPLETED
        elif is_paused:
            final_status = STATUS_PAUSED
        elif is_in_work:
            final_status = STATUS_IN_WORK
        else:
            # Все остальные варианты (включая пустые статусы) — "🆕 Доступна"
            final_status = STATUS_GROUP_AVAILABLE

        # Получаем наименование группы
        group_name = first_row.get('Наименование группы', '')
        if not group_name:
            group_name = first_row.get('Группа', str_group_id)

        summary_rows.append({
            'ID группы': str_group_id,
            'Наименование группы': group_name,
            'Количество товаров': len(group_df),
            'Статус': final_status,
            'Исполнитель': first_row.get('Исполнитель', ''),
            'Дата взятия': first_row.get('Дата взятия', ''),
            'Причина паузы': first_row.get('Причина паузы', '') if is_paused else ''
        })

    return pd.DataFrame(summary_rows)
