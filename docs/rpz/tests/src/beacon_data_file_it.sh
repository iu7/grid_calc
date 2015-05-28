#!/bin/bash
python ../beacon_backend/beacon_backend.py 50003 &
python ../data_backend/data_backend.py localhost:50003 10.0.0.10:5432 50001 &
python ../file_backend/file_backend.py localhost:50003 50002 &

echo "sleep 30"
sleep 50

killall -9 python