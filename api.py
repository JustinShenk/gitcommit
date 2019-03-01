import configparser

from github import Github
from geopy import geocoders

config = configparser.ConfigParser()
config.read('config.ini')

gh = Github(config['DEFAULT']['GITHUB_API_KEY'])
geo = geocoders.GoogleV3(api_key=config['DEFAULT']['GOOGLE_API_KEY'])
