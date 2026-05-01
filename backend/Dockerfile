FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias primero (capa cacheada mientras requirements no cambie)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Crear directorio de datos para los archivos SQLite (montado como volume en producción)
RUN mkdir -p /app/data

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
