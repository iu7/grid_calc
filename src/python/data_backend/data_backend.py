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

def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

def check_mtm(table, value_json):
    if table in mtm_table_name_d:
        mtmd = mtm_table_name_d[table]
        kwargs = {}
        for pk, tbl in list(mtmd[1].items()) + list(mtmd[0].items()):
            if pk in value_json:
                value = value_json[pk]
                kwargs.update({pk : value})
        res = db_session.query(mtmd[2]).filter_by(**kwargs).first()
        if res:
            return api_200(kwargs)
        else:
            return api_404()
    elif table in table_name_d:
        return api_400('Bad request: Only MtM tables supported')
    else:
        return api_404(msg_tbl_not_found_fmt.format(table))

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
        return api_400('Bad request: For MtM table use GET /data/table/mtmcheck endpoint')
    else:
        return api_404(msg_tbl_not_found_fmt.format(table))

def post_item(table, value_json):
    if table in table_name_d:
        tbl = table_name_d[table]
        kwargs = {}
        for field, value in value_json.items():
            if field in tbl.metainf.col_type_d:
                tp = tbl.metainf.col_type_d[field]
                tppsr = tbl.metainf.col_type_parsers[field] if field in tbl.metainf.col_type_parsers else tp
                try:
                    kwargs.update({field : tppsr(value)})
                except Exception as e:
                    return api_400(msg_type_err_fmt.format(table, field, value, tp, type(value)))
            else:
                return api_404(msg_col_not_found_fmt.format(table, field))
        val = None
        try:
            val = tbl(**kwargs)
        except Exception as e:
            return api_400(str(e))
        db_session.add(val)
        db_session.commit()
        return api_200(val.to_dict())
    elif table in mtm_table_name_d:
        mtmd = mtm_table_name_d[table]
        par_tbl_pk, par_tbl = list(mtmd[0].items())[0]
        for pk, tbl in mtmd[1].items():
            if pk in value_json:
                obj = tbl.query.filter_by(**{tbl.metainf.pk_field : value_json[pk]}).first()
                if obj:
                    if pk in par_tbl.metainf.relationship_lst:
                        if par_tbl_pk in value_json:
                            parobj = par_tbl.query.filter_by(**{par_tbl.metainf.pk_field : value_json[par_tbl_pk]}).first()
                            if parobj:
                                parobj.metainf.relationship_by_pk(pk, parobj).append(obj)
                                db_session.commit()
                                return api_200()
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
    else:
        return api_404(msg_tbl_not_found_fmt.format(table))

def put_item(table, pkf, pkfv, value_json):
    if table in table_name_d:
        tbl = table_name_d[table]

        if pkf != tbl.metainf.pk_field:
            pkft = tbl.metainf.col_type_d[pkf]
            pkftpsr = tbl.metainf.col_type_parsers[pkf] if pkf in tbl.metainf.col_type_parsers else pkft
            pkfvs = value_json[pkf]
            pkfv = None
            try:
                pkfv = pkpftpsr(pkfvs)
            except Exception as e:
                return api_400(msg_type_err_fmt.format(table, pkf, pkfvs, pkft, pkf, type(pkfvs)))
            
            item = None
            try:
                tbl.query.filter_by({pkf : pkfv}).first()
            except Exception as e:
                return api_404(msg_col_not_found_fmt.format(table, pkf))
            
            if not item:
                return api_404()

            for field, value in value_json.items():
                if field in tbl.metainf.col_type_d:
                    tp = tbl.metainf.col_type_d[field]
                    tppsr = tbl.metainf.col_type_parsers[field] if field in tbl.metainf.col_type_parsers else tp
                    try:
                        setattr(item, field, tppsr(field))
                    except Exception as e:
                        return api_400(msg_type_err_fmt.format(table, field, value, tp, type(value)))
                else:
                    return api_404(msg_col_not_found_fmt.format(table, field))

            db_session.update(item)
            db_session.commit()
        else:
            return api_400(msg_pk_invalid_fmt.format(table, pkf))
    else:
        return api_404(msg_tbl_not_found_fmt.format(table))

def delete_item(table, pkf, pkfv):
    if table in table_name_d:
        tbl = table_name_d[table]
        
        if pkf != tbl.metainf.pk_field:
            pkft = tbl.metainf.col_type_d[pkf]
            pkftpsr = tbl.metainf.col_type_parsers[pkf] if pkf in tbl.metainf.col_type_parsers else pkft
            pkfvs = value_json[pkf]
            pkfv = None
            try:
                pkfv = pkpftpsr(pkfvs)
            except Exception as e:
                return api_400(msg_type_err_fmt.format(table, pkf, pkfvs, pkft, pkf, type(pkfvs)))
            
            item = None
            try:
                tbl.query.filter_by({pkf : pkfv}).first()
            except Exception as e:
                return api_404(msg_col_not_found_fmt.format(table, pkf))
            
            if not item:
                return api_404()

            db_session.delete(item)
            db_session.commit()
        else:
            return api_400(msg_pk_invalid_fmt.format(table, pkf))
    else:
        return api_404(msg_tbl_not_found_fmt.format(table))

@app.route('/data/<table>/mtmcheck', methods=['GET'])
def rest_check_mtm(table):
    value = get_url_parameter('value')
    return check_mtm(table, value)

@app.route('/data/<table>/<column>/<value>', methods=['GET'])
def rest_get_item(table, column, value):
    return get_item(table, column, value)

@app.route('/data/<table>/<int:id>', methods=['GET'])
def rest_get_item_by_id(table, id):
    return get_item(table, 'id', id)

@app.route('/data/<table>', methods=['POST'])
def rest_post_item(table):
    value = get_url_parameter('value')
    return post_item(table, value)

@app.route('/data/<table>/<column>/<value>', methods=['PUT'])
def rest_put_item(table, column, value):
    return put_item(table, column, value)

@app.route('/data/<table>/<column>/<value>', methods=['DELETE'])
def rest_delete_item(table, column, value):
    return delete_item(table, column, value)

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