# Локальный запуск CI/CD конвейера через act.
# Флаги --artifact-server-path и --secret-file act запрещает хранить
# в проектном .actrc, поэтому они заданы здесь.

# --bind монтирует рабочий каталог в контейнер раннера по тому же пути,
# иначе сканеры, запускаемые как соседние контейнеры, не видят файлы джобы
ACT_FLAGS := --artifact-server-path /tmp/act-artifacts --secret-file .secrets --bind --rm

# Docker Desktop обращается к серверам act на Mac через host.docker.internal.
ifeq ($(shell uname -s),Darwin)
ACT_ENV := ACTIONS_RUNTIME_URL=http://host.docker.internal:34567/
ACT_FLAGS += --artifact-server-addr 127.0.0.1 --artifact-server-port 34567
ACT_FLAGS += --cache-server-addr 127.0.0.1 --cache-server-port 34568
ACT_FLAGS += --cache-server-external-url http://host.docker.internal:34568
endif

.PHONY: ci build test sast deploy jobs

ci:            ## весь конвейер
	$(ACT_ENV) act push $(ACT_FLAGS)

build test sast deploy:  ## отдельная стадия, например: make sast
	$(ACT_ENV) act -j $@ $(ACT_FLAGS)

jobs:          ## список джоб
	act -l
