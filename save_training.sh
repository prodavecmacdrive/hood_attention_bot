#!/bin/bash
# Скрипт для швидкого збереження прогресу навчання

timestamp=$(date +'%Y-%m-%d %H:%M')

echo "🧠 Збереження прогресу навчання..."

# Перевірка що ми на правильній гілці
current_branch=$(git branch --show-current)
if [ "$current_branch" != "trained-model" ]; then
    echo "⚠️  Ви не на гілці trained-model! Переключаюсь..."
    git checkout trained-model
fi

# Додаємо БД
git add bot_config.db

# Питаємо опис (опціонально)
echo -n "Опис змін (Enter для автоматичного): "
read description

if [ -z "$description" ]; then
    description="Auto-save: $timestamp"
else
    description="$description ($timestamp)"
fi

# Комітимо
git commit -m "🧠 $description"

# Пушимо
echo ""
echo "📤 Завантаження на GitHub..."
git push origin trained-model

echo ""
echo "✅ Готово! Прогрес збережено."
echo "🔗 https://github.com/prodavecmacdrive/hood_attention_bot/tree/trained-model"
