.PHONY: setup dev build start test clean

setup:
	./scripts/setup.sh

dev:
	./scripts/dev.sh

build:
	./scripts/build.sh

start:
	./scripts/start.sh

test:
	./scripts/test.sh

clean:
	./scripts/clean.sh

