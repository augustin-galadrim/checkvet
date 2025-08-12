import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
#import anvil.server
from anvil import open_form

# Functions to set up auth handling in any form

def setup_auth_handlers(form):
  """
  Set up authentication handlers on a form

  Usage in any form:
    from ..auth_helpers import setup_auth_handlers

    def __init__(self, **properties):
        self.init_components(**properties)
        setup_auth_handlers(self)
  """
  form.add_event_handler("show", lambda **e: form.call_js("setupSessionHandlers"))

  # Add the refresh_session_relay method to the form
  def refresh_session_relay(self, **event_args):
    """Relay session refresh from JS to server"""
    try:
      result = anvil.server.call_s("check_session")

      if result['status'] == 'expired':
        # Session expired, redirect to login
        open_form("StartupForm")
        return False

      # Session valid (either active or refreshed)
      return True

    except Exception as e:
      print(f"Session refresh error: {str(e)}")
      return False

  # Bind the method to the form instance
  form.refresh_session_relay = refresh_session_relay.__get__(form)
