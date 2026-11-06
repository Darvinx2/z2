"""Консольный интерфейс файлового менеджера."""

from __future__ import annotations

from collections.abc import Callable

from app.cli.menu import Menu, MenuItem
from app.cli.prompts import ExitRequested, ask, ask_multiline, ask_password, confirm
from app.db.session import session_scope
from app.models import User
from app.services import (
    archive_service,
    audit_service,
    auth_service,
    data_service,
    drive_service,
    file_service,
)
from app.utils.errors import AppError
from app.utils.formatting import format_dt, human_size, render_table
from app.utils.paths import STORAGE_ROOT


def safe(handler: Callable[[], None]) -> Callable[[], None]:
    """Перехватывает ожидаемые ошибки, чтобы не прерывать работу меню."""

    def wrapper() -> None:
        try:
            handler()
        except AppError as exc:
            print(f"Ошибка: {exc}")

    return wrapper


class ConsoleApp:
    def __init__(self) -> None:
        self.user: User | None = None

    # --- точка входа -----------------------------------------------------

    def run(self) -> None:
        print("Файловый менеджер с журналированием в базе данных")
        print(f"Каталог хранилища: {STORAGE_ROOT}")
        try:
            while self.user is None:
                if not self._auth_menu().show_once():
                    return
            self._main_menu().run()
            print("До свидания!")
        except ExitRequested:
            print("\nЗавершение работы.")

    # --- меню ------------------------------------------------------------

    def _auth_menu(self) -> Menu:
        return Menu(
            "Вход в систему",
            [
                MenuItem("1", "Войти", safe(self.login)),
                MenuItem("2", "Зарегистрироваться", safe(self.register)),
            ],
        )

    def _main_menu(self) -> Menu:
        assert self.user is not None
        return Menu(
            f"Главное меню (пользователь: {self.user.username})",
            [
                MenuItem("1", "Диски и файловая система", safe(self.show_drives)),
                MenuItem("2", "Операции с файлами", lambda: self._files_menu().run()),
                MenuItem("3", "Данные JSON / XML", lambda: self._data_menu().run()),
                MenuItem("4", "ZIP-архивы", lambda: self._archive_menu().run()),
                MenuItem("5", "Журналы", lambda: self._journal_menu().run()),
            ],
        )

    def _files_menu(self) -> Menu:
        return Menu(
            "Операции с файлами",
            [
                MenuItem("1", "Просмотр каталога", safe(self.list_directory)),
                MenuItem("2", "Прочитать файл", safe(self.read_file)),
                MenuItem("3", "Записать файл", safe(self.write_file)),
                MenuItem("4", "Удалить файл", safe(self.delete_file)),
                MenuItem("5", "Мои файлы (из базы данных)", safe(self.list_user_files)),
            ],
            back_title="Назад",
        )

    def _data_menu(self) -> Menu:
        return Menu(
            "Данные JSON / XML",
            [
                MenuItem("1", "Создать и сохранить записи", safe(self.save_records)),
                MenuItem("2", "Прочитать записи из файла", safe(self.load_records)),
                MenuItem("3", "Конвертировать JSON <-> XML", safe(self.convert_records)),
            ],
            back_title="Назад",
        )

    def _archive_menu(self) -> Menu:
        return Menu(
            "ZIP-архивы",
            [
                MenuItem("1", "Создать архив", safe(self.create_archive)),
                MenuItem("2", "Содержимое архива", safe(self.list_archive)),
                MenuItem("3", "Распаковать архив", safe(self.extract_archive)),
            ],
            back_title="Назад",
        )

    def _journal_menu(self) -> Menu:
        return Menu(
            "Журналы",
            [
                MenuItem("1", "Операции с файлами", safe(self.show_operations)),
                MenuItem("2", "Журнал активности", safe(self.show_audit)),
            ],
            back_title="Назад",
        )

    # --- аутентификация --------------------------------------------------

    def register(self) -> None:
        username = ask("Логин")
        password = ask_password()
        if password != ask_password("Повторите пароль"):
            raise AppError("Пароли не совпадают")
        with session_scope() as session:
            self.user = auth_service.register(session, username, password)
        print(f"Пользователь {username} зарегистрирован, выполнен вход.")

    def login(self) -> None:
        username = ask("Логин")
        password = ask_password()
        with session_scope() as session:
            self.user = auth_service.authenticate(session, username, password)
        print(f"Добро пожаловать, {username}!")

    @property
    def current_user(self) -> User:
        if self.user is None:
            raise AppError("Требуется вход в систему")
        return self.user

    # --- диски -----------------------------------------------------------

    def show_drives(self) -> None:
        rows = []
        for drive in drive_service.list_drives():
            rows.append(
                [
                    drive.device,
                    drive.mountpoint,
                    drive.fstype or "-",
                    human_size(drive.total) if drive.ready else "-",
                    human_size(drive.used) if drive.ready else "-",
                    human_size(drive.free) if drive.ready else "-",
                    f"{drive.percent_used:.0f}%" if drive.ready else "не готов",
                ]
            )
        print(
            render_table(
                ["Устройство", "Точка монтирования", "ФС", "Объём", "Занято", "Свободно", "Исп."],
                rows,
            )
        )
        audit_service.log_action("drives.list", user=self.current_user)

    # --- файлы -----------------------------------------------------------

    def list_directory(self) -> None:
        path = ask("Путь внутри хранилища", default=".")
        current, entries = file_service.list_directory(path)
        print(f"\nКаталог: {current}")
        rows = [
            [
                entry.name + ("/" if entry.is_dir else ""),
                "каталог" if entry.is_dir else "файл",
                "-" if entry.is_dir else human_size(entry.size),
                format_dt(entry.modified),
            ]
            for entry in entries
        ]
        print(render_table(["Имя", "Тип", "Размер", "Изменён"], rows))
        audit_service.log_action("directory.list", user=self.current_user, details=current)

    def read_file(self) -> None:
        path = ask("Путь к файлу")
        with session_scope() as session:
            content = file_service.read_file(session, self.current_user, path)
        print("--- содержимое ---")
        print(content)
        print("--- конец ---")

    def write_file(self) -> None:
        path = ask("Путь к файлу")
        append = confirm("Дописать в конец файла?")
        content = ask_multiline("Введите содержимое")
        with session_scope() as session:
            record = file_service.write_file(
                session, self.current_user, path, content, append=append
            )
        print(f"Записано: {record.location} ({human_size(record.size)})")

    def delete_file(self) -> None:
        path = ask("Путь к файлу")
        if not confirm(f"Удалить {path}?"):
            print("Отменено.")
            return
        with session_scope() as session:
            location = file_service.delete_file(session, self.current_user, path)
        print(f"Удалено: {location}")

    def list_user_files(self) -> None:
        with session_scope() as session:
            records = file_service.list_user_files(session, self.current_user)
            rows = [
                [
                    str(r.id),
                    r.filename,
                    r.location,
                    human_size(r.size),
                    format_dt(r.created_at),
                    "удалён" if r.deleted_at else "активен",
                ]
                for r in records
            ]
        print(render_table(["ID", "Имя", "Расположение", "Размер", "Создан", "Статус"], rows))

    # --- JSON / XML ------------------------------------------------------

    @staticmethod
    def _ask_format() -> str:
        value = ask("Формат (json/xml)", default="json").lower()
        if value not in (data_service.JSON, data_service.XML):
            raise AppError("Поддерживаются только форматы json и xml")
        return value

    def save_records(self) -> None:
        fmt = self._ask_format()
        path = ask("Путь к файлу")
        records: list[dict[str, str]] = []
        print("Ввод записей. Пустое имя поля завершает запись, пустая запись — ввод.")
        while True:
            record: dict[str, str] = {}
            while True:
                key = ask("  Поле", allow_empty=True)
                if not key:
                    break
                record[key] = ask(f"  Значение «{key}»", allow_empty=True)
            if not record:
                break
            records.append(record)
            print(f"  Запись #{len(records)} добавлена.")
        if not records:
            print("Нет записей для сохранения.")
            return
        with session_scope() as session:
            file_record = data_service.save_records(
                session, self.current_user, path, records, fmt
            )
        print(f"Сохранено {len(records)} записей в {file_record.location}")

    def load_records(self) -> None:
        fmt = self._ask_format()
        path = ask("Путь к файлу")
        with session_scope() as session:
            records = data_service.load_records(session, self.current_user, path, fmt)
        if not records:
            print("Записей нет.")
            return
        headers = sorted({key for record in records for key in record})
        rows = [[record.get(h, "") for h in headers] for record in records]
        print(render_table(headers, rows))

    def convert_records(self) -> None:
        print("Исходный файл:")
        source_fmt = self._ask_format()
        source = ask("Путь к исходному файлу")
        print("Файл назначения:")
        target_fmt = self._ask_format()
        target = ask("Путь к файлу назначения")
        with session_scope() as session:
            record = data_service.convert(
                session, self.current_user, source, source_fmt, target, target_fmt
            )
        print(f"Готово: {record.location}")

    # --- архивы ----------------------------------------------------------

    def create_archive(self) -> None:
        path = ask("Путь к создаваемому архиву")
        print("Укажите файлы и каталоги для упаковки (пустая строка — закончить):")
        sources: list[str] = []
        while True:
            source = ask("  Источник", allow_empty=True)
            if not source:
                break
            sources.append(source)
        with session_scope() as session:
            record = archive_service.create_archive(session, self.current_user, path, sources)
        print(f"Архив создан: {record.location} ({human_size(record.size)})")

    def list_archive(self) -> None:
        path = ask("Путь к архиву")
        with session_scope() as session:
            entries = archive_service.list_archive(session, self.current_user, path)
        rows = [
            [name, human_size(packed), human_size(unpacked)]
            for name, packed, unpacked in entries
        ]
        print(render_table(["Имя", "В архиве", "После распаковки"], rows))

    def extract_archive(self) -> None:
        path = ask("Путь к архиву")
        destination = ask("Каталог назначения")
        with session_scope() as session:
            extracted = archive_service.extract_archive(
                session, self.current_user, path, destination
            )
        print(f"Распаковано записей: {len(extracted)}")
        for name in extracted:
            print(f"  {name}")

    # --- журналы ---------------------------------------------------------

    def show_operations(self) -> None:
        with session_scope() as session:
            operations = audit_service.list_operations(session, self.current_user)
            rows = [
                [
                    str(op.id),
                    format_dt(op.timestamp),
                    str(op.operation_type),
                    op.file.location,
                ]
                for op in operations
            ]
        print(render_table(["ID", "Время", "Операция", "Файл"], rows))

    def show_audit(self) -> None:
        with session_scope() as session:
            entries = audit_service.list_audit(session, self.current_user)
            rows = [
                [
                    str(entry.id),
                    format_dt(entry.timestamp),
                    entry.action,
                    "да" if entry.success else "нет",
                    entry.details or "-",
                ]
                for entry in entries
            ]
        print(render_table(["ID", "Время", "Действие", "Успех", "Детали"], rows))
