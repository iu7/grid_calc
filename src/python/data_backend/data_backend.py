import os, sys
PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

import requests as pyrequests
from flask import *
from werkzeug.routing import BaseConverter

import settings
from common.common import get_url_parameter, has_url_parameter, response_builder, BeaconWrapper, parse_db_argv
from common.sharding_settings import encode_pkv as sh_ev, decode_pkv as sh_dv, SHARDS_COUNT

app = Flask(__name__)
app.config.update(DEBUG = True)

###>> MAIN ###
def init_conn_string(dbhost, dbport = 5432):
    app.config.update(dict(SQLALCHEMY_DATABASE_URI=settings.get_connection_string(dbhost, dbport)))

if __name__ == '__main__':
    host = '0.0.0.0'
    SHARD_NUMBER, beacon, dbhost, dbport, port = parse_db_argv(sys.argv)
    print('Starting with settings: Beacon: {0} DB: {1}:{2}, self: {3}:{4}'.format(beacon, dbhost, dbport, host, port))

    init_conn_string(dbhost, dbport)
else:
    init_conn_string('10.0.0.20', 5432)
###<< MAIN ##

###>> init models
from common.models import *
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

msg_put_invalid_input = 'PUT requires additional json field <changes>:[list_of_key-value_pairs]}'

###>> Sharding ###
def encode_pkv(val):
    return sh_ev(val, SHARDS_COUNT, SHARD_NUMBER)

def decode_pkv(val):
    return sh_dv(val, SHARDS_COUNT, SHARD_NUMBER)

def encode_kwargs(tbl, kwargs):
    #for k, v in kwargs.items():
    #    if k in tbl.metainf.fk_fields:
    #        kwargs[k] = encode_pkv(v)
    return kwargs

def decode_kwargs(tbl, kwargs):
    #for k, v in kwargs.items():
    #    if k in tbl.metainf.fk_fields:
    #        kwargs[k] = decode_pkv(v)
    return kwargs

def to_dict(obj):
    #affected_flds = obj.metainf.fk_fields + [obj.metainf.pk_field]
    affected_flds = [obj.metainf.pk_field]
    d = obj.to_dict()
    for f in obj.metainf.col_type_d:
        if f in affected_flds:
            if d[f]:
                d.update({f : decode_pkv(d[f])})
    return d

###<< Sharding ###

def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

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
    tbl = table_name_d[table]

    bres, maybe_val = parse_field_value(tbl, column, value)
    if not bres:
        return maybe_val
    epkv = encode_pkv(maybe_val)

    res = tbl.query.filter_by(**{column : epkv}).first()
    if res:
        return api_200(to_dict(res))
    else:
        return api_404()

def post_item(table, value_json):
    tbl = table_name_d[table]
    
    bres, maybe_kwargs = try_json_to_filter_kwargs(tbl, value_json)
    if not bres:
        return maybe_kwargs
    ekws = encode_kwargs(tbl, maybe_kwargs)

    val = None
    try:
        val = tbl(**ekws)
    except Exception as e:
        return api_400(str(e))
    
    try:
        db_session.add(val)
        db_session.flush()
    except IntegrityError as e:
        db_session.rollback()
        return api_500(str(e))
    
    return api_200(to_dict(val))

def put_item(table, pkf, pkfvs, value_json):
    tbl = table_name_d[table]

    if pkf == tbl.metainf.pk_field:
        bres, maybe_val = parse_field_value(tbl, pkf, pkfvs)
        if not bres:
            return maybe_val
        epkv = encode_pkv(maybe_val)

        item = None
        try:
            item = tbl.query.filter_by(**{pkf : epkv}).first()
        except Exception as e:
            return api_404(msg_col_not_found_fmt.format(table, pkf))
        
        if not item:
            return api_404()

        bres, maybe_kwargs = try_json_to_filter_kwargs(tbl, value_json)
        if not bres:
            return maybe_kwargs
        ekws = encode_kwargs(tbl, maybe_kwargs)

        db_session.begin()
        try:
            update_table_object(item, **ekws)
            db_session.commit()
        except IntegrityError as e:
            db_session.rollback()
            return api_500(str(e))
        
        return api_200(to_dict(item))
    else:
        return api_400(msg_pk_invalid_fmt.format(table, pkf))

