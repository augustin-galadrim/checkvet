from ._anvil_designer import StartupFormTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class StartupForm(StartupFormTemplate):
  def __init__(self, **properties):
    # Run server-side dependency checks as the very first step.
    anvil.server.call('initialize_server_environment')
    # Initialize components defined in the Designer.
    self.init_components(**properties)

    # First try to get a remembered user without showing the login form
    user = anvil.users.get_user(allow_remembered=True)

    # If no remembered user exists, then show the login form
    if not user:
      print("No remembered user found, showing login form")
      user = anvil.users.login_with_form()  # Cannot pass remember=True here
    else:
      print("Remembered user found, refreshing session")
      # Ensure the session is refreshed for longevity
      try:
        anvil.server.call("ensure_persistent_session")
      except anvil.server.SessionExpiredError:
        anvil.server.reset_session()
        anvil.server.call("ensure_persistent_session")

    if user:
      # After successful login, ensure session is remembered
      # This will help persist the session
      try:
        anvil.server.call("ensure_persistent_session")
      except anvil.server.SessionExpiredError:
        anvil.server.reset_session()
        anvil.server.call("ensure_persistent_session")

      # Retrieve and print the user's favorite language.
      try:
        fav_language = anvil.server.call("pick_user_favorite_language")
      except anvil.server.SessionExpiredError:
        anvil.server.reset_session()
        fav_language = anvil.server.call("pick_user_favorite_language")

      print(f"User's favorite language is: {fav_language}")

      try:
        structure_name = anvil.server.call("pick_user_structure")
      except anvil.server.SessionExpiredError:
        anvil.server.reset_session()
        structure_name = anvil.server.call("pick_user_structure")

      print(f"User's structure is: {structure_name}")

      # Open the appropriate form based on the user's favorite language.
      if structure_name == "Test":
          #open_form("TEST_AudioManager")
          #open_form("TEST_OfflineAudioManager")
          #open_form("TEST_AudioDumper")
        open_form("TEST_AudioManagerUltimate35")
      else:
        if fav_language == 'FR':
          open_form("AudioManager")
        elif fav_language in ('EN', 'ES', 'DE', None):
          open_form("EN_AudioManager")
        else:
          alert("Authentication failed. Please try again.")
