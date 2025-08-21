from ._anvil_designer import HeaderNavTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.js
from ... import TranslationService as t
from ...AppEvents import events


class HeaderNav(HeaderNavTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    events.subscribe("language_changed", self.update_ui_texts)
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Called every time the component is shown. This is the key to the fix."""
    # Re-attach JavaScript event listeners to the current buttons in the DOM.
    self.call_js("js_attachHeaderEvents")

    # Now, set the translated text and active tab state.
    self.update_ui_texts()
    if self.active_tab:
      self.call_js("setActiveTab", self.active_tab)

  def update_ui_texts(self, **event_args):
    """Sets all translatable text on the component."""
    self.call_js(
      "setElementText",
      "headerNav-button-production",
      t.t("headerNav_button_production"),
    )
    self.call_js(
      "setElementText", "headerNav-button-templates", t.t("headerNav_button_templates")
    )
    self.call_js(
      "setElementText", "headerNav-button-archives", t.t("headerNav_button_archives")
    )
    self.call_js(
      "setElementText", "headerNav-button-settings", t.t("headerNav_button_settings")
    )

  def open_production_form(self, **event_args):
    open_form("Production.AudioManagerForm")

  def open_templates_form(self, **event_args):
    open_form("Templates.Templates")

  def open_archives_form(self, **event_args):
    open_form("Archives.ArchivesForm")

  def open_settings_form(self, **event_args):
    open_form("Settings.Settings")
