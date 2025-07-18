import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime

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

    return {
        "user": user,
        "status": status
    }
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
def pick_user_favorite_language():
  """Get user's preferred language"""
  user = anvil.users.get_user()
  if not user:
    return "EN"  # Default
  return user.get("favorite_language", "EN")

@anvil.server.callable
def pick_user_structure():
  """Get user's structure"""
  user = anvil.users.get_user()
  if not user:
    return None

  structure = user.get("structure")
  if isinstance(structure, tables.Row):
    return structure["name"]
  return structure
