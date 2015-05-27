import settings
from common import *

from flask import *
from werkzeug.routing import BaseConverter

import requests as pyrequests
import json as pyjson

app = Flask(__name__)
app.config.update(DEBUG = True)

###>> MAIN ###
import sys

def init_conn_string(dbhost, dbport = 5432):
    app.config.update(dict(SQLALCHEMY_DATABASE_URI=settings.get_sqlite_connection_string(dbhost, dbport)))

init_conn_string()
###<< MAIN ##

###>> SHARDING ###
shards_cnt = 2
def sharding_f(id, shd_cnt):
    return id % shd_cnt
###<< SHARDING ###

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

def get_item(table, column, value):
    if table in mtm_table_name_d:
        return api_400(msg_mtm_use_another_endpoint_fmt.format('GET', table))
    elif table in table_name_d:
        tbl = table_name_d[table]
        res = None
        if column in tbl.metainf.col_type_d:

            try:
                pyrequests.get(\
                ,\
                params = {'username': un, 'password': pw}\

            bres, maybe_val = parse_field_value(tbl, column, value)
            if not bres:
                return maybe_val
            else:
                res = tbl.query.filter_by(**{column : maybe_val}).first()
                if res:
                    return api_200(res.to_dict())
                else:
                    return api_404()
        else:
            return api_404(msg_col_not_found_fmt.format(table, column))
    else:
        return api_404(msg_tbl_not_found_fmt.format(table))

def post_item(table, value_json):
    if table in table_name_d:
        tbl = table_name_d[table]
        
        bres, maybe_kwargs = try_json_to_filter_kwargs(tbl, value_json)
        if not bres:
            return maybe_kwargs

        val = None
        try:
            val = tbl(**maybe_kwargs)
        except Exception as e:
            return api_400(str(e))
        
        try:
            db_session.add(val)
            db_session.flush()
        except IntegrityError as e:
            db_session.rollback()
            return api_500(str(e))
        
        return api_200(val.to_dict())
    else:
        return api_404(msg_tbl_not_found_fmt.format(table))

def put_item(table, pkf, pkfvs, value_json):
    if table in mtm_table_name_d:
        return api_400(msg_mtm_use_another_endpoint_fmt.format('PUT', table))
    elif table in table_name_d:
        tbl = table_name_d[table]

        if pkf == tbl.metainf.pk_field:
            bres, maybe_val = parse_field_value(tbl, pkf, pkfvs)
            if not bres:
                return maybe_val
            
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
        else:
            return api_400(msg_pk_invalid_fmt.format(table, pkf))
    else:
        return api_404(msg_tbl_not_found_fmt.format(table))

def delete_item(table, pkf, pkfvs):
    if table in mtm_table_name_d:
        return api_400(msg_mtm_use_another_endpoint_fmt.format('DELETE', table))
    elif table in table_name_d:
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
    else:
        return api_404(msg_tbl_not_found_fmt.format(table))

def table_filter_get(table, value_json):
    if table in table_name_d:
        tbl = table_name_d[table]

        bres, maybe_kwargs = try_json_to_filter_kwargs(tbl, value_json)
        if not bres:
            return maybe_kwargs

        reslo = tbl.query.filter_by(**maybe_kwargs).all()
        resld = list(map(lambda x: x.to_dict(), reslo))
        return api_200({'result': resld})
    else:
        return api_404(msg_tbl_not_found_fmt.format(table))

def table_filter_delete(table, value_json):
    if table in table_name_d:
        tbl = table_name_d[table]

        bres, maybe_kwargs = try_json_to_filter_kwargs(tbl, value_json)
        if not bres:
            return maybe_kwargs
        bres, 

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
    else:
        return api_404(msg_tbl_not_found_fmt.format(table))

def table_filter_put(table, value_json):
    if 'changes' in value_json:
        if table in table_name_d:
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
        else:
            return api_404(msg_tbl_not_found_fmt.format(table))
    else:
        return api_400(msg_put_invalid_input)

### Custom ###
def get_free_task_by_agent_id(agent_id):


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