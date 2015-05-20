import settings
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
    host = '0.0.0.0'
    port = 50001
    try:
        dbhost, sdbport = sys.argv[1].split(':')
        dbport = int(sdbport)
        if len(sys.argv) > 2:
            port = int(sys.argv[2])
    except Exception as e:
        print('Usage: {0} dbhost:dbport [port]'.format(sys.argv[0]))
        sys.exit()

    print('Starting with settings: DB: {0}:{1}, self: {2}:{3}'.format(dbhost, dbport, host, port))

    init_conn_string(dbhost, dbport)
else:
    init_conn_string('10.0.0.10', 5432)

###<< MAIN ##

###>> init models
from models import *
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], convert_unicode=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

init_models(Base)
Subtask,\
Task,\
Agent,\
Trait,\
User,\
UserSession = table_name_d.values()
###<< init models

msg_type_err_fmt = 'table <{0}>, column <{1}>: cannot convert <{2}> to type <{3}> from type <{4}>'
msg_pk_invalid_fmt = 'table <{0}>: invalid primary key field <{1}> specified'
msg_col_not_found_fmt = 'table <{0}>: column <{1}> not found'
msg_tbl_not_found_fmt = 'table <{0}>: not found'
msg_item_not_found_fmt = 'table <{0}>: <{1}> = <{2}> not found'
msg_mtm_pk_not_found_fmt = 'MtM table <{0}>: pk <{1}> not found in input'

msg_mtm_only = 'Bad request: Only MtM tables supported'
msg_mtm_not_found = 'MtM relation not found'
msg_put_invalid_input = 'Bad request: PUT requires additional json field "changes":[list_of_key-value_pairs]}'

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

def get_mtm(table, value_json):
    if table in mtm_table_name_d:
        mtmd = mtm_table_name_d[table]
        kwargs = {}
        for pk, tbl in list(mtmd[1].items()) + list(mtmd[0].items()):
            if pk in value_json:
                value = value_json[pk]
                kwargs.update({pk : value})
            else:
                return api_404(msg_mtm_pk_not_found_fmt.format(table, pk))
        res = db_session.query(mtmd[2]).filter_by(**kwargs).first()
        if res:
            return api_200(kwargs)
        else:
            return api_404()
    elif table in table_name_d:
        return api_400(msg_mtm_only)
    else:
        return api_404(msg_tbl_not_found_fmt.format(table))

def delete_mtm(table, value_json):
    if table in mtm_table_name_d:
        mtmd = mtm_table_name_d[table]
        par_tbl_pk, par_tbl = list(mtmd[0].items())[0]
        for pk, tbl in mtmd[1].items():
            if pk in value_json:
                bres, res = parse_field_value(tbl, tbl.metainf.pk_field, value_json[pk])
                if not bres:
                    return res
                obj = tbl.query.filter_by(**{tbl.metainf.pk_field : res}).first()
                if obj:
                    if pk in par_tbl.metainf.relationship_lst:
                        if par_tbl_pk in value_json:
                            bres_, res_ = parse_field_value(par_tbl, par_tbl.metainf.pk_field, value_json[par_tbl_pk])
                            if not bres_:
                                return res_
                            parobj = par_tbl.query.filter_by(**{par_tbl.metainf.pk_field : res_}).first()
                            if parobj:
                                coll = parobj.metainf.relationship_by_pk(pk, parobj)
                                if obj in coll:
                                    parobj.metainf.relationship_by_pk(pk, parobj).remove(obj)
                                else:
                                    return api_404(msg_mtm_not_found)
                            else:
                                return api_404(msg_item_not_found_fmt.format(par_tbl.__tablename__, par_tbl.metainf.pk_field, value_json[par_tbl_pk]))
                        else:
                            return api_400(msg_mtm_pk_not_found_fmt.format(table, par_tbl_pk))
                    else:
                        return api_404(msg_col_not_found_fmt.format(par_tbl, pk))
                else:
                    return api_404(msg_item_not_found_fmt.format(tbl.__tablename__, tbl.metainf.pk_field, value_json[pk]))
            else:
                return api_400(msg_mtm_pk_not_found_fmt.format(table, pk))
        db_session.commit()
        return api_200()
    elif table in table_name_d:
        return api_400(msg_mtm_only)
    else:
        return api_404(msg_tbl_not_found_fmt.format(table))

