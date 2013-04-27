
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

def population_filename(name):
    return 'population_' + name + '.txt'

n_processes = 4
info_fields = 'id,name,about,address,bio,age_range,birthday,currency,devices,education,favorite_athletes,favorite_teams,gender,hometown,inspirational_people,interested_in,languages,locale,location,meeting_for,political,quotes,relationship_status,religion,sports,work,significant_other,books,checkins,albums,events,activities,games,groups,interests,likes,locations,music,movies,notes,photos,picture,posts,television'
