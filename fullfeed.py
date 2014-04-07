import tornado.ioloop
import tornado.web
import tornado.httpclient
import tornado.escape
import os
import binascii
import feedparser
import json
from bs4 import BeautifulSoup as Soup
import re
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.orm.exc import NoResultFound


extraction_rules = {
    'blog.fefe.de': 'ul li',
    'www.spiegel.de': 'ul li',
}

domain_re = re.compile('https?://([0-9a-zA-Z.-]+)/?.*')

engine = create_engine('sqlite:///:memory:', echo=True)

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    feeds = relationship("Feed", order_by="Feed.id")


class Feed(Base):
    __tablename__ = 'feeds'
    id = Column(Integer, primary_key=True)
    url = Column(String)
    rule = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship("User")


Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)


def extract_article(article, url, rule=None):
    if not rule:
        rule = extraction_rules[url]

    soup = Soup(article)
    ext = soup.select(rule)
    texts = map(lambda e: e.text, ext)
    res = ''.join(texts)

    return res


def fetch_articles(feed, rule):
    f = feedparser.parse(feed)

    jsonobj = []

    for e in f['entries']:
        req = tornado.httpclient.HTTPRequest(
            url=e['link'],
            method="GET",
            follow_redirects=False,
            allow_nonstandard_methods=True
        )

        client = tornado.httpclient.HTTPClient()
        try:
            response = client.fetch(req)
            url = domain_re.findall(e['link'])[0]
            extracted = extract_article(response.body, url, rule)
            jsonobj.append({
                'link': e['link'],
                'content': extracted,
            })
        except tornado.httpclient.HTTPError as e:
            if hasattr(e, 'response') and e.response:
                return None

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


def fetch_feed(url):
    req = tornado.httpclient.HTTPRequest(
        url=url,
        method="GET",
        follow_redirects=False,
        allow_nonstandard_methods=True
    )

    client = tornado.httpclient.HTTPClient()
    try:
        response = client.fetch(req)
        return response.body
    except tornado.httpclient.HTTPError as e:
        return e


class MainHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, user, url):
        session = Session()
        u = get_user(user, session)
        if len(url):
            try:
                session.query(Feed).filter_by(url=url).one()
            except NoResultFound:
                session.add(Feed(url=url, user=u))
                session.commit()
        feeds = session.query(Feed).filter_by(user_id=u.id)
        session.close()
        feed = fetch_feed(url)
        articles = fetch_articles(feed, None)
        self.render("index.html", user=u, feeds=map(lambda f: f.url, feeds), fetched_feed=articles)


class ProxyHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, url):
        self.set_status(200)
        self.set_header('Content-Type', 'application/json')
        rule = self.get_query_argument('rule', None)
        self.write(json.dumps(fetch_articles(fetch_feed(url), rule)))
        self.finish()


def main():
    app = tornado.web.Application(
        [
            (r"/u/([0-9a-zA-Z_]+)/?(.*)", MainHandler),
            (r"/p/(.*)", ProxyHandler),
        ],
        cookie_secret=binascii.hexlify(os.urandom(32)),
        xsrf_cookies=True,
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        static_path=os.path.join(os.path.dirname(__file__), 'static'),
    )
    app.listen(8080)
    tornado.ioloop.IOLoop.instance().start()


main()