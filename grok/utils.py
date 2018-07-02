import requests
import json
import os

class Downloader:
    def __init__(self, url):
        self.url = url
