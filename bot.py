import microdata
import urllib
import pprint
import json
import random
import requests
import sys
import tweepy
import tempfile
import os.path
import logging

logging.basicConfig()

foods = [food.strip() for food in open('foods.txt')]
starts = [start.strip() for start in open('start.txt')]
comments = [comment.strip() for comment in open('comments.txt')]
measurements = set(['cup', 'teaspoon', 'tsp', 'tablespoon', 'tbsp', 'ounce', 'pound', 'oz', 'lb'])
    
from secret import *

API_KEY = food2fork
API_URL = 'http://food2fork.com/api/search'

MAX_TRIES = 10

def find_random_recipe(tries):
    
    try:
        food = random.sample(foods, 1)[0].split(' ')[-1]
        r = requests.get(API_URL, params={'key': API_KEY,
                                          'q': food,}).json()
        recipe = random.sample(r['recipes'], 1)[0]
    except ValueError:
        tries += 1
        if tries >= MAX_TRIES:
            raise Exception("Too many retries for query")
        return find_random_recipe(tries)

    return (recipe, tries)
                                      

def get_comments(recipe=None):
    url = recipe['source_url']
    title = recipe['title']
    try:
        items = microdata.get_items(urllib.request.urlopen(url))
    except urllib.error.HTTPError:
        return None
    except AttributeError:
        return None
    
    for item in items:
        if len(item.get_all('ingredients')) > 0:
            try:
                ingredients = [' '.join(i.replace('\n', '').split()) for i in item.get_all('ingredients')]
            except TypeError:
                return None
            for ing in ingredients:
                found = False
                ings = ing.split(' ')
                for i, word in enumerate(ings):
                    for m in measurements:
                        if word.startswith(m):
                            ings = ings[i+1:]
                            found = True if ings else False
                if found:
                    final = ' '.join(ings)
                    mesg = u"{}: {} {} with {}. {} ".format(title,
                                                              random.sample(starts, 1)[0],
                                                              final,
                                                              random.sample(foods, 1)[0],
                                                              random.sample(comments, 1)[0],
                    )
                    if len(mesg) > (140 - 23 - 23):
                        # This message is too long
                        logging.warning("Message was too long; retrying")
                        return None
                    else:
                        return mesg + url

def loop(tries=0):
    (recipe, tries) = find_random_recipe(tries)
    result = get_comments(recipe)
    if not result:
        return loop(tries=tries + 1)
    else:
        return(recipe, result)

def tweet(recipe, message):
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.secure = True
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)
    
    if recipe['image_url']:
        # Get the image
        r = requests.get(recipe['image_url'], stream=True)
        filename = recipe['image_url'].split('/')[-1]
        tfile = os.path.join(tempfile.mkdtemp(), filename)
        with open(tfile, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024): 
                if chunk: 
                    f.write(chunk)
                    f.flush()
        api.update_with_media(tfile, status=message)
    else:
        api.update(status=message)                    
    
if __name__ == '__main__':

    (recipe, message) = loop()
    logging.info("Posting message {}".format(message))
    tweet(recipe, message)
