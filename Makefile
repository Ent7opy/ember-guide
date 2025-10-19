.PHONY: help setup run-pipeline serve-api serve-ui clean test

help:
	@echo "EmberGuide POC - Available Commands"
	@echo "===================================="
	@echo "make setup        - Create virtual environment and install dependencies"
	@echo "make run-pipeline - Run the pipeline to generate nowcasts"
	@echo "make serve-api    - Start the FastAPI backend"
	@echo "make serve-ui     - Start the Streamlit UI"
	@echo "make clean        - Remove generated data and cache"
	@echo "make test         - Run tests"

setup:
	python -m venv venv
	@echo "Virtual environment created. Activate with:"
	@echo "  Windows: venv\\Scripts\\activate"
	@echo "  Unix/Mac: source venv/bin/activate"
	@echo "Then run: pip install -r requirements.txt"

run-pipeline:
	python -m pipeline.run --config configs/active.yml

serve-api:
	uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

serve-ui:
	streamlit run ui/app.py --server.port 8501

clean:
	rm -rf data/raw/* data/interim/* data/products/*
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

test:
	pytest tests/ -v

