import requests
import json
import os
import re
from multiprocessing import Process, Queue
from Queue import Empty
import datetime
import string

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
            self.min = _dict['min']
            self.max = _dict['max']
        else:
            self.sums = [0, 0, 0, 0, 0]
            self.min = None
            self.max = None
    def update(self, x):
        prod = 1
        for i in range(len(self.sums)):
            self.sums[i] += prod
            prod *= x
        if self.min == None or x < self.min:
            self.min = x
        if self.max == None or x > self.max:
            self.max = x
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
    def row_display(self):
        column_1 = "%.3f" % self.min
        column_2 = "%.3f" % self.max
        avg = self.avg()
        if avg:
            column_3 = "%.3f" % avg
        else:
            column_3 = 'None'
        std_dev = self.std_dev()
        if std_dev:
            column_4 = "%.3f" % std_dev
        else:
            column_4 = 'None'
        row = ''
        row += column_1 + (' '*(7 - len(column_1)))
        row += column_2 + (' '*(7 - len(column_2)))
        row += column_3 + (' '*(7 - len(column_3)))
        row += column_4 + (' '*(7 - len(column_4)))
        return row


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
            for w in re.findall('[a-z0-9]+', ws.lower()):
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
        if not isinstance(obj, PopulationWordCounts):
            return super(PopulationWordCountsEncoder, self).default(obj)
        d = obj.__dict__
        for s in d['counts']:
            d['counts'][s]['stats'] = d['counts'][s]['stats'].__dict__
        return d

class FriendInfo(object):
    def __init__(self, o, friend_id=None, friend_name=None):
        if friend_id:
            self.id = friend_id
        if friend_name:
            self.name = friend_name
        for key in o:
            setattr(self, key, o[key])
    def get_name(self):
        return self.name
    def get_id(self):
        return self.id
    def clean_string(self, s):
        return list(set(re.findall('[a-z0-9]+', s.lower())).difference(config.common_words))
    def get_activities(self):
        d = getattr(self, 'activities', None)
        if not d or type(d) != dict or 'data' not in d:
            return []
        activities = []
        for a in d['data']:
            activities.append(a['name'].lower())
        return activities
    def get_bio(self):
        d = getattr(self, 'bio', None)
        if not d:
            return
        return self.clean_string(d)
    def get_birthday(self):
        d = getattr(self, 'birthday', None)
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
        if not year:
            return
        now = datetime.datetime.now()
        age = now.year - year
        if month > now.month or \
           month == now.month and day > now.day:
           age -= 1
        return age
    def get_books(self):
        d = getattr(self, 'books', None)
        if not d or 'data' not in d:
            return
        books = []
        for b in d['data']:
            books.append(' '.join(self.clean_string(b['name'])))
        return books
    def get_checkins(self):
        d = getattr(self, 'checkins', None)
        if not d or 'data' not in d:
            return
        checkins = []
        for c in d['data']:
            if 'place' in c and 'location' in c['place']:
                l = c['place']['location']
                place = ''
                if 'city' in l:
                    place += l['city']
                if 'state' in l:
                    place += ' ' + l['state']
                if 'country' in l:
                    place += ' ' + l['country']
                if place:
                    checkins.append(place)
        return checkins
    def get_currency(self):
        d = getattr(self, 'currency', None)
        if not d or 'user_currency' not in d:
            return
        return d['user_currency']
    def get_schools(self):
        d = getattr(self, 'education', None)
        if not d:
            return
        schools = []
        for s in d:
            if 'school' in s and 'name' in s['school']:
                schools.append(s['school']['name'])
        return schools
    def get_games(self):
        d = getattr(self, 'games', None)
        if not d or 'data' not in d:
            return
        games = []
        for g in d['data']:
            if 'name' in g:
                games.append(g['name'])
        return games
    def get_interests(self):
        d = getattr(self, 'interests', None)
        if not d or 'data' not in d:
            return
        interests = []
        for i in d['data']:
            if 'name' in i:
                interests.append(i['name'].lower())
        return interests
    compares = {
            'bio':.01,
            'birthday':1,
            'activities':1,
            'astrological_sign':.1,
            'age':1,
            'books':1,
            'checkins':1,
            'currency':1,
            'schools':1,
            'games':1,
            'interests':1
    }
    def similarity_with(self, other):
        sim = 0
        why = {}
        for attr, weight in FriendInfo.compares.iteritems():
            self_val =  getattr(self, 'get_'+attr, lambda x: None)()
            other_val = getattr(other, 'get_'+attr, lambda x: None)()
            if self_val and other_val:
                if type(self_val) == str or type(self_val) == tuple:
                    incr = weight * (self_val == other_val)
                    if incr:
                        sim += incr
                        why[attr] = self_val
                elif type(self_val) == list:
                    intersect = set(self_val).intersection(set(other_val))
                    incr = weight * len(intersect)
                    if incr:
                        sim += incr
                        why[attr] = list(intersect)
        return {'score':sim, 'why':why}


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

