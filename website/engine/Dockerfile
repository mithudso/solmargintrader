# Build context: repository root. Run behind an authenticated HTTPS gateway.
FROM python:3.13-slim
WORKDIR /app
COPY backtester /app/backtester
COPY oracle /app/oracle
COPY website/engine /app/website/engine
RUN python -m pip install --no-cache-dir ./backtester ./oracle \
    && useradd --uid 10001 --create-home analysis
USER 10001:10001
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8790
CMD ["python", "-m", "website.engine.server", "--host", "0.0.0.0"]
