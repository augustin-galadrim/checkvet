class EventManager:
  def __init__(self):
    self._subscribers = {}

  def subscribe(self, event, callback):
    """Subscribe a callback function to an event."""
    if event not in self._subscribers:
      self._subscribers[event] = []
    self._subscribers[event].append(callback)
    print(f"EventManager: '{callback.__qualname__}' subscribed to '{event}'")

  def unsubscribe(self, event, callback):
    """Unsubscribe a callback function from an event."""
    if event in self._subscribers:
      try:
        self._subscribers[event].remove(callback)
      except ValueError:
        # Callback was not in the list, ignore.
        pass

  def publish(self, event, *args, **kwargs):
    """Publish an event, calling all subscribed callbacks."""
    print(f"EventManager: Publishing event '{event}'")
    if event in self._subscribers:
      for callback in self._subscribers[event]:
        try:
          callback(*args, **kwargs)
        except Exception as e:
          print(f"Error calling event handler for '{event}': {e}")

events = EventManager()
