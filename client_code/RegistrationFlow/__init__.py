from ._anvil_designer import RegistrationFlowTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class RegistrationFlow(RegistrationFlowTemplate):
  def __init__(self, **properties):
    print("DEBUG: Initializing RegistrationFlow form...")
    # Initialize the form components
    self.init_components(**properties)
    print("DEBUG: RegistrationFlow components initialized.")
    # Variables to temporarily store data from step 1
    self.user_name = ""
    self.user_phone = ""

  def next_click(self, **event_args):
    """
    Called when the user clicks "Next" on the first modal.
    Collects name and phone, then transitions to step 2.
    """
    try:
      name_val = self.call_js("getValueById", "reg-name")
      phone_val = self.call_js("getValueById", "reg-phone")
      print(f"DEBUG: Collected name: {name_val}, phone: {phone_val}")
      if not name_val or not phone_val:
        alert("Please fill in both name and phone.")
        return
      # Save the collected values for later use
      self.user_name = name_val
      self.user_phone = phone_val
      # Transition: hide modal step 1 and show modal step 2
      self.call_js("hideModal", "modal-step1")
      self.call_js("showModal", "modal-step2")
    except Exception as e:
      print(f"DEBUG: Error in next_click: {str(e)}")
      alert(f"An error occurred while proceeding to the next step: {str(e)}")

  def back_click(self, **event_args):
    """
    Called when the user clicks "Back" on the second modal.
    Returns to the first modal.
    """
    try:
      self.call_js("hideModal", "modal-step2")
      self.call_js("showModal", "modal-step1")
    except Exception as e:
      print(f"DEBUG: Error in back_click: {str(e)}")
      alert(f"An error occurred while going back: {str(e)}")

  def submit_click(self, **event_args):
    """
    Called when the user clicks "Submit" on the second modal.
    Collects the specialité selection and logs all user data via the server.
    Also assigns the Horse template to users who select Equin specialty.
    """
    try:
      specialite_val = self.call_js("getRadioValueByName", "specialite")
      print(f"DEBUG: Collected specialite: {specialite_val}")
      if not specialite_val:
        alert("Please select a specialité.")
        return

      # Relay the registration via a server function
      success = anvil.server.call(
          "write_user",
          name=self.user_name,
          phone=self.user_phone,
          specialite=specialite_val,
          additional_info=True
      )
      print(f"DEBUG: Server response for write_user: {success}")

      if success:
        # If the user selected "Equin", assign the Horse template
        if specialite_val == "Equin":
          try:
            # Get the current user
            current_user = anvil.users.get_user()
            print(f"DEBUG: Assigning Horse template to user: {current_user['email']}")

            # First get the base template row
            horse_template = anvil.server.call("get_base_template", "Horse")
            if horse_template:
              # Now pass the row object to affect_base_template
              result = anvil.server.call("affect_base_template", horse_template, current_user)
              print(f"DEBUG: Horse template assignment result: {result}")
            else:
              print("DEBUG: Horse base template not found")
          except Exception as e:
            print(f"DEBUG: Error assigning Horse template: {str(e)}")
            # Continue with the flow even if template assignment fails

        alert("Registration successful!")
        # Hide any active modals before navigating away
        self.call_js("hideModal", "modal-step2")
        self.call_js("hideModal", "modal-step1")
        open_form("AudioManager.AudioManagerForm")
      else:
        alert("Registration failed. Please try again.")
    except Exception as e:
      print(f"DEBUG: Error in submit_click: {str(e)}")
      alert(f"An error occurred during registration: {str(e)}")

  def cancel_click(self, **event_args):
    """
    Called when the user clicks "Cancel" on the first modal.
    Hides the modals and redirects to the AudioManager form.
    """
    # Hide any active modals and overlay before navigation
    self.call_js("hideModal", "modal-step1")
    self.call_js("hideModal", "modal-step2")
    open_form("AudioManager.AudioManagerForm")
