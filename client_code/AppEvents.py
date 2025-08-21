from .LoggingClient import ClientLogger


class EventManager:
  def __init__(self):
    self.logger = ClientLogger(self.__class__.__name__)
    self._subscribers = {}
    self.logger.info("EventManager initialized.")

  def subscribe(self, event, callback):
    """Subscribe a callback function to an event."""
    if event not in self._subscribers:
      self._subscribers[event] = []
    self._subscribers[event].append(callback)
    self.logger.info(
      f"Callback '{callback.__qualname__}' subscribed to event '{event}'."
    )

  def unsubscribe(self, event, callback):
    """Unsubscribe a callback function from an event."""
    if event in self._subscribers:
      try:
        self._subscribers[event].remove(callback)
        self.logger.debug(f"Unsubscribed '{callback.__qualname__}' from '{event}'.")
      except ValueError:
        pass

  def publish(self, event, *args, **kwargs):
    """Publish an event, calling all subscribed callbacks."""
    self.logger.info(f"Publishing event '{event}'.")
    if event in self._subscribers:
      for callback in self._subscribers[event]:
        try:
          callback(*args, **kwargs)
        except Exception as e:
          self.logger.error(f"Error calling event handler for '{event}'.", e)


events = EventManager()
