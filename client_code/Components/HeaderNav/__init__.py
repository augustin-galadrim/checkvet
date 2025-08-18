from ._anvil_designer import HeaderNavTemplate
from anvil import *
import anvil.server
import anvil.users
from ... import TranslationService as t
from ...AppEvents import events


class HeaderNav(HeaderNavTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    events.subscribe("language_changed", self.update_ui_texts)
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    self.update_ui_texts()
    # When the component is shown, tell JavaScript which tab to make active
    if self.active_tab:
      self.call_js("setActiveTab", self.active_tab)

  def update_ui_texts(self):
    anvil.js.call_js("setElementText", "nav_production", t.t("nav_production"))
    anvil.js.call_js("setElementText", "nav_templates", t.t("nav_templates"))
    anvil.js.call_js("setElementText", "nav_archives", t.t("nav_archives"))
    anvil.js.call_js("setElementText", "nav_settings", t.t("nav_settings"))

  def open_production_form(self, **event_args):
    open_form("Production.AudioManagerForm")

  def open_templates_form(self, **event_args):
    open_form("Templates.Templates")

  def open_archives_form(self, **event_args):
    open_form("Archives.ArchivesForm")

  def open_settings_form(self, **event_args):
    open_form("Settings.Settings")
