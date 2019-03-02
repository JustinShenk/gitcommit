import datetime
import logging

import github
from sqlalchemy.orm import validates

from api import gh, geo
from app import db
from cache import Cache


class GHUser(db.Model):
    __tablename__ = 'ghuser'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    location = db.Column(db.String(80))
    timezone = db.Column(db.String(80))
    plot_filename = db.Column(db.String(80), unique=True)

    @validates('username')
    def validate_username(self, key, username):
        assert len(username) <= 39
        return username

    def __init__(self, username, location=None, timezone=None, events=None):
        self.username = username
        self.location = location
        self.timezone = timezone
        self.events = events

    def __repr__(self):
        return f'<User {self.username}>'


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, nullable=False)
    username = db.relationship('GHUser', backref=db.backref('user_events', lazy=True))
    username_id = db.Column(db.Integer, db.ForeignKey('ghuser.id'),
                            nullable=False)

    def __init__(self, timestamp, username):
        self.timestamp = timestamp
        self.username = username

    def __repr__(self):
        return f'<Event {self.timestamp}, username {self.username}>'


class Query(db.Model):
    # __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=False)
    timestamp = db.Column(db.String(80), default=datetime.datetime.now())

    def __init__(self, username, timestamp):
        self.username = username
        self.timestamp = timestamp

    def __repr__(self):
        return f'<Query {self.username}, {self.timestamp}>'


def add_query(username):
    """Someone queried 'username', log it."""
    db.session.add(Query(username=username, timestamp=datetime.datetime.now()))
    db.session.commit()


def add_user(username: str, **kwargs):
    """Add user to database"""
    user = GHUser(username, **kwargs)
    db.session.add(user)
    db.session.commit()
    return user


def query_user(username: str, attr='plot_filename'):
    """Main method - get plot filename from user. Returns None if note found."""
    add_query(username)
    user = get_user(username, create=True)
    if user is None:
        return None
    if attr == 'plot_filename':
        return user.plot_filename


def get_user(username: str, create:bool=False):
    """Get user database object."""
    user = GHUser.query.filter_by(username=username).first()
    if not user:
        try:
            gh_user = gh.get_user(username)
        except github.UnknownObjectException as e:
            # User not found on GitHub
            return None
        if create:
            events_pages = gh_user.get_events()
            events = [x.last_modified for x in events_pages]
            user = add_user(username, location=gh_user.location, events=events)
    return user


def create_user_from_gh(gh_user: github.NamedUser.NamedUser, events=[], timezone=None):
    """Add user to database from github API user object."""
    username = gh_user.login
    location = gh_user.location
    user = GHUser(username, location=location, timezone=timezone)
    for timestamp in events:
        db.session.add(Event(timestamp=timestamp, username=user))
    db.session.add(user)
    db.session.commit()
    logging.info(f"Added user {username} to database.")


def add_plot(user: GHUser, plot_filename):
    """Add plot to database."""
    user.plot_filename = plot_filename
    db.session.commit()
    print(f"Added {plot_filename} to database.")


cache = Cache('app.db')

if __name__ == "__main__":
    # Run this file directly to create the database tables.
    print("Creating database tables...")
    try:
        db.create_all()
    except Exception as e:
        print("Error creating database", e)
    print("Done!")
