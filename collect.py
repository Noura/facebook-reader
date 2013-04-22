#!/usr/bin/python

import requests
import json
import os

import config
from secret_constants import access_token

outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), config.data_dir)

class FacebookException(Exception):
    pass

def fb_call(node, fields):
    params = {'fields': fields, 'access_token': access_token}
    r = requests.get(config.fb_graph_url + node + '?', params=params)
    r = r.json()
    if 'error' in r:
        raise FacebookException('error in response from facebook')
    return r

def getter(node, fields, out):
    out = os.path.join(outdir, out)
    try:
        f = open(out, 'r')
        return json.loads(f.read())
    except IOError:
        data = fb_call(node, fields)
        with open(out, 'w') as out:
            out.write(json.dumps(data, indent=4, sort_keys=True))
        return data

if __name__ == '__main__':
    friends = getter('me', 'friends', config.friends_list_filename)
    for friend in friends['friends']['data']:
        try:
            getter(friend['id'], 'statuses', config.friend_statuses_filename(friend['id'], friend['name']))
        except:
            break

