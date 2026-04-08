#!/bin/sh
echo "Starting AlloyDB proxy..."
./alloydb-proxy \
  projects/stocksage-491412/locations/us-central1/clusters/second-brain-cluster/instances/second-brain-primary \
  --port 5432 &

sleep 8
echo "Starting FastAPI..."
exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080}