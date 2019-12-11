#!/usr/bin/python

from TwitterSearch import *

try:
    tso = TwitterSearchOrder() # create a TwitterSearchOrder object
    tso.set_keywords(['massiveart']) # let's define all words we would like to have a look for
    #tso.set_language('de') # we want to see German tweets only
    tso.set_include_entities(False) # and don't give us all those entity information

    # it's about time to create a TwitterSearch object with our secret tokens
    ts = TwitterSearch(
        consumer_key = 'YDp8DXqYCxZJTotRaGYN4iLHs',
        consumer_secret = 'WEGzOBoy466F1AYB1HfRslVmRHXRdTaOs6imeVpvfSRvgqTTAP',
        access_token = '16464327-vbZOdScB1Qa5gJCkotEjxnbt029Fp7woO5FoLsTng',
        access_token_secret = '6fRD12iElqxF3kPaJjzw7M7jPG562wupfS5QxctVFamO0'
     )

     # this is where the fun actually starts :)
    for tweet in ts.search_tweets_iterable(tso):
        print( '@%s tweeted: %s' % ( tweet['user']['screen_name'], tweet['text'] ) )

except TwitterSearchException as e: # take care of all those ugly errors if there are some
    print(e)