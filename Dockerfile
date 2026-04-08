FROM python:3.11-slim

WORKDIR /app

# Download AlloyDB proxy
RUN apt-get update && apt-get install -y wget && \
    wget -O alloydb-proxy https://storage.googleapis.com/alloydb-auth-proxy/v1.13.1/alloydb-auth-proxy.linux.amd64 && \
    chmod +x alloydb-proxy && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agents/ agents/
COPY api/ api/
COPY mcp_tools/ mcp_tools/
COPY db/ db/
COPY scripts/ scripts/
COPY frontend/ frontend/
COPY start.sh .

RUN chmod +x start.sh

COPY start-job.sh .
RUN chmod +x start-job.sh

EXPOSE 8080

CMD ["./start.sh"]