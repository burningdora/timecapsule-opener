# -*- coding: utf-8 -*-
"""timecapsule-dev-opener: раз в минуту открывает капсулы, у которых наступило время.

Возвращает событие capsule.opened; Lambda отправляет запись о вызове в тему
timecapsule-dev-events (асинхронное назначение), где подписка с фильтром
пропускает только события открытия.
"""
import datetime
import os

import psycopg2


def connect():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        sslmode=os.environ.get("PGSSLMODE", "require").replace("no-verify", "require"),
        connect_timeout=10,
    )


def handler(event, context):
    conn = connect()
    opened = []
    try:
        with conn.cursor() as cur:
            cur.execute(
                """update capsules set opened_at = now()
                    where open_at <= now() and opened_at is null
                    returning id, user_id, title, open_at, opened_at""")
            rows = cur.fetchall()
            for cid, uid, title, open_at, opened_at in rows:
                cur.execute(
                    """insert into notifications (capsule_id, user_id, kind, capsule_title)
                       values (%s, %s, 'opened', %s)
                       on conflict (capsule_id, kind) do nothing""",
                    (cid, uid, title))
                opened.append({"capsule_id": cid, "title": title,
                               "open_at": open_at.isoformat(),
                               "opened_at": opened_at.isoformat()})
        conn.commit()
        print("открыто капсул: %d" % len(opened))
    finally:
        conn.close()

    # даже при нуле открытий возвращаем событие: назначение отправит запись,
    # а фильтр подписки отсеет её по count
    return {"event": "capsule.opened", "count": len(opened), "opened": opened,
            "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
