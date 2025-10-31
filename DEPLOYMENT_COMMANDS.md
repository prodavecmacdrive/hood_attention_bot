# AWS EC2 Deployment Commands

## Шаг 3: Установка зависимостей

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Python и необходимых пакетов
sudo apt install -y python3 python3-pip python3-venv git htop

# Проверка версий
python3 --version
git --version
```

## Шаг 4: Клонирование репозитория

```bash
# Клонирование репозитория
cd ~
git clone https://github.com/prodavecmacdrive/hood_attention_bot.git
cd hood_attention_bot

# Переключение на ветку server-deployment
git checkout server-deployment

# Проверка текущей ветки
git branch
```

## Шаг 5: Настройка виртуального окружения

```bash
# Создание виртуального окружения
python3 -m venv venv

# Активация виртуального окружения
source venv/bin/activate

# Обновление pip
pip install --upgrade pip

# Установка зависимостей
pip install -r requirements.txt

# Проверка установленных пакетов
pip list
```

## Шаг 6: Настройка переменных окружения

```bash
# Копирование шаблона .env
cp .env.example .env

# Редактирование .env файла
nano .env
```

**Заполните следующие переменные в .env:**
```
API_ID=ваш_api_id
API_HASH=ваш_api_hash
PHONE=+ваш_номер_телефона
BOT_TOKEN=ваш_bot_token
CHANNELS=@channel1,@channel2
KEYWORDS=keyword1,keyword2
TARGET_CHANNEL=@your_target_channel
```

**Сохранение в nano:** `Ctrl+O`, `Enter`, `Ctrl+X`

## Шаг 7: Первый запуск и авторизация

```bash
# Активация виртуального окружения (если не активно)
source venv/bin/activate

# Запуск бота
python3 main.py
```

**Следуйте инструкциям:**
1. Введите код из Telegram (придет на ваш номер)
2. Если есть 2FA - введите пароль
3. Дождитесь сообщения "✅ Бот успешно запущен"
4. Нажмите `Ctrl+C` для остановки

## Шаг 8: Настройка systemd службы

```bash
# Обновление путей в hood_bot.service
nano hood_bot.service
```

**Проверьте/измените следующие строки:**
```
User=ubuntu
WorkingDirectory=/home/ubuntu/hood_attention_bot
ExecStart=/home/ubuntu/hood_attention_bot/start.sh
```

```bash
# Сделать start.sh исполняемым
chmod +x start.sh

# Копирование файла службы
sudo cp hood_bot.service /etc/systemd/system/

# Перезагрузка systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable hood_bot

# Запуск службы
sudo systemctl start hood_bot

# Проверка статуса
sudo systemctl status hood_bot
```

## Шаг 9: Мониторинг и проверка

```bash
# Просмотр логов в реальном времени
journalctl -u hood_bot -f

# Просмотр последних 100 строк логов
journalctl -u hood_bot -n 100

# Проверка использования памяти
free -h
htop

# Проверка работы бота
ps aux | grep python
```

## Полезные команды для управления

```bash
# Остановка бота
sudo systemctl stop hood_bot

# Перезапуск бота
sudo systemctl restart hood_bot

# Просмотр статуса
sudo systemctl status hood_bot

# Отключение автозапуска
sudo systemctl disable hood_bot

# Обновление кода из GitHub
cd ~/hood_attention_bot
git pull origin server-deployment
sudo systemctl restart hood_bot
```

## Резервное копирование

```bash
# Создание резервной копии базы данных и сессий
cd ~/hood_attention_bot
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz *.db *.session

# Скачивание резервной копии на локальный компьютер (запустить на локальной машине)
# scp -i your-key.pem ubuntu@your-instance-ip:~/hood_attention_bot/backup_*.tar.gz ./
```

## Мониторинг памяти

```bash
# Проверка использования памяти ML моделью
watch -n 5 'free -h && echo "---" && ps aux | grep python | grep -v grep'

# Если памяти недостаточно:
# 1. Рассмотрите использование более легкой модели
# 2. Включите swap (swap file)
# 3. Оптимизируйте код для освобождения памяти
```

## Создание swap файла (если нужно)

```bash
# Создание 2GB swap файла
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Проверка swap
sudo swapon --show
free -h

# Сделать swap постоянным
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```
