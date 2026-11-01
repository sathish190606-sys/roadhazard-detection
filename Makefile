.PHONY: setup train test run-sim run-robot run-backend run-dashboard migrate-plsql clean

setup:
	@echo "Setting up Python virtual environments and Node dependencies..."
	python -m pip install --upgrade pip
	python -m pip install -r backend/requirements.txt
	python -m pip install -r robot/requirements.txt
	python -m pip install -r simulator/requirements.txt
	python -m pip install -r ml/requirements.txt
	cd dashboard && npm install

train:
	@echo "Starting YOLOv8 training pipeline..."
	python ml/train.py --epochs 100 --batch 16 --imgsz 640

test:
	@echo "Running test suite across backend and robot modules..."
	python -m pytest backend/tests -v
	python -m pytest robot/tests -v

run-backend:
	@echo "Starting FastAPI cloud backend server..."
	python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

run-dashboard:
	@echo "Starting React Leaflet dashboard..."
	cd dashboard && npm run dev

run-robot:
	@echo "Starting Robot edge application in simulation mode..."
	python robot/main.py --config robot/config.yaml

run-sim:
	@echo "Running campus route hazard simulation..."
	python simulator/simulate_route.py --speed 1.0

migrate-plsql:
	@echo "Migrating local database to PL/SQL database (Oracle / PostgreSQL)..."
	python scripts/migrate_to_plsql.py --target-url "$${TARGET_DATABASE_URL:-oracle+oracledb://roadbot:roadbot_pass@localhost:1521/?service_name=FREEPDB1}"

clean:
	@echo "Cleaning cache and build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
