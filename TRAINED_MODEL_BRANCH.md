# 🧠 Trained Model Branch

Ця гілка містить **навчену модель** та **базу даних** з прикладами користувачів.

## 📊 Що зберігається тут:

### ✅ База даних (БД)
- `bot_config.db` - налаштування користувачів, приклади, ключові слова
- Містить позитивні та негативні ML приклади
- Оптимізовані дані по районах

### ✅ ML модель
- Завантажена модель sentence-transformers
- Кеш embeddings для швидшої роботи

### ❌ НЕ зберігається
- `*.session` - сесії Telegram (приватні)
- `config.py` - API ключі (приватні)
- `.env` - секретні змінні

---

## 🔄 Робочий процес

### 1. Перша робота (клонування)

```bash
# Клонуємо репозиторій
git clone https://github.com/prodavecmacdrive/hood_attention_bot.git
cd hood_attention_bot

# Переходимо на гілку з навченою моделлю
git checkout trained-model

# Створюємо config.py
cp config.example.py config.py
# Заповнюємо свої API ключі

# Встановлюємо залежності
pip install -r requirements.txt

# Запускаємо бота - БД вже з прикладами!
python main.py
```

### 2. Після тренування (збереження прогресу)

```bash
# Після додавання нових прикладів через бота:

# Додаємо змінену БД
git add bot_config.db

# Комітимо з описом що додано
git commit -m "🧠 Додано 5 нових ML прикладів для Салтівки"

# Пушимо в trained-model гілку
git push origin trained-model
```

### 3. Оновлення на іншій машині

```bash
# На іншому комп'ютері
git checkout trained-model
git pull origin trained-model

# Тепер у вас свіжа БД з новими прикладами!
python main.py
```

---

## 📝 Приклади комітів

**Хороші коміти:**
```bash
git commit -m "🧠 Додано 10 прикладів для району Жуки"
git commit -m "🎯 Оптимізовано дані для Салтівського району"
git commit -m "👎 Додано 5 негативних прикладів (дизлайки)"
git commit -m "📊 Після тижня роботи: 50 прикладів, 3 райони"
```

**Погані коміти:**
```bash
git commit -m "update"  # ❌ Не інформативно
git commit -m "db"      # ❌ Що саме змінено?
```

---

## 🔀 Синхронізація з main

Іноді потрібно оновити код з `main` гілки:

```bash
# Переходимо на trained-model
git checkout trained-model

# Зливаємо зміни з main (код)
git merge main

# Якщо є конфлікти - вирішуємо їх
# БД та ML дані залишаться з trained-model

# Пушимо
git push origin trained-model
```

---

## 📊 Статистика БД

Щоб побачити що в БД:

```bash
# Запустити тест
python -c "from database import Database; db = Database(); 
print(f'Користувачів: {len(db.get_all_active_users())}');
print(f'Каналів: {len(db.get_channels())}');"
```

---

## ⚠️ Важливо!

1. **НЕ комітити** `config.py` та `*.session` файли
2. **Перевіряти** що комітиться перед push: `git status`
3. **Робити backup** БД перед великими змінами
4. **Описувати** в коміті що навчали

---

## 🎯 Використання

### Сценарій 1: Робота на одному ПК

```bash
# Щодня додаєте приклади через бота
# Раз на тиждень комітите:
git add bot_config.db
git commit -m "🧠 Тиждень навчання: +20 прикладів"
git push origin trained-model
```

### Сценарій 2: Робота на декількох ПК

**На робочому ПК:**
```bash
# Навчили бота
git add bot_config.db
git commit -m "🧠 Робочий ПК: додано 10 прикладів"
git push origin trained-model
```

**Вдома:**
```bash
# Отримуємо свіжі дані
git pull origin trained-model
# Продовжуємо навчання з тими самими даними
```

### Сценарій 3: Backup перед експериментом

```bash
# Перед великими змінами
git add bot_config.db
git commit -m "💾 Backup перед тестуванням нової оптимізації"
git push origin trained-model

# Експериментуємо...
# Якщо щось пішло не так:
git checkout bot_config.db  # Відкатити зміни
```

---

## 🔄 Автоматизація

Можна додати скрипт для автоматичного збереження:

```bash
# save_training.sh
#!/bin/bash
git add bot_config.db
git commit -m "🧠 Auto-save: $(date +'%Y-%m-%d %H:%M')"
git push origin trained-model
```

Або Windows PowerShell:
```powershell
# save_training.ps1
git add bot_config.db
git commit -m "🧠 Auto-save: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
git push origin trained-model
```

---

## 📈 Моніторинг прогресу

```bash
# Подивитись історію навчання
git log --oneline --grep="🧠"

# Подивитись коли була остання синхронізація
git log -1 --format="%cd" --date=relative
```

---

## 🆘 Troubleshooting

**Проблема:** `error: failed to push some refs`

**Рішення:**
```bash
# Спочатку отримати зміни
git pull origin trained-model --rebase

# Потім запушити
git push origin trained-model
```

**Проблема:** Забув що змінив в БД

**Рішення:**
```bash
# Подивитись останні коміти
git log -5 --oneline

# Подивитись конкретний коміт
git show <commit-hash>
```

---

Ця гілка дозволяє зберігати прогрес навчання та синхронізувати між пристроями! 🚀
