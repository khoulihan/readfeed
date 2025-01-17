import os
import math
from datetime import datetime
from urllib.parse import unquote
from flask import Flask
from flask import render_template, request, send_from_directory
from flask import abort, redirect, url_for, current_app
from readfeed.data import Article, ArticleStore

PAGE_SIZE = 10
DB_FILE = 'articles.db'


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, DB_FILE)
    )

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.get("/")
    def index():
        articles = []
        page = 1
        pages = 1
        error_text = None
        if 'page' in request.args:
            page = int(request.args['page'])
        if 'error_text' in request.args:
            error_text = unquote(request.args['error_text'])
        with ArticleStore(current_app.config['DATABASE']) as store:
            total_articles = store.get_processed_article_count()
            page, pages = _normalise_pages(page, pages, total_articles)
            articles = store.get_range(PAGE_SIZE*(page-1), PAGE_SIZE)
        return render_template(
            "index.html",
            articles=articles,
            pages=pages,
            page=page,
            error_text=error_text
        )
    
    @app.post("/")
    def index_post():
        articles = []
        queued = False
        page = 1
        pages = 1
        validation_error = ""
        if 'page' in request.args:
            page = int(request.args['page'])
        url = unquote(request.form['url'])
        validation_error = _validate_url(url)
        with ArticleStore(current_app.config['DATABASE']) as store:
            if not validation_error:
                queued = _queue_url(store, url)
            total_articles = store.get_processed_article_count()
            page, pages = _normalise_pages(page, pages, total_articles)
            articles = store.get_range(PAGE_SIZE*(page-1), PAGE_SIZE)
        # TODO: The logic here seems a bit unclear.
        if not validation_error and not queued:
            validation_error = "That article was submitted previously! If it is not in the list then it has not yet been processed."
        return render_template(
            "index.html",
            articles=articles,
            queue_attempted=(not validation_error),
            article_queued=queued,
            article_url=url,
            pages=pages,
            page=page,
            error_text=validation_error
        )
    
    @app.route("/remove")
    def remove():
        if not 'url' in request.args:
            abort(400)
        with ArticleStore(current_app.config['DATABASE']) as store:
            store.remove(unquote(request.args['url']))
        return redirect(url_for('index'))
    
    @app.get("/status")
    def status():
        if not 'url' in request.args:
            abort(400)
        article = None
        with ArticleStore(current_app.config['DATABASE']) as store:
            article = store.get_article(unquote(request.args['url']))
        if not article:
            abort(404)
        return {
            'processed': article.processed,
            'processing_failed': article.processing_failed,
            'attempts': article.attempts,
        }
    
    # This allows the development server to serve static files from the "feeds"
    # directory. These would hopefully be served by the web server in production.
    @app.get('/feeds/<path:filename>')
    def feeds_static(filename):
        return send_from_directory(app.root_path + '/feeds/', filename)
    
    return app


def _validate_url(url):
    if url == "" or url.isspace():
        return "No URL was provided!"
    return None


def _normalise_pages(page, pages, total_articles):
    pages = math.ceil(total_articles / PAGE_SIZE)
    if page > pages:
        page = pages
    if page < 1:
        page = 1
    if pages < 1:
        pages = 1
    return page, pages


def _queue_url(store, url):
    if not store.has_url(url):
        store.add({
            'url': url,
            'title': "",
            'subtitle': "",
            'summary': "",
            'author': "",
            'source': "",
            'date_submitted': datetime.utcnow(),
            'processed': False,
            'processing_failed': False,
            'attempts': 0
        })
        return True
    return False

