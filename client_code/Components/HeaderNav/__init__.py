from ._anvil_designer import HeaderNavTemplate
from anvil import *
import anvil.server
import anvil.users


class HeaderNav(HeaderNavTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    # When the component is shown, tell JavaScript which tab to make active
    if self.active_tab:
      self.call_js("setActiveTab", self.active_tab)

  # --- Navigation Methods ---
  def open_production_form(self, **event_args):
    open_form("Production.AudioManagerForm")

  def open_templates_form(self, **event_args):
    open_form("Templates.Templates")

  def open_archives_form(self, **event_args):
    open_form("Archives.Archives")

  def open_settings_form(self, **event_args):
    open_form("Settings.Settings")
