# In client_code/Components/ReportFooter/__init__.py
from ._anvil_designer import ReportFooterTemplate
from anvil import *
import anvil.js
import anvil.server


class ReportFooter(ReportFooterTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Called when the component is shown on the screen."""
    print("DEBUG: ReportFooter -> form_show: Attaching JS events.")
    anvil.js.call_js("attachFooterEvents")

  # --- Public Method ---
  def update_status_display(self, status_key):
    """Updates the text of the status button."""
    display_text = (
      status_key.replace("_", " ").title()
      if status_key and status_key != "not_specified"
      else "Status"
    )
    anvil.js.call_js("setFooterStatusText", display_text)

  # --- Internal Logic and Event Raising ---
  def status_button_click(self, **event_args):
    """
    Handles the status button click internally, gets options from the server,
    shows the dialog, and raises an event with the result.
    """
    status_options = anvil.server.call("get_status_options")

    buttons = [(opt.replace("_", " ").title(), opt) for opt in status_options]
    buttons.append(("Cancel", None))

    # Show the dialog
    choice = alert("Choose status:", buttons=buttons)

    # If the user made a choice (and didn't cancel), raise the event
    if choice:
      # MODIFIED: Changed event name to match the component's YAML definition
      self.raise_event("x_status_clicked", status_key=choice)

  def save_button_click(self, **event_args):
    """Raises the event to tell the parent form to save."""
    print("DEBUG: ReportFooter -> save_button_click: Python method called from JS.")
    self.raise_event("x_save_clicked")
    print("DEBUG: ReportFooter -> save_button_click: 'x-save-clicked' event raised.")

  def share_button_click(self, **event_args):
    """Raises the event to tell the parent form to share."""
    self.raise_event("x_share_clicked")
