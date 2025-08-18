from ._anvil_designer import ModalTemplate
from anvil import *
import anvil.js


class Modal(ModalTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    anvil.js.call_js("attachModalEvents", self.get_id())

  def open(self):
    anvil.js.call_js(
      "showModalComponent", self.title, self.width, self.show_close_button
    )

  def close(self):
    anvil.js.call_js("hideModalComponent")


  def raise_close_event_from_js(self, **event_args):
    """Called by JavaScript when the overlay or close button is clicked."""
    self.raise_event("x-close")
