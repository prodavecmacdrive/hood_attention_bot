#!/usr/bin/env pwsh
# Скрипт для швидкого збереження прогресу навчання

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"

Write-Host "🧠 Збереження прогресу навчання..." -ForegroundColor Cyan

# Перевірка що ми на правильній гілці
$currentBranch = git branch --show-current
if ($currentBranch -ne "trained-model") {
    Write-Host "⚠️  Ви не на гілці trained-model! Переключаюсь..." -ForegroundColor Yellow
    git checkout trained-model
}

# Додаємо БД
git add bot_config.db

# Питаємо опис (опціонально)
Write-Host "`nОпис змін (Enter для автоматичного): " -NoNewline -ForegroundColor Green
$description = Read-Host

if ([string]::IsNullOrWhiteSpace($description)) {
    $description = "Auto-save: $timestamp"
} else {
    $description = "$description ($timestamp)"
}

# Комітимо
git commit -m "🧠 $description"

# Пушимо
Write-Host "`n📤 Завантаження на GitHub..." -ForegroundColor Cyan
git push origin trained-model

Write-Host "`n✅ Готово! Прогрес збережено." -ForegroundColor Green
Write-Host "🔗 https://github.com/prodavecmacdrive/hood_attention_bot/tree/trained-model" -ForegroundColor Blue
