#!/bin/bash

set -v

curl localhost:50001/data/trait              -X POST   -H "Content-Type: application/json" -d '{"value":{"name":"trait1", "version":"1.0"}}'; echo
curl localhost:50001/data/trait              -X POST   -H "Content-Type: application/json" -d '{"value":{"name":"trait2", "version":"2.0"}}'; echo
curl localhost:50001/data/trait              -X POST   -H "Content-Type: application/json" -d '{"value":{"name":"trait3", "version":"2.0"}}'; echo
curl localhost:50001/data/trait              -X POST   -H "Content-Type: application/json" -d '{"value":{"name":"trait4", "version":"4.0"}}'; echo
curl localhost:50001/data/trait              -X POST   -H "Content-Type: application/json" -d '{"value":{"name":"trait5", "version":"5.0"}}'; echo
curl localhost:50001/data/trait              -X POST   -H "Content-Type: application/json" -d '{"value":{"name":"trait6", "version":"5.0"}}'; echo

curl localhost:50001/data/trait/id/3         -X PUT    -H "Content-Type: application/json" -d '{"value":{"version":"1.0"}}'; echo
curl localhost:50001/data/trait/filter       -X PUT    -H "Content-Type: application/json" -d '{"value":{"name":"trait3", "changes":{"version":"3.0"}}}'; echo

curl localhost:50001/data/trait/id/4         -X DELETE  ; echo
curl localhost:50001/data/trait/filter       -X DELETE -H "Content-Type: application/json" -d '{"value":{"version":"5.0"}}'; echo

curl localhost:50001/data/trait/id/1         -X GET     ; echo
curl localhost:50001/data/trait/filter       -X GET    -H "Content-Type: application/json" -d '{"value":{"name":"trait2"}}'; echo
curl localhost:50001/data/trait/filter       -X GET    -H "Content-Type: application/json" -d '{"value":{"version":"3.0"}}'; echo

curl localhost:50001/data/agent              -X POST   -H "Content-Type: application/json" -d '{"value":{}}'; echo
curl localhost:50001/data/agent              -X POST   -H "Content-Type: application/json" -d '{"value":{}}'; echo

curl localhost:50001/data/mtm_traitagent     -X POST   -H "Content-Type: application/json" -d '{"value":{"trait_id":"1", "agent_id":"2"}}'; echo
curl localhost:50001/data/mtm_traitagent     -X POST   -H "Content-Type: application/json" -d '{"value":{"agent_id":"2", "trait_id":"3"}}'; echo
curl localhost:50001/data/mtm_traitagent     -X POST   -H "Content-Type: application/json" -d '{"value":{"agent_id":"1", "trait_id":"2"}}'; echo

curl localhost:50001/data/mtm/mtm_traitagent -X GET    -H "Content-Type: application/json" -d '{"value":{"agent_id":"1", "trait_id":"2"}}'; echo
curl localhost:50001/data/mtm/mtm_traitagent -X DELETE -H "Content-Type: application/json" -d '{"value":{"agent_id":"1", "trait_id":"2"}}'; echo
curl localhost:50001/data/mtm/mtm_traitagent -X GET    -H "Content-Type: application/json" -d '{"value":{"agent_id":"1", "trait_id":"2"}}'; echo

##

curl localhost:50001/data/trait/filter       -X PUT    -H "Content-Type: application/json" -d '{"value":{"name":"trait1", "changes":{}}}'; echo
curl localhost:50001/data/trait/filter       -X PUT    -H "Content-Type: application/json" -d '{"value":{"name":"trait", "changes":{"version":"3.0"}}}'; echo

##

curl localhost:50001/data/trait              -X POST   -H "Content-Type: application/json" -d '{"value":{"name":"trait_bad1"}}'; echo
curl localhost:50001/data/trait              -X POST   -H "Content-Type: application/json" -d '{"value":{"name":"trait_bad2","kdmfds":"kksdlkl"}}'; echo
curl localhost:50001/data/trait              -X POST   -H "Content-Type: application/json" -d '{"value":{"name":"trait_bad3", "version": "123", "kdmfds":"kksdlkl"}}'; echo

curl localhost:50001/data/trait/id/3         -X PUT    -H "Content-Type: application/json" -d '{"value":{"versio":"1.0"}}'; echo
curl localhost:50001/data/trait/id/100       -X PUT    -H "Content-Type: application/json" -d '{"value":{"version":"1.0"}}'; echo

curl localhost:50001/data/trait/filter       -X PUT    -H "Content-Type: application/json" -d '{"value":{"nam":"trait", "changes":{"version":"3.0"}}}'; echo
curl localhost:50001/data/trait/filter       -X PUT    -H "Content-Type: application/json" -d '{"value":{"name":"trait1"}}'; echo

##

curl localhost:50001/data/user               -X POST   -H "Content-Type: application/json" -d '{"value":{"username":"123","pw_hash":"1234","mail":"12345","phone":"123456"}}'; echo
curl localhost:50001/data/usersession        -X POST   -H "Content-Type: application/json" -d '{"value":{"user_id":"1","timestamp":"21 MAY 15 12:02:31"}}'; echo
curl localhost:50001/data/usersession        -X POST   -H "Content-Type: application/json" -d '{"value":{"user_id":"1","timestamp":"21-MY-15 kl 12:02:31"}}'; echo
