#!/bin/sh

# Run the Streamlit app
exec poetry run streamlit run app.py --server.port=8501 --server.address=0.0.0.0