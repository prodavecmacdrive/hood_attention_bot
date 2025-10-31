# 🚀 Быстрый деплой на AWS EC2

## Шаг 1: Подключение к серверу

### Вариант A: Через PowerShell (с вашей машины)

1. Откройте PowerShell в папке проекта
2. Отредактируйте `connect_to_server.ps1`:
   - Замените `YOUR_EC2_PUBLIC_IP` на реальный IP вашего EC2
3. Запустите:
   ```powershell
   .\connect_to_server.ps1
   ```

### Вариант B: Через AWS Console (в браузере)

1. AWS Console → EC2 → Instances
2. Выберите инстанс `attention-bot`
3. Кнопка **"Connect"** → **"EC2 Instance Connect"**
4. **"Connect"** → откроется терминал в браузере

---

## Шаг 2: Автоматический деплой на сервере

После подключения к серверу выполните **одну команду**:

```bash
curl -o deploy.sh https://raw.githubusercontent.com/prodavecmacdrive/hood_attention_bot/server-deployment/deploy_on_server.sh && chmod +x deploy.sh && ./deploy.sh
```

Скрипт автоматически:
- ✅ Обновит систему
- ✅ Установит все зависимости
- ✅ Склонирует репозиторий
- ✅ Создаст виртуальное окружение
- ✅ Установит Python пакеты
- ✅ Создаст .env файл из шаблона
- ✅ Настроит systemd службу
- ✅ Запустит бота

### ⚠️ Важно:

Когда скрипт попросит отредактировать `.env` файл:

```bash
nano ~/hood_attention_bot/.env
```

Заполните:
```env
API_ID=ваш_реальный_api_id
API_HASH=ваш_реальный_api_hash
PHONE=+ваш_номер_телефона
BOT_TOKEN=ваш_bot_token
CHANNELS=@channel1,@channel2
KEYWORDS=keyword1,keyword2
TARGET_CHANNEL=@your_target_channel
```

**Сохранение:** `Ctrl+O` → `Enter` → `Ctrl+X`

---

## Шаг 3: Первая авторизация (если нужно)

Если это первый запуск, нужно авторизоваться:

```bash
cd ~/hood_attention_bot
source venv/bin/activate
python3 main.py
```

1. Введите код из Telegram
2. Если есть 2FA - введите пароль
3. После успешной авторизации: `Ctrl+C`
4. Перезапустите службу:
   ```bash
   sudo systemctl restart hood_bot
   ```

---

## Шаг 4: Проверка работы

```bash
# Статус службы
sudo systemctl status hood_bot

# Логи в реальном времени
journalctl -u hood_bot -f

# Использование памяти
free -h
```

---

## 🛠️ Полезные команды

```bash
# Перезапуск бота
sudo systemctl restart hood_bot

# Остановка бота
sudo systemctl stop hood_bot

# Запуск бота
sudo systemctl start hood_bot

# Обновление кода с GitHub
cd ~/hood_attention_bot
git pull origin server-deployment
sudo systemctl restart hood_bot

# Просмотр последних 100 строк логов
journalctl -u hood_bot -n 100

# Резервная копия
cd ~/hood_attention_bot
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz *.db *.session
```

---

## 📋 Где взять данные для .env

- **API_ID и API_HASH**: https://my.telegram.org → API Development Tools
- **BOT_TOKEN**: Telegram → @BotFather → /newbot
- **PHONE**: Ваш номер в формате +1234567890
- **CHANNELS**: Каналы для мониторинга (через запятую)
- **KEYWORDS**: Ключевые слова для поиска (через запятую)
- **TARGET_CHANNEL**: Канал для репоста (нужны права админа)

---

## ❗ Troubleshooting

### Проблема: Недостаточно памяти

```bash
# Создать swap файл 2GB
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Проблема: Бот не запускается

```bash
# Проверить логи на ошибки
journalctl -u hood_bot -n 100

# Проверить .env файл
cat ~/hood_attention_bot/.env

# Попробовать запустить вручную
cd ~/hood_attention_bot
source venv/bin/activate
python3 main.py
```

### Проблема: Нет прав на канал

Убедитесь, что бот (или ваш аккаунт) имеет права администратора в `TARGET_CHANNEL`.
