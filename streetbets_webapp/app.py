from flask import Flask, request, render_template, session, redirect
import praw
import pandas as pd
import time
import requests
from bs4 import BeautifulSoup
from collections import Counter
from rq import Queue
from worker import conn
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)

def loadup_func():
    print("Task Starting.")
    wsb_ticker_list = []
    wsb_name_list = []
    URL = 'https://stockanalysis.com/stocks/'
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'lxml')
    wsb_tickers = soup.find_all('li')

    for i in wsb_tickers[12:-18]:
        #print(i.text.split(" - "))
        wsb_ticker_list.append(i.text.split(" - ")[0])
        wsb_name_list.append(i.text.split(" - ")[1])

    print(len(wsb_ticker_list), len(wsb_name_list))
    print("Task Complete.")
    return wsb_ticker_list

@app.route('/')
def welcome():
    #Landing page for site
    q = Queue(connection=conn)

    ticks = q.enqueue(loadup_func)
    print(ticks)
    print(names)

    return render_template('launch.html')


@app.route('/trends')
def trends():
    #Stock Tickers and Names
    #nasdaq = pd.read_csv('nasdaq_screener_1615222693757.csv')
    #wsb_ticker_list = []
    #wsb_name_list = []
    #for i in range(len(nasdaq)):
        #wsb_ticker_list.append(nasdaq.Symbol[i])
        #wsb_name_list.append(" ".join(nasdaq.Name[i].split()[0:-2]))
    #Crypto Tickers and Names
    URL = 'https://coinmarketcap.com/all/views/all/'
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'lxml')
    ssb_names = soup.find_all('td',
                            class_ = 'cmc-table__cell cmc-table__cell--sticky cmc-table__cell--sortable cmc-table__cell--left cmc-table__cell--sort-by__name')
    ssb_name_list = []

    for i in ssb_names:
        ssb_name_list.append(i.text.split('\">"')[0])

    ssb_tickers = soup.find_all('td',
                            class_ = 'cmc-table__cell cmc-table__cell--sortable cmc-table__cell--left cmc-table__cell--sort-by__symbol')
    ssb_ticker_list = []

    for i in ssb_tickers:
        ssb_ticker_list.append(i.text.split('\">"')[0])

    reddit = praw.Reddit(client_id='HG7dA6CRLvCD_w',
                     client_secret='rH5FP42F__la6jpUdt01BQvZU48WiA',
                     user_agent='WSB_Trends')


    stopword_df = pd.read_csv('stopwords.csv')
    stopwords_list = list(stopword_df.word)

    def comments_scraper(sub, comment_age, hot, case_sensitive = False):
        posts = []
        subreddit = reddit.subreddit(sub)
        for post in subreddit.hot(limit = hot):
            posts.append([post.title, post.score, post.id, post.subreddit, post.url, post.num_comments, post.selftext, post.created])
        posts = pd.DataFrame(posts,columns=['title', 'score', 'id', 'subreddit', 'url', 'num_comments', 'body', 'created'])

        comment_count = 0
        comments = ""

        for post_id in posts.id:
            submission = reddit.submission(id=post_id)
            submission.comments.replace_more(limit=0)
            for comment in submission.comments.list():
                '''Loops through all comments. comment.body is a string with each comment's contents.
                comment.created is the time the comment was created.'''
                comment_age = (comment.created - time.time())/3600
                if comment_age <=comment_age:
                    comments += comment.body + " "
                    comment_count+=1
        if case_sensitive == False:
            comments = comments.upper()

        for character in'$ -.,\n!<>':
            comments = comments.replace(character, " ")

        comments = comments.split()
        comments_counter = Counter(comments)
        return(comments_counter)
    def wsb_leaderboard(n, hours, hot):
        wsb_comments = comments_scraper('wallstreetbets', hours, hot, case_sensitive = True)

        frequencies = []
        for tick in wsb_ticker_list:
            if tick not in stopwords_list:
                frequencies.append(wsb_comments[tick])
            else:
                frequencies.append(0)

        wsb_tickers_and_counts = pd.DataFrame([wsb_name_list, wsb_ticker_list, frequencies]).T
        wsb_tickers_and_counts.columns = ['Name','Ticker','Mentions']
        wsb_tickers_and_counts = wsb_tickers_and_counts.sort_values(by = ['Mentions'], ascending = False)[0:n]
        wsb_tickers_and_counts.index = range(1,n+1)
        return wsb_tickers_and_counts
    def ssb_leaderboard(n, hours, hot):
        ssb_comments = comments_scraper('satoshistreetbets', hours, hot, case_sensitive = True)

        frequencies = []

        for coin in range(len(ssb_name_list)):
            freq = 0
            #print(name_list[coin], ticker_list[coin])
            if ssb_name_list[coin] not in stopwords_list:
                freq+=ssb_comments[ssb_name_list[coin]]
            else:
                freq+=0
            if ssb_ticker_list[coin] not in stopwords_list:
                freq+=ssb_comments[ssb_ticker_list[coin]]
            else:
                freq+=0

            frequencies.append(freq)

        ssb_tickers_and_counts = pd.DataFrame([ssb_name_list, ssb_ticker_list, frequencies]).T
        ssb_tickers_and_counts.columns = ['Name','Ticker','Mentions']
        ssb_tickers_and_counts = ssb_tickers_and_counts.sort_values(by = ['Mentions'], ascending = False)[0:n]
        ssb_tickers_and_counts.index = range(1,n+1)
        return ssb_tickers_and_counts


    wsb = wsb_leaderboard(10,6,10)
    ssb = ssb_leaderboard(10,6,10)

    return render_template('template.html',  tables=[wsb.to_html(classes='data'), ssb.to_html(classes='data')],
    titles=["WallStreetBets", "SatoshiStreetBets"])

@socketio.on('long-running-event')
def handle_my_custom_event():

    emit('processing-finished', json.dumps({'data': 'finished processing!'}))

if __name__ == '__main__':
    socketio.run(app)
