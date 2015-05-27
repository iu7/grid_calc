import settings
from common import *

from flask import *
from werkzeug.routing import BaseConverter

import requests as pyrequests
from requests.exceptions import Timeout as TimeoutErr
import json as pyjson

app = Flask(__name__)
app.config.update(DEBUG = True)

###>> MAIN ###
import sys

def init_conn_string(dbhost, dbport = 5432):
    app.config.update(dict(SQLALCHEMY_DATABASE_URI=settings.get_sqlite_connection_string(dbhost, dbport)))

init_conn_string()
###<< MAIN ##

###>> init models
from models import *
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError

engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], convert_unicode=True)
db_session = scoped_session(sessionmaker(autocommit=True, autoflush=True, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

init_models(Base)
###<< init models

msg_type_err_fmt = 'table <{0}>, column <{1}>: cannot convert <{2}> to type <{3}> from type <{4}>'
msg_pk_invalid_fmt = 'table <{0}>: invalid primary key field <{1}> specified'
msg_col_not_found_fmt = 'table <{0}>: column <{1}> not found'
msg_tbl_not_found_fmt = 'table <{0}>: not found'
msg_item_not_found_fmt = 'table <{0}>: <{1}> = <{2}> not found'
msg_mtm_pk_not_found_fmt = 'MtM table <{0}>: pk <{1}> not found in input'
msg_mtm_use_another_endpoint_fmt = 'For MtM table use {0} /{1}/filter endpoint with required JSON parameters.'

msg_mtm_only = 'Bad request: Only MtM tables supported'
msg_mtm_not_found = 'MtM relation not found'
msg_put_invalid_input = 'PUT requires additional json field <changes>:[list_of_key-value_pairs]}'
msg_mtm_put_unsupported = 'Unsupported for MtM tables. Perform a chain Delete -> Insert.'

wrn_timed_out_shd_fmt = 'WARNING: Timed out connecting to shard {0}'
wrn_local_write       = 'WARNING: Writing to local database'

###>> SHARDING ###
shards_cnt = 2
shard_name_fmt = 'http://pg_shd{0}_master/'
shards = [shard_name_fmt.format(i) for i in range(shards_cnt)]
def shard_addr_by_pk(pk, shd_cnt):
    return shard_name_fmt.format(pk % shards_cnt)
###<< SHARDING ###

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

###

def get_item(table, pkcolumn, value):
    if table in mtm_table_name_d:
        return api_400(msg_mtm_use_another_endpoint_fmt.format('GET', table))
    elif table not in table_name_d:
        return api_404(msg_tbl_not_found_fmt.format(table))
    
    tbl = table_name_d[table]
    res = None
    if pkcolumn == tbl.metainf.pk_field:
        bres, maybe_val = parse_field_value(tbl, column, value)
        if not bres:
            return maybe_val
        
        shd_addr = shard_addr_by_id(maybe_val)
        resp = None
        try:
            resp = pyrequests.get(shard_addr_by_id + '/{0}/{1}/{2}'.format(table, pkcolumn, value),\
                data = pyjson.dumps({'post_ids': [p['id'] for p in posts]}),\
                headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}\
            )
        except TimeoutErr as e:
            print(wrn_timed_out_shd_fmt.format(shd_addr))
            
            res = tbl.query.filter_by(**{column : maybe_val}).first()
            if res:
                return api_200(res.to_dict())
            else:
                return api_404()
        
        return from_pyresponce(resp)
    else:
        return api_404(msg_pk_invalid_fmt.format(table, column))
        

def post_item(table, value_json):
    if table not in table_name_d:
        return api_404(msg_tbl_not_found_fmt.format(table))
    
    tbl = table_name_d[table]
    bres, maybe_kwargs = try_json_to_filter_kwargs(tbl, value_json)
    if not bres:
        return maybe_kwargs

    val = None
    try:
        val = tbl(**maybe_kwargs)
    except Exception as e:
        return api_400(str(e))
    
    shd_addr = shard_addr_by_id(val[tbl.metainf.pk_field])
    resp = None
    try:
        resp = pyrequests.get(shard_addr_by_id + '/{0}/{1}/{2}'.format(table, pkcolumn, value),\
            data = pyjson.dumps({'post_ids': [p['id'] for p in posts]}),\
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}\
        )
    except TimeoutErr as e:
        print(wrn_timed_out_shd_fmt.format(shd_addr))
        print(wrn_local_write)
        try:
            db_session.add(val)
            db_session.flush()
        except IntegrityError as e:
            db_session.rollback()
            return api_500(str(e))
        return api_200(val.to_dict())

    return from_pyresponce(resp)

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
        
        shd_addr = shard_addr_by_id(val[tbl.metainf.pk_field])
        resp = None
        try:
            resp = pyrequests.get(shard_addr_by_id + '/{0}/{1}/{2}'.format(table, pkcolumn, value),\
                data = pyjson.dumps({'post_ids': [p['id'] for p in posts]}),\
                headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}\
            )
        except TimeoutErr as e:
            print(wrn_timed_out_shd_fmt.format(shd_addr))

            item = None
            try:
                item = tbl.query.filter_by(**{pkf : maybe_val}).first()
            except Exception as e:
                return api_404(msg_col_not_found_fmt.format(table, pkf))
            
            if not item:
                return api_404()

            bres, maybe_kwargs = try_json_to_filter_kwargs(tbl, value_json)
            if not bres:
                return maybe_kwargs

            db_session.begin()
            try:
                update_table_object(item, **maybe_kwargs)
                db_session.commit()
            except IntegrityError as e:
                db_session.rollback()
                return api_500(str(e))
            return api_200(item.to_dict())

        return from_pyresponce(resp)
    else:
        return api_400(msg_pk_invalid_fmt.format(table, pkf))

