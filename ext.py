import logging
import argparse
import datetime

from configparser import ConfigParser

from os import chdir

chdir('/home/emiliano/Desktop/mb_releases')

def now(format='%Y-%m-%d'):
    return datetime.datetime.now().strftime(format)

config = ConfigParser()
config.read('config.cfg')

argparser = argparse.ArgumentParser(description='Import artists from a file and get new releases')
argparser.add_argument('-f', '--file', 
                       help='File containing artists to import', 
                       required=False)
argparser.add_argument('-r', '--refresh', 
                       help='Refresh the releases', 
                       action='store_true')
argparser.add_argument('-v', '--verbose', 
                       help='Verbose output', 
                       action='store_true')
argparser.add_argument('-t', '--type', 
                       help='Output file format', 
                       choices=['ics', 'rss', 'all'])
argparser.add_argument('-n', '--notify',
                       help='Notify new releases to telegram',
                       action='store_true')
argparser.add_argument('-a', '--auto',
                       help='Auto mode for artists select, no user input',
                       action='store_true')
argparser.add_argument('-p', '--pick-artists',
                       help='Pick artists to refresh',
                       required=False)

args = argparser.parse_args()

level = logging.DEBUG if args.verbose else logging.INFO

logging.basicConfig(level=level)
    
logger = logging.getLogger(__name__)

if not args.type and not args.notify:
    argparser.error('No action requested, add -t or -n')