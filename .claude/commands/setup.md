# Настройка окружения ГринМаркет

Проведи пользователя через настройку шаг за шагом. Выполняй каждый пункт, сообщай результат, переходи к следующему только после успеха.

## Шаг 1 — Создать и заполнить `.env`

Проверь, существует ли файл:

```bash
ls .env
```

Если файл отсутствует — создай его из шаблона:

```bash
cp .env.example .env
```

Открой файл и проверь, заполнены ли переменные:

```bash
cat .env
```

Если переменные пустые — сообщи пользователю:

> Нужно заполнить файл `.env` реквизитами базы данных. Организатор должен был выдать:
> - `POSTGRES_HOST` — хост базы
> - `POSTGRES_PORT` — порт (обычно `6432`)
> - `POSTGRES_DB` — название базы
> - `POSTGRES_USER` — имя пользователя
> - `POSTGRES_PASSWORD` — пароль

Попроси пользователя ввести значения и заполни `.env` через Edit-инструмент. Не продолжай до заполнения.

## Шаг 2 — Проверить Node.js

```bash
node --version
```

Если команда не найдена:

```bash
# macOS
brew install node
```

Для Windows: попроси скачать установщик с https://nodejs.org и перезапустить терминал.

После установки проверь снова.

## Шаг 3 — Проверить CA-сертификат

```bash
ls ca.pem
```

Если файл отсутствует — скачай:

```bash
curl -o ca.pem https://storage.yandexcloud.kz/cloud-certs/CA.pem
```

Проверь, что файл скачался:

```bash
ls -lh ca.pem
```

## Шаг 4 — Проверить MCP-подключение к базе

```bash
node --version && echo "Node OK"
```

Затем проверь подключение к PostgreSQL напрямую:

```bash
python3 -c "
import psycopg2, os
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(
    host=os.getenv('POSTGRES_HOST'), port=os.getenv('POSTGRES_PORT','6432'),
    dbname=os.getenv('POSTGRES_DB'), user=os.getenv('POSTGRES_USER'),
    password=os.getenv('POSTGRES_PASSWORD'), sslmode='require'
)
cur = conn.cursor()
cur.execute(\"SELECT COUNT(*) FROM orders\")
print('Заказов в базе:', cur.fetchone()[0])
conn.close()
print('Подключение OK')
"
```

Если `psycopg2` не установлен:

```bash
pip install psycopg2-binary python-dotenv
```

## Шаг 5 — Перезапустить MCP (если Claude Code уже был открыт)

Сообщи пользователю:

> MCP-сервер подключается к базе автоматически при открытии папки в Claude Code.
> Если Claude Code был открыт до заполнения `.env` — нажми `/mcp` и перезапусти сервер `postgres`, или полностью перезапусти Claude Code.

Проверь статус MCP: выполни тестовый SQL-запрос через MCP:

```sql
SELECT COUNT(*) FROM orders;
```

## Итог

Если все шаги прошли — сообщи:

> ✅ Всё настроено. Можешь задавать вопросы по данным — например:
> - «Какая выручка за последние 30 дней?»
> - «Где средний чек выше — онлайн или магазин?»
> - «Топ-10 товаров по выручке за апрель»
