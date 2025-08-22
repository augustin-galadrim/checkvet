import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime
from functools import wraps
from .logging_server import get_logger

# Instantiate the logger for this module
logger = get_logger(__name__)

# List of authorized admin email addresses
ADMIN_EMAILS = ["augustincramer.galadrim@gmail.com", "biffy071077@gmail.com"]


# Decorator to protect admin-only functions
def admin_required(func):
  """
  A decorator to ensure that the calling user is an administrator.
  Raises a PermissionDenied exception if the user is not an admin.
  """

  @wraps(func)
  def wrapper(*args, **kwargs):
    user = anvil.users.get_user(allow_remembered=True)
    if user and user["email"].lower() in [email.lower() for email in ADMIN_EMAILS]:
      logger.debug(
        f"Admin access granted for user '{user['email']}' to function '{func.__name__}'."
      )
      return func(*args, **kwargs)
    else:
      user_email = user["email"] if user else "Not logged in"
      logger.warning(
        f"Unauthorized access attempt by user '{user_email}' to admin function '{func.__name__}'."
      )
      raise anvil.server.PermissionDenied(
        "You must be an administrator to perform this action."
      )

  return wrapper


# Single session management function - the core of our simplified approach
@anvil.server.callable
def ensure_auth(remember=True):
  """
  Core auth function that ensures a user is authenticated.
  """
  logger.info("ensure_auth called.")
  try:
    user = anvil.users.get_user(allow_remembered=False)
    status = "active"
    if not user:
      user = anvil.users.get_user(allow_remembered=True)
      status = "restored" if user else "none"

    logger.info(f"Auth status: {status}. User: {user['email'] if user else 'None'}.")

    if user and remember:
      anvil.server.session.set_expiry(3600 * 24 * 30)  # 30 days
      anvil.users.set_remembered_user(user)
      logger.debug(f"Session extended and user '{user['email']}' remembered.")

    return {"user": user, "status": status}
  except Exception as e:
    logger.error(f"Exception in ensure_auth: {e}", exc_info=True)
    return {"user": None, "status": "error", "error": str(e)}


# The rest of the functions in this file remain unchanged from the previous step.
# They are standard authentication flows and do not require extensive custom logging.
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
  """
  current_user = anvil.users.get_user()
  if current_user:
    user_row = app_tables.users.get(email=current_user["email"])
    if user_row:
      if not user_row["remembered_logins"]:
        user_row["remembered_logins"] = {}
      anvil.users.force_login(user_row, remember=True)
      return True
  return False


@anvil.server.callable
def check_session():
  """
  Checks the user's session status and refreshes it if needed.
  This is called by the global session handler.

  Returns:
    dict: A dictionary with the status ('active', 'refreshed', or 'expired').
  """
  # Check for a fully active session (not just a 'remember me' cookie)
  if anvil.users.get_user(allow_remembered=False):
    logger.debug("Session is active.")
    return {"status": "active"}

  # If no active session, check if a remembered user exists
  user = anvil.users.get_user(allow_remembered=True)
  if user:
    # Promote the 'remembered' session to a full, active one
    anvil.users.force_login(user, remember=True)
    logger.info(
      f"Session for '{user['email']}' was restored from 'remember me' cookie."
    )
    return {"status": "refreshed"}

  # If no user is found, the session has expired
  logger.warning(
    "Session check failed: No active or remembered user found. Session expired."
  )
  return {"status": "expired"}
