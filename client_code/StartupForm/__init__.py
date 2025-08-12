from ._anvil_designer import StartupFormTemplate
from anvil import *
import anvil.server
import anvil.users
from .. import TranslationService as t
from ..Cache import user_settings_cache


class StartupForm(StartupFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    try:
      # 1. AUTHENTICATION: Attempt to get a logged-in user or show the login form.
      user = anvil.users.get_user(allow_remembered=True)
      if not user:
        user = anvil.users.login_with_form()

      if user:
        # --- User is now logged in ---
        anvil.server.call("ensure_persistent_session")

        # 2. REGISTRATION CHECK (Updated with Caching)
        additional_info_complete = user_settings_cache.get("additional_info")
        if additional_info_complete is None:
          # If not in cache, fetch from the server
          print("Startup cache miss: Fetching 'additional_info'.")
          additional_info_complete = anvil.server.call(
            "get_user_info", "additional_info"
          )
          # Store the result in the cache for this session
          user_settings_cache["additional_info"] = additional_info_complete

        if not additional_info_complete:
          # If registration is not complete, redirect to the registration flow.
          print("User has not completed registration. Redirecting to RegistrationFlow.")
          open_form("RegistrationFlow")
        else:
          # 3. LOAD MAIN APP (Updated with Caching)
          lang_code = user_settings_cache.get("language")
          if lang_code is None:
            # If not in cache, fetch the user's language from the server.
            print("Startup cache miss: Fetching 'favorite_language'.")
            lang_code = anvil.server.call("get_user_info", "favorite_language") or "en"
            # Store the result in the cache. Note the key is 'language'.
            user_settings_cache["language"] = lang_code

          t.load_language(lang_code)

          # Open the main production form for online users.
          open_form("Production.AudioManagerForm")
      else:
        # User cancelled the login prompt. They can still use the app offline.
        alert("Login cancelled. Proceeding with offline capabilities.")
        open_form("Production.OfflineAudioManagerForm")

    except anvil.server.AppOfflineError:
      # Handle the case where the app starts in offline mode.
      print("App is offline. Loading offline-first audio manager.")
      open_form("Production.OfflineAudioManagerForm")

    except Exception as e:
      # Catch any other unexpected errors during the startup process.
      print(f"An unexpected error occurred during startup: {e}")
      alert("An error occurred while starting the app. You can try the offline mode.")
      open_form("Production.OfflineAudioManagerForm")
