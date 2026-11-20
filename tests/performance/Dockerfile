# Qolqe para las pruebas de rendimiento (plan B de "dos equipos": se corre con --cpus=1 --memory=1g).
# docker build -f tests/performance/Dockerfile -t qolqe-rendimiento .   (desde la raíz)
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY qolqe qolqe
ENV QOLQE_MODO_PRUEBA=1
CMD ["uvicorn", "qolqe.main:app", "--host", "0.0.0.0", "--port", "8000"]
