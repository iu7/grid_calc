import os, sys
PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

from flask import *
from werkzeug.routing import BaseConverter
import requests as pyrequests
from requests.exceptions import Timeout as TimeoutErr
import json as pyjson
import threading
from functools import reduce

import settings
from common.common import get_url_parameter, has_url_parameter, response_builder, BeaconWrapper, parse_argv, platform_dependent_on_run

app = Flask(__name__)
app.config.update(DEBUG = True)
app.config.update(GRID_CALC_ROLE = 'SHARDING_BACKEND')
app.config.update(DATA_BACKENDS = None)
app.config.update(ROUND_ROBIN = 0)

from common.models import *
from sqlalchemy.ext.declarative import declarative_base
init_models(declarative_base())

msg_tbl_not_found_fmt = 'table <{0}>: not found'
msg_col_not_found_fmt = 'table <{0}>: column <{1}> not found'
msg_type_err_fmt = 'table <{0}>, column <{1}>: cannot convert <{2}> to type <{3}> from type <{4}>'

msg_mtm_use_another_endpoint_fmt = 'For MtM table use {0} /{1}/filter endpoint with required JSON parameters.'

wrn_timed_out_shd_fmt = 'WARNING: Timed out connecting to shard {0}!'

msg_timed_out_shard_fmt = 'Timed out connecting to shard {0}'

###>> Sharding ###
from common.sharding_settings import get_shd_num, SHARDS_COUNT
shard_name_fmt = 'http://{0}'
shards = None

def to_shd_addr(shd_num):
    return shard_name_fmt.format(app.config['DATA_BACKENDS'][shd_num])

def shard_addr_by_pk(pk):
    shd_num = get_shd_num(pk, SHARDS_COUNT)
    return shd_num, to_shd_addr(shd_num)

def round_robin_next():
    retv = (app.config['ROUND_ROBIN'] + 1) % SHARDS_COUNT
    app.config['ROUND_ROBIN'] = retv
    return retv
###<< Sharding ###

def update_table_object(obj, **kwargs):
    for k, v in kwargs.items():
        setattr(obj, k, v)
    return obj

def parse_field_value(tbl, field, value):
    res = None
    tp = tbl.metainf.col_type_d[field]
    tppsr = tbl.metainf.col_type_parsers[field] if field in tbl.metainf.col_type_parsers else tp
    try:
        res = tppsr(value)
    except Exception as e:
        return False, api_400(msg_type_err_fmt.format(tbl.__tablename__, field, value, tp.__name__, type(value).__name__))
    return True, res

def try_json_to_filter_kwargs(tbl, value_json, exclude_lst = []):
    kwargs = {}
    for field, value in value_json.items():
        if field in tbl.metainf.col_type_d:
            bres, maybe_val = parse_field_value(tbl, field, value)
            if bres:
                kwargs.update({field : maybe_val})
            else:
                return False, maybe_val
        elif field not in exclude_lst:
            return False, api_404(msg_col_not_found_fmt.format(tbl.__tablename__, field))
    return True, kwargs

### Simple requests processing ###

def get_item(table, pkcolumn, value):
    if table in mtm_table_name_d:
        return api_400(msg_mtm_use_another_endpoint_fmt.format('GET', table))
    elif table not in table_name_d:
        return api_404(msg_tbl_not_found_fmt.format(table))
    
    tbl = table_name_d[table]
    res = None
    if pkcolumn == tbl.metainf.pk_field:
        bres, maybe_val = parse_field_value(tbl, pkcolumn, value)
        if not bres:
            return maybe_val

        shd_num, shd_addr = shard_addr_by_pk(maybe_val)
        resp = None
        try:
            resp = pyrequests.get(shd_addr + '/{0}/{1}/{2}'.format(table, pkcolumn, value))
        except Exception as e:
            print(wrn_timed_out_shd_fmt.format(shd_addr))
            return api_456(msg_timed_out_shard_fmt.format(shd_addr))

        return from_pyresponse(resp)
    else:
        return api_404(msg_pk_invalid_fmt.format(table, column))
        

