from ._anvil_designer import ReportFooterTemplate
from anvil import *
import anvil.js
import anvil.server
from ... import TranslationService as t
from ...AppEvents import events


class ReportFooter(ReportFooterTemplate):
  def __init__(self, **properties):
    self.save_button_text = ""
    self.init_components(**properties)
    events.subscribe("language_changed", self.update_ui_texts)
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Called when the component is shown on the screen."""
    self.update_ui_texts()
    anvil.js.call_js("attachFooterEvents")

  def update_ui_texts(self, **event_args):
    """Sets all translatable text on the component."""
    self.call_js(
      "setElementText", "reportFooter-button-status", t.t("reportFooter_button_status")
    )
    self.call_js(
      "setElementText",
      "reportFooter-button-archive",
      t.t("reportFooter_button_archive"),
    )
    self.call_js(
      "setElementText", "reportFooter-button-share", t.t("reportFooter_button_share")
    )

  # --- Public Method ---
  def update_status_display(self, status_key):
    """Updates the text of the status button based on a selected status."""
    display_text = (
      t.t(status_key)
      if status_key and status_key != "not_specified"
      else t.t("reportFooter_button_status")
    )
    anvil.js.call_js("setFooterStatusText", display_text)

  # --- Internal Logic and Event Raising ---
  def status_button_click(self, **event_args):
    """
    Handles the status button click internally, gets options from the server,
    shows the dialog, and raises an event with the result.
    """
    status_options = anvil.server.call_s("get_status_options")

    # Translate the options for the dialog
    buttons = [(t.t(opt), opt) for opt in status_options if opt != "not_specified"]
    buttons.append((t.t("cancel"), None))

    choice = alert(t.t("reportFooter_status_dialog_title"), buttons=buttons)

    if choice:
      self.raise_event("x_status_clicked", status_key=choice)

  def save_button_click(self, **event_args):
    """Raises the event to tell the parent form to save."""
    self.raise_event("x_save_clicked")

  def share_button_click(self, **event_args):
    """Raises the event to tell the parent form to share."""
    self.raise_event("x_share_clicked")
