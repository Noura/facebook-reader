facebook-reader
===============

I want to try to group my facebook friends into demographics algorithmically based on the words they used in their facebook status messages. I am most definitely NOT sharing any facebook data, but with this code you can play around with your facebook friends' data.

1. Make a folder called 'friends' in the repo to store your data, or change config.py to call it something else.
0. Go to https://developers.facebook.com/tools/explorer and get an API key with all the permissions so you can read your own data. Save it as a variable called access_token in a file called secret_constants.py
1. fab gather_data pre_analysis
2. fab analyze
