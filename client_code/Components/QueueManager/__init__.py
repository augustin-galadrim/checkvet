# In client_code/Components/QueueManager/__init__.py

from ._anvil_designer import QueueManagerTemplate
from anvil import *
import anvil.js


class QueueManager(QueueManagerTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    # This state is no longer needed for the 'pull' mechanism
    # self._current_blob_to_save = None
    # self._current_title_to_save = None
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Called when the component is shown. Initializes JS."""
    disable_import_flag = getattr(self, "disable_import", False)
    anvil.js.call_js("qm_initialize", disable_import_flag)

  # --- Public methods (Callable by the parent form) ---

  # MODIFICATION: This method now directly calls the JS function with arguments
  def add_to_queue(self, audio_proxy, title):
    """
    Tells JS to add the provided audio proxy and title to the queue.
    """
    # Passes the audio_proxy straight to JavaScript
    anvil.js.call_js("qm_addToQueue", audio_proxy, title)

  def open_title_modal(self, audio_proxy):
    """Stores the audio proxy and opens the naming modal."""
    # This stores the proxy object temporarily
    self._current_proxy_to_save = audio_proxy
    self.call_js("qm_openTitleModal")

  def refresh_badge(self):
    """Public method to manually refresh the badge count from the parent."""
    anvil.js.call_js("qm_refreshBadge")

  def delete_item_from_queue(self, item_id):
    """
    Public method that parent forms can call to instruct the component
    to delete an item from its internal IndexedDB storage.
    """
    print(f"QueueManager Python: Instructed to delete item {item_id}.")
    anvil.js.call_js("qm_deleteItem", item_id)

  # --- Internal Relay Methods (Called from JavaScript) ---

  def handle_import_click(self, item_id, audio_blob, **event_args):
    """
    Relay from JS: raises the x_import_item event for the parent.
    'audio_blob' received here is a JS Blob Proxy from the component's own JS.
    We will pass this proxy directly to the parent form to maintain consistency.
    """
    self.raise_event("x_import_item", item_id=item_id, audio_blob=audio_blob)
    self.delete_item_from_queue(item_id=item_id)

  def handle_confirm_save(self, title, **event_args):
    """Relay from JS: Called when user confirms the title."""
    if hasattr(self, "_current_proxy_to_save") and self._current_proxy_to_save:
      final_title = (
        title.strip() or f"Recording from {anvil.js.window.Date().toLocaleString()}"
      )
      # Call add_to_queue, passing the stored proxy
      self.add_to_queue(self._current_proxy_to_save, final_title)
      self._current_proxy_to_save = None

  def handle_queue_updated(self, **event_args):
    """Relay from JS: raises the x_queue_updated event for the parent."""
    self.raise_event("x_queue_updated")
