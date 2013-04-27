import requests
import json
import os
import re
from multiprocessing import Process, Queue
from Queue import Empty

import config
from secret_constants import access_token

outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), config.data_dir)

#######################
### DATA STRUCTURES ###
#######################

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

class PopulationWordCounts(FriendWordCounts):
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

# the Population's Stats objects get encoded this way
class PopulationWordCountsEncoder(json.JSONEncoder):
    def default(self, obj):
        if not isinstance(obj, Population):
            return super(PopulationWordCountsEncoder, self).default(obj)
        d = obj.__dict__
        for s in d['counts']:
            d['counts'][s]['stats'] = d['counts'][s]['stats'].__dict__
        return d

class FriendInfo(object):
    def __init__(self, o):
        for key in o:
            setattr(self, key, o[key])
    def get_activities(self):
        d = getattr(self, 'activities', None)
        if not d or type(d) != 'dict' or 'data' not in d:
            return []
        activities = []
        for a in d['data']:
            activities.append(a['name'])
        return activities
    def get_birthday(self):
        d = getattr(self, 'birthday', None)
        print d
        if not d:
            return
        b = d.split('/')
        month = int(b[0])
        day = int(b[1])
        if len(b) == 2:
            return month, day, None
        if len(b) == 3:
            year = int(b[2])
            return month, day, year
    def get_astrological_sign(self):
        birthday = self.get_birthday()
        if not birthday:
            return
        month, day, year = birthday
        if (month == 12 and day >= 22) or \
           (month == 1 and day <= 19):
            return 'Capricorn'
        if (month == 1 and day >= 20) or \
           (month == 2 and day <= 18):
            return 'Aquarius'
        if (month == 2 and day >= 19) or \
           (month == 3 and day <= 20):
            return 'Pisces'
        if (month == 3 and day >= 21) or \
           (month == 4 and day <= 19):
            return 'Aries'
        if (month == 4 and day >= 20) or \
           (month == 5 and day <= 20):
            return 'Taurus'
        if (month == 5 and day >= 21) or \
           (month == 6 and day <= 20):
            return 'Gemini'
        if (month == 6 and day >= 21) or \
           (month == 7 and day <= 22):
            return 'Cancer'
        if (month == 7 and day >= 23) or \
           (month == 8 and day <= 22):
            return 'Leo'
        if (month == 8 and day >= 23) or \
           (month == 9 and day <= 22):
            return 'Virgo'
        if (month == 9 and day >= 23) or \
           (month == 10 and day <= 22):
            return 'Libra'
        if (month == 10 and day >= 23) or \
           (month == 11 and day <= 21):
            return 'Scorpio'
        if (month == 11 and day >= 22) or \
           (month == 12 and day <= 21):
            return 'Sagittarius'
    def get_age(self):
        birthday = self.get_birthday()
        if not birthday:
            return
        month, day, year = birthday

def test_friend_info():
    friends = get_friends()
    for friend in friends[0:50]:
        with open(os.path.join(outdir, config.friend_info_filename(friend['id'], friend['name'])), 'r') as fin:
            o = json.loads(fin.read())
        info = FriendInfo(o)
        print info.get_birthday()
        print info.get_activities()
        print info.get_astrological_sign()
        

##################################
### TALK TO FACEBOOK GRAPH API ###
##################################

class FacebookException(Exception):
    pass

def fb_call(node, section='', params=None, page_url=None):
    if page_url:
        r = requests.get(page_url)
    else:
        params['access_token'] = access_token
        url = config.fb_graph_url + node
        if section:
            url += '/' + section
        url += '?'
        r = requests.get(url, params=params)
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
        data = fb_call(node, params={'fields':fields})
        with open(out, 'w') as out:
            out.write(json.dumps(data, indent=4, sort_keys=True))
        return data

###################
### GATHER DATA ###
###################

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
            r = fb_call(friend['id'], section='statuses', params={'limit':100}, page_url=page_url)
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

####################
### ANALYZE DATA ###
####################

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

def friend_word_counts():
    # iterates over the word counts for all friends
    # for missing data it calculates word counts
    for friend in get_friends():
        yield get_FriendWordCounts(friend)

def collect_friend_word_counts():
    for wc in friend_word_counts():
        print wc.friend_id

def population_word_counts(population_name, friends=None):
    out = os.path.join(outdir, config.population_filename(population_name))
    try:
        with open(out, 'r') as f:
            return PopulationWordCounts(_dict=json.loads(f.read()))
    except IOError:
        if population_name == 'everyone':
            friends = get_friends()
        pop = PopulationWordCounts(population_name)
        for friend in friends:
            pop.update(get_FriendWordCounts(friend))

        with open(os.path.join(outdir, config.population_filename('everyone')), 'w') as out:
            out.write(json.dumps(pop, cls=PopulationWordCountsEncoder, indent=4, sort_keys=True))
        return pop

def find_interesting_words():
    pop = population_word_counts('everyone')
    friend_word_counts = {}
    for wc in word_counts():
        friend_word_counts[wc.friend_id] = wc.counts
    for word, d in pop.word_counts():
        if d['stats'].n() > 10:
            cutoff = 1.5*d['stats'].std_dev()
            avg = d['stats'].avg()
            highs = []
            for friend_id in d['ids']:
                diff = friend_word_counts[friend_id][word] - avg
                if diff > cutoff:
                    highs.append(friend_id)
            s1 = word
            print s1, ' '*(20-len(s1)),
            s2 = str(d['stats'].n())
            print s2, ' '*(5-len(s2)),
            s3 = "%.5f" % d['stats'].avg()
            print s3, ' '*(7-len(s3)),
            s4 = "%.5f" % d['stats'].std_dev()
            print s4, ' '*(7-len(s4))
            std_dev = d['stats'].std_dev()
            print '\t highs:', highs




#################
### SHORTCUTS ###
#################

def gather():
    get_friends()
    collect_statuses()
    collect_info()

def analyze():
    collect_friend_word_counts()
    population_word_counts('everyone')
    find_interesting_words()

