from ._anvil_designer import TextEditorTemplate
from anvil import *
import anvil.js
from ... import TranslationService as t
from ...AppEvents import events


class TextEditor(TextEditorTemplate):
  def __init__(self, **properties):
    self._html_content = ""
    self.undo_stack = []
    self.redo_stack = []

    self.init_components(**properties)
    events.subscribe("language_changed", self.update_ui_texts)
    self.add_event_handler("show", self.form_show)

  def update_ui_texts(self, **event_args):
    """Sets all translatable text on the component."""
    self.call_js(
      "setElementTitle", "textEditor-button-undo", t.t("textEditor_button_undo_tooltip")
    )
    self.call_js(
      "setElementTitle", "textEditor-button-redo", t.t("textEditor_button_redo_tooltip")
    )
    self.call_js(
      "setElementTitle", "textEditor-button-bold", t.t("textEditor_button_bold_tooltip")
    )
    self.call_js(
      "setElementTitle",
      "textEditor-button-italic",
      t.t("textEditor_button_italic_tooltip"),
    )
    self.call_js(
      "setElementTitle",
      "textEditor-button-underline",
      t.t("textEditor_button_underline_tooltip"),
    )
    self.call_js(
      "setElementTitle",
      "textEditor-button-alignLeft",
      t.t("textEditor_button_alignLeft_tooltip"),
    )
    self.call_js(
      "setElementTitle",
      "textEditor-button-alignCenter",
      t.t("textEditor_button_alignCenter_tooltip"),
    )
    self.call_js(
      "setElementTitle",
      "textEditor-button-alignRight",
      t.t("textEditor_button_alignRight_tooltip"),
    )
    self.call_js(
      "setElementText",
      "textEditor-button-insertImage",
      t.t("textEditor_button_insertImage"),
    )
    self.call_js(
      "setElementText", "textEditor-button-copy", t.t("textEditor_button_copy")
    )

  def get_content(self):
    """Returns the current HTML content from the editor."""
    return self.call_js("getEditorContent")

  @property
  def html_content(self):
    return self.get_content()

  @html_content.setter
  def html_content(self, value):
    self._html_content = value
    if getattr(self, "parent", None):
      self.call_js("setEditorContent", value or "")
      if not self.undo_stack or (value or "") != self.undo_stack[-1]:
        self.undo_stack.append(value or "")
        self.redo_stack = []
      self._update_undo_redo_buttons()

  def record_version(self):
    """Public method for parent forms to trigger a version snapshot."""
    self._push_new_version()

  def form_show(self, **event_args):
    """Called when the component is shown. Sets up UI and initial state."""
    self.update_ui_texts()
    self.call_js("setEditorContent", self._html_content or "")
    self._update_button_visibility("styleButtons", self.show_style_buttons)
    self._update_button_visibility("alignButtons", self.show_align_buttons)
    self._update_button_visibility(
      "textEditor-button-insertImage", self.show_image_button
    )
    self._update_button_visibility("textEditor-button-copy", self.show_copy_button)
    self._update_button_visibility("undoRedoButtons", self.show_undo_redo_buttons)

    self.undo_stack = [self._html_content or ""]
    self.redo_stack = []
    self._update_undo_redo_buttons()
    self.call_js("initializeEditor")

  def _push_new_version(self):
    current_content = self.get_content()
    if not self.undo_stack or current_content != self.undo_stack[-1]:
      self.undo_stack.append(current_content)
      self.redo_stack = []
      self._update_undo_redo_buttons()

  def undo_change(self, **event_args):
    """Handles the Undo button click from JS."""
    if len(self.undo_stack) > 1:
      current_state = self.undo_stack.pop()
      self.redo_stack.append(current_state)
      new_content = self.undo_stack[-1]
      self.call_js("setEditorContent", new_content)
      self._update_undo_redo_buttons()

  def redo_change(self, **event_args):
    """Handles the Redo button click from JS."""
    if self.redo_stack:
      state_to_restore = self.redo_stack.pop()
      self.undo_stack.append(state_to_restore)
      self.call_js("setEditorContent", state_to_restore)
      self._update_undo_redo_buttons()

  def _update_button_visibility(self, element_id, is_visible):
    if getattr(self, "parent", None):
      self.call_js("setElementVisibility", element_id, is_visible)

  def _update_undo_redo_buttons(self):
    """Enables/disables the undo/redo buttons."""
    if getattr(self, "parent", None) and self.show_undo_redo_buttons:
      self.call_js(
        "setButtonEnabled", "textEditor-button-undo", len(self.undo_stack) > 1
      )
      self.call_js(
        "setButtonEnabled", "textEditor-button-redo", len(self.redo_stack) > 0
      )

  def on_blur_handler(self, **event_args):
    """Handles the blur event from JS to save a version from manual typing."""
    self.record_version()

  def reset_content_and_history(self, new_html_content=""):
    """
    Définit un nouveau contenu pour l'éditeur et réinitialise complètement 
    l'historique d'annulation/rétablissement.
    Idéal pour charger un nouveau document ou un template.
    """
    self._html_content = new_html_content or ""
    self.undo_stack = [self._html_content]
    self.redo_stack = []
    if getattr(self, "parent", None):
      self.call_js("setEditorContent", self._html_content)
      self._update_undo_redo_buttons()