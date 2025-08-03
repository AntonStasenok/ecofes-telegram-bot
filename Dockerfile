FROM python:3.11-slim as builder

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    python3-distutils \
    && rm -rf /var/lib/apt/lists/*

# Установка pip и зависимостей
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Финальный образ
FROM python:3.11-slim

# Копируем только установленные пакеты
COPY --from=builder /root/.local /root/.local

# Рабочая директория
WORKDIR /app

# Копируем код
COPY . .

# Добавляем /root/.local/bin в PATH
ENV PATH=/root/.local/bin:$PATH

# Запуск
CMD ["python", "-m", "bot.main"]
