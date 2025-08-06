from ._anvil_designer import TemplateEditorTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users
import json
import uuid


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
      - id: the unique identifier of the template
      - name: the name of the template
      - html: the content in rich format for display templates
    """
    anvil.users.login_with_form()
    print("Debug: Template received in TemplateEditor:", template)
    self.init_components(**properties)

    # Build a template dictionary if none is provided
    if template is None:
      template = {
        "id": None,
        "name": "Untitled Template",
        "html": "",
      }

    # Use safe_value to ensure each field is defined
    self.template = {
      "id": safe_value(template, "id", None),
      "name": safe_value(template, "name", "Untitled Template"),
      "html": safe_value(template, "html", ""),
    }
    self.initial_content = self.template.get("html")
    self.original_template_name = self.template.get("name")
    self.template_id = self.template.get("id")

    # Attach the form show event to populate the editor later
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """When the form is displayed, ensure the editor shows the current template content."""
    if self.initial_content:
      self.text_editor_1.html_content = self.initial_content
    self.call_js("setTemplateNameValue", self.template.get("name"))

  def refresh_session_relay(self, **event_args):
    """Relay method for refreshing the session when called from JS"""
    try:
      return anvil.server.call("check_and_refresh_session")
    except Exception as e:
      print(f"[DEBUG] Error in refresh_session_relay: {str(e)}")
      return False

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
      html_content = self.text_editor_1.get_content()
      print(f"Debug: HTML content length: {len(html_content)}")
      print(f"Debug: Number of images: {len(images)}")

      # Use the existing write_template server function with updated parameters
      result = anvil.server.call(
        "write_template",
        name=name,
        html=html_content,
        display=True,
        template_id=self.template_id,
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
