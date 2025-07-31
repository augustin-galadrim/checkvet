from ._anvil_designer import StartupFormTemplate
from anvil import *
import anvil.server
import anvil.users
from .. import TranslationService as t


class StartupForm(StartupFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    try:
      user = anvil.users.get_user(allow_remembered=True)
      if not user:
        user = anvil.users.login_with_form()

      if user:
        # If online and logged in, proceed with the normal flow.
        anvil.server.call("ensure_persistent_session")
        lang_code = anvil.server.call("pick_user_favorite_language") or "en"
        t.load_language(lang_code)

        # Open the main production form for online users
        open_form("Production.AudioManagerForm")
      else:
        # If online but the user cancelled the login, they can still proceed to the offline form.
        alert("Login cancelled. Proceeding with offline capabilities.")
        open_form("Production.OfflineAudioManagerForm")

    except anvil.server.AppOfflineError:
      print("App is offline. Loading offline-first audio manager.")
      # Open the form specifically designed for offline use. No login is required.
      open_form("Production.OfflineAudioManagerForm")

    except Exception as e:
      # Catch any other unexpected errors during startup
      print(f"An unexpected error occurred during startup: {e}")
      alert("An error occurred while starting the app. You can try the offline mode.")
      # As a fallback, still try to open the offline form.
      open_form("Production.OfflineAudioManagerForm")
