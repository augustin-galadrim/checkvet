import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime

@anvil.server.callable
def check_session():
  """Check and refresh session if needed"""
  try:
    # Try to get active user (not remembered)
    active_user = anvil.users.get_user(allow_remembered=False)
    if active_user:
      # Session is active
      return {'status': 'active'}

    # Try to get remembered user
    remembered_user = anvil.users.get_user(allow_remembered=True)
    if remembered_user:
      # User remembered but session expired, log event
      if 'auth_events' in app_tables.list_tables():
        app_tables.auth_events.add_row(
            user=remembered_user,
            event_type='session_refresh',
            timestamp=datetime.now()
        )
      # Session refreshed
      return {'status': 'refreshed'}

    # No user found
    return {'status': 'expired'}
  except Exception as e:
    print(f"Session check error: {str(e)}")
    return {'status': 'error'}

@anvil.server.callable
def check_remembered_login():
  """Check if user has a valid remembered login"""
  try:
    return anvil.users.get_user(allow_remembered=True) is not None
  except Exception as e:
    print(f"Remembered login check error: {str(e)}")
    return False
