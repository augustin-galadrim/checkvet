from ._anvil_designer import TextEditorTemplate
from anvil import *
import anvil.js


class TextEditor(TextEditorTemplate):
  def __init__(self, **properties):
    # --- Component State ---
    self._html_content = ""
    self.undo_stack = []
    self.redo_stack = []

    self.init_components(**properties)
    self.add_event_handler("show", self.form_show)

  # --- Public Properties & Methods ---

  def get_content(self):
    """Returns the current HTML content from the editor."""
    return self.call_js("getEditorContent")

  @property
  def html_content(self):
    return self.get_content()

  @html_content.setter
  def html_content(self, value):
    """
    Sets the editor content and intelligently adds it as a new version.
    """
    self._html_content = value
    if getattr(self, "parent", None):
      # Set the content in the browser's editor
      self.call_js("setEditorContent", value or "")

      # --- MODIFIED LOGIC ---
      # Instead of resetting the history, we push this new state as a version.
      # This handles programmatic changes (like from a voice command) correctly.
      if not self.undo_stack or (value or "") != self.undo_stack[-1]:
        self.undo_stack.append(value or "")
        self.redo_stack = []  # Clear redo stack on new action
        print(
          f"TextEditor: Programmatic change created new version. Undo: {len(self.undo_stack)}"
        )

      self._update_undo_redo_buttons()

  def record_version(self):
    """Public method for parent forms to trigger a version snapshot."""
    self._push_new_version()

  # --- Form & Component Lifecycle ---

  def form_show(self, **event_args):
    """Called when the component is shown. Sets up UI and initial state."""
    # Set initial content and button visibility from properties
    self.call_js("setEditorContent", self._html_content or "")
    self._update_button_visibility("styleButtons", self.show_style_buttons)
    self._update_button_visibility("alignButtons", self.show_align_buttons)
    self._update_button_visibility("insertImageBtn", self.show_image_button)
    self._update_button_visibility("copyBtn", self.show_copy_button)
    self._update_button_visibility("undoRedoButtons", self.show_undo_redo_buttons)

    # Initialize the version stacks and attach the blur listener via JS
    self.undo_stack = [self._html_content or ""]
    self.redo_stack = []
    self._update_undo_redo_buttons()
    self.call_js("initializeEditor")

  # --- Internal Undo/Redo Logic ---

  def _push_new_version(self):
    current_content = self.get_content()
    if not self.undo_stack or current_content != self.undo_stack[-1]:
      self.undo_stack.append(current_content)
      self.redo_stack = []  # Clear redo stack on new action
      self._update_undo_redo_buttons()
      print(
        f"TextEditor: Pushed version. Undo: {len(self.undo_stack)}, Redo: {len(self.redo_stack)}"
      )

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
      self.call_js("setButtonEnabled", "undoBtn", len(self.undo_stack) > 1)
      self.call_js("setButtonEnabled", "redoBtn", len(self.redo_stack) > 0)

  def on_blur_handler(self, **event_args):
    """Handles the blur event from JS to save a version from manual typing."""
    self.record_version()
