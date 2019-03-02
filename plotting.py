from datetime import datetime, timedelta
import os

import flask
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.dates import date2num
from matplotlib.ticker import FuncFormatter as ff
import pandas as pd
import seaborn as sns

from codetimes import m2hm, dt2m, get_tz, get_user_activity, get_location
from models import get_user, add_plot, GHUser


def discrete_cmap(N: int, base_cmap=None):
    """Create an N-bin discrete colormap from the specified input map,
    from https://gist.github.com/jakevdp/91077b0cae40f8f8244a."""
    base = plt.cm.get_cmap(base_cmap)
    color_list = base(np.linspace(0, 1, N))
    cmap_name = base.name + str(N)
    return base.from_list(cmap_name, color_list, N)


def plot_activity(username: str, overwrite=False):
    """Generate plot and add user to database."""
    username = username.lower()
    user = get_user(username, create=True)
    if user is None:
        # User not found on GitHub
        return None
    if not overwrite and user.plot_filename:
        return user.plot_filename

    timezone = get_tz(user.location)
    user.timezone = timezone
    timestamps = get_user_activity(username)
    if timestamps is None:
        return None
    # TODO: Get latest timestamp for updating old entries
    # url_suffix=''
    # if 'GITHUB_CLIENT_ID' in os.environ and 'GITHUB_CLIENT_SECRET' in os.environ:
    #     url_suffix = f"?client_id=${os.environ.get('GITHUB_CLIENT_ID')}&client_secret=${os.environ.get('GITHUB_CLIENT_SECRET')}"
    plot_filename = plot_timestamps(timestamps, user=user, timezone=timezone)
    return plot_filename


def plot_timestamps(timestamps: pd.Series, user: GHUser, timezone=None):
    """Plot datetimes with matplotlib."""

    if timezone is not None and timestamps is not None:
        timestamps = timestamps.dt.tz_convert(timezone)

    # color points distant from midday (1pm)
    dist_from_13h = abs(timestamps.dt.hour - 13)

    times = [dt2m(x) for x in timestamps]
    times = [x + 1440 if x < 240 else x for x in times]  # Looping

    dates = [x.date() for x in timestamps.dt.to_pydatetime()]

    fig, ax = plt.subplots(figsize=(8, 6))

    ax.set_ylim(240, 1440 + 240)  # 4am
    ax.set_ylabel(timezone or 'UTC' + f' ({user.location})')
    ax.yaxis.set_major_locator(ticker.MultipleLocator(60))
    # ax.yaxis.set_minor_locator(ticker.MultipleLocator(15))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.get_xaxis().tick_bottom()
    ax.get_yaxis().tick_left()
    ax.yaxis.set_major_formatter(ff(m2hm))

    ax.yaxis.grid(color='k', linestyle='--', linewidth=0.5, alpha=.3)
    ax.set_title(user.username)
    ax.set_xlim([min(dates)-timedelta(days=1), max(dates) + timedelta(days=1)])

    # ax.scatter(dates, times, c=dist_from_13h, cmap=discrete_cmap(24, 'autumn_r'))
    # sns.lineplot(date2num(dates), times, ci=99, alpha =0.3)
    sns.scatterplot(date2num(dates), times, alpha=0.7)
    weekends = get_weekends(dates)
    for start, end in weekends:
        ax.axvspan(start - timedelta(hours=12), end + timedelta(hours=12), alpha=0.05, color='gray')

    plt.autoscale(True, axis='x', tight=True)
    plt.gcf().autofmt_xdate()

    plot_filename = create_plot_filename(user.username)
    fig.savefig(to_local_path(plot_filename))
    add_plot(user, plot_filename)
    return plot_filename

def get_weekends(dates):
    weekends = []
    date_range = np.arange(min(dates) - timedelta(days=1), max(dates) + timedelta(days=1), timedelta(days=1)).astype(datetime)
    weekdays = [x.weekday() for x in date_range]
    for ind, day in enumerate(weekdays):
        if ind is 0:
            if day is 6:
                weekend = (date_range[ind], date_range[ind])
                weekends.append(weekend)
        else:
            if day is 5:
                if ind < len(weekdays) - 1:
                    weekend = (date_range[ind], date_range[ind+1])
                else:
                    # Last day of plot
                    weekend = (date_range[ind], date_range[ind])
                weekends.append(weekend)
    return weekends


def to_weekday(date):
    return date.weekday()

def plot_mean_and_CI(mean, lb, ub, color_mean=None, color_shading=None):
    # plot the shaded range of the confidence intervals
    plt.fill_between(range(mean.shape[0]), ub, lb,
                     color=color_shading, alpha=.5)
    # plot the mean on top
    plt.plot(mean, color_mean)


def create_plot_filename(username: str):
    # TODO: Update to something reasonable
    return f'{username}_activity.png'


def to_local_path(filename: str):
    if not flask.has_app_context():  # Debugging only
        return filename
    return os.path.join(flask.current_app.config['UPLOAD_FOLDER'], filename)


def get_plot(username: str):
    """Main entrance to plotting - get plot filename from username."""
    username = username.lower()
    # Check if already in database
    user = get_user(username)
    if user is None: # not found on GitHub
        return None
    if user.plot_filename:
        return user.plot_filename
    else:
        plot_filename = plot_activity(username=username)
    return plot_filename


if __name__ == '__main__':
    # timestamps = pd.date_range(start='1/1/2019', periods=5, freq='20t')
    import sys
    username = sys.argv[1]
    from models import GHUser
    user = GHUser.query.filter_by(username=username).first()

    timestamps = pd.Series([x.timestamp for x in user.events])
    plot_timestamps(timestamps, user)
    plt.show()
