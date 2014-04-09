from asyncore import loop
import tornado.ioloop
import tornado.web
import tornado.escape
import feedparser
import json
from bs4 import BeautifulSoup as Soup
from sqlalchemy.orm.exc import NoResultFound
from models import *
from utils import *
import asyncio
import time


loop = asyncio.get_event_loop()

cache_store = {}


def diff_time(t1, t2):
    return (time.mktime(t1) - time.mktime(t2)) / 60


def cache(key, value):
    cache_store[key] = {
        'value': value,
        'time': time.localtime()
    }


def extract_article(article, rule):
    if not rule:
        rule = 'body'
    soup = Soup(article)
    ext = soup.select(rule)
    texts = map(lambda e: ' '.join(map(lambda c: str(c), e.contents)), ext)
    res = ''.join(texts)

    return res


def fetch_articles(feed, rule):
    f = feedparser.parse(feed)

    jsonobj = []

    @asyncio.coroutine
    def process_article(url):
        response = fetch_url(url)

        extracted = extract_article(response, rule)
        jsonobj.append({
            'link': url,
            'content': extracted,
        })

    tasks = []
    for e in f['entries']:
        tasks.append(asyncio.Task(process_article(e['link'])))

    loop.run_until_complete(asyncio.wait(tasks))

    return jsonobj


def get_user(user, session):
    try:
        u = session.query(User).filter_by(name=user).one()
    except NoResultFound:
        u = User(name=user)
        session.add(u)
        session.commit()
        u = session.query(User).filter_by(name=user).one()

    return u


def insert_feed(user, url, session):
    if len(url):
        try:
            session.query(Feed).filter_by(url=url, user=user).one()
        except NoResultFound:
            session.add(Feed(url=url, user=user))
            session.commit()


def get_or_create_feed(user, url, session):
    insert_feed(user, url, session)

    return get_feed(user, url, session)


def get_feed(user, url, session):
    feed = session.query(Feed).filter_by(user=user, url=url).one()

    return feed


def get_feeds_by_user(user, session):
    feeds = session.query(Feed).filter_by(user=user)

    return feeds


class FeedHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, user, url):
        session = Session()
        u = get_user(user, session)
        feeds = get_feeds_by_user(u, session)

        if not url:
            url = feeds[0].url

        feed = get_or_create_feed(u, url, session)
        feedxml = fetch_url(url)

        if (not url in cache_store) or (diff_time(time.localtime(), cache_store[url]['time']) > 60):
            articles = fetch_articles(feedxml, feed.rule)
            cache(url, articles)
        else:
            articles = cache_store[url]['value']

        edit_mode = False
        if self.get_argument('edit', False):
            edit_mode = True

        self.render("feed.html",
                    user=u,
                    feeds=map(lambda f: f.url, feeds),
                    fetched_feed=list(articles),
                    feed_rule=feed.rule,
                    feed_url=url,
                    edit_mode=edit_mode)
        session.close()

    @tornado.web.asynchronous
    def post(self, user, url):
        session = Session()
        u = get_user(user, session)

        if self.get_argument('delete', False):
            feed = get_feed(u, self.get_argument('url'), session)
            session.delete(feed)
            session.commit()
            feeds = get_feeds_by_user(u, session)
            self.redirect('/u/' + u.name + '/' + feeds[0].url)
            session.close()
            return

        if self.get_argument('rule', False):
            feed = get_or_create_feed(u, self.get_argument('url'), session)
            feed.rule = self.get_argument('rule')
            session.commit()

        self.redirect('/u/' + u.name + '/' + self.get_argument('url'))
        session.close()


class ProxyHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, url):
        self.set_status(200)
        self.set_header('Content-Type', 'application/json')
        rule = self.get_query_argument('rule', None)
        self.write(json.dumps(fetch_articles(fetch_url(url), rule)))
        self.finish()


class MainHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        self.render('index.html')

    @tornado.web.asynchronous
    def post(self):
        self.redirect('/u/'+self.get_argument('user')+'/'+self.get_argument('url'))


def main():
    app = tornado.web.Application(
        [
            (r"/", MainHandler),
            (r"/u/([0-9a-zA-Z_]+)/?(.*)", FeedHandler),
            (r"/p/(.*)", ProxyHandler),
        ],
        #cookie_secret=binascii.hexlify(os.urandom(32)),
        #xsrf_cookies=True,
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        static_path=os.path.join(os.path.dirname(__file__), 'static'),
    )
    app.listen(8080)
    tornado.ioloop.IOLoop.instance().start()


main()