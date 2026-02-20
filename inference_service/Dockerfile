FROM python:3.12-slim

# Impostiamo variabili d'ambiente per Python
# PYTHONDONTWRITEBYTECODE: evita la creazione di file .pyc
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Installiamo le dipendenze di sistema minime (se necessarie per scikit-learn/pandas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiamo e installiamo i requisiti Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Creiamo la struttura delle cartelle
RUN mkdir -p /app/src /app/models /app/data

# Copiamo il codice sorgente
COPY src/ /app/src/

# Aggiungiamo /app/src al PYTHONPATH per facilitare gli import
ENV PYTHONPATH="/app/src"

# Comando di avvio automatico
CMD ["python", "src/main.py"]