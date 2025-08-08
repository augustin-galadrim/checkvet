from ._anvil_designer import TimeDisplayTemplate
from anvil import *


class TimeDisplay(TimeDisplayTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Add an event handler to run code when the form is shown
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """This method is called when the component is shown on the screen."""
    # Tell the JavaScript within the component's HTML to initialize itself.
    self.call_js("initTimeDisplay")
