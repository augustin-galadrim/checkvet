import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server

@anvil.server.callable
def ensure_persistent_session():
  """
  Ensures the current user's session is set to be remembered.
  Call this when you want to make sure the user stays logged in.
  """
  current_user = anvil.users.get_user()
  if current_user:
    # Get the user row to update remembered_logins
    user_row = app_tables.users.get(email=current_user['email'])
    if user_row:
      # If remembered_logins is None or empty, initialize it
      if not user_row['remembered_logins']:
        user_row['remembered_logins'] = {}

      # Force a login to refresh the session cookie
      anvil.users.force_login(user_row, remember=True)
      return True
  return False

@anvil.server.callable
def check_and_refresh_session():
  """
  Check if the current session is active and refresh it if needed.
  Returns True if session is valid, False otherwise.
  """
  try:
    current_user = anvil.users.get_user(allow_remembered=True)
    if current_user:
      # Session is valid, ensure it's persistent
      return ensure_persistent_session()
    return False
  except:
    return False
