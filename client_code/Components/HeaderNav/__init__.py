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
    lang = anvil.server.call("pick_user_favorite_language")
    if lang == "FR":
      open_form("Templates.Templates")
    else:
      open_form("Templates.EN_Templates")

  def open_archives_form(self, **event_args):
    user = anvil.users.get_user(allow_remembered=True)
    lang = anvil.server.call("pick_user_favorite_language")
    if user and user["supervisor"]:
      if lang == "FR":
        open_form("Archives.ArchivesSecretariat")
      else:
        open_form("Archives.EN_ArchivesSecretariat")
    else:
      if lang == "FR":
        open_form("Archives.Archives")
      else:
        open_form("Archives.EN_Archives")

  def open_settings_form(self, **event_args):
    lang = anvil.server.call("pick_user_favorite_language")
    if lang == "FR":
      open_form("Settings.Settings")
    else:
      open_form("Settings.EN_Settings")
