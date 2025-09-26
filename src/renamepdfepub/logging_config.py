import logging
import sys


def configure_logging(level=logging.INFO, logfile='project.log'):
    logger = logging.getLogger()
    logger.setLevel(level)

    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        ch.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        logger.addHandler(ch)

    # add file handler if not exists
    if logfile and not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        fh = logging.FileHandler(logfile)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(fh)