def delete_item(table, pkf, pkfvs):
    tbl = table_name_d[table]
    
    if pkf == tbl.metainf.pk_field:
        bres, maybe_val = parse_field_value(tbl, pkf, pkfvs)
        if not bres:
            return maybe_val
        epkv = encode_pkv(maybe_val)

        item = None
        try:
            item = tbl.query.filter_by(**{pkf : epkv}).first()
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
    tbl = table_name_d[table]
    bres, maybe_kwargs = try_json_to_filter_kwargs(tbl, value_json)
    if not bres:
        return maybe_kwargs
    ekws = encode_kwargs(tbl, maybe_kwargs)

    reslo = tbl.query.filter_by(**ekws).all()
    if reslo:
        resld = list(map(lambda x: to_dict(x), reslo))
        return api_200({'result': resld})
    else:
        return api_404()

def table_arrayfilter_get(table, value_json):
    tbl = table_name_d[table]

    qry = tbl.query
    for f, vl in value_json.items():
        if f in tbl.metainf.col_type_d:
            pvl = []
            for v in vl:
                bres, maybe_val = parse_field_value(tbl, f, v)
                if not bres:
                    return maybe_val
                pvl += [maybe_val]
                #if f in tbl.metainf.fk_fields + [tbl.metainf.pk_field]:
                if f in [tbl.metainf.pk_field]:
                    pvl = (encode_pkv(v) for v in pvl)
            qry = qry.filter(getattr(tbl, f).in_(pvl))
        else:
            return msg_col_not_found_fmt.format(table, f)
    qres = qry.all()

    resld = list(map(lambda x: to_dict(x), qres))
    return api_200({'result': resld})

def table_filter_delete(table, value_json):
    tbl = table_name_d[table]

    bres, maybe_kwargs = try_json_to_filter_kwargs(tbl, value_json)
    if not bres:
        return maybe_kwargs
    ekws = encode_kwargs(tbl, maybe_kwargs)

    reslo = tbl.query.filter_by(**ekws).all()
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
    tbl = table_name_d[table]

    bres, maybe_filter_kwargs = try_json_to_filter_kwargs(tbl, value_json, ['changes'])
    if not bres:
        return maybe_filter_kwargs
    efkws = encode_kwargs(tbl, maybe_filter_kwargs)

    bres, maybe_changes_kwargs = try_json_to_filter_kwargs(tbl, value_json['changes'])
    if not bres:
        return maybe_changes_kwargs
    eckws = encode_kwargs(tbl, maybe_changes_kwargs)

    reslo = tbl.query.filter_by(**efkws).all()
    if reslo:
        db_session.begin()
        try:
            for obj in reslo:
                update_table_object(obj, **eckws)
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            return api_500(str(e))

        return api_200({'count': len(reslo)})
    else:
        return api_404()

def table_bulk_get(table):
    tbl = table_name_d[table]

    res = tbl.query.all()
    resd = [to_dict(r) for r in res]
    return api_200({'result' : resd})

### Bulk interface ###

@app.route('/<table>', methods=['GET'])
def view_bulk_get(table):
    return table_bulk_get(table)

### Array filtering ###
@app.route('/<table>/arrayfilter', methods=['GET'])
def view_arrayfilter_item_get(table):
    value_json = request.get_json()
    return table_arrayfilter_get(table, value_json)

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

### Custom ###
@app.route('/custom/get_free_subtask_by_agent_id', methods = ['GET'])
def hnd_get_free_subtask_by_agent_id():
    if has_url_parameter('agent_id'):
        agent_id = get_url_parameter('agent_id')
        return get_free_subtask_by_agent_id(agent_id)
    else:
        return api_400('Bad request: Required <agent_id> parameter')

### Error handlers ###
@app.errorhandler(500)
def api_500(msg = 'Internal error'):
    return response_builder({'error': msg, 'shard' : SHARD_NUMBER}, 500)

@app.errorhandler(400)
def api_400(msg = 'Bad request'):
    return response_builder({'error': msg, 'shard' : SHARD_NUMBER}, 400)

@app.errorhandler(404)
def api_404(msg = 'Not found'):
    return response_builder({'error': msg, 'shard' : SHARD_NUMBER}, 404)

@app.errorhandler(200)
def api_200(data = {}):
    return response_builder(data, 200)

### Other ###

if __name__ == '__main__':
    bw = BeaconWrapper(beacon, port, 'services/database')
    bw.beacon_setter()
    print('#' * 80)
    print('IMPORTANT: Acting as shard #{0} of {1}'.format(SHARD_NUMBER, SHARDS_COUNT))
    print('This means that all autoincrement IDs WILL be changed accordingly.')
    print('#' * 80)
    app.run(host = host, port = port)