#!/bin/bash

set -v

curl localhost:50001/trait                  -X POST   -H "Content-Type: application/json" -d '{"name":"trait1", "version":"1.0"}'; echo
curl localhost:50001/trait                  -X POST   -H "Content-Type: application/json" -d '{"name":"trait2", "version":"2.0"}'; echo
curl localhost:50001/trait                  -X POST   -H "Content-Type: application/json" -d '{"name":"trait3", "version":"2.0"}'; echo
curl localhost:50001/trait                  -X POST   -H "Content-Type: application/json" -d '{"name":"trait4", "version":"4.0"}'; echo
curl localhost:50001/trait                  -X POST   -H "Content-Type: application/json" -d '{"name":"trait5", "version":"5.0"}'; echo
curl localhost:50001/trait                  -X POST   -H "Content-Type: application/json" -d '{"name":"trait6", "version":"5.0"}'; echo

curl localhost:50001/trait/id/3             -X PUT    -H "Content-Type: application/json" -d '{"version":"1.0"}'; echo
curl localhost:50001/trait/filter           -X PUT    -H "Content-Type: application/json" -d '{"name":"trait3", "changes":{"version":"3.0"}}'; echo

curl localhost:50001/trait/id/4             -X DELETE  ; echo
curl localhost:50001/trait/filter           -X DELETE -H "Content-Type: application/json" -d '{"version":"5.0"}'; echo

curl localhost:50001/trait/id/1             -X GET     ; echo
curl localhost:50001/trait/filter           -X GET    -H "Content-Type: application/json" -d '{"name":"trait2"}'; echo
curl localhost:50001/trait/filter           -X GET    -H "Content-Type: application/json" -d '{"version":"3.0"}'; echo

curl localhost:50001/agent                  -X POST   -H "Content-Type: application/json" -d '{}'; echo
curl localhost:50001/agent                  -X POST   -H "Content-Type: application/json" -d '{}'; echo

curl localhost:50001/mtm_traitagent         -X POST   -H "Content-Type: application/json" -d '{"trait_id":"1", "agent_id":"2"}'; echo
curl localhost:50001/mtm_traitagent         -X POST   -H "Content-Type: application/json" -d '{"agent_id":"2", "trait_id":"3"}'; echo
curl localhost:50001/mtm_traitagent         -X POST   -H "Content-Type: application/json" -d '{"agent_id":"1", "trait_id":"2"}'; echo

curl localhost:50001/mtm_traitagent/filter  -X GET    -H "Content-Type: application/json" -d '{"agent_id":"1", "trait_id":"2"}'; echo
curl localhost:50001/mtm_traitagent/filter  -X DELETE -H "Content-Type: application/json" -d '{"agent_id":"1", "trait_id":"2"}'; echo
curl localhost:50001/mtm_traitagent/filter  -X GET    -H "Content-Type: application/json" -d '{"agent_id":"1", "trait_id":"2"}'; echo

##

curl localhost:50001/trait/filter           -X PUT    -H "Content-Type: application/json" -d '{"name":"trait1", "changes":{}}'; echo
curl localhost:50001/trait/filter           -X PUT    -H "Content-Type: application/json" -d '{"name":"trait", "changes":{"version":"3.0"}}'; echo

##

curl localhost:50001/trait                  -X POST   -H "Content-Type: application/json" -d '{"name":"trait_bad1"}'; echo
curl localhost:50001/trait                  -X POST   -H "Content-Type: application/json" -d '{"name":"trait_bad2","kdmfds":"kksdlkl"}'; echo
curl localhost:50001/trait                  -X POST   -H "Content-Type: application/json" -d '{"name":"trait_bad3", "version": "123", "kdmfds":"kksdlkl"}'; echo

curl localhost:50001/trait/id/3             -X PUT    -H "Content-Type: application/json" -d '{"versio":"1.0"}'; echo
curl localhost:50001/trait/id/100           -X PUT    -H "Content-Type: application/json" -d '{"version":"1.0"}'; echo

curl localhost:50001/trait/filter           -X PUT    -H "Content-Type: application/json" -d '{"nam":"trait", "changes":{"version":"3.0"}}'; echo
curl localhost:50001/trait/filter           -X PUT    -H "Content-Type: application/json" -d '{"name":"trait1"}'; echo

##

curl localhost:50001/user                   -X POST   -H "Content-Type: application/json" -d '{"username":"123","pw_hash":"1234","mail":"12345","phone":"123456"}'; echo
curl localhost:50001/usersession            -X POST   -H "Content-Type: application/json" -d '{"user_id":"1","timestamp":"21 MAY 15 12:02:31"}'; echo
curl localhost:50001/usersession            -X POST   -H "Content-Type: application/json" -d '{"user_id":"1","timestamp":"21-MY-15 kl 12:02:31"}'; echo