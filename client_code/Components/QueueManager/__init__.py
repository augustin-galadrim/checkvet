from ._anvil_designer import QueueManagerTemplate
from anvil import *
import anvil.js
from ... import TranslationService as t
from ...AppEvents import events


class QueueManager(QueueManagerTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    events.subscribe("language_changed", self.update_ui_texts)
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Called when the component is shown. Initializes JS and re-attaches events."""
    self.update_ui_texts()
    disable_import_flag = getattr(self, "disable_import", False)
    anvil.js.call_js("qm_initialize", disable_import_flag)
    anvil.js.call_js("qm_reattach_events")

  def update_ui_texts(self, **event_args):
    """Sets all translatable text on the component."""
    self.call_js(
      "setElementText",
      "queueManager-span-viewQueue",
      t.t("queueManager_span_viewQueue"),
    )
    self.call_js(
      "setElementText",
      "queueManager-header-queueTitle",
      t.t("queueManager_header_queueTitle"),
    )
    self.call_js(
      "setElementText",
      "queueManager-button-closeQueue",
      t.t("queueManager_button_closeQueue"),
    )
    self.call_js(
      "setElementText",
      "queueManager-header-nameRecordingTitle",
      t.t("queueManager_header_nameRecordingTitle"),
    )
    self.call_js(
      "setElementText",
      "queueManager-paragraph-nameRecordingDesc",
      t.t("queueManager_paragraph_nameRecordingDesc"),
    )
    self.call_js(
      "setElementText",
      "queueManager-label-recordingTitle",
      t.t("queueManager_label_recordingTitle"),
    )
    self.call_js(
      "setPlaceholder",
      "queueManager-input-recordingTitle",
      t.t("queueManager_input_recordingTitle_placeholder"),
    )
    self.call_js(
      "setElementText",
      "queueManager-button-cancelTitle",
      t.t("queueManager_button_cancelTitle"),
    )
    self.call_js(
      "setElementText",
      "queueManager-button-confirmTitle",
      t.t("queueManager_button_confirmTitle"),
    )

  @anvil.js.report_exceptions
  def get_translations_for_renderer(self):
    """Provides a dictionary of translated texts needed by the JS queue renderer."""
    return {
      "no_recordings": t.t("queueManager_renderer_no_recordings"),
      "import_disabled": t.t("queueManager_renderer_import_disabled_tooltip"),
      "import_button": t.t("queueManager_renderer_import_button"),
      "status_label": t.t("queueManager_renderer_status_label"),
      "delete_button": t.t("queueManager_renderer_delete_button"),
      "delete_confirm": t.t("queueManager_renderer_delete_confirm"),
      "default_title_prefix": t.t("queueManager_renderer_default_title_prefix"),
    }

  # --- Public methods (Callable by the parent form) ---
  def add_to_queue(self, audio_proxy, title):
    """Tells JS to add the provided audio proxy and title to the queue."""
    anvil.js.call_js("qm_addToQueue", audio_proxy, title)

  def open_title_modal(self, audio_proxy):
    """Stores the audio proxy and opens the naming modal."""
    self._current_proxy_to_save = audio_proxy
    self.call_js("qm_openTitleModal")

  def refresh_badge(self):
    """Public method to manually refresh the badge count from the parent."""
    anvil.js.call_js("qm_refreshBadge")

  def delete_item_from_queue(self, item_id):
    """Public method for parent to instruct component to delete an item."""
    anvil.js.call_js("qm_deleteItem", item_id)

  # --- Internal Relay Methods (Called from JavaScript) ---
  def handle_import_click(self, item_id, audio_blob, **event_args):
    """Relay from JS: raises the x_import_item event for the parent."""
    mime_type = audio_blob.type
    self.raise_event(
      "x_import_item", item_id=item_id, audio_blob=audio_blob, mime_type=mime_type
    )
    self.delete_item_from_queue(item_id=item_id)

  def handle_confirm_save(self, title, **event_args):
    """Relay from JS: Called when user confirms the title."""
    if hasattr(self, "_current_proxy_to_save") and self._current_proxy_to_save:
      final_title = (
        title.strip()
        or f"{self.get_translations_for_renderer()['default_title_prefix']} {anvil.js.window.Date().toLocaleString()}"
      )
      self.add_to_queue(self._current_proxy_to_save, final_title)
      self._current_proxy_to_save = None

  def handle_queue_updated(self, **event_args):
    """Relay from JS: raises the x_queue_updated event for the parent."""
    self.raise_event("x_queue_updated")
