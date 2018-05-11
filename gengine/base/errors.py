# -*- coding: utf-8 -*-
from pyramid.view import view_config
from pyramid.response import Response
import json
from pyramid.renderers import render_to_response

class APIError(Exception):
    def __init__(self, code, status, message):
        self.code = code
        self.status = status
        self.message = message

class HTMLError(Exception):
    def __init__(self, code, message, description):
        self.code = code
        self.message = message
        self.description = description

@view_config(context=APIError)
def json_exception_view(exc, request):
    s = json.dumps({
        "status": exc.status,
        "message": exc.message,
    })
    response = Response(s)
    response.content_type = "application/json"
    response.status_int = exc.code
    return response


@view_config(context=HTMLError)
def html_exception_view(exc, request):
    response = render_to_response("../templates/error.html", {
        "description": exc.description,
        "message": exc.message,
    }, request)
    response.status_int = exc.code
    return response
