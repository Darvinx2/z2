"""Простое консольное меню."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.cli.prompts import ask


@dataclass(frozen=True)
class MenuItem:
    key: str
    title: str
    handler: Callable[[], None]


class Menu:
    def __init__(self, title: str, items: list[MenuItem], *, back_title: str = "Выход") -> None:
        self.title = title
        self.items = items
        self.back_title = back_title

    def show_once(self) -> bool:
        """Показывает меню и выполняет выбранный пункт.

        Возвращает False, если пользователь выбрал выход.
        """
        print(f"\n=== {self.title} ===")
        for item in self.items:
            print(f"  {item.key}. {item.title}")
        print(f"  0. {self.back_title}")

        choice = ask("Выберите пункт")
        if choice == "0":
            return False
        for item in self.items:
            if item.key == choice:
                item.handler()
                return True
        print("Нет такого пункта меню.")
        return True

    def run(self) -> None:
        while self.show_once():
            pass
