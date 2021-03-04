#!/usr/bin/env python
# coding: utf-8

# ## wallstreetbets Trend Data
#
# This notebook looks at recent posts from r/wallstreetbets to determine the hottest stocks right now. The onjective is to determine what stocks are generating buzz on the internet in hopes of anticipating future movement.
#
# First, it scrapes all stock tickers currently in use to create a list of symbols to search for.
#
# Next, it uses PRAW, a Python Wrapper for Reddit's API, to scrape the comments from the 25 hottest posts in r/wallstreetbets. It then parses these comments to find the most commonly referenced ticker symbols, excepting tickers that are also common english words (I, A, AN, etc.).
#
#
# Credit to Gilbert Tanner, writer of <a href = "https://towardsdatascience.com/scraping-reddit-data-1c0af3040768">this</a> article detailing how to use PRAW to scrape Reddit data.

# ### Imports

# In[1]:


import praw
import pandas as pd
import time
import requests
from bs4 import BeautifulSoup
from collections import Counter
from nltk.corpus import stopwords


# ### All Ticker Symbols
#
# Uses <a href = 'https://www.crummy.com/software/BeautifulSoup/bs4/doc/'>BeautifulSoup</a> to scrape a list of stock tickers from https://stockanalysis.com/stocks/. Leaves us with a list of 661 stock tickers and the corresponding name of each company. This is the universe of stocks we will look for in trends from Reddit data.

# In[19]:


URL = 'https://stockanalysis.com/stocks/'
page = requests.get(URL)
soup = BeautifulSoup(page.content, 'lxml')
tickers = soup.find_all('li')

ticker_list = []
name_list = []

for i in tickers[12:-18]:
    #print(i.text.split(" - "))
    ticker_list.append(i.text.split(" - ")[0])
    name_list.append(i.text.split(" - ")[1])

len(ticker_list), len(name_list)


# ### Reddit Data

# In[20]:


reddit = praw.Reddit(client_id='HG7dA6CRLvCD_w',
                     client_secret='rH5FP42F__la6jpUdt01BQvZU48WiA',
                     user_agent='WSB_Trends')


# In[21]:


posts = []
ml_subreddit = reddit.subreddit('wallstreetbets')
for post in ml_subreddit.hot(limit = 25):
    posts.append([post.title, post.score, post.id, post.subreddit, post.url, post.num_comments, post.selftext, post.created])
posts = pd.DataFrame(posts,columns=['title', 'score', 'id', 'subreddit', 'url', 'num_comments', 'body', 'created'])

#print(posts)


# In[22]:


## All comments within the last 6 hours from top 25 hottest posts in WSB
comment_count = 0
comments_last_hour = ""


for post_id in posts.id:
    submission = reddit.submission(id=post_id)
    submission.comments.replace_more(limit=0)
    for comment in submission.comments.list():
        '''Loops through all comments. comment.body is a string with each comment's contents.
        comment.created is the time the comment was created.'''
        comment_age = (comment.created - time.time())/3600
        if comment_age <=6:
            comments_last_hour += comment.body + " "
            comment_count+=1

print(comment_count)


# In[23]:


for character in' -.,\n':
    comments_last_hour = comments_last_hour.replace(character, " ")
#comments_last_hour = comments_last_hour.upper()

comments_last_hour = comments_last_hour.split()
last_hour_word_counts = Counter(comments_last_hour)


# In[24]:


stopwords_list = stopwords.words('english')

for ind in range(len(stopwords_list)):
    stopwords_list[ind] = stopwords_list[ind].upper()


# In[25]:


frequencies = []
for tick in ticker_list:
    if tick not in stopwords_list:
        frequencies.append(last_hour_word_counts[tick])
    else:
        frequencies.append(0)


# In[26]:


tickers_and_counts = pd.DataFrame([name_list, ticker_list, frequencies]).T
tickers_and_counts.columns = ['name','ticker','frequency']
print(tickers_and_counts.sort_values(by = ['frequency'], ascending = False)[0:15])
