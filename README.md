# Simple JSON DB

Небольшая учебная консольная программа «простая база данных» без SQL.
Таблицы и записи хранятся в JSON-файлах в каталоге `./db/`.

## Возможности

- создание и удаление таблиц со схемой полей и типов
- добавление записей с авто-инкрементным `id`
- выборка записей с фильтрацией (`where`)
- обновление записей (`set` + `where`)
- удаление записей (с `where` или полностью)

Поддерживаемые типы полей: `str`, `int`, `float`, `bool`.

## Быстрый старт

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -e .
simpledb --help
```

Каталог `db/` создаётся автоматически рядом с корнем проекта.

## Примеры

```bash
simpledb create-table users name:str age:int active:bool
simpledb insert users name="Alice" age=30 active=true
simpledb insert users name="Bob" age=25 active=false

simpledb select users
simpledb select users --where 'age>=30 and active=true'

simpledb update users --set 'active=false' --where 'name="Alice"'
simpledb delete users --where 'id=2'
```

## Структура данных

- `db/meta.json` — описания схем и счётчики `id`
- `db/<table>.json` — массив записей таблицы
