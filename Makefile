.PHONY: setup pipeline dashboard
 
# Install all Python dependencies
setup:
	pip install -r requirements.txt
 
# Run the full data pipeline end-to-end:
#   1. load_data.py  → creates cell_counts.db
#   2. analysis.py   → creates all outputs in outputs/
pipeline:
	python load_data.py
	python analysis.py
 
# Start the interactive dashboard on http://localhost:8050
dashboard:
	python dashboard.py