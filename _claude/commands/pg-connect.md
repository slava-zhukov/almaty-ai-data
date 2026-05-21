# Подключение к PostgreSQL Yandex Cloud (Kazakhstan)

Инстанс находится в Yandex Cloud **Казахстан** (`kz1`). Параметры подключения зашиты ниже.

## Ключевые особенности

**SSL**: Сервер использует `YCKZInternalRootCA` (казахстанский CA), которого нет в стандартных хранилищах. Нужен специальный CA-сертификат.

**CA-сертификат** — скачивается один раз с официального хранилища Yandex Cloud KZ:

```bash
curl -o ca.pem https://storage.yandexcloud.kz/cloud-certs/CA.pem
```

**MCP (Claude Code)**: `.mcp.json` использует `sslmode=verify-ca&sslrootcert=<путь к ca.pem>`. Без этого файла MCP-сервер не поднимается.

**Python/psql**: используйте `sslmode=require` без явной верификации CA — `~/.postgresql/root.crt` может содержать российский Yandex CA (`YandexCLCA`), который ломает верификацию казахстанского сервера.

## Параметры подключения

Все значения берутся из `.env`:

```
POSTGRES_HOST=<хост>.mdb.yandexcloud.kz
POSTGRES_PORT=6432
POSTGRES_DB=<база>
POSTGRES_USER=<пользователь>
POSTGRES_PASSWORD=<пароль>
```

## Python (psycopg2)

```python
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=        os.getenv("POSTGRES_HOST"),
    port=        os.getenv("POSTGRES_PORT", "6432"),
    dbname=      os.getenv("POSTGRES_DB"),
    user=        os.getenv("POSTGRES_USER"),
    password=    os.getenv("POSTGRES_PASSWORD"),
    sslmode=     "require",
    sslrootcert= "disable",
)
```

## psql

```bash
source .env
psql "postgresql://$POSTGRES_USER@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB?sslmode=require&sslrootcert=disable"
```

## Проверка подключения

```bash
python3 -c "
import psycopg2, os
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(
    host=os.getenv('POSTGRES_HOST'), port=os.getenv('POSTGRES_PORT','6432'),
    dbname=os.getenv('POSTGRES_DB'), user=os.getenv('POSTGRES_USER'),
    password=os.getenv('POSTGRES_PASSWORD'), sslmode='require', sslrootcert='disable'
)
cur = conn.cursor()
cur.execute(\"SELECT tablename FROM pg_tables WHERE schemaname='public'\")
print([r[0] for r in cur.fetchall()])
conn.close()
"
```

## Частые ошибки

**`SSL error: certificate verify failed`** — psql/psycopg2 подхватил российский Yandex CA из `~/.postgresql/root.crt`. Используйте параметры выше (`sslrootcert=disable`).

**`could not translate host name`** — DNS не резолвит `.yandexcloud.kz`. Смените DNS на `8.8.8.8` или переключите сеть.

**`connection refused`** — ваш IP не в whitelist. Сообщите организатору ваш публичный IP:
```bash
curl -s https://api.ipify.org
```
