import datetime


class ClientLogger:
  def __init__(self, context_name):
    """
    Initializes the logger with a context name, typically the form's class name.
    Example: self.logger = ClientLogger(self.__class__.__name__)
    """
    self.context = context_name

  def _get_timestamp(self):
    """
    Gets a formatted HH:MM:SS timestamp using the client-side datetime module.
    """
    try:
      # Get the current time from the browser's clock via Skulpt's datetime
      now = datetime.datetime.now()
      return now.strftime("%H:%M:%S")
    except Exception:
      # Fallback in case of any issues with the datetime implementation
      return "NO_TIMESTAMP"

  def _log(self, level, message):
    """Internal log function that now includes a timestamp."""
    timestamp = self._get_timestamp()
    print(f"[{timestamp}] [{level}] [CLIENT:{self.context}] {message}")

  def debug(self, message):
    self._log("DEBUG", message)

  def info(self, message):
    self._log("INFO", message)

  def warning(self, message):
    self._log("WARNING", message)

  def error(self, message, e=None):
    if e:
      self._log("ERROR", f"{message} - Exception: {e}")
    else:
      self._log("ERROR", message)
