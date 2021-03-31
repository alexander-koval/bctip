"""
  Copyright (c) 2007 Jan-Klaas Kollhof

  This file is part of jsonrpc.

  jsonrpc is free software; you can redistribute it and/or modify
  it under the terms of the GNU Lesser General Public License as published by
  the Free Software Foundation; either version 2.1 of the License, or
  (at your option) any later version.

  This software is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Lesser General Public License for more details.

  You should have received a copy of the GNU Lesser General Public License
  along with this software; if not, write to the Free Software
  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
import json
from json import dumps

import requests


class JSONRPCException(Exception):
    def __init__(self, rpc_error):
        Exception.__init__(self)
        self.error = rpc_error


class ServiceProxy(object):
    def __init__(self, service_url, service_name=None):
        self.__service_url = service_url
        self.__service_name = service_name

    def __getattr__(self, name):
        if self.__service_name is not None:
            name = "%s.%s" % (self.__service_name, name)
        return ServiceProxy(self.__service_url, name)

    def __call__(self, *args):
        post_data = dumps({"method": self.__service_name, 'params': args, 'id': 'jsonrpc'})
        headers = {'Content-Type': "application/json"}
        payload = "{\"jsonrpc\":\"1.0\",\"method\":\"%s\",\"params\":%s}" % (
            self.__service_name, json.dumps(list(args)))
        # payload = "{\"jsonrpc\":\"1.0\", \"method\": {}, \"params\": {}}".format(self.__service_name, args)
        print(payload)
        response = requests.request("POST", self.__service_url, data=payload, headers=headers)
        # resp_data = request.urlopen(self.__service_url, post_data.encode('utf-8')).read()
        # resp = loads(resp_data)
        resp = response.json()
        print(resp)
        if resp['error'] is not None:
            raise JSONRPCException(resp['error'])
        else:
            return resp['result']
