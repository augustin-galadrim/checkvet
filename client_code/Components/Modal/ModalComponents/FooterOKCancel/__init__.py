# In FooterOKCancel/__init__.py
from ._anvil_designer import FooterOKCancelTemplate
from anvil import *
import anvil.js


class FooterOKCancel(FooterOKCancelTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.add_event_handler("show", self.show_handler)

  def show_handler(self, **event_args):
    dom_node = anvil.js.get_dom_node(self)
    self.call_js("footerOKCancel_init", dom_node)

  def set_button_text(self, ok_text=None, cancel_text=None):
    """
    Public method to allow the parent to customize the button labels.
    This is a key part of making the component reusable.
    """
    if ok_text:
      self.call_js("setElementText", "footer-ok-btn", ok_text)
    if cancel_text:
      self.call_js("setElementText", "footer-cancel-btn", cancel_text)
