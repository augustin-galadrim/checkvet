import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime
from .logging_server import get_logger
logger = get_logger(__name__)

# Single session management function - the core of our simplified approach
@anvil.server.callable
def ensure_auth(remember=True):
  """
  Core auth function that ensures a user is authenticated.
  It will:
  1. Return active user if session is valid
  2. Restore remembered user if available
  3. Extend session lifetime

  Returns:
      dict: User data including auth status
  """
  try:
    # Try to get active user first (no remembered user)
    user = anvil.users.get_user(allow_remembered=False)
    status = "active"

    if not user:
      # No active session, try remembered user
      user = anvil.users.get_user(allow_remembered=True)
      status = "restored" if user else "none"

    # If we have a user (either active or restored), make session persistent
    if user and remember:
      # Extend session lifetime
      anvil.server.session.set_expiry(3600 * 24 * 30)  # 30 days

      # Remember this user for future visits
      anvil.users.set_remembered_user(user)

    return {"user": user, "status": status}
  except Exception as e:
    print(f"[ERROR] Auth error: {str(e)}")
    return {"user": None, "status": "error", "error": str(e)}


@anvil.server.callable
def login_user(remember=True):
  """Simple function that shows login form and remembers user"""
  try:
    user = anvil.users.login_with_form()
    if user and remember:
      anvil.server.session.set_expiry(3600 * 24 * 30)
      anvil.users.set_remembered_user(user)
    return user
  except:
    return None


@anvil.server.callable
def logout_user():
  """Log user out and clear remembered status"""
  try:
    anvil.users.set_remembered_user(None)
    anvil.users.logout()
    return True
  except:
    return False


@anvil.server.callable
def ensure_persistent_session():
  """
  Ensures the current user's session is set to be remembered.
  Call this when you want to make sure the user stays logged in.
  """
  current_user = anvil.users.get_user()
  if current_user:
    # Get the user row to update remembered_logins
    user_row = app_tables.users.get(email=current_user["email"])
    if user_row:
      # If remembered_logins is None or empty, initialize it
      if not user_row["remembered_logins"]:
        user_row["remembered_logins"] = {}

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
