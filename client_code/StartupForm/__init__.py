from ._anvil_designer import StartupFormTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .. import TranslationService as t

class StartupForm(StartupFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    user = anvil.users.get_user(allow_remembered=True)
    if not user:
      user = anvil.users.login_with_form()

    if user:

      try:
        anvil.server.call("ensure_persistent_session")
      except anvil.server.SessionExpiredError:
        anvil.server.reset_session()
        anvil.server.call("ensure_persistent_session")

      try:
        lang_code = anvil.server.call("pick_user_favorite_language") or 'en'
        print(f"User's preferred language is: {lang_code}")

        t.load_language(lang_code)

        structure_name = anvil.server.call("pick_user_structure")
        print(f"User's structure is: {structure_name}")

        if structure_name == "Test":
          open_form("TEST_AudioManagerUltimate35")
        else:
          open_form("AudioManagerForm")

      except Exception as e:
        print(f"ERROR during startup sequence: {e}")
        try:
          t.load_language('en')
          open_form("AudioManagerForm")
        except Exception as final_e:
          print(f"CRITICAL ERROR: Could not open fallback form. {final_e}")
          alert("A critical error occurred while starting the application. Please contact support.")

    else:
      print("User login failed or was cancelled.")