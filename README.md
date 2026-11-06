# Файловый менеджер с журналированием в базе данных

Практика 1 по дисциплине «Разработка безопасного программного обеспечения».
Консольное приложение на Python для работы с файлами (текст, JSON, XML, ZIP),
с аутентификацией пользователей, учётом файлов и журналом активности в PostgreSQL.

## Возможности (по ТЗ)

| Требование ТЗ | Где реализовано |
| --- | --- |
| Список дисков и свойств файловой системы | `app/services/drive_service.py` |
| Чтение, запись, удаление файлов | `app/services/file_service.py` |
| Хранение и чтение данных в JSON и XML | `app/services/data_service.py`, `app/utils/serialization.py` |
| Создание и извлечение ZIP-архивов | `app/services/archive_service.py`, `app/utils/archives.py` |
| Интеграция с БД (файлы и операции) | `app/models/`, миграции в `migrations/` |
| Журнал активности пользователей | `app/models/audit.py`, `app/services/audit_service.py` |
| Аутентификация с хешированием паролей | `app/services/auth_service.py`, `app/utils/security.py` |

## Структура проекта

```
app/
  config.py              настройки из .env
  main.py                точка входа
  cli/                   консольный интерфейс (меню, ввод)
  db/                    подключение к БД и базовый класс моделей
  models/                ORM-модели: User, FileRecord, Operation, AuditLog
  services/              бизнес-логика (диски, файлы, JSON/XML, ZIP, журналы, авторизация)
  utils/                 переиспользуемые утилиты (пути, файлы, сериализация, архивы, пароли, вывод)
migrations/              миграции Alembic
storage/                 каталог-песочница, внутри которого работает приложение
```

## Запуск

```bash
# 1. Виртуальное окружение и зависимости
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Настройки
cp .env.example .env

# 3. База данных PostgreSQL
docker compose up -d

# 4. Миграции
alembic upgrade head

# 5. Приложение
python -m app.main
```

## Схема базы данных

* `users` — пользователи: логин и bcrypt-хеш пароля.
* `files` — файлы под управлением приложения: имя, путь в хранилище, размер, даты, владелец (FK на `users`).
* `operations` — операции над файлами: тип (`create` / `modify` / `delete`), время, FK на `files` и `users`.
* `audit_log` — журнал активности: действие, детали, признак успеха, время, FK на `users`.

Журнал активности пишется отдельной транзакцией, поэтому неудачные действия
(например, ошибка входа или заблокированная распаковка архива) тоже сохраняются.

## Реализованные меры безопасности

* **Пароли** — bcrypt с солью, минимальная длина 8 символов; при неверном входе
  не раскрывается, существует ли логин.
* **SQL-инъекции** — все запросы строятся через SQLAlchemy ORM с параметрами,
  пользовательский ввод никогда не склеивается с текстом SQL.
* **Path traversal** — все пользовательские пути разрешаются только внутри
  каталога-песочницы `STORAGE_ROOT` (`app/utils/paths.py`): абсолютные пути,
  `..` и выход по символическим ссылкам отклоняются.
* **Zip-бомбы** — при распаковке ограничены число записей, суммарный объём
  распакованных данных (контролируется по фактически записанным байтам) и
  степень сжатия отдельной записи.
* **Zip slip** — имена записей архива проверяются перед распаковкой.
* **Небезопасная десериализация** — JSON и XML разбираются с ограничением
  размера и проверкой структуры; XML парсится через `defusedxml` (защита от XXE
  и «billion laughs»).
* **Race conditions** — запись файлов атомарная: данные пишутся во временный
  файл и затем подменяют целевой через `os.replace`, поэтому параллельный
  читатель никогда не видит частично записанный файл.

---

# Практика 2. Локальный CI/CD

