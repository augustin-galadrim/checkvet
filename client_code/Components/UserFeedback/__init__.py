from ._anvil_designer import UserFeedbackTemplate
from anvil import *
import anvil.js
from ... import TranslationService as t
from ...AppEvents import events


class UserFeedback(UserFeedbackTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.visible = False
    events.subscribe("language_changed", self.update_ui_texts)
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    self.update_ui_texts()

  def update_ui_texts(self, **event_args):
    """Sets the default translatable text on the component."""
    self.default_status = t.t("userFeedback_p_status_default")
    if self.visible:
      self.call_js("uf_setStatus", self.default_status)

  def show(self, status=None):
    """Makes the component visible and sets the status text."""
    self.visible = True
    # Use the provided status, or fall back to the translated default
    display_status = (
      status if status is not None else getattr(self, "default_status", "Processing...")
    )
    self.call_js("uf_setStatus", display_status)

  def hide(self):
    """Hides the component."""
    self.visible = False

  def set_status(self, new_status):
    """Updates the status text while the component is visible."""
    if self.visible:
      self.call_js("uf_setStatus", new_status)
