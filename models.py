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
    username = db.Column(db.String(40), unique=True, nullable=False)
    location = db.Column(db.String(80))
    timezone = db.Column(db.String(80))
    plot_filename = db.Column(db.String(80), unique=True)

    @validates('username')
    def validate_username(self, key, username):
        assert len(username) <= 39
        return username

    def __repr__(self):
        return f'<User {self.username}>'


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False)
    ghuser_id = db.Column(db.Integer, db.ForeignKey('ghuser.id'),
                          nullable=False)
    ghuser = db.relationship('GHUser', backref=db.backref('events', lazy=True))

    def __repr__(self):
        return f'<Event {self.timestamp}, username {self.ghuser.username}>'


class Query(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=False)
    timestamp = db.Column(db.String(80), default=datetime.datetime.now())

    def __repr__(self):
        return f'<Query {self.username}, {self.timestamp}>'


def add_query(username):
    """Someone queried 'username', log it."""
    db.session.add(Query(username=username, timestamp=datetime.datetime.now()))
    db.session.commit()


def add_user(username: str, **kwargs):
    """Add user to database"""
    user = GHUser(username=username, **kwargs)
    db.session.add(user)
    db.session.commit()
    logging.info(f"Added user {username} to database with {len(user.events)} events.")
    return user


def query_user(username: str, attr='plot_filename'):
    """Main method - get plot filename from user. Returns None if note found."""
    add_query(username)
    user = get_user(username, create=True)
    if user is None:
        return None
    if attr == 'plot_filename':
        return user.plot_filename


def add_events(user: GHUser, events: list):
    """Add events (datetime) to database."""
    for e in events:
        db.session.add(Event(timestamp=e, ghuser=user))
    db.session.commit()


def get_user(username: str, create: bool = False):
    """Get user database object."""
    user = GHUser.query.filter_by(username=username).first()
    if not user:
        try:
            gh_user = gh.get_user(username)
        except github.UnknownObjectException as e:
            # User not found on GitHub
            return None
        if create:
            user = add_user(username, location=gh_user.location)
            events_pages = gh_user.get_events()
            # Get datetime
            events = [x.created_at for x in events_pages]
            add_events(user, events)
    return user


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