def get_FriendInfo(friend):
    out = os.path.join(outdir, config.friend_info_filename(friend['id'], friend['name']))
    try:
        with open(out, 'r') as f:
            o = json.loads(f.read())
    except IOError:
        o = fb_getter(friend['id'], config.info_fields, config.friend_info_filename(friend['id'], friend['name']))
    return FriendInfo(o, friend_id=friend['id'], friend_name=friend['name'])

def friend_word_counts():
    # iterates over the word counts for all friends
    # for missing data it calculates word counts
    for friend in get_friends():
        yield get_FriendWordCounts(friend)

def collect_friend_word_counts():
    for wc in friend_word_counts():
        print wc.friend_id

def population_word_counts(population_name, friends=None):
    out = os.path.join(outdir, config.population_word_counts_filename(population_name))
    try:
        with open(out, 'r') as f:
            return PopulationWordCounts(_dict=json.loads(f.read()))
    except IOError:
        if population_name == 'everyone':
            friends = get_friends()
        pop = PopulationWordCounts(population_name)
        for friend in friends:
            pop.update(get_FriendWordCounts(friend))

        with open(out, 'w') as f:
            f.write(json.dumps(pop, cls=PopulationWordCountsEncoder, indent=4, sort_keys=True))
        return pop

def similarity_stats(population_name=None, friends=None):
    def calc(friends):
        friends_info = [get_FriendInfo(f) for f in friends]
        similarity_stats = Stats()
        for i in range(len(friends)):
            f1 = friends_info[i]
            for j in range(i+1, len(friends)):
                f2 = friends_info[j]
                sim = f1.similarity_with(f2)
                similarity_stats.update(sim['score'])
        return similarity_stats

    # only write to a file if population_name == 'everyone'
    # because that is what takes a long time to calculate
    if population_name == 'everyone':
        out = os.path.join(outdir, config.population_similarity_stats_filename)
        try:
            with open(out, 'r') as f:
                return Stats(_dict=json.loads(f.read()))
        except IOError:
            stats = calc(get_friends())
            with open(out, 'w') as f:
                f.write(json.dumps(stats.__dict__, indent=4, sort_keys=True))
            return stats
    else:
        return calc(friends)

def find_interesting_words():
    friends = get_friends()
    pop_wcs = population_word_counts('everyone')
    pop_sim_stats = similarity_stats('everyone')
    friend_wcs = {wc.friend_id: wc for wc in friend_word_counts()}


    pop_cutoff = pop_sim_stats.avg() + 2*pop_sim_stats.std_dev()
    group_sims = Stats()
    for word, d in pop_wcs.word_counts():
        if d['stats'].n() > 1: # more than 1 person used this word
            cutoff = d['stats'].avg() + 2*d['stats'].std_dev()
            highs = []
            for friend_id in d['ids']: # of the people who used it a lot
                if friend_wcs[friend_id].counts[word] > cutoff:
                    highs.append(friend_id)
            if len(highs) > 1:         # how similar are they?
                sim_stats = similarity_stats(friends = [{'id':i, 'name':friend_wcs[i].friend_name} for i in highs])
                avg = sim_stats.avg()
                group_sims.update(avg)

    print 'EVERYONE'
    print pop_sim_stats.row_display()

    print '\nGROUPS'
    print group_sims.row_display()

def test_friend_info():
    #f1 = get_FriendInfo({'id':'1510738', 'name':'Christine Stawitz'})
    #f2 = get_FriendInfo({'id':'1237879', 'name':'Clark Leung'})
    #print f1.similarity_with(f2)
    friends = get_friends()
    friend_infos = [get_FriendInfo(friend) for friend in friends]
    n = 50
    for i in range(n):
        f1 = friend_infos[i]
        for j in range(i+1, n):
            f2 = friend_infos[j]
            sim = f1.similarity_with(f2)
            if sim['score']:
                print '\n'
                print f1.get_name(), '&', f2.get_name()
                print sim['score']
                print '\t\t', sim['why']


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