Конвейер описан в `.github/workflows/main.yml` (GitHub Actions) и запускается
локально утилитой [act](https://nektosact.com/), которая транслирует стадии в
Docker-контейнеры. Тестовое приложение конвейера — файловый менеджер из
Практики 1.

## Соответствие требованиям ТЗ

| Требование ТЗ | Где реализовано |
| --- | --- |
| Изоляция: все шаги в Docker-контейнерах | act запускает каждую джобу в контейнере `catthehacker/ubuntu:act-latest`; SAST-сканеры и smoke-тест — отдельные контейнеры |
| Стадия Build | джоба `build`: `compileall` + сборка wheel/sdist |
| Стадия Test с отчётом JUnit/Cobertura | джоба `test`: `pytest --junitxml` + `--cov-report=xml` (Cobertura) |
| Стадия SAST, падение на High/Critical | джоба `sast`: Semgrep (`--severity ERROR --error`) и Trivy (`--severity HIGH,CRITICAL --exit-code 1`) |
| Стадия Local Deploy | джоба `deploy`: сборка образа, запуск с `-p 8080:8080`, smoke-тест `/health` |
| Dockerfile: multi-stage, непривилегированный пользователь | `Dockerfile`: стадии `builder` и `runtime`, пользователь `appuser` (uid 10001) |
| Явные стадии, артефакты, кэш | `stages` выражены через `needs`; `actions/upload-artifact` для wheel, отчётов и образа; `actions/cache` для `~/.cache/pip` |
| Секреты вне кода | `DATABASE_URL` берётся из `${{ secrets.DATABASE_URL }}`, локально — из файла `.secrets` (в репозиторий не попадает) |

## Запуск конвейера локально

```bash
brew install act          # требуется запущенный Docker
cp .secrets.example .secrets
make ci                   # весь конвейер
make test                 # отдельная стадия (build / test / sast / deploy)
make jobs                 # список джоб
```

`make` — обёртка над act. Образ раннера задан в `.actrc`, а флаги
`--artifact-server-path` (локальный сервер артефактов) и `--secret-file`
act не разрешает держать в проектном `.actrc`, поэтому они прописаны
в `Makefile`. Без make то же самое:

```bash
act push --artifact-server-path /tmp/act-artifacts --secret-file .secrets --bind
```

`--bind` монтирует рабочий каталог в контейнер раннера по тому же пути: без
него SAST-сканеры, которые запускаются как соседние контейнеры, не видят
файлы джобы и не могут записать отчёты.

## Стадии конвейера

```
build ──┬── test ──┬── deploy
        └── sast ──┘
```

1. **build** — установка зависимостей (с кэшем pip), компиляция исходников,
   сборка wheel и sdist; `dist/` выгружается как артефакт.
2. **test** — модульные тесты `pytest` (39 тестов: пути и path traversal,
   JSON/XML и XXE, ZIP-бомбы и zip slip, атомарная запись, хеширование
   паролей, форматирование). Отчёты `reports/junit.xml` (JUnit) и
   `reports/coverage.xml` (Cobertura) выгружаются как артефакт.
3. **sast** — Semgrep (наборы правил `p/python`, `p/secrets`) и Trivy
   (зависимости, секреты, конфигурация Dockerfile). Любая находка уровня
   High/Critical завершает джобу с ненулевым кодом и останавливает конвейер.
4. **deploy** — многоступенчатая сборка Docker-образа, проверка, что контейнер
   работает не от root, запуск с пробросом порта 8080 и smoke-тест эндпоинта
   `/health` (`app/health.py`), сохранение образа (`docker save`) как артефакта.

## Локальный образ приложения

```bash
docker build -t secure-file-manager:latest .
docker run --rm -it -v "$PWD/storage:/data" \
  -e DATABASE_URL=postgresql+psycopg://filemanager:filemanager@host.docker.internal:5433/filemanager \
  secure-file-manager:latest            # консольный файловый менеджер

docker run -d -p 8080:8080 secure-file-manager:latest python -m app.health
curl --noproxy '*' http://127.0.0.1:8080/health
```

## Риски локального CI/CD

* Проброс `/var/run/docker.sock` в контейнер раннера (так работает act и так
  собирается образ в стадии deploy) даёт раннеру полный контроль над хостом.
  Это допустимо только на машине разработчика; в продакшене используют
  изолированные раннеры или DinD.
* Docker-in-Docker требует `privileged: true` — лучшая изоляция файловой
  системы, но привилегированный контейнер тоже может быть использован для
  побега.
* Секреты не хранятся в репозитории: файл `.secrets` добавлен в `.gitignore`,
  в репозитории лежит только `.secrets.example`.
