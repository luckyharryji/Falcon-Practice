import json
import logging
import uuid
import wsgiref import simple_server

import falcon
import request

class StorageEngine(object):
    def get_things(self,marker,limit):
        return [{'id':str(uuid.uuid4()),'color':'green'}]

    def add_things(self,thing):
        thing['id']=str(uuid.uuid4())
        return thing

class StorageError(Exception):
    @staticmethod
    def handle(ex,req,resp,params):
        description=('sorry, could not write your thing to the dataabase')
        raise falcon.HTTPError(falcon.HTTP_725,'Data Base Error',description)

class SinkAdapter(object):
    engines = {
        'ddg': 'https://duckduckgo.com',
        'y': 'https://search.yahoo.com/search',
    }
    def __call__(self,req,resp,engine):
        url = self.engines[engine]
        params = {'q':req.get_param('q',True)}
        result = request.get(url,params=params)
        resp.status = str(result.status_code)+' '+resp.reason
        resp.content_type = result.handlers['content_type']
        resp.body = result.text

class AuthMiddleware(object):
    def _token_is_valid(self,token,project):
        return True

    def process_request(self,req,resp):
        token = req.get_header('X-Auth-Token')
        project = req.get_header('X-Project-ID')
        if token is None:
            description = ('please provide auth token')
            raise falcon.HTTPUnauthorized('Auth token required',description,href='http://docs.example.com/auth',scheme='Token; UUID'))
        if not self._token_is_valid(token,project):
            description = ('the token is not valid')
            raise falcon.HTTPUnauthorized('Auth required',description,href='http://docs.example.com/auth',scheme = 'Token;UUID')


class RequireJSON(object):
    def process_request(self,req,resp):
        if not req.client_accepts_json:
            raise falcon.HTTPNotAcceptable('API only supports responses encodes as JSON',href='http://docs.examples.com/api/json')
        if req.method in('POST','PUT'):
            if 'application/json' not in req.content_type:
                raise falcon.HTTPUnsupportedMediaType('API only supports requests encoded as JSON',href='http://docs.examples.com/api/json')

class JSONTranslator(object):
    def process_request(self,req,resp):
        if req.content_length in (None, 0):
            # Nothing to do
            return

        body = req.stream.read()
        if not body:
            raise falcon.HTTPBadRequest('Empty request body',
                                        'A valid JSON document is required.')

        try:
            req.context['doc'] = json.loads(body.decode('utf-8'))

        except (ValueError, UnicodeDecodeError):
            raise falcon.HTTPError(falcon.HTTP_753,
                                   'Malformed JSON',
                                   'Could not decode the request body. The '
                                   'JSON was incorrect or not encoded as '
                                   'UTF-8.')

    def process_response(self, req, resp, resource):
        if 'result' not in req.context:
            return

        resp.body = json.dumps(req.context['result'])


def max_body(limit):
    def hook(req, resp, resource, params):
        length = req.content_length
        if length is not None and length > limit:
            msg = ('The size of the request is too large. The body must not '
                   'exceed ' + str(limit) + ' bytes in length.')

            raise falcon.HTTPRequestEntityTooLarge(
                'Request body is too large', msg)

    return hook


class ThingsResource:
