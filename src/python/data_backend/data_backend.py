import settings
import threading
import requests as pyrequests

from common import *

from flask import *
from werkzeug.routing import BaseConverter

app = Flask(__name__)
app.config.update(DEBUG = True)

###>> MAIN ###
import sys

def init_conn_string(dbhost, dbport = 5432):
    app.config.update(dict(SQLALCHEMY_DATABASE_URI=settings.get_connection_string(dbhost, dbport)))

if __name__ == '__main__':
    dbhost = None
    dbport = None
    beacon_host = None
    beacon_port = None
    host = '0.0.0.0'
    port = 50001
    try:
        beacon_host, beacon_port = sys.argv[1].split(':')
        dbhost, sdbport = sys.argv[2].split(':')
        dbport = int(sdbport)
        if len(sys.argv) > 3:
            port = int(sys.argv[3])
    except Exception as e:
        print('Usage: {0} dbhost:dbport [port]'.format(sys.argv[0]))
        sys.exit()

    print('Starting with settings: Beacon: {0}:{1} DB: {2}:{3}, self: {4}:{5}'.format(beacon_host, beacon_port, dbhost, dbport, host, port))

    init_conn_string(dbhost, dbport)
else:
    init_conn_string('127.0.0.1', 5432)

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
    res = tbl.query.filter_by(**{column : maybe_val}).first()
    if res:
        return api_200(res.to_dict())
    else:
        return api_404()

def post_item(table, value_json):
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

def put_item(table, pkf, pkfvs, value_json):
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

def delete_item(table, pkf, pkfvs):
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
    tbl = table_name_d[table]
    bres, maybe_kwargs = try_json_to_filter_kwargs(tbl, value_json)
    if not bres:
        return maybe_kwargs

    reslo = tbl.query.filter_by(**maybe_kwargs).all()
    resld = list(map(lambda x: x.to_dict(), reslo))
    return api_200({'result': resld})

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
            qry = qry.filter(getattr(tbl, f).in_(pvl))
        else:
            return msg_col_not_found_fmt.format(table, f)
    qres = qry.all()

    resld = list(map(lambda x: x.to_dict(), qres))
    return api_200({'result': resld})

def table_filter_delete(table, value_json):
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

def sync(batch):
    for json_obj in batch:
        if all(field in json_obj for field in ['table', 'data']):
            table = json_obj['table']
            data = json_obj['data']
            if table in table_name_d:
                tbl = table_name_d[table]
                for jobj in data:
                    bres, maybe_kwargs = try_json_to_filter_kwargs(tbl, jobj)
                    if not bres:
                        return maybe_kwargs
                    qry = None
                    if table in mtm_table_name_d:
                        qry = tbl.query.filter_by(**maybe_kwargs)
                    else:
                        qry = tbl.query.filter_by(**{tbl.metainf.pk_field : maybe_kwargs[tbl.metainf.pk_field]})
                    obj = qry.first()
                    if obj:
                        try:
                            fill_object(obj, tbl.metainf.col_type_d, **maybe_kwargs)
                        except Exception as e:
                            return api_400(str(e))
                    else:
                        try:
                            val = tbl(**maybe_kwargs)
                        except Exception as e:
                            return api_400(str(e))
                            db_session.add(val)
            else:
                return api_404(msg_tbl_not_found_fmt.format(table))
        else:
            return api_400('Bad request: Sync requires {["table":"tablename", "data": [objects]]}')

### Custom ###
def get_free_subtask_by_agent_id(agent_id, status = 'queued', newstatus = 'taken'):
    bres, maybe_val = parse_field_value(table_name_d['agent'], 'id', agent_id)
    if not bres:
        return maybe_val
    agent_id = maybe_val

    tblMtmTA = table_name_d['mtm_traitagent']
    tblMtmTT = table_name_d['mtm_traittask']
    tblSubtask = table_name_d['subtask']

    trait_idc = tblMtmTA.query.filter_by(agent_id = agent_id).all()
    trait_ids = (mtmtr.trait_id for mtmtr in trait_idc)

    subtasks = tblSubtask.query.filter_by(status = status).all()
    task_ids = (sbtsk.task_id for sbtsk in subtasks)

    mtmtto = tblMtmTT.query\
        .filter(tblMtmTT.task_id.in_(task_ids))\
        .filter(tblMtmTT.trait_id.in_(trait_ids))\
        .first()
    if mtmtto:
        res = next(sbtsk for sbtsk in subtasks if sbtsk.task_id == mtmtto.task_id)
        res.status = newstatus
        res.agent_id = agent_id
        db_session.flush()
        return api_200(res.to_dict())
    else:
        return api_404()

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

### Sync (with local DB on sharding backend after connection reestablishment) ###
@app.route('/sync', methods=['POST'])
def rpc_sync(table):
    value = request.get_json()
    return sync(value)

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
beacon_adapter_cycletime = 3
beacon_fmt = 'http://{0}:{1}'
stateNormal = 'Operating normally'
stateNoBeacon = 'Unable to find beacon'
state = stateNormal

bcmsg = False
def beaconDownMsg():
    global bcmsg
    if (not bcmsg): 
        print ('Beacon is down. Waiting to reconnect.')
        bcmsg = True

def beaconUpMsg():
    global bcmsg
    if (bcmsg): 
        print ('Beacon is back up.')
        bcmsg = False
        
def beacon_setter():
    beacon = beacon_fmt.format(beacon_host, beacon_port)
    messaged = False
    global selfaddress
    global state
    while (not messaged):
        try:
            if selfaddress == None:
                selfaddress = pyrequests.post(beacon + '/services/database', data={'port':beacon_port, 'state':state}).json()['address']
            else:
                pyrequests.put(beacon + '/services/database/' + selfaddress, data={'state':state})
            
            thr = threading.Timer(beacon_adapter_cycletime, beacon_setter)
            thr.daemon = True
            thr.start()
            messaged = True
            state = stateNormal
            beaconUpMsg()
        except:
            state = stateNoBeacon
            beaconDownMsg()
selfaddress = None

if __name__ == '__main__':
    beacon_setter()
    app.run(host = host, port = port)