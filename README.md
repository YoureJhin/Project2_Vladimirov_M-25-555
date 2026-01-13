# Primitive DB — простая файловая база данных на Python

Учебный консольный проект: небольшая «база данных» без SQL, где таблицы и записи хранятся в JSON-файлах.

## Возможности

- Управление таблицами:
  - `create_table` — создать таблицу с полями и типами
  - `drop_table` — удалить таблицу
  - `list_tables` — вывести список таблиц и схем

- CRUD:
  - `insert` — добавить запись (ID генерируется автоматически)
  - `select` — вывести записи (с фильтрацией `where`)
  - `update` — обновить записи (через `set` + `where`)
  - `delete` — удалить записи (с `where` или полностью)

- Дополнительно:
  - декораторы: `handle_db_errors`, `log_command`, `confirm_action`
  - кэширование `select` через замыкание (авто-инвалидация при изменениях)

Данные по умолчанию создаются рядом с репозиторием:
- `db_meta.json` — метаданные (схемы/счётчики ID)
- `data/*.json` — записи таблиц
- `logs/commands.log` — лог команд

## Установка и запуск

```bash
make install
make project
```

Либо напрямую через poetry:

```bash
poetry install
poetry run project
```

## Синтаксис команд

### create_table

```text
create_table <table> <field:type> <field:type> ...
```

Пример:

```text
create_table users name:str age:int is_active:bool
```

### list_tables

```text
list_tables
```

### drop_table

```text
drop_table <table>
```

> Для удаления таблицы требуется подтверждение (декоратор `confirm_action`).

### insert

```text
insert <table> <field=value> <field=value> ...
```

Пример:

```text
insert users name="Alice" age=30 is_active=true
insert users name="Bob" age=25 is_active=false
```

### select

```text
select <table> [where <условие>]
```

Поддерживаются операторы: `=`, `!=`, `>`, `<`, `>=`, `<=`.

Примеры:

```text
select users
select users where age>=30
select users where name="Alice" and is_active=true
```

### update

```text
update <table> set <field=value>, <field=value> [where <условие>]
```

Пример:

```text
update users set age=31, is_active=false where name="Alice"
```

### delete

```text
delete <table> [where <условие>]
```

Примеры:

```text
delete users where id=2
delete users
```

> Если `where` не указан, удаляются **все** записи — потребуется подтверждение.

### help / exit

```text
help
exit

```bash
asciinema rec demo.cast
## Сценарий демонстрации (для проверки/записи asciinema)

Ниже — последовательность команд, которая демонстрирует полный цикл работы и покрывает критерии:

```text
help
create_table users name:str, age:int, is_active:bool
insert users name="Alice" age=30 is_active=true
insert users name="Bob" age=25 is_active=false
select users
select users where age>=30 and is_active=true
update users set age=31, is_active=false where name="Alice"
select users where name="Alice"
delete users where id=2
select users
drop_table users
exit
```

exit
asciinema upload demo.cast
```

## Структура проекта

```text
src/primitive_db/
  main.py         # REPL/точка входа
  parser.py       # парсер команд + where/set
  commands.py     # диспетчеризация команд и вывод
  core.py         # бизнес-логика БД
  storage.py      # файловое хранилище (JSON)
  decorators.py   # handle_db_errors / log_command / confirm_action
  utils.py        # вспомогательные функции (типизация/парсинг)
  errors.py       # типы ошибок
  constants.py    # константы/пути/поддерживаемые типы
```

## Примечания по типам

Поддерживаемые типы:
- `int`, `float`, `str`, `bool`

Для `bool` принимаются: `true/false`, `1/0`, `yes/no` (регистр не важен).

## Сборка пакета (опционально)

- `make build` — собрать sdist/wheel в `dist/`
- `make publish` — опубликовать пакет через Poetry (потребуются токены)
- `make package-install` — установить собранный wheel локально из `dist/`
