FROM python:3.11-slim

WORKDIR /app

# Create non-root user for security
RUN groupadd -r turbine && useradd -r -g turbine turbine

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Give ownership to non-root user
RUN chown -R turbine:turbine /app
USER turbine

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
