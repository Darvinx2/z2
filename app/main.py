"""Точка входа консольного приложения."""

from __future__ import annotations

from app.cli.app import ConsoleApp


def main() -> None:
    ConsoleApp().run()


if __name__ == "__main__":
    main()
