import tornado.httpclient


def fetch_url(url):
    req = tornado.httpclient.HTTPRequest(
        url=url,
        method="GET",
        follow_redirects=True,
        allow_nonstandard_methods=True
    )

    client = tornado.httpclient.HTTPClient()
    response = client.fetch(req)

    return response.body