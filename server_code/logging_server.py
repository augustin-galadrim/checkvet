import logging


def get_logger(name):
  """
  Gets a logger instance.
  This version relies on Anvil's default logging configuration,
  which is more robust, especially for background tasks.
  """
  return logging.getLogger(name)
