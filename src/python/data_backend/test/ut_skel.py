## Just a conversion from curl-system-test to ut, not really a ut
## In case of integration in data_backend needs responce handling

post_item('trait', {"name":"trait1", "version":"1.0"})
post_item('trait', {"name":"trait2", "version":"2.0"})
post_item('trait', {"name":"trait3", "version":"2.0"})
post_item('trait', {"name":"trait4", "version":"4.0"})
post_item('trait', {"name":"trait5", "version":"5.0"})
post_item('trait', {"name":"trait6", "version":"5.0"})

put_item('trait', 'id', 3, {"version":"1.0"})
table_filter_put('trait', {"name":"trait3", "changes":{"version":"3.0"}})

delete_item('trait', 'id', 4)  
table_filter_delete('trait', {"version":"5.0"})

get_item('trait', 'id', 1)     
table_filter_get('trait', {"name":"trait2"})
table_filter_get('trait', {"version":"3.0"})

post_item('agent', {})
post_item('agent', {})

post_item('mtm_traitagent', {"trait_id":"1", "agent_id":"2"})
post_item('mtm_traitagent', {"agent_id":"2", "trait_id":"3"})
post_item('mtm_traitagent', {"agent_id":"1", "trait_id":"2"})

table_filter_get('mtm_traitagent', {"agent_id":"1", "trait_id":"2"})
table_filter_delete('mtm_traitagent', {"agent_id":"1", "trait_id":"2"})
table_filter_get('mtm_traitagent', {"agent_id":"1", "trait_id":"2"})

##

table_filter_put('trait', {"name":"trait1", "changes":{}})
table_filter_put('trait', {"name":"trait", "changes":{"version":"3.0"}})

##

post_item('trait', {"name":"trait_bad1"})
post_item('trait', {"name":"trait_bad2","kdmfds":"kksdlkl"})
post_item('trait', {"name":"trait_bad3", "version": "123", "kdmfds":"kksdlkl"})

put_item('trait', 'id', 3, {"versio":"1.0"})
put_item('trait', 'id', 100, {"version":"1.0"})

table_filter_put('trait', {"nam":"trait", "changes":{"version":"3.0"}})
table_filter_put('trait', {"name":"trait1"})

##

post_item('user', {"username":"123","pw_hash":"1234","mail":"12345","phone":"123456"})
post_item('usersession', {"user_id":"1","timestamp":"21 MAY 15 12:02:31"})
post_item('usersession', {"user_id":"1","timestamp":"21-MY-15 kl 12:02:31"})