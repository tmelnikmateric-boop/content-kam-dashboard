import datetime
import pandas as pd
import streamlit as st

# ==========================================
# КОНСТАНТЫ СТАТУСОВ
# ==========================================
# Статусы для товаров (Загруженные данные контента)
STATUS_ITEM_NEW = "🆕 Новый"

# Статусы для сводной таблицы групп (👥 Рабочие группы контента)
STATUS_GROUP_AVAILABLE = "🆕 Доступна"
STATUS_IN_WORK = "🔄 В работе"
STATUS_PAUSED = "⏸ На паузе"
STATUS_COMPLETED = "✅ Готово"


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

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mask = df['ID группы'].isin(target_ids) if 'ID группы' in df.columns else df.index.isin(target_ids)

    # Присвоение статуса "🔄 В работе"
    df.loc[mask, 'Статус'] = STATUS_IN_WORK
    if 'Статус группы' in df.columns:
        df.loc[mask, 'Статус группы'] = STATUS_IN_WORK

    df.loc[mask, 'Исполнитель'] = executor_name.strip()
    df.loc[mask, 'Дата взятия'] = now_str
    
    # Очистка полей паузы при старте работы
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
    mask = df['ID группы'].isin(target_ids) if 'ID группы' in df.columns else df.index.isin(target_ids)

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
    
    Логика статусов группы:
    - Новая/Не начатая группа -> '🆕 Доступна'
    - В работе -> '🔄 В работе'
    - На паузе -> '⏸ На паузе'
    - Завершена -> '✅ Готово'
    """
    if df.empty:
        return pd.DataFrame()

    summary_rows = []

    # Определяем колонку с ID группы
    group_col = 'ID группы' if 'ID группы' in df.columns else 'Группа'
    grouped = df.groupby(group_col, sort=False)

    for group_id, group_df in grouped:
        first_row = group_df.iloc[0]

        st_val = str(first_row.get('Статус', '')).strip().lower()
        st_grp = str(first_row.get('Статус группы', '')).strip().lower()
        date_take = first_row.get('Дата взятия', '')
        
        # 1. Проверка на Завершено
        is_completed = (
            st_val in ['готово', 'завершено', '✅ готово'] or 
            'готово' in st_grp or '✅' in st_grp
        )
        
        # 2. Проверка на Паузу
        is_paused = (
            st_val in ['на паузе', 'пауза', '⏸ на паузе'] or 
            'пауза' in st_grp or '⏸' in st_grp
        )
        
        # 3. Проверка на В работе
        is_in_work = (
            not is_completed and not is_paused and (
                st_val in ['в работе', 'взято в работу', '🔄 в работе'] or 
                'в работе' in st_grp or '🔄' in st_grp or bool(date_take)
            )
        )

        # 4. Проверка на Новую группу (Доступна)
        is_new = (
            not is_completed and not is_paused and not is_in_work and (
                st_val in ['', 'nan', 'none', 'новый', '🆕 новый', 'доступна', '🆕 доступна', 'не начато'] or
                st_grp in ['', 'nan', 'none', 'доступна', '🆕 доступна', 'не начато']
            )
        )

        # Присвоение итогового статуса для таблицы "👥 Рабочие группы контента"
        if is_completed:
            final_status = STATUS_COMPLETED
        elif is_paused:
            final_status = STATUS_PAUSED
        elif is_in_work:
            final_status = STATUS_IN_WORK
        else:
            # Для всех новых / непомеченных групп
            final_status = STATUS_GROUP_AVAILABLE

        summary_rows.append({
            'ID группы': group_id,
            'Наименование группы': first_row.get('Наименование группы', first_row.get('Группа', '')),
            'Количество товаров': len(group_df),
            'Статус': final_status,
            'Исполнитель': first_row.get('Исполнитель', ''),
            'Дата взятия': first_row.get('Дата взятия', ''),
            'Причина паузы': first_row.get('Причина паузы', '') if is_paused else ''
        })

    summary_df = pd.DataFrame(summary_rows)
    return summary_df
