# Базовый образ
FROM python:3.9-slim

# Создаем директорию для логов и настраиваем права
RUN mkdir -p /app/logs && \
    chmod 755 /app/logs

# Проверяем создание директории
RUN ls -la /app/logs

# Устанавливаем системные зависимости заранее
RUN apt-get update && \
    apt-get install -y python3-dev && \
    ln -sf /usr/bin/python3 /usr/bin/python

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем только requirements.txt для установки зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем gunicorn
RUN pip install gunicorn==20.1.0

# Копируем остальной код проекта
COPY . .

# Запускаем gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "foodgram.wsgi"]
