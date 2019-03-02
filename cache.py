import configparser

import geopy
import sqlite3


class Cache(object):
    def __init__(self, fn='app.db'):
        self.conn = conn = sqlite3.connect(fn)
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS '
                    'geo ( '
                    'id INTEGER PRIMARY KEY, '
                    'location STRING, '
                    'timezone STRING '
                    ')')
        conn.commit()

    def timezone_cached(self, location):
        cur = self.conn.cursor()
        cur.execute('SELECT timezone FROM geo WHERE location=?', (location,))
        res = cur.fetchone()
        if res is None: return False
        return res[0]

    def save_to_cache(self, timezone, location):
        cur = self.conn.cursor()
        cur.execute('INSERT INTO geo(location, timezone) VALUES(?, ?)',
                    (location, timezone))
        self.conn.commit()


if __name__ == '__main__':
    """Test caching of timezones for locations to reduce API calls."""
    cache = Cache('app.db')
    location = '1 Murphy St, Sunnyvale, CA'
    timezone = cache.timezone_cached(location)
    if timezone:
        print('was cached: {}'.format(timezone.zone))
    else:
        print('was not cached, looking up and caching now')
        config = configparser.ConfigParser()
        config.read('config.ini')
        geo = geopy.geocoders.GoogleV3(api_key=config['DEFAULT']['GOOGLE_API_KEY'])
        place, (lat, lng) = geo.geocode(location)
        tz = geo.timezone((lat, lng))
        print('found as: {}'.format(tz.zone))
        cache.save_to_cache(location, tz.zone)
        print('... and now cached.')
