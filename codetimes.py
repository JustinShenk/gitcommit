#!/usr/bin/env python3
# coding: utf-8
import sys
import logging
import requests

import github
from geopy.exc import GeocoderTimedOut
import matplotlib.pyplot as plt
import pandas as pd
from pandas.plotting import register_matplotlib_converters

from api import gh, geo
from models import GHUser, Cache, add_events

register_matplotlib_converters()

MAX_PAGES = 10  # Github limit is 30 events x 10 pages


def localize(datetime, tz):
    return tz.localize(datetime)


def dt2m(dt):
    return (dt.hour * 60) + dt.minute


def m2hm(x, i):
    h = int(x / 60) % 24
    m = int(x % 60)
    return '%(h)02d:%(m)02d' % {'h': h, 'm': m}


def get_tz(location):
    cache = Cache()
    if location is None:
        return None
    timezone = cache.timezone_cached(location)
    if timezone:
        return timezone
    try:
        place, (lat, lng) = geo.geocode(location, timeout=10)
    except GeocoderTimedOut as e:
        print("Error: geocode failed on input %s with message %s" % (location, e.message))
        return None
    tz = geo.timezone((lat, lng))
    timezone = tz.zone
    cache.save_to_cache(location, timezone)
    return timezone


def to_iso(events):
    timestamps = []
    if events:
        timestamps = [x.timestamp.isoformat() for x in events]    
    return timestamps
    

def get_user_activity(username, method='api'):
    """Returns formatted timestamps for GitHub user converted to timezone."""
    user = GHUser.query.filter_by(username=username).first()
    timezone = user.timezone
    timestamps = to_iso(user.events)

    if not timestamps and method == 'scrape':
        events_url = f'https://api.github.com/users/{username}/events'
        timestamps = []
        for page in range(MAX_PAGES):
            events = requests.get(events_url + f"?page={page}")
            for event in events.json():
                timestamps.append(event['created_at'])
    elif not timestamps and method == 'api':
        gh_user = gh.get_user(username)
        events_pages = gh_user.get_events()
        # Get datetime
        events = [x.created_at for x in events_pages]
        add_events(user, events)
        timestamps = to_iso(user.events)

    if timestamps:
        # Format, reverse, and localize
        timestamps = pd.to_datetime(pd.Series(timestamps))[::-1]
        if timezone:
            timestamps = timestamps.dt.tz_localize('UTC')
            timestamps = timestamps.dt.tz_convert(timezone)
    return timestamps


def get_location(username: str):
    location = None
    try:
        location = gh.get_user(username).location
    except github.GithubException.BadCredentialsException as e:
        logging.error(f'{e}')
    except Exception as e:
        logging.error(f"Error getting location: {e}")
    return location


def main(username: str):
    from plotting import plot_activity
    user = GHUser.query.filter_by(username=username.lower()).first()
    if not user:
        _ = plot_activity(username)
        plt.show()
    else:
        print(f"User events plotted at {user.plot_filename}")


if __name__ == '__main__':
    """Plot `username` passed via command line."""
    main(sys.argv[1])
