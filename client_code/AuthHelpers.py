# In client_code/AuthHelpers.py

import anvil.server
from anvil import open_form
import anvil.js  # <--- Make sure this import is present

# Functions to set up auth handling in any form


def setup_auth_handlers(component):
  """
  Set up authentication handlers on a form or custom component.
  This version passes the component's DOM node directly to JavaScript.
  """
  # Get the JavaScript DOM node corresponding to this Python component instance.
  component_dom_node = anvil.js.get_dom_node(component)

  # When the component is shown, call the JS function and pass the DOM node.
  component.add_event_handler(
    "show", lambda **e: component.call_js("setupSessionHandlers", component_dom_node)
  )

  # Add the refresh_session_relay method to the component instance
  def refresh_session_relay(self, **event_args):
    """Relay session refresh from JS to the server"""
    try:
      result = anvil.server.call_s("check_session")

      if result and result.get("status") == "expired":
        open_form("StartupForm")
        return False

      return True

    except Exception as e:
      print(f"Session refresh error: {str(e)}")
      return False

  # Bind the method to the component instance
  component.refresh_session_relay = refresh_session_relay.__get__(component)
