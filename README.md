# Telegram Channel Parser Bot

Бот для мониторинга публичных Telegram каналов и репоста сообщений с ключевыми словами.

## Локальная установка и запуск

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Получение API ключей

1. Перейдите на https://my.telegram.org
2. Войдите с вашим номером телефона
3. Перейдите в "API Development Tools"
4. Создайте приложение
5. Скопируйте `api_id` и `api_hash`

### 3. Настройка

1. Скопируйте `.env.example` в `.env`:
```bash
copy .env.example .env
```

2. Заполните `.env` файл:
   - `API_ID` - ваш API ID
   - `API_HASH` - ваш API Hash
   - `PHONE` - номер телефона в международном формате (+1234567890)
   - `CHANNELS` - список каналов через запятую (@channel1,@channel2)
   - `KEYWORDS` - ключевые слова через запятую (bitcoin,crypto)
   - `TARGET_CHANNEL` - канал для репоста (@your_channel)

### 4. Первый запуск (авторизация)

```bash
python main.py
```

При первом запуске:
1. Введите код из Telegram (придет на ваш номер)
2. Если есть 2FA - введите пароль
3. Создастся файл `bot_session.session` - сохраните его!

### 5. Последующие запуски

```bash
python main.py
```

Бот начнет мониторить указанные каналы и пересылать сообщения с ключевыми словами.

## Требования

- Python 3.8+
- Номер телефона для Telegram аккаунта
- Права администратора в целевом канале

## AWS Free Tier Deployment

### Prerequisites
- AWS Account with Free Tier eligibility
- GitHub repository with this code
- Telegram API credentials

### 1. Launch EC2 Instance
1. Go to AWS EC2 Console
2. Launch Instance:
   - AMI: Ubuntu Server 22.04 LTS (free tier)
   - Instance Type: t2.micro (free tier)
   - Storage: 30GB (default)
   - Security Group: Allow SSH (22) and HTTP (80) if needed

### 2. Connect to Instance
```bash
ssh -i your-key.pem ubuntu@your-instance-ip
```

### 3. Install Dependencies
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
```

### 4. Clone Repository
```bash
git clone https://github.com/your-username/hood_attention_bot.git
cd hood_attention_bot
git checkout server-deployment
```

### 5. Setup Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 6. Configure Environment
```bash
cp .env.example .env
nano .env  # Edit with your credentials
```

### 7. First Run (Authorization)
```bash
python3 main.py
```
Follow the prompts to authorize with Telegram.

### 8. Setup Systemd Service
```bash
sudo cp hood_bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable hood_bot
sudo systemctl start hood_bot
```

### 9. Check Status
```bash
sudo systemctl status hood_bot
journalctl -u hood_bot -f  # View logs
```

### Memory Considerations
- The ML model requires ~471MB RAM
- t2.micro has 1GB RAM total
- Monitor memory usage: `free -h`
- Consider lighter models if needed

### Backup Strategy
- Session files are critical - backup regularly
- Database files should be backed up
- Consider using StringSession for cloud deployments

## AWS Free Tier Deployment

### Prerequisites
- AWS Account with Free Tier eligibility
- GitHub repository with this code
- Telegram API credentials

### 1. Launch EC2 Instance
1. Go to AWS EC2 Console
2. Launch Instance:
   - AMI: Ubuntu Server 22.04 LTS (free tier)
   - Instance Type: t2.micro (free tier)
   - Storage: 30GB (default)
   - Security Group: Allow SSH (22) and HTTP (80) if needed

### 2. Connect to Instance
```bash
ssh -i your-key.pem ubuntu@your-instance-ip
```

### 3. Install Dependencies
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
```

### 4. Clone Repository
```bash
git clone https://github.com/your-username/hood_attention_bot.git
cd hood_attention_bot
git checkout server-deployment
```

### 5. Setup Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 6. Configure Environment
```bash
cp .env.example .env
nano .env  # Edit with your credentials
```

### 7. First Run (Authorization)
```bash
python3 main.py
```
Follow the prompts to authorize with Telegram.
