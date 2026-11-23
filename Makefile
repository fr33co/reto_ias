.PHONY: setup up down test test-api test-web perf tokens

setup:
	./scripts/setup.sh

up: setup
	docker compose up --build -d
	@echo "Aplicacion en http://localhost:$${WEB_PORT:-8088}  ·  tokens: make tokens"

down:
	docker compose down

test: test-api test-web

test-api: setup
	docker compose --profile test run --rm --build api-tests

test-web:
	docker compose --profile test run --rm --build web-tests

perf: setup
	docker compose --profile test run --rm --build api-tests pytest -m perf -s

tokens:
	@for s in B-NORTE-01 B-SUR-01 B-SUR-02; do echo "$$s:"; docker compose run --rm --no-deps -T init flask --app wsgi issue-token $$s; done