def post_item(table, value_json):
    if table not in table_name_d:
        return api_404(msg_tbl_not_found_fmt.format(table))
    
    tbl = table_name_d[table]
    bres, maybe_kwargs = try_json_to_filter_kwargs(tbl, value_json)
    if not bres:
        return maybe_kwargs
    
    ec, resp = table_filter_get(table, value_json)
    if ec in [408, 456]:
        return api_xxx(ec, resp)
    if ec == 200:
        if not tbl.metainf.duplicatable:
            return api_500('Entry already exists')

    shd_addr = to_shd_addr(round_robin_next())
    resp = None
    try:
        resp = pyrequests.post(shd_addr + '/{0}'.format(table),\
            data = pyjson.dumps(value_json),\
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}\
        )
    except Exception as e:
        print(wrn_timed_out_shd_fmt.format(shd_addr))
        return api_408(msg_timed_out_shard_fmt.format(shd_addr))

    return from_pyresponse(resp)

def put_item(table, pkf, pkfvs, value_json):
    if table in mtm_table_name_d:
        return api_400(msg_mtm_use_another_endpoint_fmt.format('PUT', table))
    elif table not in table_name_d:
        return api_404(msg_tbl_not_found_fmt.format(table))
    
    tbl = table_name_d[table]
    if pkf == tbl.metainf.pk_field:
        bres, maybe_val = parse_field_value(tbl, pkf, pkfvs)
        if not bres:
            return maybe_val
        
        shd_num, shd_addr = shard_addr_by_pk(maybe_val)
        resp = None
        try:
            resp = pyrequests.put(shd_addr + '/{0}/{1}/{2}'.format(table, pkf, pkfvs),\
                data = pyjson.dumps(value_json),\
                headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}\
            )
        except Exception as e:
            print(wrn_timed_out_shd_fmt.format(shd_addr))
            return api_408(msg_timed_out_shard_fmt.format(shd_addr))

        return from_pyresponse(resp)
    else:
        return api_400(msg_pk_invalid_fmt.format(table, pkf))

def delete_item(table, pkf, pkfvs):
    if table in mtm_table_name_d:
        return api_400(msg_mtm_use_another_endpoint_fmt.format('DELETE', table))
    elif table not in table_name_d:
        return api_404(msg_tbl_not_found_fmt.format(table))
    
    tbl = table_name_d[table]
    if pkf == tbl.metainf.pk_field:
        bres, maybe_val = parse_field_value(tbl, pkf, pkfvs)
        if not bres:
            return maybe_val
        
        shd_num, shd_addr = shard_addr_by_pk(maybe_val)
        resp = None
        try:
            resp = pyrequests.delete(shd_addr + '/{0}/{1}/{2}'.format(table, pkf, pkfvs))
        except Exception as e:
            print(wrn_timed_out_shd_fmt.format(shd_addr))
            return api_408(msg_timed_out_shard_fmt.format(shd_addr))

        return from_pyresponse(resp)
    else:
        return api_400(msg_pk_invalid_fmt.format(table, pkf))

### Filer requests processing ###

class FakeResponse:
    status_code = None
    json_ = None
    def __init__(self, status_code, json):
        self.status_code = status_code
        self.json_ = json
    def json(self): return self.json_
    def __repr__(self): return '{0}: code {1}'.format(FakeResponse.__name__, self.status_code)

def try_request(reqf, shd_addr, json, endpoint, resp):
    try:
        resp.append(reqf(shd_addr + endpoint, data = pyjson.dumps(json), headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}))
    except Exception as e:
        resp.append(FakeResponse(408, {"error": msg_timed_out_shard_fmt.format(shd_addr)}))

def dict_sum(d1, d2):
    s = {}
    for k in d1.keys():
        if isinstance(d1[k], dict):
            s[k] = dict_sum(d1[k], d2[k])
        else:
            return {k: d1[k] + d2[k]}
    return s

