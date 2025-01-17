from datetime import datetime
from urllib.parse import urlparse
import click
import requests
from bs4 import BeautifulSoup
from jinja2 import Environment, PackageLoader, select_autoescape
from .data import Article, ArticleStore


DB_NAME = "articles.db"
FEED_SIZE = 20
ID_URL = "http://localhost:5000/"
FEED_URL = ID_URL + "feeds/atom.xml"


@click.group()
def _cli():
    pass


@_cli.command(help="Process all submitted articles outstanding")
@click.option('--force-regenerate', is_flag=True)
def process(force_regenerate):
    click.echo("Processing...")
    with ArticleStore(DB_NAME) as store:
        articles = store.get_unprocessed()
        any_processed = False
        for article in articles:
            click.echo(article)
            try:
                if not _process_article(article):
                    click.echo("Processing of article %s failed!" % article.url)
                    article.attempts = 1 if not article.attempts else article.attempts + 1
                else:
                    any_processed = True
            except requests.RequestException as ex:
                click.echo("Failed to retrieve article: %s" % article.url)
                click.echo(ex)
                article.attempts = 1 if not article.attempts else article.attempts + 1
            if not article.processed:
                if article.attempts > 3:
                    _process_failed_article(article)
                    any_processed = True
            store.update(article)


        if any_processed or force_regenerate:
            _regenerate_feed(store.get_range(0, FEED_SIZE))


@_cli.command(help="Reset all articles to be processed again. Temporary command for testing purposes!")
def reset():
    click.echo("Resetting...")
    with ArticleStore(DB_NAME) as store:
        articles = store.get_all()
        for article in articles:
            article.title = ""
            article.summary = ""
            article.processed = False
            article.processing_failed = False
            article.attempts = 0
            article.subtitle = ""
            article.author = ""
            article.source = ""
            store.update(article)


def _process_article(article):
    headers = {
        'user-agent': "readfeed/0.1.0",
        'accept': "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    response = requests.get(article.url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    article.source = _extract_source(soup, article.url)
    article.title = _extract_title(soup, article.url)
    article.summary = _extract_summary(soup)
    # This seems the same as the summary it turns out...
    article.subtitle = ""
    article.author = _extract_author(soup)
    article.processed = True
    click.echo(article)
    return True


def _process_failed_article(article):
    article.processed = True
    article.processing_failed = True
    parsed = urlparse(article.url)
    article.source = parsed.hostname
    article.summary = "A summary of this article could not be retrieved."
    article.author = ""
    article.subtitle = ""
    # TODO: Populate any other fields possible. Final path segment for the
    # title if there is one, domain name if there is no path?
    if parsed.path:
        article.title = parsed.path.split('/')[-1]
    if article.title == "":
        article.title = article.source


def _extract_source(soup, url):
    site_meta = soup.head.find("meta", property="og:site_name")
    if site_meta:
        return site_meta['content']
    parsed = urlparse(url)
    return parsed.hostname


def _extract_title(soup, url):
    title_meta = soup.head.find("meta", property="og:title")
    if title_meta:
        return title_meta['content']
    if soup.title:
        return soup.title.string
    return _extract_source(soup, url)


def _extract_summary(soup):
    if soup.head:
        summary_meta = soup.head.find("meta", property="og:description")
        if summary_meta:
            return summary_meta['content']

        summary_meta = soup.head.find("meta", attrs={'name': "description"})
        if summary_meta:
            return summary_meta['content']
    
    if soup.p:
        # Hoping this is the first paragraph of the content!
        return soup.p.string
    return "A summary of this article could not be found."


def _extract_author(soup):
    if soup.head:
        author_meta = soup.head.find("meta", property="author")
        if author_meta:
            return author_meta['content']
    return None


def _regenerate_feed(articles):
    feed = _render_template(
        "feed.xml",
        articles=articles,
        id=ID_URL,
        feed_url=FEED_URL,
        updated=datetime.utcnow()
    )
    with open("./feeds/atom.xml", 'w') as feedfile:
        feedfile.write(feed)


def _render_template(name, **kwargs):
    env = Environment(
        loader=PackageLoader("readfeed"),
        autoescape=select_autoescape()
    )
    template = env.get_template(name)
    return template.render(**kwargs)


def main():
    _cli()
