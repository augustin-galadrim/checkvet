from ._anvil_designer import StartupFormTemplate
from anvil import *
import anvil.server
import anvil.users
from .. import TranslationService as t
from ..Cache import user_settings_cache
from ..AppEvents import events


class StartupForm(StartupFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    # The form's logic is now handled in the 'show' event
    self.add_event_handler("show", self.form_show)

  def update_ui_texts(self):
    """Sets all translatable text on the form."""
    # This provides feedback to the user if loading takes a moment
    self.call_js(
      "setElementText",
      "startupForm-center-loadingMessage",
      t.t("startupForm_loading_message"),
    )

  def form_show(self, **event_args):
    """This method runs when the form is displayed and handles the app startup sequence."""

    # Set default language to English before user is known, then update the UI text
    t.load_language("en")
    self.update_ui_texts()

    try:
      # 1. AUTHENTICATION
      user = anvil.users.get_user(allow_remembered=True)
      if not user:
        user = anvil.users.login_with_form()

      if user:
        # --- User is logged in ---
        anvil.server.call_s("ensure_persistent_session")
        user_data = anvil.server.call_s("read_user")
        self.call_js("ImageStaging.cleanupOldImages")

        if not user_data:
          alert("Could not load your user profile. Please contact support.")
          anvil.users.logout()
          open_form("StartupForm")
          return

        user_settings_cache["user_data"] = user_data
        user_settings_cache["additional_info"] = user_data.get("additional_info")
        user_settings_cache["language"] = user_data.get("favorite_language")

        if not user_data.get("additional_info"):
          open_form("RegistrationFlow")
          return

        lang_code = user_data.get("favorite_language", "en")
        t.load_language(lang_code)
        open_form("Production.AudioManagerForm")
      else:
        # User cancelled login, proceed offline
        alert(t.t("startupForm_alert_loginCancelled"))
        open_form("Production.OfflineAudioManagerForm")

    except anvil.server.AppOfflineError:
      alert(t.t("startupForm_alert_offline"))
      open_form("Production.OfflineAudioManagerForm")
    except Exception as e:
      print(f"An unexpected error occurred during startup: {e}")
      alert(f"{t.t('startupForm_alert_unexpectedError')}: {e}")
      open_form("Production.OfflineAudioManagerForm")
