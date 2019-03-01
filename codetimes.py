#!/usr/bin/env python3
# coding: utf-8
import sys
import configparser
import logging
import requests

import github
from github import Github
from geopy import geocoders
from geopy.exc import GeocoderTimedOut
import matplotlib.pyplot as plt
import pandas as pd
from pandas.plotting import register_matplotlib_converters

from models import GHUser, Cache


register_matplotlib_converters()

config = configparser.ConfigParser()
config.read('config.ini')

MAX_PAGES = 10  # Github limit is 30 events x 10 pages
gh = Github(config['DEFAULT']['GITHUB_API_KEY'])
geo = geocoders.GoogleV3(api_key=config['DEFAULT']['GOOGLE_API_KEY'])


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


def get_gh_event_times(gh_user: github.NamedUser.NamedUser):
    timestamps = []
    events = gh_user.events
    if not events:
        print(f"No events found for {gh_user.login}")
        return None
    for event in events:
        datetime = datetime.strptime(event.last_modified, '%a, %d %b %Y %H:%M:%S GMT')
        timestamps.append(datetime.isoformat())
    timestamps = pd.Series(timestamps[::-1])
    logging.info(f"{len(timestamps)} events found for {gh_user.login} since {timestamps.iloc[0]}")
    return timestamps



def get_activity(username, timezone=None):
    events_url = f'https://api.github.com/users/{username}/events'

    timestamps = []
    for page in range(MAX_PAGES):
        events = requests.get(events_url + f"?page={page}")
        for event in events.json():
            timestamps.append(event['created_at'])

    timestamps = pd.to_datetime(pd.Series(timestamps))[::-1]
    logging.info(f"{len(timestamps)} events found for {username} since {timestamps.iloc[0]}")
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
