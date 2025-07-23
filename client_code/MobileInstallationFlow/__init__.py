from ._anvil_designer import MobileInstallationFlowTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class MobileInstallationFlow(MobileInstallationFlowTemplate):
  def __init__(self, **properties):
    print("DEBUG: Initializing MobileInstallationFlow form...")
    # Initialize the form components
    self.init_components(**properties)
    print("DEBUG: MobileInstallationFlow components initialized.")

  def next_click_1(self, **event_args):
    """
    Called when the user clicks "Next" on the first modal.
    Transitions to step 2.
    """
    try:
      self.call_js("hideModal", "modal-step1")
      self.call_js("showModal", "modal-step2")
    except Exception as e:
      print(f"DEBUG: Error in next_click_1: {str(e)}")
      alert(f"An error occurred while proceeding to the next step: {str(e)}")

  def next_click_2(self, **event_args):
    """
    Called when the user clicks "Next" on the second modal.
    Transitions to step 3.
    """
    try:
      self.call_js("hideModal", "modal-step2")
      self.call_js("showModal", "modal-step3")
    except Exception as e:
      print(f"DEBUG: Error in next_click_2: {str(e)}")
      alert(f"An error occurred while proceeding to the next step: {str(e)}")

  def install_click(self, **event_args):
    """
    Called when the user clicks "I installed the app on my phone" on the third modal.
    Logs the installation via the server.
    """
    try:
      success = anvil.server.call("write_user", mobile_installation=True)
      print(f"DEBUG: Server response for write_user: {success}")
      if success:
        alert("Installation recorded successfully!")
        self.call_js("hideModal", "modal-step3")
        open_form("Production.AudioManagerForm")
      else:
        alert("Failed to record installation. Please try again.")
    except Exception as e:
      print(f"DEBUG: Error in install_click: {str(e)}")
      alert(f"An error occurred during installation recording: {str(e)}")
