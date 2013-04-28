
fb_graph_url = 'https://graph.facebook.com/'

data_dir = 'friends'
friends_list_filename = 'friends.txt'
def base_friend_filename(frid, frname):
    return frid + '_' + frname.replace(' ', '') + '_'
def friend_id(filename):
    return filename.split('_')[0]
def friend_info_filename(frid, frname):
    return base_friend_filename(frid, frname) + 'info.txt'
def friend_statuses_filename(frid, frname):
    return base_friend_filename(frid, frname) + 'statuses.txt'
def friend_word_counts_filename(frid, frname):
    return base_friend_filename(frid, frname) + 'word_counts.txt'

def population_word_counts_filename(name):
    return 'population_' + name + 'word_counts.txt'
population_similarity_stats_filename = 'population_similarity_stats.txt'

n_processes = 4
info_fields = 'id,name,about,address,bio,age_range,birthday,currency,devices,education,favorite_athletes,favorite_teams,gender,hometown,inspirational_people,interested_in,languages,locale,location,meeting_for,political,quotes,relationship_status,religion,sports,work,significant_other,books,checkins,albums,events,activities,games,groups,interests,likes,locations,music,movies,notes,photos,picture,posts,television'

common_words = 'the be to of and a in that have i it for not on with he as you do at this but his by from they we say her she or an will my one all would there their what so up out if about who get which go me when make can like time no just him know take people into year your good some could them see other than then now look only come its over think also back after use two how our work first well way is t s much even new want because any these give day most us'.split(' ')
