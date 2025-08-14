from ._anvil_designer import TemplatesTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import base64
from ...Cache import template_cache_manager


class Templates(TemplatesTemplate):
  def __init__(self, **properties):
    print("Initialisation du formulaire Templates...")
    self.init_components(**properties)
    print("Composants du formulaire initialisés.")

    self.all_templates = []
    self.default_template_id = None

    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Now uses the cache and handles the default template ID."""
    print("Templates form showing. Checking cache.")

    template_data = template_cache_manager.get()
    if template_data is None:
      print("Fetching fresh templates from server.")
      template_data = anvil.server.call_s("read_templates")
      template_cache_manager.set(template_data)  # Store the whole dictionary

    self.all_templates = template_data.get("templates", [])
    self.default_template_id = template_data.get("default_template_id")

    print(f"Loading {len(self.all_templates)} templates. Default ID: {self.default_template_id}")
    self.call_js("populateTemplates", self.all_templates, self.default_template_id)

  def refresh_session_relay(self, **event_args):
    """Relay method for refreshing the session when called from JS"""
    try:
      return anvil.server.call("check_and_refresh_session")
    except Exception as e:
      print(f"[DEBUG] Error in refresh_session_relay: {str(e)}")
      return False

  def open_template_editor(self, template_id=None, **event_args):
    """
    *** FIX: Invalidates the cache before navigating to the editor. ***
    This ensures that if a change is made, the cache will be refreshed on return.
    """

    print(f"Opening template editor. Invalidating cache as a precaution.")
    template_cache_manager.invalidate()

    if template_id:
      found_template = next(
        (t for t in self.all_templates if t.get("id") == template_id), None
      )
      if not found_template:
        alert(f"Template with ID {template_id} not found.")
        return
      open_form("Templates.TemplateEditor", template=found_template)
    else:
      open_form("Templates.TemplateEditor")

  def search_templates_client(self, query, **event_args):
    """MODIFIED to use the local self.all_templates list."""
    print(f"Client-side template search with query: {query}")
    if not query:
      self.call_js("populateTemplates", self.all_templates, self.default_template_id)
      return
    search_term = query.lower()
    results = [
      t for t in self.all_templates if search_term in t.get("name", "").lower()
    ]
    self.call_js("populateTemplates", results, self.default_template_id)

  def delete_template(self, template_id, **event_args):
    if confirm("Are you sure you want to delete this template?"):
      try:
        success = anvil.server.call("delete_template", template_id)
        if success:
          # *** FIX: Invalidate the cache after a successful deletion ***
          template_cache_manager.invalidate()
          self.form_show()  # Refresh the view
        else:
          alert("Could not delete the template.")
      except Exception as e:
        alert(f"An error occurred: {e}")

  def toggle_template_display(self, template_id, new_display_state, **event_args):
    """
    Called from JavaScript when the show/hide button is clicked.
    Updates the 'display' property of the specified template.
    """
    try:
      # Call the existing server function to update the template's display property
      success = anvil.server.call("write_template", template_id=template_id, display=new_display_state)

      if success:
        # On success, invalidate the cache and reload the form to show the change
        template_cache_manager.invalidate()
        self.form_show()
      else:
        alert("Failed to update the template's visibility.")
    except Exception as e:
      alert(f"An error occurred while updating template visibility: {e}")

  def set_default_template(self, template_id, **event_args):
    """
    Called from JavaScript to set the user's default template.
    """
    try:
      success = anvil.server.call('set_default_template', template_id)
      if success:
        # Invalidate cache so the new default is fetched next time
        template_cache_manager.invalidate() 
        self.form_show() # Refresh the view to show the change immediately
      else:
        alert("Could not set the default template.")
    except Exception as e:
      alert(f"An error occurred: {e}")