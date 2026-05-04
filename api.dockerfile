FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11

WORKDIR /app/

COPY ./app/pyproject.toml ./app/poetry.lock* /app/
RUN pip install --upgrade pip && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root

EXPOSE 8000

COPY ./entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

COPY ./app /app
ENV PYTHONPATH=/app

ENTRYPOINT ["/entrypoint.sh"]