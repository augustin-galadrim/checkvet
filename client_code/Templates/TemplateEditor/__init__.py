from ._anvil_designer import TemplateEditorTemplate
from anvil import *
import anvil.server
import anvil.js
from ...Cache import template_cache_manager
from ... import TranslationService as t
from ...AppEvents import events


def safe_value(template, key, default_value):
  if template is None:
    return default_value
  val = template.get(key)
  return default_value if val is None else val


class TemplateEditor(TemplateEditorTemplate):
  def __init__(self, template=None, **properties):
    self.init_components(**properties)
    events.subscribe("language_changed", self.update_ui_texts)

    if template is None:
      template = {"id": None, "name": "", "html": "", "language": "en"}

    self.template = {
      "id": safe_value(template, "id", None),
      "name": safe_value(template, "name", ""),
      "html": safe_value(template, "html", ""),
      "language": safe_value(template, "language", "en"),
    }
    self.template_id = self.template.get("id")
    self.add_event_handler("show", self.form_show)

  def update_ui_texts(self, **event_args):
    """Sets all translatable text on the form."""
    self.header_return_1.title = t.t("templateEditor_header_title")
    self.call_js(
      "setPlaceholder",
      "templateEditor-input-name",
      t.t("templateEditor_input_name_placeholder"),
    )
    self.call_js(
      "setElementText",
      "templateEditor-button-cancel",
      t.t("templateEditor_button_cancel"),
    )
    self.call_js(
      "setElementText", "templateEditor-button-save", t.t("templateEditor_button_save")
    )

  def form_show(self, **event_args):
    """When the form is displayed, set up the UI and attach events."""
    self.update_ui_texts()
    self.text_editor_1.html_content = self.template.get("html")
    self.call_js("setTemplateNameValue", self.template.get("name"))
    self.call_js("setLanguageValue", self.template.get("language"))
    self.call_js("js_attachTemplateEditorEvents")

  def save_template(self, name, language, **event_args):
    """Called from JS to save the template. Includes server-side validation."""
    if not name or not name.strip():
      alert(t.t("templateEditor_alert_nameRequired"))
      return

    try:
      html_content = self.text_editor_1.get_content()
      result = anvil.server.call_s(
        "write_template",
        name=name,
        html=html_content,
        display=True,
        template_id=self.template_id,
        language=language,
      )

      if result:
        template_cache_manager.invalidate()
        self.call_js(
          "displayBanner", t.t("templateEditor_banner_saveSuccess"), "success"
        )
        open_form("Templates.Templates")
      else:
        alert(t.t("templateEditor_alert_saveFailed"))
    except Exception as e:
      alert(f"{t.t('templateEditor_alert_saveError')}: {str(e)}")
