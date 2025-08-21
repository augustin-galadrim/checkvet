import logging

# A flag to ensure this setup runs only once per server session.
_is_configured = False

def get_logger(name):
  """
    Gets a logger instance. If this is the first time it's called,
    it will configure the root logger for the entire application.
    """
  global _is_configured

  if not _is_configured:
    # Get the root logger. All other loggers will inherit its settings.
    root_logger = logging.getLogger()

    # Set the minimum level to capture all logs from DEBUG upwards.
    root_logger.setLevel(logging.DEBUG)

    # Define our clear and informative log format.
    log_format = "[%(asctime)s] [%(levelname)s] [SERVER:%(name)s] %(message)s"
    formatter = logging.Formatter(log_format)

    # To prevent duplicate logs on app reloads, clear any existing handlers.
    if root_logger.hasHandlers():
      root_logger.handlers.clear()

      # Create a handler to send logs to the Anvil log service (standard output).
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    # Add the new handler to the root logger.
    root_logger.addHandler(handler)

    # Set the flag so this block never runs again.
    _is_configured = True

    logging.getLogger(__name__).info("Server-side logging configured automatically.")

    # Return the logger for the specific module that requested it.
  return logging.getLogger(name)