# Build context: repository root. Run behind an authenticated HTTPS gateway.
FROM python:3.13.18-slim
WORKDIR /app
COPY backtester /app/backtester
COPY oracle /app/oracle
COPY website/engine /app/website/engine
RUN python -m pip install --no-cache-dir --constraint website/engine/constraints.txt ./backtester ./oracle ./website/engine \
    && useradd --uid 10001 --create-home analysis \
    && mkdir /data && chown analysis:analysis /data
USER 10001:10001
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8790
CMD ["python", "-I", "-m", "website.engine.runtime", "--host", "0.0.0.0"]
