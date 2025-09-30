from ._anvil_designer import BaseModalTemplate
from anvil import *
import anvil.js
from .....LoggingClient import ClientLogger


class BaseModal(BaseModalTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.logger = ClientLogger(self.__class__.__name__)
    self.add_event_handler("show", self._show_handler)

  def _show_handler(self, **event_args):
    dom_node = anvil.js.get_dom_node(self)
    anvil.js.call_js("baseModal_init", dom_node)

  def open(self):
    self.logger.info("Opening modal.")
    self.call_js("showModal")  # Calls the instance-specific function

  def close(self):
    self.logger.info("Closing modal.")
    self.call_js("hideModal")  # Calls the instance-specific function
    self.raise_event("x_closed")
