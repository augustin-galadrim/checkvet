from ._anvil_designer import HeaderReturnTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.js  # NEW: Import anvil.js
from ... import TranslationService as t  # NEW: Import the TranslationService
from ...AppEvents import events  # NEW: Import the events manager


class HeaderReturn(HeaderReturnTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    # NEW: Subscribe to the language_changed event to update text dynamically
    events.subscribe("language_changed", self.update_ui_texts)
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    # Set the dynamic title from the component's properties
    self.call_js("setHeaderTitle", self.title)
    # NEW: Set the translated text for static elements
    self.update_ui_texts()
    # Attach the JavaScript event listener for the return button
    self.call_js("attachReturnButtonListener")

  # NEW: This function sets all translatable text on the component
  def update_ui_texts(self, **event_args):
    """Sets all translatable text on the component."""
    # This key 'headerReturn_button_return' should be added to your Locales.py file
    return_text = f"← {t.t('headerReturn_button_return')}"
    self.call_js("setReturnButtonText", return_text)

  def return_button_click(self, **event_args):
    """Called from JavaScript when the return button is clicked."""
    if self.return_form:
      open_form(self.return_form)
    else:
      # As a fallback, go to the startup form if return_form is not set
      open_form("StartupForm")
