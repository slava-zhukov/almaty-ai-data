# Настройка ежедневного отчёта ГринМаркет

Автоматизация работает по схеме:
- **Claude routine** (10:00 MSK) запускает GitHub Actions через API
- **GitHub Actions** подключается к PostgreSQL, сохраняет данные как артефакт
- **Claude routine** скачивает артефакт, генерирует саммари и отправляет в Telegram

---

## 0. Создать GitHub-репозиторий и опубликовать код

Автоматизация запускается через GitHub Actions — значит, код должен лежать в твоём репозитории на GitHub.

### Создать репозиторий

1. Открой [github.com/new](https://github.com/new)
2. Заполни:
   - **Repository name** — например, `greenmarket-reports`
   - Видимость — **Private** (рекомендуется: в репо будут секреты с паролями)
3. **Не добавляй** README, .gitignore или лицензию — репозиторий должен быть пустым
4. Нажми **Create repository**
5. Скопируй ссылку вида `https://github.com/<твой-логин>/greenmarket-reports.git`

### Подключить репозиторий и запушить код

В терминале (замени URL на свой):

```bash
git remote add origin https://github.com/<твой-логин>/greenmarket-reports.git
git branch -M main
git push -u origin main
```

Если GitHub запрашивает авторизацию — войди через браузер или введи Personal Access Token (создаётся в шаге 2).

### Включить GitHub Actions

Открой репозиторий на GitHub → вкладка **Actions** → нажми **I understand my workflows, go ahead and enable them**.

---

## 1. GitHub — секреты репозитория

`github.com/<репо>/settings/secrets/actions` → **New repository secret**

| Секрет | Значение |
|---|---|
| `POSTGRES_HOST` | хост базы данных |
| `POSTGRES_PORT` | порт (обычно `6432`) |
| `POSTGRES_DB` | название базы |
| `POSTGRES_USER` | пользователь |
| `POSTGRES_PASSWORD` | пароль |

---

## 2. GitHub — Personal Access Token (PAT)

1. Открой [github.com/settings/tokens](https://github.com/settings/tokens) → **Generate new token (classic)**
2. Отметь права: `repo` + `workflow`
3. Скопируй токен — понадобится в шаге 4

---

## 3. Telegram — бот и канал

1. Создай бота через [@BotFather](https://t.me/BotFather) → `/newbot` → скопируй токен
2. Добавь бота в канал как **администратора** с правом отправки сообщений
3. Узнай `chat_id`: отправь любое сообщение в канал, затем открой:
   ```
   https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
   ```
   Найди `"chat": {"id": ...}` — это и есть `TELEGRAM_CHAT_ID`

---

## 4. Claude Code — подключить GitHub

В терминале:
```bash
brew install gh
gh auth login
```
Затем в Claude Code:
```
/web-setup
```

---

## 5. Claude Code — создать окружение AICheck

Открой [claude.ai](https://claude.ai) → **Environments** → **New environment**

| Поле | Значение |
|---|---|
| Name | `AICheck` |
| Network access | **Full** ← обязательно |

**Environment variables:**
```
POSTGRES_HOST=...
POSTGRES_PORT=...
POSTGRES_DB=...
POSTGRES_USER=...
POSTGRES_PASSWORD=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
GITHUB_TOKEN=...    ← PAT из шага 2
```

Setup script — оставить пустым.

---

## 6. Claude Code — создать routine

Открой [claude.ai/code/routines](https://claude.ai/code/routines) → **New routine**

| Поле | Значение |
|---|---|
| Name | `ГринМаркет — ежедневный отчёт` |
| Schedule | `0 7 * * *` (10:00 MSK = 07:00 UTC) |
| Environment | `AICheck` |
| Repository | `https://github.com/<owner>/<repo>` |
| Model | `claude-sonnet-4-6` |

**Промпт:**
```
Run the daily GreenMarket report:

1. Trigger GitHub Actions workflow:
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" -H "Accept: application/vnd.github.v3+json" https://api.github.com/repos/<owner>/<repo>/actions/workflows/daily_report.yml/dispatches -d '{"ref":"main"}'
Sleep 5 seconds, then get the run ID:
RUN_ID=$(curl -s -H "Authorization: token $GITHUB_TOKEN" -H "Accept: application/vnd.github.v3+json" "https://api.github.com/repos/<owner>/<repo>/actions/runs?per_page=1" | python3 -c "import sys,json; print(json.load(sys.stdin)['workflow_runs'][0]['id'])")

2. Poll until workflow completes (check every 15s, timeout 3 min):
STATUS=$(curl -s -H "Authorization: token $GITHUB_TOKEN" -H "Accept: application/vnd.github.v3+json" "https://api.github.com/repos/<owner>/<repo>/actions/runs/$RUN_ID" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")

3. Download artifact:
ARTIFACT_URL=$(curl -s -H "Authorization: token $GITHUB_TOKEN" -H "Accept: application/vnd.github.v3+json" "https://api.github.com/repos/<owner>/<repo>/actions/runs/$RUN_ID/artifacts" | python3 -c "import sys,json; print(json.load(sys.stdin)['artifacts'][0]['archive_download_url'])")
curl -sL -H "Authorization: token $GITHUB_TOKEN" "$ARTIFACT_URL" -o report.zip
unzip -p report.zip > report_data.json

4. Read report_data.json. Write a 4-6 sentence business summary in Russian with emojis (highlight revenue change vs previous day, top category, channel split).

5. Send to Telegram:
pip install -q requests && python daily_report.py send --message "YOUR_SUMMARY"

6. Confirm sent.
```

---

## Проверка

Запусти routine вручную через [claude.ai/code/routines](https://claude.ai/code/routines) — через 2-3 минуты сообщение появится в Telegram-канале.
