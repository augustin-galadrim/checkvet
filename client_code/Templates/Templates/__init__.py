from ._anvil_designer import TemplatesTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import base64
from ...Cache import template_cache_manager
from ...LoggingClient import ClientLogger


class Templates(TemplatesTemplate):
  def __init__(self, **properties):
    # 2. Instantiate the logger in the __init__ method
    self.logger = ClientLogger(self.__class__.__name__)
    self.logger.info("Initializing...")

    self.init_components(**properties)
    self.logger.debug("Components initialized.")

    self.all_templates = []
    self.default_template_id = None

    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Now uses the cache and handles the default template ID."""
    self.logger.info("Form showing. Checking cache for templates.")

    template_data = template_cache_manager.get()
    if template_data is None:
      self.logger.warning("Cache miss. Fetching fresh templates from server.")
      template_data = anvil.server.call_s("read_templates")
      template_cache_manager.set(template_data)

    self.all_templates = template_data.get("templates", [])
    self.default_template_id = template_data.get("default_template_id")

    self.logger.info(
      f"Loading {len(self.all_templates)} templates. Default ID: {self.default_template_id}"
    )
    self.call_js("populateTemplates", self.all_templates, self.default_template_id)

  def refresh_session_relay(self, **event_args):
    """Relay method for refreshing the session when called from JS"""
    try:
      return anvil.server.call_s("check_and_refresh_session")
    except Exception as e:
      self.logger.error("Error in refresh_session_relay.", e)
      return False

  def open_template_editor(self, template_id=None, **event_args):
    """
    Opens the editor for a new or existing template.
    Invalidates the cache to ensure changes are reflected upon return.
    """
    self.logger.info("Opening template editor. Invalidating cache as a precaution.")
    template_cache_manager.invalidate()

    if template_id:
      self.logger.debug(f"Attempting to edit template with ID: {template_id}")
      found_template = next(
        (t for t in self.all_templates if t.get("id") == template_id), None
      )
      if not found_template:
        alert(f"Template with ID {template_id} not found.")
        self.logger.error(f"Template with ID {template_id} not found in local list.")
        return
      open_form("Templates.TemplateEditor", template=found_template)
    else:
      self.logger.debug("Opening editor for a new template.")
      open_form("Templates.TemplateEditor")

  def search_templates_client(self, query, **event_args):
    """Performs a client-side search on the loaded templates."""
    self.logger.debug(f"Client-side template search with query: '{query}'")
    if not query:
      self.call_js("populateTemplates", self.all_templates, self.default_template_id)
      return

    search_term = query.lower()
    results = [
      t for t in self.all_templates if search_term in t.get("name", "").lower()
    ]
    self.call_js("populateTemplates", results, self.default_template_id)

  def delete_template(self, template_id, **event_args):
    """Deletes a template after user confirmation."""
    if confirm("Are you sure you want to delete this template?"):
      self.logger.info(f"Attempting to delete template with ID: {template_id}")
      try:
        success = anvil.server.call_s("delete_template", template_id)
        if success:
          self.logger.info(
            f"Successfully deleted template ID: {template_id}. Invalidating cache."
          )
          template_cache_manager.invalidate()
          self.form_show()  # Refresh the view
        else:
          alert("Could not delete the template.")
          self.logger.error(
            f"Server returned failure for deleting template ID: {template_id}"
          )
      except Exception as e:
        self.logger.error(
          f"An error occurred while deleting template ID: {template_id}", e
        )
        alert(f"An error occurred: {e}")

  def toggle_template_display(self, template_id, new_display_state, **event_args):
    """Updates the 'display' property of the specified template."""
    self.logger.info(
      f"Toggling display state for template ID {template_id} to {new_display_state}."
    )
    try:
      success = anvil.server.call_s(
        "write_template", template_id=template_id, display=new_display_state
      )
      if success:
        self.logger.info(
          f"Successfully toggled display for template ID: {template_id}. Invalidating cache."
        )
        template_cache_manager.invalidate()
        self.form_show()
      else:
        alert("Failed to update the template's visibility.")
        self.logger.error(
          f"Server returned failure for toggling display on template ID: {template_id}"
        )
    except Exception as e:
      self.logger.error(
        f"An error occurred while toggling display for template ID: {template_id}", e
      )
      alert(f"An error occurred while updating template visibility: {e}")

  def set_default_template(self, template_id, **event_args):
    """Sets the user's default template."""
    self.logger.info(f"Setting template ID {template_id} as default for user.")
    try:
      success = anvil.server.call_s("set_default_template", template_id)
      if success:
        self.logger.info(
          f"Successfully set default template to ID: {template_id}. Invalidating cache."
        )
        template_cache_manager.invalidate()
        self.form_show()
      else:
        alert("Could not set the default template.")
        self.logger.error(
          f"Server returned failure for setting default template ID: {template_id}"
        )
    except Exception as e:
      self.logger.error(
        f"An error occurred while setting default template ID: {template_id}", e
      )
      alert(f"An error occurred: {e}")
