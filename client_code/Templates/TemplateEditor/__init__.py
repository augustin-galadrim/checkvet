from ._anvil_designer import TemplateEditorTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users
import json

def safe_value(template, key, default_value):
  """Returns the value associated with 'key' in 'template', or 'default_value' if missing or None."""
  if template is None:
    return default_value
  val = template.get(key)
  return default_value if val is None else val

class TemplateEditor(TemplateEditorTemplate):
  def __init__(self, template=None, **properties):
    """
    This form is used to edit a template.

    It accepts a template dictionary via the parameter 'template'.

    The template dictionary should contain:
      - template_name: the name of the template
      - text_to_display: the content in rich format for display templates
    """
    anvil.users.login_with_form()
    print("Debug: Template received in TemplateEditor:", template)
    self.init_components(**properties)

    # Build a template dictionary if none is provided
    if template is None:
      template = {
        "template_name": "Untitled Template",
        "text_to_display": "",
        "prompt": "",
        "priority": 0
      }

    # Use safe_value to ensure each field is defined
    self.template = {
      "template_name": safe_value(template, "template_name", "Untitled Template"),
      "text_to_display": safe_value(template, "text_to_display", ""),
      "prompt": safe_value(template, "prompt", ""),
      "priority": safe_value(template, "priority", 0)
    }

    self.original_template_name = self.template.get("template_name")
    self.initial_content = self.template.get("text_to_display")  # Use text_to_display instead of human_readable

    # Attach the form show event to populate the editor later
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """When the form is displayed, ensure the editor shows the current template content."""
    if self.initial_content:
      self.editor_content = self.initial_content
    self.call_js("setTemplateNameValue", self.template.get("template_name"))

  def refresh_session_relay(self, **event_args):
    """Relay method for refreshing the session when called from JS"""
    try:
      return anvil.server.call("check_and_refresh_session")
    except Exception as e:
      print(f"[DEBUG] Error in refresh_session_relay: {str(e)}")
      return False

  # ----------------------------------------------------------
  # Editor properties
  # ----------------------------------------------------------
  @property
  def editor_content(self):
    try:
      return self.call_js("getEditorContent")
    except Exception as e:
      print("ERROR when retrieving editor content:", e)
      return None

  @editor_content.setter
  def editor_content(self, value):
    try:
      self.call_js("setEditorContent", value)
    except Exception as e:
      print("ERROR when setting editor content:", e)

  # ----------------------------------------------------------
  # Save template
  # ----------------------------------------------------------
  def save_template(self, name, content_json, images, **event_args):
    """
    Called when the user clicks "Save". Updates the existing template record
    by calling the server function write_template.
    """
    print("Debug: save_template() called from JS")
    try:
      parsed = json.loads(content_json)
      html_content = parsed.get("content", "")
      print(f"Debug: HTML content length: {len(html_content)}")
      print(f"Debug: Number of images: {len(images)}")

      # Use the existing write_template server function with updated parameters
      result = anvil.server.call(
        "write_template",
        name,                   # template_name
        None,                   # prompt (not modified in this editor)
        None,                   # human_readable (not modified in this editor)
        None,                   # priority (not modified in this editor)
        html_content,           # text_to_display
        True                    # display_template
      )

      if result:
        self.call_js("displayBanner", "Template saved successfully", "success")
        open_form("Templates.Templates")  # Go back to templates list
      else:
        alert("Failed to save template. Please try again.")
    except Exception as e:
      print("Exception in save_template:", e)
      alert("Error saving template: " + str(e))
    return True

  # ----------------------------------------------------------
  # Return button
  # ----------------------------------------------------------
  def return_clicked(self, **event_args):
    """Return to the Templates page without confirmation."""
    open_form("Templates.Templates")
