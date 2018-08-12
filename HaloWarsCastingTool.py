"""Halo Wars Casting Tool."""
import logging

import hwctool

# create logger with 'spam_application'
logger = logging.getLogger('hwctool')
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler(hwctool.settings.getLogFile(), 'w')
# create console handler
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter(
    '%(asctime)s, %(name)s, %(levelname)s: %(message)s',
    datefmt="%Y-%m-%d %H:%M:%S")
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)

if __name__ == '__main__':
    try:
        hwctool.main()
    finally:
        fh.close()
        logger.removeHandler(fh)
