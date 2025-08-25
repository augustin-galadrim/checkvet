from ._anvil_designer import SettingsTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.js
from ... import TranslationService as t
from ...Cache import user_settings_cache, reports_cache_manager, template_cache_manager
from ...AppEvents import events
from ...AuthHelpers import setup_auth_handlers


class Settings(SettingsTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    setup_auth_handlers(self)
    events.subscribe("language_changed", self.update_ui_texts)
    self.add_event_handler("show", self.on_form_show)

  def on_form_show(self, **event_args):
    self.header_nav_1.active_tab = "Settings"
    self.update_ui_texts()
    self.load_vet_data()
    self.load_favorite_language_modal()

  def update_ui_texts(self, **event_args):
    """Sets all translatable text on the form."""
    self.call_js(
      "setElementText", "settings-h2-vetInfoTitle", t.t("settings_h2_vetInfoTitle")
    )
    self.call_js("setElementText", "settings-label-name", t.t("settings_label_name"))
    self.call_js("setElementText", "settings-label-phone", t.t("settings_label_phone"))
    self.call_js("setElementText", "settings-label-email", t.t("settings_label_email"))
    self.call_js("setElementText", "settings-h2-orgTitle", t.t("settings_h2_orgTitle"))
    self.call_js(
      "setElementText", "settings-label-structure", t.t("settings_label_structure")
    )
    self.call_js(
      "setElementText",
      "settings-button-joinStructure",
      t.t("settings_button_joinStructure"),
    )
    self.call_js(
      "setElementText",
      "settings-span-supervisorMessage",
      t.t("settings_span_supervisorMessage"),
    )
    self.call_js(
      "setElementText", "settings-label-joinCode", t.t("settings_label_joinCode")
    )
    self.call_js(
      "setElementText", "settings-h2-prefsTitle", t.t("settings_h2_prefsTitle")
    )
    self.call_js(
      "setElementText", "settings-label-favLanguage", t.t("settings_label_favLanguage")
    )
    self.call_js(
      "setElementText", "settings-h2-toolsTitle", t.t("settings_h2_toolsTitle")
    )
    self.call_js(
      "setElementText", "settings-button-micTest", t.t("settings_button_micTest")
    )
    self.call_js(
      "setElementText",
      "settings-button-installGuide",
      t.t("settings_button_installGuide"),
    )
    self.call_js(
      "setElementText", "settings-button-cancel", t.t("settings_button_cancel")
    )
    self.call_js(
      "setElementText", "settings-button-submit", t.t("settings_button_submit")
    )
    self.call_js(
      "setElementText", "settings-button-admin", t.t("settings_button_admin")
    )
    self.call_js(
      "setElementText", "settings-button-logout", t.t("settings_button_logout")
    )
    self.call_js(
      "setElementText", "settings-h3-joinModalTitle", t.t("settings_h3_joinModalTitle")
    )
    self.call_js(
      "setElementText", "settings-p-joinModalDesc", t.t("settings_p_joinModalDesc")
    )
    self.call_js(
      "setElementText",
      "settings-label-joinCodeModal",
      t.t("settings_label_joinCodeModal"),
    )
    self.call_js(
      "setElementText",
      "settings-button-submitJoinCode",
      t.t("settings_button_submitJoinCode"),
    )
    self.call_js(
      "setElementText",
      "settings-h3-favLangModalTitle",
      t.t("settings_h3_favLangModalTitle"),
    )

  def load_vet_data(self):
    """Retrieves the current user's data from the server and updates the UI."""
    try:
      user_data = anvil.server.call_s("read_user")
      if not user_data:
        alert("Could not retrieve your user data.")
        return

      self.call_js("setValue", "settings-input-name", user_data.get("name", ""))
      self.call_js("setValue", "settings-input-email", user_data.get("email", ""))
      self.call_js("setValue", "settings-input-phone", user_data.get("phone", ""))

      structure_value = user_data.get("structure", "independent")
      is_independent = structure_value == "independent"
      display_text = (
        t.t("settings_structure_independent") if is_independent else structure_value
      )
      self.call_js("setValue", "settings-input-structureDisplay", display_text)
      self.call_js("toggleJoinButton", is_independent)

      favorite_language = user_data.get("favorite_language", "en")
      lang_map = {"fr": t.t("language_fr"), "en": t.t("language_en")}
      lang_display_text = lang_map.get(favorite_language, t.t("language_en"))
      self.call_js("setValue", "favorite-language", favorite_language)
      self.call_js("setElementText", "settings-button-favLanguage", lang_display_text)

      is_supervisor = user_data.get("supervisor", False)
      join_code = user_data.get("join_code")
      self.call_js("updateSupervisorView", is_supervisor, join_code)
      self.call_js("showAdminButton", self.is_admin_user())

    except Exception as e:
      alert(f"An error occurred while loading your data: {str(e)}")

  def attempt_to_join_structure(self, join_code, **event_args):
    """Called from JS to attempt joining a structure."""
    try:
      result = anvil.server.call_s("join_structure_as_vet", join_code)
      if result.get("success"):
        self.load_vet_data()
      return result
    except Exception as e:
      return {"success": False, "message": str(e)}

  def load_favorite_language_modal(self):
    """Populates the favorite language selection modal."""
    options = [
      {"display": t.t("language_fr"), "value": "fr"},
      {"display": t.t("language_en"), "value": "en"},
    ]
    current_fav = anvil.server.call_s("get_user_info", "favorite_language") or "en"
    self.call_js("populateFavoriteLanguageModal", options, current_fav)

  def submit_click(self, **event_args):
    """Gathers data, saves it, and reloads translations if language changed."""
    try:
      form_data = {
        "name": self.call_js("getValueById", "settings-input-name"),
        "phone": self.call_js("getValueById", "settings-input-phone"),
        "favorite_language": self.call_js("getValueById", "favorite-language"),
      }
      new_language = form_data.get("favorite_language")
      success = anvil.server.call_s("write_user", **form_data)
      if success:
        user_settings_cache["language"] = None
        if new_language != t.CURRENT_LANG:
          t.load_language(new_language)
          events.publish("language_changed")
        self.call_js("displayBanner", t.t("settings_update_success_banner"), "success")
        self.load_vet_data()
      else:
        alert(t.t("settings_update_fail_alert"))
    except Exception as e:
      alert(f"{t.t('settings_submit_error_alert')}: {str(e)}")

  def cancel_click(self, **event_args):
    """Discards changes by reloading user data."""
    self.load_vet_data()
    self.call_js("displayBanner", t.t("settings_cancel_banner"), "info")

  def logout_click(self, **event_args):
    """Logs the user out."""
    reports_cache_manager.invalidate()
    template_cache_manager.invalidate()
    for key in user_settings_cache:
      user_settings_cache[key] = None

    anvil.users.logout()
    open_form("StartupForm")

  def openMicrophoneTest(self, **event_args):
    """Navigates to the microphone test form."""
    open_form("Settings.MicrophoneTest")

  def show_install_guide_click(self, **event_args):
    """Navigates to the mobile installation guide form."""
    open_form("MobileInstallationFlow")

  def is_admin_user(self):
    """Checks if the current user is an administrator."""
    user = anvil.users.get_user()
    if not user:
      return False
    admin_emails = ["augustincramer.galadrim@gmail.com", "biffy071077@gmail.com"]
    return user["email"].lower() in admin_emails

  def openAdmin(self, **event_args):
    """Navigates to the Administration panel."""
    open_form("Settings.Admin")
