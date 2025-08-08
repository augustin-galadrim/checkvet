# In client_code/Components/QueueManager/__init__.py

from ._anvil_designer import QueueManagerTemplate
from anvil import *
import anvil.js


class QueueManager(QueueManagerTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self._current_blob_to_save = None
    # ADD THIS LINE to store the title alongside the blob
    self._current_title_to_save = None
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Called when the component is shown. Initializes JS."""
    disable_import_flag = getattr(self, "disable_import", False)
    anvil.js.call_js("qm_initialize", disable_import_flag)

  # --- Public methods (Callable by the parent form) ---

  # REVERT the previous change here. We will NOT use anvil.js.to_blob.
  def add_to_queue(self, audio_blob, title):
    """
    Stores the item to be queued and tells JS to start the process.
    """
    # Store the data on the Python side
    self._current_blob_to_save = audio_blob
    self._current_title_to_save = title

    # Trigger the JS function, which will then call back to get the data.
    anvil.js.call_js("qm_addToQueue")

  def open_title_modal(self, audio_blob):
    """Stores the blob and opens the naming modal."""
    self._current_blob_to_save = audio_blob
    self.call_js("qm_openTitleModal")

  def refresh_badge(self):
    """Public method to manually refresh the badge count from the parent."""
    anvil.js.call_js("qm_refreshBadge")

  # --- Internal Relay Methods (Called from JavaScript) ---

  def handle_import_click(self, item_id, audio_blob, **event_args):
    """Relay from JS: raises the x_import_item event for the parent."""
    anvil_media_blob = anvil.js.to_media(audio_blob)
    self.raise_event("x_import_item", item_id=item_id, audio_blob=anvil_media_blob)

  # UPDATE this method
  def handle_confirm_save(self, title, **event_args):
    """Relay from JS: Called when user confirms the title in the modal."""
    if self._current_blob_to_save:
      final_title = (
        title.strip()
        if title.strip()
        else f"Recording from {anvil.js.window.Date().toLocaleString()}"
      )

      # Call the new add_to_queue method, which now just stores the data
      self.add_to_queue(self._current_blob_to_save, final_title)

      self._current_blob_to_save = None  # Clear after starting the process

  # ADD THIS ENTIRE NEW METHOD
  def get_item_to_queue(self, **event_args):
    """
    Called FROM JavaScript to retrieve the blob and title.
    This avoids serialization issues by having JS pull the data.
    """
    if self._current_blob_to_save and self._current_title_to_save:
      return {"blob": self._current_blob_to_save, "title": self._current_title_to_save}
    return None

  def handle_queue_updated(self, **event_args):
    """Relay from JS: raises the x_queue_updated event for the parent."""
    self.raise_event("x_queue_updated")