def delete_item(table, pkf, pkfvs):
    if table in mtm_table_name_d:
        return api_400(msg_mtm_use_another_endpoint_fmt.format('DELETE', table))
    elif table not in table_name_d:
        return api_404(msg_tbl_not_found_fmt.format(table))
    
    tbl = table_name_d[table]
    if pkf == tbl.metainf.pk_field:
        pkft = tbl.metainf.col_type_d[pkf]
        pkftpsr = tbl.metainf.col_type_parsers[pkf] if pkf in tbl.metainf.col_type_parsers else pkft
        pkfv = None
        try:
            pkfv = pkftpsr(pkfvs)
        except Exception as e:
            return api_400(msg_type_err_fmt.format(table, pkf, pkfvs, pkft, pkf, type(pkfvs)))
        
        item = None
        try:
            item = tbl.query.filter_by(**{pkf : pkfv}).first()
        except Exception as e:
            return api_404(msg_col_not_found_fmt.format(table, pkf))
        
        if not item:
            return api_404()

        try:
            db_session.delete(item)
        except IntegrityError as e:
            db_session.rollback()
            return api_500(str(e))
        
        return api_200()
    else:
        return api_400(msg_pk_invalid_fmt.format(table, pkf))

def table_filter_get(table, value_json):
    if table not in table_name_d:
        return api_404(msg_tbl_not_found_fmt.format(table))
    
    tbl = table_name_d[table]

    bres, maybe_kwargs = try_json_to_filter_kwargs(tbl, value_json)
    if not bres:
        return maybe_kwargs

    reslo = tbl.query.filter_by(**maybe_kwargs).all()
    resld = list(map(lambda x: x.to_dict(), reslo))
    return api_200({'result': resld})

def table_filter_delete(table, value_json):
    if table not in table_name_d:
        return api_404(msg_tbl_not_found_fmt.format(table))

    tbl = table_name_d[table]
    bres, maybe_kwargs = try_json_to_filter_kwargs(tbl, value_json)
    if not bres:
        return maybe_kwargs

    reslo = tbl.query.filter_by(**maybe_kwargs).all()
    if reslo:
        db_session.begin()
        try:
            for obj in reslo:
                db_session.delete(obj)
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            return api_500(str(e))
        
        return api_200({'count': len(reslo)})
    else:
        return api_404()

def table_filter_put(table, value_json):
    if 'changes' not in value_json:
        return api_400(msg_put_invalid_input)
    if table not in table_name_d:
        return api_404(msg_tbl_not_found_fmt.format(table))
    
    tbl = table_name_d[table]
    bres, maybe_filter_kwargs = try_json_to_filter_kwargs(tbl, value_json, ['changes'])
    if not bres:
        return maybe_filter_kwargs

    bres, maybe_changes_kwargs = try_json_to_filter_kwargs(tbl, value_json['changes'])
    if not bres:
        return maybe_changes_kwargs

    reslo = tbl.query.filter_by(**maybe_filter_kwargs).all()
    if reslo:
        db_session.begin()
        try:
            for obj in reslo:
                update_table_object(obj, **maybe_changes_kwargs)
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            return api_500(str(e))

        return api_200({'count': len(reslo)})
    else:
        return api_404()
        

### Custom ###
def get_free_task_by_agent_id(agent_id):
    pass

### Filtering (or access by compound PK) ###

@app.route('/<table>/filter', methods=['GET'])
def view_filter_item_get(table):
    value_json = request.get_json()
    return table_filter_get(table, value_json)

@app.route('/<table>/filter', methods=['PUT'])
def view_filter_item_put(table):
    value_json = request.get_json()
    return table_filter_put(table, value_json)

@app.route('/<table>/filter', methods=['DELETE'])
def view_filter_item_delete(table):
    value_json = request.get_json()
    return table_filter_delete(table, value_json)

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

### Sync ###

@app.route('/sync', methods=['GET'])
def rpc_sync(table):
    value = request.get_json()
    return sync(value)

### Custom ###
@app.route('/custom/free_task_by_agent_id', methods=['GET'])
def cst_free_task_by_agent_id(table):
    if has_url_parameter('agent_id'):
        return get_free_task_by_agent_id(get_url_parameter('agent_id'))
    else:
        return api_400('Bad request: <agent_id> not found in input')

### Error handlers ###
def from_pyresponce(pyresp):
   if pyresp.status_code == 200:
       return api_200(pyresp.json())
   elif pyresp.status_code == 404:
       return api_404(pyresp.json()['error'])
   elif pyresp.status_code == 400:
       return api_403(pyresp.json()['error'])
   elif pyresp.status_code == 500:
       return api_401(pyresp.json()['error'])
   else:
       return pyresp

@app.errorhandler(400)
def api_500(msg = 'Internal error'):
    return response_builder({'error': msg}, 500)

@app.errorhandler(400)
def api_400(msg = 'Bad request'):
    return response_builder({'error': msg}, 400)

@app.errorhandler(404)
def api_404(msg = 'Not found'):
    return response_builder({'error': msg}, 404)

@app.errorhandler(200)
def api_200(data = {}):
    return response_builder(data, 200)

### Other ###
        
if __name__ == '__main__':
    app.run(host = host, port = port)
    