import requests
import json
import os
import re
from multiprocessing import Process, Queue
from Queue import Empty

import config
from secret_constants import access_token

outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), config.data_dir)

class Stats(object):
    def __init__(self, _dict=None):
        if _dict:
            self.sums = _dict['sums']
        else:
            self.sums = [0, 0, 0, 0, 0]
    def update(self, x):
        prod = 1
        for i in range(len(self.sums)):
            self.sums[i] += prod
            prod *= x
    def n(self):
        return self.sums[0]
    def avg(self):
        if self.sums[0] == 0:
            return None
        else:
            return float(self.sums[1])/self.sums[0]
    def std_dev(self):
        if self.sums[0] == 0:
            return None
        else:
            return (float(self.sums[2])/self.sums[0] - self.avg()**2)**(.5)

class FriendWordCounts(object):
    def __init__(self, friend_id=None, friend_name=None, _dict=None):
    # provide (friend_id and friend_name) or _dict
        if _dict:
            self.friend_id = _dict['friend_id']
            self.friend_name = _dict['friend_name']
            self.counts = _dict['counts']
            self.n = _dict['n']
        else:
            self.friend_id = friend_id
            self.friend_name = friend_name
            self.counts = {}
            self.n = 0
    def update(self, words):
        # words is a list or generator 
        # of words or of messages that should be split into words
        for ws in words:
            for w in re.findall('[A-Za-z0-9]+', ws):
                if w not in self.counts:
                    self.counts[w] = 0
                self.counts[w] += 1
                self.n += 1
    def finalize(self):
        if self.n <= 0:
            return
        n = float(self.n)
        for w in self.counts:
            self.counts[w] /= n
    def word_counts(self):
        return self.counts.iteritems()

class Population(object):
    def __init__(self, name=None, _dict=None):
        if _dict:
            self.name = _dict['name']
            self.counts = {
                word: {
                    'word': word,
                    'ids': d['ids'],
                    'stats': Stats(_dict=d['stats'])
                } for word, d in _dict['counts'].iteritems()
            }
            self.n = _dict['n']
        else:
            self.name = name
            self.counts = {}
            self.n = 0
    def update(self, word_counts):
        for word, count in word_counts.word_counts():
            if word not in self.counts:
                self.counts[word] = {
                    'word': word,
                    'ids': [],
                    'stats': Stats()
                }
            self.counts[word]['ids'].append(word_counts.friend_id)
            self.counts[word]['stats'].update(count)
            self.n += 1
    def word_counts(self):
        return self.counts.iteritems()

class PopulationEncoder(json.JSONEncoder):
    def default(self, obj):
        if not isinstance(obj, Population):
            return super(PopulationEncoder, self).default(obj)
        d = obj.__dict__
        for s in d['counts']:
            d['counts'][s]['stats'] = d['counts'][s]['stats'].__dict__
        return d

class FacebookException(Exception):
    pass

def fb_call(node, fields, page_url=None):
    if page_url:
        r = requests.get(page_url)
    else:
        if type(fields) == 'list' or type(fields) == 'tuple':
            combined = ''
            for f in fields:
                combined += str(f) + ','
            fields = combined[0:-1] # remove last comma
        params = {'access_token': access_token, 'fields': fields}
        r = requests.get(config.fb_graph_url + node + '?', params=params)
    r = r.json()
    if 'error' in r:
        raise FacebookException('error in response from facebook:' + json.dumps(r['error']))
    return r

def fb_getter(node, fields, out):
    out = os.path.join(outdir, out)
    try:
        f = open(out, 'r')
        return json.loads(f.read())
    except IOError:
        data = fb_call(node, fields)
        with open(out, 'w') as out:
            out.write(json.dumps(data, indent=4, sort_keys=True))
        return data

def get_friends():
    data = fb_getter('me', 'friends', config.friends_list_filename)
    return data['friends']['data']

def process_collect_statuses(q, i):
    print i, 'start'
    while True:
        try:
            friend = q.get(True, timeout=5)
            print i, friend['name']
        except Empty:
            print i, 'exiting'
            return

        out = os.path.join(outdir, config.friend_statuses_filename(friend['id'], friend['name']))
        msgs = []
        page_url = None
        while True:
            r = fb_call(friend['id'], 'statuses', page_url)
            if 'data' in r:
                d = r
            elif 'statuses' in r and 'data' in r['statuses']:
                d = r['statuses']
            else:
                break

            for status in d['data']:
                if 'message' in status:
                    msgs.append(status['message'])

            if 'paging' not in r or 'next' not in d['paging']:
                break
            page_url = d['paging']['next']
        data = {'id': friend['id'], 'name': friend['name'], 'statuses': msgs}
        with open(out, 'w') as f:
            f.write(json.dumps(data, indent=4, sort_keys=True))

def collect_statuses():
    q = Queue()
    for f in get_friends():
        q.put(f)
    ps = []
    for i in range(0, config.n_processes):
        p = Process(target=process_collect_statuses, args=(q, i))
        ps.append(p)
        p.start()
    for p in ps:
        p.join()

def collect_info():
    for friend in get_friends():
        print friend['name'],
        fb_getter(friend['id'], config.info_fields, config.friend_info_filename(friend['id'], friend['name']))

def friend_statuses(friend_id, friend_name):
    with open(os.path.join(outdir, config.friend_statuses_filename(friend_id, friend_name)),'r') as fin:
        data = json.loads(fin.read())
        try:
            for status in data['statuses']:
                yield status
        except KeyError:
            pass


def get_FriendWordCounts(friend):
    out = os.path.join(outdir, config.friend_word_counts_filename(friend['id'], friend['name']))
    try:
        with open(out, 'r') as f:
            return FriendWordCounts(_dict=json.loads(f.read()))
    except IOError:
        word_counts = FriendWordCounts(friend['id'], friend['name'])
        word_counts.update(friend_statuses(friend['id'], friend['name']))
        word_counts.finalize()
        with open(out, 'w') as f:
            f.write(json.dumps(word_counts.__dict__, indent=4, sort_keys=True))
        return word_counts

def word_counts():
    # iterates over the word counts for all friends
    # for missing data it calculates word counts
    for friend in get_friends():
        yield get_FriendWordCounts(friend)

def collect_word_counts():
    for wc in word_counts():
        print wc.friend_id

def population_stats(population_name, friends=None):
    out = os.path.join(outdir, config.population_filename('everyone'))
    try:
        with open(out, 'r') as f:
            return Population(_dict=json.loads(f.read()))
    except IOError:
        if population_name == 'everyone':
            friends = get_friends()
        pop = Population(population_name)
        for friend in friends:
            pop.update(get_FriendWordCounts(friend))

        with open(os.path.join(outdir, config.population_filename('everyone')), 'w') as out:
            out.write(json.dumps(pop, cls=PopulationEncoder, indent=4, sort_keys=True))
        return pop

def find_interesting_words():
    pop = population_stats('everyone')
    for word, d in pop.word_counts():
        if d['stats'].n() > 1:
            s1 = word
            print s1, ' '*(20-len(s1)),
            s2 = str(d['stats'].n())
            print s2, ' '*(5-len(s2)),
            s3 = "%.5f" % d['stats'].avg()
            print s3, ' '*(7-len(s3)),
            s4 = "%.5f" % d['stats'].std_dev()
            print s4, ' '*(7-len(s4))

def gather():
    get_friends()
    collect_statuses()
    collect_info()

def analyze():
    collect_word_counts()
    population_stats('everyone')
    find_interesting_words()

