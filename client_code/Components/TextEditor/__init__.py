from ._anvil_designer import TextEditorTemplate
from anvil import *
import anvil.js


class TextEditor(TextEditorTemplate):
  def __init__(self, **properties):
    # Private attributes to hold the state of properties
    self._html_content = ""
    self.init_components(**properties)
    self.add_event_handler("show", self.form_show)

  def get_content(self):
    """Returns the current HTML content from the editor."""
    return self.call_js("getEditorContent")

  @property
  def html_content(self):
    return self.get_content()

  @html_content.setter
  def html_content(self, value):
    self._html_content = value
    # Check if the component has been added to a container
    if getattr(self, "parent", None):
      self.call_js("setEditorContent", value or "")

  def _update_button_visibility(self, button_id, is_visible):
    if getattr(self, "parent", None):
      self.call_js("setElementVisibility", button_id, is_visible)

  def form_show(self, **event_args):
    """This method is called when the component is shown on the screen"""
    # Set initial content and visibility when the component is added to the page
    self.call_js("setEditorContent", self._html_content or "")
    self._update_button_visibility("styleButtons", self.show_style_buttons)
    self._update_button_visibility("alignButtons", self.show_align_buttons)
    self._update_button_visibility("insertImageBtn", self.show_image_button)
    self._update_button_visibility("copyBtn", self.show_copy_button)
