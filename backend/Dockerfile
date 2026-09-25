FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Non-root user: a compromised container gets no root access
RUN groupadd -r turbine && useradd -r -g turbine turbine

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R turbine:turbine /app
USER turbine

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
