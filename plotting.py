import os
from datetime import timedelta


import flask
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.ticker import FuncFormatter as ff
import pandas as pd
import sqlite3

from codetimes import m2hm, dt2m, get_tz, get_activity, get_location
from models import get_user, add_plot, add_events, GHUser


def discrete_cmap(N: int, base_cmap=None):
    """Create an N-bin discrete colormap from the specified input map,
    from https://gist.github.com/jakevdp/91077b0cae40f8f8244a."""
    base = plt.cm.get_cmap(base_cmap)
    color_list = base(np.linspace(0, 1, N))
    cmap_name = base.name + str(N)
    return base.from_list(cmap_name, color_list, N)


def plot_activity(username: str):
    """Plot activity and add user to database."""
    username = username.lower()
    timezone = ''
    timestamps = None

    user = get_user(username)
    # TODO: Get latest timestamp for updating old entries
    # TODO: Reorganize flow
    if user and user.plot_filename:
        return user.plot_filename
    elif user and user.events:
        # Plot activity
        pass
    elif user and user.timezone:
        # Get activity
        timestamps = get_activity(username)
        if timezone:
            timestamps = timestamps.dt.tz_convert(timezone)
        add_events(username, timestamps)
    elif user and user.location:
        # Get activity and timezone
        location = user.location
        timezone = get_tz(location)
        if timezone:
            timestamps = timestamps.dt.tz_convert(timezone)
        user.timezone = timezone
        add_events(username, timestamps)
    else:
        # Get everything
        location = get_location(username)
        if location:
            user.location = str(location)
            timezone = get_tz(location)
            user.timezone = timezone
        timestamps = get_activity(username)
        if timezone:
            timestamps = timestamps.dt.tz_convert(timezone)
        add_events(username, timestamps)

    events = user.events or get_activity(username)
    timestamps = pd.Series([pd.to_datetime(x.timestamp) for x in events])
    # url_suffix=''
    # if 'GITHUB_CLIENT_ID' in os.environ and 'GITHUB_CLIENT_SECRET' in os.environ:
    #     url_suffix = f"?client_id=${os.environ.get('GITHUB_CLIENT_ID')}&client_secret=${os.environ.get('GITHUB_CLIENT_SECRET')}"
    return plot_timestamps(timestamps, user = user, timezone=timezone)

def plot_timestamps(timestamps:pd.Series, user:GHUser, timezone=None):
    # color points distant from midday (1pm)
    dist_from_13h = abs(timestamps.dt.hour - 13)

    times = [dt2m(x) for x in timestamps]
    times = [x + 1440 if x < 240 else x for x in times]  # Looping

    dates = [x.date() for x in timestamps.dt.to_pydatetime()]

    fig, ax = plt.subplots(figsize=(8, 6))

    ax.set_xlim(dates[0] - timedelta(days=1), dates[-1] + timedelta(days=1))
    ax.set_ylim(240, 1440 + 240)  # 4am
    ax.set_ylabel(timezone or 'UTC' + f' ({user.location})')
    ax.yaxis.set_major_locator(ticker.MultipleLocator(60))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(15))
    ax.yaxis.set_major_formatter(ff(m2hm))
    ax.yaxis.grid(color='r', linestyle=':', linewidth=0.2)
    ax.set_title(user.username)

    ax.scatter(dates, times, c=dist_from_13h, cmap=discrete_cmap(24, 'autumn_r'))
    plt.gcf().autofmt_xdate()

    plot_filename = create_plot_filename(user.username)
    fig.savefig(to_local_path(plot_filename))
    add_plot(user, plot_filename)
    return plot_filename


def create_plot_filename(username: str):
    # TODO: Update to something reasonable
    return f'{username}_test.png'

def to_local_path(filename: str):
    if not flask.has_app_context(): # Debugging only
        return filename
    return os.path.join(flask.current_app.config['UPLOAD_FOLDER'], filename)


def get_plot(username: str):
    """Get plot filename from username."""
    username = username.lower()

    # Check if already in database
    user = get_user(username)
    if user.plot_filename:
        return user.plot_filename
    else:
        plot_filename = plot_activity(username)
        # local_path = to_local_path(plot_filename)
    return plot_filename

if __name__ == '__main__':
    # timestamps = pd.date_range(start='1/1/2019', periods=5, freq='20t')
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    results = c.execute('Select * from event where event.username_id = 1').fetchall()
    timestamps = pd.to_datetime([x[1] for x in results]).to_series()
    user = GHUser.query.filter_by(id=1).first()
    plot_timestamps(timestamps, user)
    plt.show()

    
