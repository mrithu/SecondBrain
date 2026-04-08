#!/bin/sh
echo "Starting AlloyDB proxy..."
./alloydb-proxy \
  projects/stocksage-491412/locations/us-central1/clusters/second-brain-cluster/instances/second-brain-primary \
  --port 5432 &

sleep 5
echo "Running seed data..."
python scripts/generate_seed_data.py