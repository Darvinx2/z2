# Локальный запуск CI/CD конвейера через act.
# Флаги --artifact-server-path и --secret-file act запрещает хранить
# в проектном .actrc, поэтому они заданы здесь.

# --bind монтирует рабочий каталог в контейнер раннера по тому же пути,
# иначе сканеры, запускаемые как соседние контейнеры, не видят файлы джобы
ACT_FLAGS := --artifact-server-path /tmp/act-artifacts --secret-file .secrets --bind --rm

.PHONY: ci build test sast deploy jobs

ci:            ## весь конвейер
	act push $(ACT_FLAGS)

build test sast deploy:  ## отдельная стадия, например: make sast
	act -j $@ $(ACT_FLAGS)

jobs:          ## список джоб
	act -l
