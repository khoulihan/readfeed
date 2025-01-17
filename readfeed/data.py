from dataclasses import dataclass
from datetime import datetime
import sqlite3


class ArticleStore:

    def __init__(self, db):
        self._db = db

    def __enter__(self):
        self._con = sqlite3.connect(self._db)
        self._cursor = self._con.cursor()
        self._create_schema()
        return self

    def __exit__(self, type, value, traceback):
        self._con.close()

    def _create_schema(self):
        c = self._cursor
        r = c.execute("SELECT name FROM sqlite_master WHERE name='article'")
        if r.fetchone() is None:
            self._cursor.execute("""
                CREATE TABLE article (
                    url,
                    title,
                    subtitle,
                    summary,
                    author,
                    source,
                    date_submitted,
                    processed,
                    attempts,
                    processing_failed
                )"""
            )

    def has_url(self, url):
        c = self._cursor
        r = c.execute("SELECT * FROM article WHERE url=?", (url,))
        return not r.fetchone() is None

    def get_processed_article_count(self):
        c = self._cursor
        r = c.execute("SELECT COUNT(*) FROM article WHERE processed = 1")
        return int(r.fetchone()[0])

    def add(self, article_data):
        c = self._cursor
        c.execute(
            """
            INSERT INTO article (
                url,
                title,
                subtitle,
                summary,
                author,
                source,
                date_submitted,
                processed,
                attempts,
                processing_failed
            ) VALUES (
                :url,
                :title,
                :subtitle,
                :summary,
                :author,
                :source,
                :date_submitted,
                :processed,
                :attempts,
                :processing_failed
            )
            """,
            article_data
        )
        self._con.commit()

    def update(self, article_data):
        c = self._cursor
        # Unclear why, but for the update I had to list out the article
        # properties in a tuple, where that was not required for the insert.
        c.execute(
            """
            UPDATE article
            SET title = :title,
            subtitle = :subtitle,
            summary = :summary,
            author = :author,
            source = :source,
            date_submitted = :date_submitted,
            processed = :processed,
            attempts = :attempts,
            processing_failed = :processing_failed
            WHERE url = :url
            """,
            (article_data.title,
             article_data.subtitle,
             article_data.summary,
             article_data.author,
             article_data.source,
             article_data.date_submitted,
             article_data.processed,
             article_data.attempts,
             article_data.processing_failed,
             article_data.url
             )
        )
        self._con.commit()

    def remove(self, url):
        c = self._cursor
        c.execute("DELETE FROM article WHERE url = ?", (url,))
        self._con.commit()

    def get_range(self, start, count):
        c = self._cursor
        r = c.execute("""
            SELECT
                url,
                title,
                subtitle,
                summary,
                author,
                source,
                date_submitted,
                processed,
                attempts,
                processing_failed
            FROM article
            WHERE processed = 1
            ORDER BY date_submitted DESC
            LIMIT ? OFFSET ?
        """, (count, start))
        articles = []
        for row in r:
            articles.append(
                Article(*row)
            )
        return articles

    def get_all(self):
        c = self._cursor
        r = c.execute("""
            SELECT
                url,
                title,
                subtitle,
                summary,
                author,
                source,
                date_submitted,
                processed,
                attempts,
                processing_failed
            FROM article
            ORDER BY date_submitted DESC
        """)
        articles = []
        for row in r:
            articles.append(
                Article(*row)
            )
        return articles

    def get_unprocessed(self):
        c = self._cursor
        r = c.execute("""
            SELECT
                url,
                title,
                subtitle,
                summary,
                author,
                source,
                date_submitted,
                processed,
                attempts,
                processing_failed
            FROM article
            WHERE processed = 0 
            ORDER BY date_submitted ASC
        """)
        articles = []
        for row in r:
            articles.append(
                Article(*row)
            )
        return articles

    def get_article(self, url):
        c = self._cursor
        r = c.execute("""
            SELECT
                url,
                title,
                subtitle,
                summary,
                author,
                source,
                date_submitted,
                processed,
                attempts,
                processing_failed
            FROM article
            WHERE url = ? 
            ORDER BY date_submitted ASC
        """, (url,))
        return Article(*r.fetchone())


@dataclass
class Article:
    url: str
    title: str
    subtitle: str
    summary: str
    author: str
    source: str
    date_submitted: datetime
    processed: bool
    attempts: int
    processing_failed: bool


