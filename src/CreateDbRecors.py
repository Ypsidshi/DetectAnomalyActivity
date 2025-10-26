import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import random

conn = sqlite3.connect('logs.db')
cursor = conn.cursor()

# Создаем таблицу
cursor.execute('''
CREATE TABLE IF NOT EXISTS file_actions (
    user_id TEXT,
    action_type TEXT,
    file_id TEXT,
    timestamp TEXT,
    ip TEXT
)
''')

# Генерируем sample данные
users = ['user1', 'user2', 'user3']
actions = ['open', 'create', 'close', 'delete']
ips = ['192.168.1.1', '192.168.1.2', '10.0.0.1']  # unusual IP

data = []
start_time = datetime.now() - timedelta(days=7)
for _ in range(1000):  # 1000 записей
    user = random.choice(users)
    action = random.choice(actions)
    file = f'file_{random.randint(1,100)}'
    ts = start_time + timedelta(minutes=random.randint(0, 10080))
    ip = random.choice(ips) if user == 'user3' else ips[0]  # user3 имеет unusual IP
    data.append((user, action, file, ts.isoformat(), ip))

df_sample = pd.DataFrame(data, columns=['user_id', 'action_type', 'file_id', 'timestamp', 'ip'])
df_sample.to_sql('file_actions', conn, if_exists='replace', index=False)

conn.close()
print("Test DB created.")