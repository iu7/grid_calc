start "beacon" py beacon_backend/beacon_backend.py
start "balancer" py balancer_backend/balancer_backend.py
start "nodefront" py node_frontend/node_frontend.py
start "data" py data_backend/data_backend.py localhost:5432 50001