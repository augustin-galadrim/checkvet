from ._anvil_designer import TemplatesTemplate
from anvil import *
import anvil.server
import anvil.users
from ...Cache import template_cache_manager
from ...LoggingClient import ClientLogger
from ... import TranslationService as t
from ...AppEvents import events
from ...AuthHelpers import setup_auth_handlers


class Templates(TemplatesTemplate):
  def __init__(self, **properties):
    self.logger = ClientLogger(self.__class__.__name__)
    self.logger.info("Initializing...")
    self.init_components(**properties)
    setup_auth_handlers(self)
    events.subscribe("language_changed", self.update_ui_texts)
    self.all_templates = []
    self.default_template_id = None
    self.add_event_handler("show", self.form_show)

  def update_ui_texts(self, **event_args):
    """Sets all translatable text on the component."""
    self.call_js(
      "setElementText", "templates-button-create", t.t("templates_button_create")
    )
    self.call_js(
      "setPlaceholder",
      "templates-input-search",
      t.t("templates_input_search_placeholder"),
    )

    locale_texts = {
      "defaultTemplateTitle": t.t("templates_title_default"),
      "activeTemplatesTitle": t.t("templates_title_active"),
      "inactiveTemplatesTitle": t.t("templates_title_inactive"),
      "noDefaultTemplates": t.t("templates_renderer_noDefault"),
      "noActiveTemplates": t.t("templates_renderer_noActive"),
      "noInactiveTemplates": t.t("templates_renderer_noInactive"),
      "untitledTemplate": t.t("templates_renderer_untitled"),
      "setAsDefault": t.t("templates_renderer_setAsDefault"),
      "hide": t.t("templates_renderer_hide"),
      "show": t.t("templates_renderer_show"),
      "delete": t.t("templates_renderer_delete_tooltip"),
    }
    self.call_js("setLocaleTexts", locale_texts)

  def form_show(self, **event_args):
    """Now uses the cache and handles the default template ID."""
    self.logger.info("Form showing. Checking cache for templates.")
    self.header_nav_1.active_tab = "Templates"
    self.update_ui_texts()

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

  def open_template_editor(self, template_id=None, **event_args):
    """Opens the editor for a new or existing template."""
    self.logger.info("Opening template editor. Invalidating cache as a precaution.")
    template_cache_manager.invalidate()
    if template_id:
      found_template = next(
        (t for t in self.all_templates if t.get("id") == template_id), None
      )
      if not found_template:
        alert(f"Template with ID {template_id} not found.")
        self.logger.error(f"Template with ID {template_id} not found in local list.")
        return
      open_form("Templates.TemplateEditor", template=found_template)
    else:
      open_form("Templates.TemplateEditor")

  def delete_template(self, template_id, **event_args):
    """Deletes a template after user confirmation."""
    if confirm(t.t("templates_confirm_delete")):
      self.logger.info(f"Attempting to delete template with ID: {template_id}")
      try:
        success = anvil.server.call_s("delete_template", template_id)
        if success:
          template_cache_manager.invalidate()
          self.form_show()
        else:
          alert("Could not delete the template.")
      except Exception as e:
        self.logger.error(
          f"An error occurred while deleting template ID: {template_id}", e
        )
        alert(f"An error occurred: {e}")

  def toggle_template_display(self, template_id, new_display_state, **event_args):
    """Updates the 'display' property of the specified template."""
    try:
      success = anvil.server.call_s(
        "write_template", template_id=template_id, display=new_display_state
      )
      if success:
        template_cache_manager.invalidate()
        self.form_show()
      else:
        alert("Failed to update the template's visibility.")
    except Exception as e:
      alert(f"An error occurred while updating template visibility: {e}")

  def set_default_template(self, template_id, **event_args):
    """Sets the user's default template."""
    try:
      success = anvil.server.call_s("set_default_template", template_id)
      if success:
        template_cache_manager.invalidate()
        self.form_show()
      else:
        alert("Could not set the default template.")
    except Exception as e:
      alert(f"An error occurred: {e}")
