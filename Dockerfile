# оф.образ Python
FROM python:3.8-slim

# робоча директорія
WORKDIR /app

# залежності
RUN pip install pymongo

# Копія файлів у контейнер
COPY . /app

# робоча директорія
WORKDIR /app

# Запуск скрипта
CMD ["python", "main.py"]
