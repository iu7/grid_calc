from settings import *
from models import *

from flask import *
from werkzeug.routing import BaseConverter

app = Flask(__name__)
app.config.update(dict(\
    SQLALCHEMY_DATABASE_URI=DATABASE_CONNECTION_STRING),\
    DEBUG=True\
)

### I don't have a single idea of how this RegexCoverter works.
class RegexConverter(BaseConverter):
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


app.url_map.converters['regex'] = RegexConverter
###

@app.route('/data/<table>s/<column>/<value>', methods=['GET'])
def rest_get_item():


### Error handlers ###
        
@app.errorhandler(404)
def api_404(msg = 'Not found'):
    return response_builder({'error': msg}, 404)

@app.errorhandler(200)
def api_200(data = {}):
    return response_builder(data, 200)

### Other ###

#if __name__ == '__main__':
#    protocol, host, port = settings.backends['session'].split(':')
#    app.run(host = host[2:], port = int(port))