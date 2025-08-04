from ._anvil_designer import HeaderReturnTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class HeaderReturn(HeaderReturnTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    # Set the title from the component's properties when the form is shown
    self.call_js("setHeaderTitle", self.title)
    # Attach the JavaScript event listener for the return button
    self.call_js("attachReturnButtonListener")

  def return_button_click(self, **event_args):
    """Called from JavaScript when the return button is clicked."""
    if self.return_form:
      open_form(self.return_form)
    else:
      # As a fallback, go to the startup form if return_form is not set
      open_form("StartupForm")
