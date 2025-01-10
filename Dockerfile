# Base image olarak Python 3.12.2 kullan
FROM python:3.12.2-slim

# Çalışma dizinini oluştur
WORKDIR /app

# Gerekli bağımlılık dosyalarını kopyala
COPY requirements.txt .

# Bağımlılıkları yükle
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyasını kopyala
COPY sinavProgramiServis.py .

# Uygulama başlatma komutu
CMD ["uvicorn", "sinavProgramiServis:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
