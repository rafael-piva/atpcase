.PHONY: install run kaggle refresh test dashboard charts

install:          ## install dependencies
	pip install -r requirements.txt

kaggle:           ## download from Kaggle (needs KAGGLE_API_TOKEN) and run everything
	python -m pipeline.run --kaggle

run:              ## run on CSVs already in data/source
	python -m pipeline.run

refresh:          ## rebuild incremental models from scratch
	python -m pipeline.run --full-refresh

test:             ## unit + end-to-end tests on the fixture data
	python -m pytest -q

charts:           ## re-export README charts
	python -m dashboard.export_charts data/warehouse.duckdb

dashboard:        ## open the interactive dashboard
	streamlit run dashboard/app.py
