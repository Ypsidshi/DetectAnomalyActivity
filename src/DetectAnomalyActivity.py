import pandas as pd
import sqlite3
import numpy as np
from sklearn.ensemble import IsolationForest  # pip install scikit-learn
from datetime import datetime

# Подключение к БД ( SQLite для прототипа)
conn = sqlite3.connect('logs.db')  # путь до БД

# Извлечение данных из таблицы file_actions
# Предполагаемые столбцы: user_id (str), action_type (str, e.g. 'open', 'create'), file_id (str), timestamp (str в формате ISO), ip (str)
query = """
SELECT user_id, action_type, file_id, timestamp, ip
FROM file_actions
"""
df = pd.read_sql_query(query, conn)
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Добавляем фичи для анализа
df['hour'] = df['timestamp'].dt.hour
df['day_of_week'] = df['timestamp'].dt.dayofweek  # 0=Понедельник, 6=Воскресенье
df['is_weekend'] = df['day_of_week'].isin([5, 6])
df['is_night'] = (df['hour'] < 8) | (df['hour'] > 20)


# Шаг 1: Rule-based детекция
# Определяем подозрительные действия по правилам
def apply_rules(df):
    suspicious = []

    # Правило 1: Более 50 действий за час (группируем по user_id и часу)
    df['hour_group'] = df['timestamp'].dt.floor('H')
    actions_per_hour = df.groupby(['user_id', 'hour_group']).size().reset_index(name='count')
    high_activity = actions_per_hour[actions_per_hour['count'] > 50]
    if not high_activity.empty:
        suspicious.append({
            'rule': 'High activity per hour',
            'users': high_activity['user_id'].unique().tolist(),
            'details': high_activity
        })

    # Правило 2: Действия ночью или в выходные
    night_weekend_actions = df[(df['is_night'] | df['is_weekend'])].groupby('user_id').size().reset_index(name='count')
    high_night_activity = night_weekend_actions[
        night_weekend_actions['count'] > 20]  # Порог arbitrary, настрой под данные
    if not high_night_activity.empty:
        suspicious.append({
            'rule': 'High night/weekend activity',
            'users': high_night_activity['user_id'].unique().tolist(),
            'details': high_night_activity
        })

    # Правило 3: Необычный IP (предполагаем, что у каждого user есть 'normal_ips' - для примера hardcoded)
    normal_ips = {'user1': ['192.168.1.1'], 'user2': ['192.168.1.2']}  # Замени на реальные данные из БД
    unusual_ip = df[~df.apply(lambda row: row['ip'] in normal_ips.get(row['user_id'], []), axis=1)]
    if not unusual_ip.empty:
        suspicious.append({
            'rule': 'Unusual IP',
            'users': unusual_ip['user_id'].unique().tolist(),
            'details': unusual_ip
        })

    return suspicious


# Применяем правила
rule_suspicious = apply_rules(df)
print("Rule-based suspicious activities:")
for item in rule_suspicious:
    print(f"{item['rule']}: Users {item['users']}")

# Шаг 2: Anomaly detection с Isolation Forest
# Подготавливаем фичи для ML: агрегируем по user_id (кол-во действий, средний час, etc.)
user_agg = df.groupby('user_id').agg({
    'action_type': 'count',  # total actions
    'hour': ['mean', 'std'],  # average and variance of hours
    'is_night': 'sum',  # night actions
    'is_weekend': 'sum',  # weekend actions
    'ip': 'nunique'  # unique IPs
}).reset_index()
user_agg.columns = ['user_id', 'total_actions', 'avg_hour', 'std_hour', 'night_actions', 'weekend_actions',
                    'unique_ips']

# Фичи для модели (исключаем user_id)
features = user_agg.drop('user_id', axis=1).values

# Модель Isolation Forest (unsupervised anomaly detection)
model = IsolationForest(contamination=0.1, random_state=42)  # contamination - ожидаемая доля аномалий
model.fit(features)

# Предсказания: -1 = anomaly, 1 = normal
user_agg['anomaly'] = model.predict(features)
anomalies = user_agg[user_agg['anomaly'] == -1]

print("\nAnomaly detection results:")
print(anomalies[['user_id', 'total_actions', 'night_actions']])  # Пример вывода

# Комбинированный вывод: пользователи, флагированные правилами ИЛИ аномалиями
all_suspicious_users = set()
for item in rule_suspicious:
    all_suspicious_users.update(item['users'])
all_suspicious_users.update(anomalies['user_id'].tolist())

print("\nAll suspicious users:", list(all_suspicious_users))

# Закрываем соединение
conn.close()