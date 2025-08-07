from ._anvil_designer import QueueManagerTemplate
from anvil import *
import anvil.js


class QueueManager(QueueManagerTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self._current_blob_to_save = None
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Called when the component is shown. Initializes JS."""
    disable_import_flag = getattr(self, "disable_import", False)
    anvil.js.call_js("qm_initialize", disable_import_flag)

  # --- Public methods (Callable by the parent form) ---

  def add_to_queue(self, audio_blob, title):
    """Public method for the parent form to add an item to the queue."""
    if audio_blob and title:
      anvil.js.call_js("qm_addToQueue", audio_blob, title)

  def open_title_modal(self, audio_blob):
    """Stores the blob and opens the naming modal."""
    self._current_blob_to_save = audio_blob
    # *** THIS IS THE FIX ***
    # Call the new helper function by its name
    self.call_js("qm_openTitleModal")

  def refresh_badge(self):
    """Public method to manually refresh the badge count from the parent."""
    anvil.js.call_js("qm_refreshBadge")

  # --- Internal Relay Methods (Called from JavaScript) ---

  def handle_import_click(self, item_id, audio_blob, **event_args):
    """Relay from JS: raises the x_import_item event for the parent."""
    anvil_media_blob = anvil.js.to_media(audio_blob)
    self.raise_event("x_import_item", item_id=item_id, audio_blob=anvil_media_blob)

  def handle_confirm_save(self, title, **event_args):
    """Relay from JS: Called when user confirms the title in the modal."""
    if self._current_blob_to_save:
      # Use a default title if the user provides an empty one
      final_title = (
        title if title else f"Recording from {anvil.js.window.Date().toLocaleString()}"
      )
      self.add_to_queue(self._current_blob_to_save, final_title)
      self._current_blob_to_save = None

  def handle_queue_updated(self, **event_args):
    """Relay from JS: raises the x_queue_updated event for the parent."""
    self.raise_event("x_queue_updated")
