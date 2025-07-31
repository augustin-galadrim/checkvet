from ._anvil_designer import TextEditorTemplate
from anvil import *
import anvil.js


class TextEditor(TextEditorTemplate):
  def __init__(self, **properties):
    # Private attributes to hold the state of properties
    self._html_content = ""
    self._show_toolbar = True
    self._show_style_buttons = True
    self._show_align_buttons = True
    self._show_image_button = True
    self._show_copy_button = True

    self.init_components(**properties)

    # --- Public Method ---

  def get_content(self):
    """Returns the current HTML content from the editor."""
    return self.call_js("getEditorContent")

    # --- html_content property ---

  @property
  def html_content(self):
    return self.get_content()

  @html_content.setter
  def html_content(self, value):
    self._html_content = value
    if self.is_in_page:
      self.call_js("setEditorContent", value or "")

    # --- Property setters for toolbar buttons ---

  def _update_button_visibility(self, button_id, is_visible):
    if self.is_in_page:
      self.call_js("setElementVisibility", button_id, is_visible)

  @property
  def show_toolbar(self):
    return self._show_toolbar

  @show_toolbar.setter
  def show_toolbar(self, value):
    self._show_toolbar = value
    self._update_button_visibility("toolbar", value)

  @property
  def show_style_buttons(self):
    return self._show_style_buttons

  @show_style_buttons.setter
  def show_style_buttons(self, value):
    self._show_style_buttons = value
    self._update_button_visibility("styleButtons", value)

  @property
  def show_align_buttons(self):
    return self._show_align_buttons

  @show_align_buttons.setter
  def show_align_buttons(self, value):
    self._show_align_buttons = value
    self._update_button_visibility("alignButtons", value)

  @property
  def show_image_button(self):
    return self._show_image_button

  @show_image_button.setter
  def show_image_button(self, value):
    self._show_image_button = value
    self._update_button_visibility("insertImageBtn", value)

  @property
  def show_copy_button(self):
    return self._show_copy_button

  @show_copy_button.setter
  def show_copy_button(self, value):
    self._show_copy_button = value
    self._update_button_visibility("copyBtn", value)

    # --- Event Handlers ---

  def form_show(self, **event_args):
    """This method is called when the component is shown on the screen"""
    # Set initial content and visibility when the component is added to the page
    self.call_js("setEditorContent", self._html_content or "")
    self.call_js("setElementVisibility", "toolbar", self._show_toolbar)
    self.call_js("setElementVisibility", "styleButtons", self._show_style_buttons)
    self.call_js("setElementVisibility", "alignButtons", self._show_align_buttons)
    self.call_js("setElementVisibility", "insertImageBtn", self._show_image_button)
    self.call_js("setElementVisibility", "copyBtn", self._show_copy_button)
