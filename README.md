# timecapsule-opener

AWS Lambda-функция `timecapsule-dev-opener` для лабораторной работы №7 (часть 2):
капсулы открываются по расписанию, а не при заходе пользователя на сайт.

## Что делает функция

1. Запускается EventBridge Scheduler по выражению `rate(1 minute)`.
2. Одним запросом обновляет все созревшие капсулы:
   `update capsules set opened_at = now() where open_at <= now() and opened_at is null`.
3. Для каждой открытой капсулы пишет уведомление `kind = 'opened'`
   (`ON CONFLICT (capsule_id, kind) DO NOTHING`).
4. Возвращает событие `capsule.opened`:

```json
{"event": "capsule.opened", "count": 1,
 "opened": [{"capsule_id": 34, "title": "...", "open_at": "...", "opened_at": "..."}],
 "checked_at": "..."}
```

Возвращённое значение уходит в тему SNS `timecapsule-dev-events` **асинхронным
назначением «при успехе»** (`DestinationConfig.OnSuccess`). SNS доставляет полный
конверт вызова, поэтому подписка на e-mail фильтрует по вложенному полю:

```json
{"responsePayload": {"event": ["capsule.opened"], "count": [{"numeric": [">", 0]}]}}
```

Пустые вызовы (`count = 0`) отсекаются фильтром и не превращаются в письма.

## Переменные окружения

| Переменная | Назначение |
|---|---|
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | подключение к RDS PostgreSQL |
| `PGSSLMODE` | `require` (значение `no-verify` приводится к `require`) |

Секретов в репозитории нет: доступ к БД — через переменные окружения функции,
права — через роль выполнения.

## Сборка пакета

```bash
pip install --target build -r requirements.txt \
  --platform manylinux2014_x86_64 --python-version 3.12 \
  --implementation cp --only-binary=:all:
cd build && zip -r ../opener.zip . && cd ..
zip -g opener.zip handler.py
```

## Инфраструктура

* Расписание `timecapsule-dev-open-capsules`, `rate(1 minute)`, цель — эта функция,
  роль планировщика имеет право `lambda:InvokeFunction` только на неё.
* Функция в приватных подсетях VPC, SG `timecapsule-dev-lambda-sg`, доступ к RDS по 5432.
* Асинхронное назначение: при успехе — SNS-топик, при ошибке — 2 попытки
  (`MaximumRetryAttempts = 1`), затем событие отбрасывается (для учебной версии
  достаточно журналов).

## Проверка

* В журнале видно `открыто капсул: 0` каждую минуту и `открыто капсул: 1`
  в момент, когда наступило время капсулы.
* Капсула 34: `open_at = 14:19:15`, `opened_at = 14:19:53` — открыта расписанием
  без захода пользователя на сайт.
* Письмо `capsule.opened` пришло на e-mail с конвертом, где событие лежит
  в `responsePayload`.

Контракты событий: см. `docs/events.md` в репозитории `timecapsule-app`.
