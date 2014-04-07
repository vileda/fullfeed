import re


extraction_rules = {
    'blog.fefe.de': 'ul li',
    'www.spiegel.de': 'ul li',
}

domain_re = re.compile('https?://([0-9a-zA-Z.-]+)/?.*')