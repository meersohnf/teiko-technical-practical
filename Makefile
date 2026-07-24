PYTHON ?= python

.PHONY: setup pipeline dashboard

setup:
	$(PYTHON) -m pip install -r requirements.txt

pipeline:
	$(PYTHON) load_data.py
	$(PYTHON) analysis.py
	$(PYTHON) statistical_analysis.py
	$(PYTHON) subset_analysis.py

dashboard:
	$(PYTHON) -m streamlit run dashboard.py