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
    # The 'disable_import' property is automatically set on self by Anvil
    # from the properties panel of the parent form.
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
    self.call_js("document.getElementById('qm-titleModal').style.display = 'flex'")

  def refresh_badge(self):
    """Public method to manually refresh the badge count from the parent."""
    anvil.js.call_js("qm_refreshBadge")

  # --- Internal Relay Methods (Called from JavaScript) ---

  def handle_import_click(self, item_id, audio_blob, **event_args):
    """Relay from JS: raises the x_import_item event for the parent."""
    # Convert JS blob to Anvil Media object before raising the event
    anvil_media_blob = anvil.js.to_media(audio_blob)
    self.raise_event("x_import_item", item_id=item_id, audio_blob=anvil_media_blob)

  def handle_delete_click(self, item_id, **event_args):
    """Relay from JS: calls the server to delete and then raises an event."""
    # This now directly calls the JS function to delete from IndexedDB
    anvil.js.call_js("deleteFromQueue", item_id)
    # Then it updates the badge and notifies the parent.
    self.refresh_badge()
    self.raise_event("x_queue_updated")

  def handle_confirm_save(self, title, **event_args):
    """Relay from JS: Called when user confirms the title in the modal."""
    if self._current_blob_to_save:
      self.add_to_queue(self._current_blob_to_save, title)
      self._current_blob_to_save = None

  def handle_queue_updated(self, **event_args):
    """Relay from JS: raises the x_queue_updated event for the parent."""
    self.raise_event("x_queue_updated")
