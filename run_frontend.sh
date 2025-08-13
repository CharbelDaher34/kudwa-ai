#!/bin/bash

# Install frontend dependencies
pip install -r frontend_requirements.txt

# Run the Streamlit frontend
streamlit run frontend.py --server.port 8574 --server.address 0.0.0.0
