import logging
import logging.config
import argparse
import datetime

from configparser import ConfigParser

import logging.config
from os import chdir

'''
This module contains the shared code for the other modules
In it are initialized the logger and the configuration parser
The arguments parser is also defined here with the following options:
    -f, --file: File containing artists to import
    -r, --refresh: Refresh the releases
    -v, --verbose: Verbose output
    -t, --type: Output file format
    -n, --notify: Notify new releases to telegram
    -a, --auto: Auto mode for artists select, no user input
    -p, --pick-artists: Pick artists to refresh
It also moves the working directory to the folder where the script is located
And defines a shorthand for the datetime.now function
'''

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

if not args.type and not args.notify:
    argparser.error('No action requested, add -t or -n')

def setup_logger():
    format = '[%(asctime)s]'

    if args.verbose:
        level = logging.DEBUG
        format += '%(levelname)s:%(filename)s:'
    else:
        level = logging.INFO
    format += '%(message)s'

    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': format,
                #'datefmt': '%Y-%m-%d@%H:%M:%S',
                'datefmt': '%H:%M:%S'
            },
        },
        'handlers': {
            'default': {
                'level': level,
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            '': {
                'handlers': ['default'],
                'level': 'DEBUG',
                'propagate': True
            }
        }
    }

    logging.config.dictConfig(logging_config)