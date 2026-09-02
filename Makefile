.PHONY: help venv install test lint format run-django run-fastapi createsuperuser docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  venv              : Create Python virtual environment"
	@echo "  install           : Install Django & FastAPI requirements"
	@echo "  test              : Run all backend tests"
	@echo "  lint              : Lint the codebase (ruff)"
	@echo "  format            : Auto-format the codebase (ruff format)"
	@echo "  run-django        : Start Django Control Plane server"
	@echo "  run-fastapi       : Start FastAPI Data Plane server"
	@echo "  createsuperuser   : Create Django admin superuser (interactive)"
	@echo "  docker-up         : Start local infrastructure containers"
	@echo "  docker-down       : Stop local infrastructure containers"

venv:
	python -m venv venv

install:
	pip install -r django_backend/requirements.txt
	pip install -r fastapi_backend/requirements.txt

test:
	pytest

lint:
	ruff check fastapi_backend django_backend tests

format:
	ruff format fastapi_backend django_backend tests

run-django:
	python django_backend/manage.py runserver 0.0.0.0:8000

run-fastapi:
	uvicorn --app-dir fastapi_backend app.main:app --host 0.0.0.0 --port 8001 --reload

createsuperuser:
	python django_backend/manage.py createsuperuser

docker-up:
	docker compose -f infrastructure/docker-compose.yml up -d --build

docker-down:
	docker compose -f infrastructure/docker-compose.yml down