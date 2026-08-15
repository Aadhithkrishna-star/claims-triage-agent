FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directories
RUN mkdir -p data/uploads data/policies data/claims data/chroma_db

# Expose ports
EXPOSE 8000 8501

# Start both FastAPI and Streamlit
CMD uvicorn app.main:app --host 0.0.0.0 --port 8000 & streamlit run app/ui.py --server.port 8501 --server.address 0.0.0.0