def process_filter_request(bind_try_request):
    resps = [[] for _ in shards]
    thds = [threading.Thread(target=bind_try_request(shd_addr=shd_addr, resp=resp)) for shd_addr, resp in zip(shards, resps)]
    for th in thds:
        th.start()

    for th in thds:
        if th.is_alive():
            th.join()

    resps = [x[0] for x in resps]
    toresps = list(filter(lambda rs: rs[0].status_code == 408, zip(resps, shards)))
    if not toresps:
        errorresps = list(filter(lambda rs: rs[0].status_code not in [200, 404], zip(resps, shards)))
        if errorresps:
            res = [errorresps[0][0].json()]
            res[0].update({'shard': errorresps[0][1], 'code' : errorresps[0][0].status_code})
            for r, s in errorresps[1:]:
                d = r.json()
                d.update({'shard': s, 'code': r.status_code})
                res += d
            return 456, {'multiple_errors' : res}

        validresps = list(filter(lambda r: r.status_code == 200, resps))
        if validresps:
            res = validresps[0].json()
            for r in validresps[1:]:
                res = dict_sum(res, r.json())
            return 200, res
        else:
            return 404, 'Not found'
    else:
        toshds = []
        for tor in toresps:
            print(wrn_timed_out_shd_fmt.format(tor[1]))
            d = tor[0].json()
            d.update({'shard': tor[1], 'code' : tor[0].status_code})
            toshds += [d]
        return 456, {'multiple_errors' : toshds}

def table_filter_get(table, value_json):
    def bind_try_request(**kwargs):
        return lambda : try_request(pyrequests.get, kwargs['shd_addr'], value_json, '/{0}/filter'.format(table), kwargs['resp'])
    if table not in table_name_d:
        return 400, msg_tbl_not_found_fmt.format(table)
    return process_filter_request(bind_try_request)

def table_filter_delete(table, value_json):
    def bind_try_request(**kwargs):
        return lambda : try_request(pyrequests.delete, kwargs['shd_addr'], value_json, '/{0}/filter'.format(table), kwargs['resp'])
    if table not in table_name_d:
        return 400, msg_tbl_not_found_fmt.format(table)
    return process_filter_request(bind_try_request)

def table_filter_put(table, value_json):
    def bind_try_request(**kwargs):
        return lambda : try_request(pyrequests.put, kwargs['shd_addr'], value_json, '/{0}/filter'.format(table), kwargs['resp'])
    if 'changes' not in value_json:
        return 400, msg_put_invalid_input
    if table not in table_name_d:
        return 400, msg_tbl_not_found_fmt.format(table)
    return process_filter_request(bind_try_request)
        
def table_arrayfilter_get(table, value_json):
    def bind_try_request(**kwargs):
        return lambda : try_request(pyrequests.get, kwargs['shd_addr'], value_json, '/{0}/arrayfilter'.format(table), kwargs['resp'])
    if table not in table_name_d:
        return 400, msg_tbl_not_found_fmt.format(table)
    return process_filter_request(bind_try_request)

def table_bulk_get(table):
    def bind_try_request(**kwargs):
        return lambda : try_request(pyrequests.get, kwargs['shd_addr'], {}, '/{0}'.format(table), kwargs['resp'])
    if table not in table_name_d:
        return 400, msg_tbl_not_found_fmt.format(table)
    return process_filter_request(bind_try_request)

### Custom ###
def get_free_subtask_by_agent_id(agent_id, status = 'queued', newstatus = 'taken'):
    bres, maybe_val = parse_field_value(table_name_d['agent'], 'id', agent_id)
    if not bres:
        return maybe_val
    agent_id = maybe_val

    ec, trait_idsq = table_filter_get('mtm_traitagent', dict(agent_id = agent_id))
    if ec != 200:
        return api_xxx(ec, trait_idsq)

    ec, subtasksq = table_filter_get('subtask', dict(status = status))
    if ec != 200:
        return api_xxx(ec, subtasksq)

    trait_ids = (mtmtr['trait_id'] for mtmtr in trait_idsq['result'])
    task_ids = (sbtsk['task_id'] for sbtsk in subtasksq['result'])

    ec, mtmttq = table_arrayfilter_get('mtm_traittask', dict(task_id = list(task_ids), trait_id = list(trait_ids)))
    if ec != 200:
        return api_xxx(ec, mtmttq)
        
    mtmtts = mtmttq['result']
    if mtmtts:
        mtmtto = mtmtts[0]
        subtasks = subtasksq['result']
        stsk = next(sbtsk for sbtsk in subtasks if sbtsk['task_id'] == mtmtto['task_id'])

        changes = {'status' : newstatus, 'agent_id' : agent_id}
        return put_item('subtask', 'id', stsk['id'], changes)
    else:
        return api_404()

### Bulk interface ###

@app.route('/<table>', methods=['GET'])
def view_bulk_get(table):
    code, res = table_bulk_get(table)
    return api_xxx(code, res)

