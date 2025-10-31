# Используем полный Python образ — чтобы не было "python: not found"
FROM python:3.9

# Устанавливаем рабочую директорию
# Все файлы будут в /app/src
WORKDIR /app

# Копируем только requirements.txt сначала (для кэширования слоёв)
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код (включая папку src)
COPY . .

# Переходим в папку с кодом
WORKDIR /app/src

# === ВАЖНО: Как запускать? ===
# 1. Сначала создаём БД: python CreateDbRecors.py
# 2. Потом анализируем: python DetectAnomalyActivity.py

# Запускаем оба скрипта последовательно
CMD ["sh", "-c", "python CreateDbRecors.py && python DetectAnomalyActivity.py"]