def post_mtm(table, value_json):
    mtmd = mtm_table_name_d[table]
    par_tbl_pk, par_tbl = list(mtmd[0].items())[0]
    for pk, tbl in mtmd[1].items():
        if pk in value_json:
            bres, res = parse_field_value(tbl, tbl.metainf.pk_field, value_json[pk])
            if not bres:
                return res
            obj = tbl.query.filter_by(**{tbl.metainf.pk_field : res}).first()
            if obj:
                if pk in par_tbl.metainf.relationship_lst:
                    if par_tbl_pk in value_json:
                        bres_, res_ = parse_field_value(par_tbl, par_tbl.metainf.pk_field, value_json[par_tbl_pk])
                        if not bres_:
                            return res_
                        parobj = par_tbl.query.filter_by(**{par_tbl.metainf.pk_field : res_}).first()
                        if parobj:
                            parobj.metainf.relationship_by_pk(pk, parobj).append(obj)
                        else:
                            return api_404(msg_item_not_found_fmt.format(par_tbl.__tablename__, par_tbl.metainf.pk_field, value_json[par_tbl_pk]))
                    else:
                        return api_400(msg_mtm_pk_not_found_fmt.format(table, par_tbl_pk))
                else:
                    return api_404(msg_col_not_found_fmt.format(par_tbl, pk))
            else:
                return api_404(msg_item_not_found_fmt.format(tbl.__tablename__, tbl.metainf.pk_field, value_json[pk]))
        else:
            return api_400(msg_mtm_pk_not_found_fmt.format(table, pk))
    db_session.commit()
    return api_200()

def get_item(table, column, value):
    res = None
    if table in table_name_d:
        tbl = table_name_d[table]
        if column in tbl.metainf.col_type_d:
            tp = tbl.metainf.col_type_d[column]
            tppsr = tbl.metainf.col_type_parsers[column] if column in tbl.metainf.col_type_parsers else tp
            try:
                res = tbl.query.filter_by(**{column : tppsr(value)})
                res = res.first()
                if res:
                    return api_200(res.to_dict())
                else:
                    return api_404()
            except Exception as e:
                return api_400(msg_type_err_fmt.format(table, column, value, tp, type(value)))
        else:
            return api_404(msg_col_not_found_fmt.format(table, column))
    elif table in mtm_table_name_d:
        return api_400('Bad request: For MtM table use GET /data/mtm/table/ endpoint with required JSON parameters.')
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
        db_session.add(val)
        db_session.commit()
        return api_200(val.to_dict())
    elif table in mtm_table_name_d:
        return post_mtm(table, value_json)
    else:
        return api_404(msg_tbl_not_found_fmt.format(table))

def put_item(table, pkf, pkfvs, value_json):
    if table in table_name_d:
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

            bres, maybe_kwargs = try_json_to_filter_kwargs(tbl, value_json)
            if not bres:
                return maybe_kwargs

            update_table_object(item, **maybe_kwargs)
            db_session.commit()
            return api_200(item.to_dict())
        else:
            return api_400(msg_pk_invalid_fmt.format(table, pkf))
    elif table in mtm_table_name_d:
        return api_400('Bad request: Unsupported for MtM tables. Perform a chain Delete -> Insert.')
    else:
        return api_404(msg_tbl_not_found_fmt.format(table))

def delete_item(table, pkf, pkfvs):
    if table in table_name_d:
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

            db_session.delete(item)
            db_session.commit()
            return api_200()
        else:
            return api_400(msg_pk_invalid_fmt.format(table, pkf))
    elif table in mtm_table_name_d:
        return api_400('Bad request: For MtM table use DELETE /data/mtm/table/ endpoint with required JSON parameters')
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
            for obj in reslo:
                db_session.delete(obj)
            db_session.commit()
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
                for obj in reslo:
                    update_table_object(obj, **maybe_changes_kwargs)
                db_session.commit()
                return api_200({'count': len(reslo)})
            else:
                return api_404()
        else:
            return api_404(msg_tbl_not_found_fmt.format(table))
    else:
        return api_400('Bad request: Object <changes> not found in input')

### MtM ###

@app.route('/data/mtm/<table>', methods=['GET'])
def view_mtm_get(table):
    value = get_url_parameter('value')
    return get_mtm(table, value)

@app.route('/data/mtm/<table>', methods=['DELETE'])
def view_mtm_delete(table):
    value = get_url_parameter('value')
    return delete_mtm(table, value)

### Filtering ###

@app.route('/data/<table>/filter', methods=['GET'])
def view_filter_item_get(table):
    value_json = get_url_parameter('value')
    return table_filter_get(table, value_json)

@app.route('/data/<table>/filter', methods=['PUT'])
def view_filter_item_put(table):
    value_json = get_url_parameter('value')
    return table_filter_put(table, value_json)

@app.route('/data/<table>/filter', methods=['DELETE'])
def view_filter_item_delete(table):
    value_json = get_url_parameter('value')
    return table_filter_delete(table, value_json)

### Normal ###

@app.route('/data/<table>/<column>/<value>', methods=['GET'])
def view_rest_get_item(table, column, value):
    return get_item(table, column, value)

@app.route('/data/<table>/<int:id>', methods=['GET'])
def view_rest_get_item_by_id(table, id):
    return get_item(table, 'id', id)

@app.route('/data/<table>/<column>/<value>', methods=['PUT'])
def view_rest_put_item(table, column, value):
    value_json = get_url_parameter('value')
    return put_item(table, column, value, value_json)

@app.route('/data/<table>/<column>/<value>', methods=['DELETE'])
def view_rest_delete_item(table, column, value):
    return delete_item(table, column, value)

### Both ###

@app.route('/data/<table>', methods=['POST'])
def rest_post_item(table):
    value = get_url_parameter('value')
    return post_item(table, value)

### Error handlers ###
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