### Array filtering ###
@app.route('/<table>/arrayfilter', methods=['GET'])
def view_arrayfilter_item_get(table):
    value_json = request.get_json()
    code, res = table_arrayfilter_get(table, value_json)
    return api_xxx(code, res)

### Filtering (or access by compound PK) ###

@app.route('/<table>/filter', methods=['GET'])
def view_filter_item_get(table):
    value_json = request.get_json()
    code, res = table_filter_get(table, value_json)
    return api_xxx(code, res)

@app.route('/<table>/filter', methods=['PUT'])
def view_filter_item_put(table):
    value_json = request.get_json()
    code, res = table_filter_put(table, value_json)
    return api_xxx(code, res)

@app.route('/<table>/filter', methods=['DELETE'])
def view_filter_item_delete(table):
    value_json = request.get_json()
    code, res = table_filter_delete(table, value_json)
    return api_xxx(code, res)

### Access by singular PK ###

@app.route('/<table>/<column>/<value>', methods=['GET'])
def view_rest_get_item(table, column, value):
    return get_item(table, column, value)

@app.route('/<table>/<int:id>', methods=['GET'])
def view_rest_get_item_by_id(table, id):
    return get_item(table, 'id', id)

@app.route('/<table>/<column>/<value>', methods=['PUT'])
def view_rest_put_item(table, column, value):
    value_json = request.get_json()
    return put_item(table, column, value, value_json)

@app.route('/<table>/<column>/<value>', methods=['DELETE'])
def view_rest_delete_item(table, column, value):
    return delete_item(table, column, value)

### Posting ###

@app.route('/<table>', methods=['POST'])
def rest_post_item(table):
    value = request.get_json()
    return post_item(table, value)

### Custom ###
@app.route('/custom/get_free_subtask_by_agent_id', methods=['GET'])
def cst_get_free_subtask_by_agent_id():
    if has_url_parameter('agent_id'):
        return get_free_subtask_by_agent_id(get_url_parameter('agent_id'))
    else:
        return api_400('Bad request: <agent_id> not found in input')

### Error handlers ###
def api_xxx(code, msg):
    if code == 200:
        return api_200(msg)
    elif code == 400:
        return api_400(msg)
    elif code == 404:
        return api_404(msg)
    elif code == 408:
        return api_408(msg)
    elif code == 456:
        return api_456(msg)
    elif code == 500:
        return api_500(msg)

def from_pyresponse(pyresp):
   if pyresp.status_code == 200:
       return api_200(pyresp.json())
   elif pyresp.status_code in [400, 404, 408, 456, 500]:
       return api_xxx(pyresp.status_code, pyresp.json()['error'])
   else:
       return pyresp

@app.errorhandler(500)
def api_500(msg = 'Internal error'):
    return response_builder({'error': msg}, 500)

@app.errorhandler(400)
def api_400(msg = 'Bad request'):
    return response_builder({'error': msg}, 400)

@app.errorhandler(404)
def api_404(msg = 'Not found'):
    return response_builder({'error': msg}, 404)

@app.errorhandler(408)
def api_408(msg = 'Timed out'):
    return response_builder({'error': msg}, 408)

@app.errorhandler(456)
def api_456(msg = 'Unrecoverable error'):
    return response_builder({'error': msg}, 456)

@app.errorhandler(200)
def api_200(data = {}):
    return response_builder(data, 200)

### Other ###
        
if __name__ == '__main__':
    host = '0.0.0.0'
    beacon, port = parse_argv(sys.argv, 'data_backend:port[,data_backend:port]')
    dbcss = sys.argv[3]
    ss = dbcss.split(',')
    app.config.update(DATA_BACKENDS = ss)
    print('Starting with settings: Beacon: {0} self: {1}:{2} data_backends: {3}'.format(beacon, host, port, ss))

    bw = BeaconWrapper(beacon, port, 'services/database')
    bw.beacon_setter()
    shards = list(map(lambda x: shard_name_fmt.format(x), app.config['DATA_BACKENDS'][:SHARDS_COUNT]))
    print(app.config['GRID_CALC_ROLE'])
    platform_dependent_on_run(app.config['GRID_CALC_ROLE'])
    app.run(host = host, port = port)