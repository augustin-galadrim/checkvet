from ._anvil_designer import RecordingWidgetTemplate
from anvil import *
import anvil.server
import anvil.js
from ... import TranslationService as t
from ...AppEvents import events


class RecordingWidget(RecordingWidgetTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.add_event_handler("recording_complete", self.on_recording_complete)
    events.subscribe("language_changed", self.update_ui_texts)
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    self.update_ui_texts()

  def update_ui_texts(self, **event_args):
    """Sets all translatable text on the component."""
    tooltip = t.t("recordingWidget_button_toggle_tooltip")
    self.call_js("setElementTitle", "recordingWidget-button-toggle", tooltip)

  # Methods called by JavaScript within this component
  def start_recording(self, **event_args):
    pass

  def stop_recording(self, **event_args):
    pass

  def show_error(self, error_message, **event_args):
    alert(error_message)

  def handle_js_recording_complete(self, blob, mime_type, **event_args):
    """Called by this component's own JavaScript when a recording is finished."""
    self.raise_event("recording_complete", audio_blob=blob, mime_type=mime_type)

  def on_recording_complete(self, audio_blob, mime_type, **event_args):
    """This is the event handler for our custom event."""
    pass
