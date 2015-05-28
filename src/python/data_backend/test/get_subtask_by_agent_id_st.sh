#!/bin/bash
set -v

curl localhost:50001/trait                  -X POST   -H "Content-Type: application/json" -d '{"name":"trait1","version":"1.0"}'; echo
curl localhost:50001/trait                  -X POST   -H "Content-Type: application/json" -d '{"name":"trait2","version":"2.0"}'; echo
curl localhost:50001/trait                  -X POST   -H "Content-Type: application/json" -d '{"name":"trait3","version":"3.0"}'; echo
curl localhost:50001/trait                  -X POST   -H "Content-Type: application/json" -d '{"name":"trait4","version":"4.0"}'; echo

curl localhost:50001/agent                  -X POST   -H "Content-Type: application/json" -d '{}'; echo
curl localhost:50001/agent                  -X POST   -H "Content-Type: application/json" -d '{}'; echo

curl localhost:50001/task                   -X POST   -H "Content-Type: application/json" -d '{"max_time":160,"archive_name":"cocoque"}'; echo
curl localhost:50001/task                   -X POST   -H "Content-Type: application/json" -d '{"max_time":260,"archive_name":"kukareque"}'; echo

curl localhost:50001/subtask                -X POST   -H "Content-Type: application/json" -d '{"task_id":1,"status":"queued","archive_name":"cocoque0"}'; echo
curl localhost:50001/subtask                -X POST   -H "Content-Type: application/json" -d '{"task_id":2,"status":"queued","archive_name":"cocoque1"}'; echo
curl localhost:50001/subtask                -X POST   -H "Content-Type: application/json" -d '{"task_id":1,"status":"queued","archive_name":"cocoque2"}'; echo
curl localhost:50001/subtask                -X POST   -H "Content-Type: application/json" -d '{"task_id":2,"status":"queued","archive_name":"cocoque3"}'; echo
curl localhost:50001/subtask                -X POST   -H "Content-Type: application/json" -d '{"task_id":1,"status":"queued","archive_name":"cocoque4"}'; echo

curl localhost:50001/mtm_traitagent         -X POST   -H "Content-Type: application/json" -d '{"trait_id":1,"agent_id":2}'; echo
curl localhost:50001/mtm_traitagent         -X POST   -H "Content-Type: application/json" -d '{"trait_id":2,"agent_id":3}'; echo
curl localhost:50001/mtm_traitagent         -X POST   -H "Content-Type: application/json" -d '{"trait_id":3,"agent_id":4}'; echo
curl localhost:50001/mtm_traitagent         -X POST   -H "Content-Type: application/json" -d '{"trait_id":4,"agent_id":1}'; echo
curl localhost:50001/mtm_traitagent         -X POST   -H "Content-Type: application/json" -d '{"trait_id":2,"agent_id":2}'; echo
curl localhost:50001/mtm_traitagent         -X POST   -H "Content-Type: application/json" -d '{"trait_id":4,"agent_id":4}'; echo

curl localhost:50001/mtm_traittask          -X POST   -H "Content-Type: application/json" -d '{"trait_id":1,"task_id":1}'; echo
curl localhost:50001/mtm_traittask          -X POST   -H "Content-Type: application/json" -d '{"trait_id":2,"task_id":1}'; echo
curl localhost:50001/mtm_traittask          -X POST   -H "Content-Type: application/json" -d '{"trait_id":3,"task_id":1}'; echo
curl localhost:50001/mtm_traittask          -X POST   -H "Content-Type: application/json" -d '{"trait_id":2,"task_id":2}'; echo
curl localhost:50001/mtm_traittask          -X POST   -H "Content-Type: application/json" -d '{"trait_id":4,"task_id":2}'; echo
curl localhost:50001/mtm_traittask          -X POST   -H "Content-Type: application/json" -d '{"trait_id":1,"task_id":2}'; echo

##

curl "localhost:50001/custom/get_free_subtask_by_agent_id?agent_id=1"; echo
curl "localhost:50001/custom/get_free_subtask_by_agent_id?agent_id=1"; echo
curl "localhost:50001/custom/get_free_subtask_by_agent_id?agent_id=1"; echo
curl "localhost:50001/custom/get_free_subtask_by_agent_id?agent_id=2"; echo
curl "localhost:50001/custom/get_free_subtask_by_agent_id?agent_id=2"; echo
curl "localhost:50001/custom/get_free_subtask_by_agent_id?agent_id=2"; echo
curl "localhost:50001/custom/get_free_subtask_by_agent_id?agent_id=2"; echo

##

curl "localhost:50001/custom/get_free_subtask_by_agent_id?agent_id=10"; echo

##

curl "localhost:50001/custom/get_free_subtask_by_agent_id?agent_id=lkkl"; echo
curl "localhost:50001/custom/get_free_subtask_by_agent_id?agen=lkkl"; echo
curl "localhost:50001/custom/get_free_subtask_by_agent_id"; echo
