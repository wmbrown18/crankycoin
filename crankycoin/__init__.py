from bottle import Bottle
import logging
import yaml

app = Bottle()

with open("config/config.yaml", 'r') as ymlfile:
    config = yaml.load(ymlfile)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

