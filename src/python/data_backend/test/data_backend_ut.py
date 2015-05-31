
import sys
import os

PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

import unittest
from data_backend import post_item, get_free_subtask_by_agent_id, init_db

class utDataBackend(unittest.TestCase):
    
    def test_get_free_subtask_by_agent_id(self):
        def ut_assert(self, qry, code = 200):
            self.assertTrue(qry == code)
        init_db()

        ut_assert(self, post_item('trait', {"name":"trait1","version":"1.0"}))
        ut_assert(self, post_item('trait', {"name":"trait2","version":"2.0"}))
        ut_assert(self, post_item('trait', {"name":"trait3","version":"3.0"}))
        ut_assert(self, post_item('trait', {"name":"trait4","version":"4.0"}))

        ut_assert(self, post_item('agent', {}))
        ut_assert(self, post_item('agent', {}))

        ut_assert(self, post_item('task', {"max_time":160,"archive_name":"cocoque"}))
        ut_assert(self, post_item('task', {"max_time":260,"archive_name":"kukareque"}))

        ut_assert(self, post_item('subtask', {"task_id":1,"status":"queued","archive_name":"cocoque0"}))
        ut_assert(self, post_item('subtask', {"task_id":2,"status":"queued","archive_name":"cocoque1"}))
        ut_assert(self, post_item('subtask', {"task_id":1,"status":"queued","archive_name":"cocoque2"}))
        ut_assert(self, post_item('subtask', {"task_id":2,"status":"queued","archive_name":"cocoque3"}))
        ut_assert(self, post_item('subtask', {"task_id":1,"status":"queued","archive_name":"cocoque4"}))

        ut_assert(self, post_item('mtm_traitagent', {"trait_id":1,"agent_id":2}))
        ut_assert(self, post_item('mtm_traitagent', {"trait_id":2,"agent_id":3}))
        ut_assert(self, post_item('mtm_traitagent', {"trait_id":3,"agent_id":4}))
        ut_assert(self, post_item('mtm_traitagent', {"trait_id":4,"agent_id":1}))
        ut_assert(self, post_item('mtm_traitagent', {"trait_id":2,"agent_id":2}))
        ut_assert(self, post_item('mtm_traitagent', {"trait_id":4,"agent_id":4}))

        ut_assert(self, post_item('mtm_traittask', {"trait_id":1,"task_id":1}))
        ut_assert(self, post_item('mtm_traittask', {"trait_id":2,"task_id":1}))
        ut_assert(self, post_item('mtm_traittask', {"trait_id":3,"task_id":1}))
        ut_assert(self, post_item('mtm_traittask', {"trait_id":2,"task_id":2}))
        ut_assert(self, post_item('mtm_traittask', {"trait_id":4,"task_id":2}))
        ut_assert(self, post_item('mtm_traittask', {"trait_id":1,"task_id":2}))

        ut_assert(self, get_free_subtask_by_agent_id(1))
        ut_assert(self, get_free_subtask_by_agent_id(1))
        ut_assert(self, get_free_subtask_by_agent_id(1), 404)
        ut_assert(self, get_free_subtask_by_agent_id(2))
        ut_assert(self, get_free_subtask_by_agent_id(2))
        ut_assert(self, get_free_subtask_by_agent_id(2))
        ut_assert(self, get_free_subtask_by_agent_id(2), 404)

        ut_assert(self, get_free_subtask_by_agent_id(10), 404)

        ut_assert(self, get_free_subtask_by_agent_id('lkkl'), 400)

if __name__ == '__main__':
    unittest.main()
