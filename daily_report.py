#!/usr/bin/env python3
"""
Ежедневный отчёт ГринМаркет.

Режимы:
  python daily_report.py fetch   — забрать данные из PostgreSQL, сохранить report_data.json
  python daily_report.py send    — прочитать report_data.json, отправить в Telegram (используется в routine)
  python daily_report.py full    — полный цикл через Claude API (fetch + generate + send)
"""

import os
import json
from datetime import date, timedelta
from pathlib import Path

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv()

CA_PEM = Path(__file__).parent / "ca.pem"


def get_connection():
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        sslmode="require",
    )


def fetch_yesterday_stats() -> dict:
    yesterday  = date.today() - timedelta(days=1)
    day_before = yesterday - timedelta(days=1)

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*), ROUND(SUM(total_amount)::numeric, 0), ROUND(AVG(total_amount)::numeric, 0)
            FROM orders WHERE ordered_at::date = %s
        """, (yesterday,))
        orders, revenue, avg_order = cur.fetchone()

        cur.execute("""
            SELECT COUNT(*), ROUND(SUM(total_amount)::numeric, 0)
            FROM orders WHERE ordered_at::date = %s
        """, (day_before,))
        prev_orders, prev_revenue = cur.fetchone()

        cur.execute("""
            SELECT channel, COUNT(*), ROUND(SUM(total_amount)::numeric, 0)
            FROM orders WHERE ordered_at::date = %s
            GROUP BY channel ORDER BY SUM(total_amount) DESC
        """, (yesterday,))
        channels = [{"channel": r[0], "orders": int(r[1]), "revenue": int(r[2])} for r in cur.fetchall()]

        cur.execute("""
            SELECT p.category, ROUND(SUM(oi.line_total)::numeric, 0) AS rev
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            JOIN products p ON p.id = oi.product_id
            WHERE o.ordered_at::date = %s
            GROUP BY p.category ORDER BY rev DESC LIMIT 5
        """, (yesterday,))
        categories = [{"category": r[0], "revenue": int(r[1])} for r in cur.fetchall()]

    return {
        "date": str(yesterday),
        "orders": int(orders),
        "revenue": int(revenue),
        "avg_order": int(avg_order),
        "prev_orders": int(prev_orders),
        "prev_revenue": int(prev_revenue),
        "channels": channels,
        "categories": categories,
    }


def generate_summary_via_api(stats: dict) -> str:
    import anthropic
    orders_delta = stats["orders"] - stats["prev_orders"]
    revenue_delta_pct = (
        round((stats["revenue"] - stats["prev_revenue"]) / stats["prev_revenue"] * 100, 1)
        if stats["prev_revenue"] else 0
    )
    prompt = f"""Составь краткий ежедневный отчёт для топ-менеджера розничной сети ГринМаркет.

Данные за {stats["date"]}:
- Заказов: {stats["orders"]} (день назад: {stats["prev_orders"]}, изменение: {orders_delta:+d})
- Выручка: {stats["revenue"]:,} ₽ (день назад: {stats["prev_revenue"]:,} ₽, изменение: {revenue_delta_pct:+.1f}%)
- Средний чек: {stats["avg_order"]:,} ₽

По каналам:
{chr(10).join(f"- {c['channel']}: {c['orders']} заказов, {c['revenue']:,} ₽" for c in stats["channels"])}

Топ категории по выручке:
{chr(10).join(f"- {c['category']}: {c['revenue']:,} ₽" for c in stats["categories"])}

Требования:
- 4-6 предложений, деловой тон, без технических деталей
- Выдели главное: рост или падение, что бросается в глаза
- Используй эмодзи (📈 📉 💰 🛒)"""

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def send_to_telegram(text: str):
    url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage"
    resp = requests.post(url, json={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": text}, timeout=30)
    resp.raise_for_status()


DATA_FILE = Path(__file__).parent / "report_data.json"

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "full"

    if cmd == "fetch":
        # Только забрать данные из PostgreSQL и сохранить файл (для GitHub Actions)
        print("Собираю статистику за вчера...")
        stats = fetch_yesterday_stats()
        DATA_FILE.write_text(json.dumps(stats, ensure_ascii=False, indent=2))
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        print(f"\nСохранено в {DATA_FILE}")

    elif cmd == "send":
        # Прочитать готовые данные и отправить в Telegram (для Claude routine)
        stats = json.loads(DATA_FILE.read_text())
        print("Данные загружены:", json.dumps(stats, ensure_ascii=False, indent=2))
        print("\nОтправляю в Telegram...")
        # Саммари передаётся как аргумент: python daily_report.py send --message "текст"
        import argparse
        p = argparse.ArgumentParser()
        p.add_argument("send")
        p.add_argument("--message", required=True)
        args = p.parse_args()
        send_to_telegram(args.message)
        print("Готово.")

    elif cmd == "full":
        # Полный цикл через Claude API (для локального запуска)
        import argparse
        p = argparse.ArgumentParser()
        p.add_argument("full", nargs="?")
        p.add_argument("--dry-run", action="store_true")
        args = p.parse_args()

        print("Собираю статистику за вчера...")
        stats = fetch_yesterday_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))

        print("\nГенерирую саммари...")
        summary = generate_summary_via_api(stats)
        print("\n" + "=" * 50)
        print(summary)
        print("=" * 50)

        if args.dry_run:
            print("\nРежим dry-run: отправка в Telegram пропущена.")
        else:
            print("\nОтправляю в Telegram...")
            send_to_telegram(summary)
            print("Готово.")
    else:
        print(f"Неизвестная команда: {cmd}. Используй: fetch | send | full")
