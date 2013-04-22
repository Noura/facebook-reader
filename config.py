
fb_graph_url = 'https://graph.facebook.com/'

data_dir = 'friends'
friends_list_filename = 'friends.txt'
def friend_info_filename(frid, frname):
    return frid + '_' + frname.replace(' ', '') + '_info.txt'
def friend_statuses_filename(frid, frname):
    return frid + '_' + frname.replace(' ', '') + '_statuses.txt'
def friend_id(filename):
    return filename.split('_')[0]
