FROM python:3.11-slim as builder

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --user --no-cache-dir -r requirements.txt

# Финальный образ
FROM python:3.11-slim

# Установка необходимых системных пакетов
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копируем установленные пакеты
COPY --from=builder /root/.local /root/.local

# Добавляем /root/.local/bin в PATH
ENV PATH=/root/.local/bin:$PATH

# Копируем код
COPY . .

# Проверка установки основных компонентов
RUN python -c "import torch, requests; print('✅ torch и requests установлены')"

# Запуск приложения
CMD ["python", "-m", "bot.main"]
