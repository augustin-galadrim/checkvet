from ._anvil_designer import UserFeedbackTemplate
from anvil import *
import anvil.js

class UserFeedback(UserFeedbackTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.visible = False # The component starts off hidden

  def show(self, status="Processing..."):
    """Makes the component visible and sets the initial status text."""
    self.visible = True
    self.call_js("uf_setStatus", status)

  def hide(self):
    """Hides the component."""
    self.visible = False

  def set_status(self, new_status):
    """Updates the status text while the component is visible."""
    if self.visible:
      self.call_js("uf_setStatus", new_status)