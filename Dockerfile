# Usa una imagen de Python oficial
FROM python:3.11-slim

# Evitar que Python genere archivos .pyc y forzar salida de logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema para lxml y linter
RUN apt-get update && apt-get install -y \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requerimientos e instalar
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código del servidor
COPY server/ .

# Crear un usuario no root para seguridad (Hugging Face lo recomienda)
RUN useradd -m polaris
USER polaris

# Exponer el puerto que Hugging Face espera (7860)
EXPOSE 7860

# Comando para arrancar la app usando el puerto de HF
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
