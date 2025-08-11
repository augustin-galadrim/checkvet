from ._anvil_designer import RegistrationFlowTemplate
from anvil import *
import anvil.server
import anvil.users

class RegistrationFlow(RegistrationFlowTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    # State variables to hold user data across steps
    self.registration_data = {}

    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Called when the form is shown. Displays the first step."""
    self.call_js("showModal", "modal-step1")

  def go_to_step(self, step_number, **event_args):
    """Handles navigation between steps, validating and saving data along the way."""
    if step_number == 2:
      # --- Moving from Step 1 (Language) to Step 2 (Info) ---
      self.registration_data['favorite_language'] = self.call_js("getRadioValueByName", "language")
      if not self.registration_data.get('favorite_language'):
        alert("Please select a language.")
        return
      self.call_js("hideModal", "modal-step1")
      self.call_js("showModal", "modal-step2")

    elif step_number == 3:
      # --- Moving from Step 2 (Info) to Step 3 (Structure) ---
      self.registration_data['name'] = self.call_js("getValueById", "reg-name")
      self.registration_data['phone'] = self.call_js("getValueById", "reg-phone")
      if not self.registration_data.get('name') or not self.registration_data.get('phone'):
        alert("Please fill in both your name and phone number.")
        return
      self.call_js("hideModal", "modal-step2")
      self.call_js("showModal", "modal-step3")

    elif step_number == 1:
      # --- Going back from Step 2 to Step 1 ---
      self.call_js("hideModal", "modal-step2")
      self.call_js("showModal", "modal-step1")

    elif step_number == 2:
      # --- Going back from Step 3 to Step 2 ---
      self.call_js("hideModal", "modal-step3")
      self.call_js("showModal", "modal-step2")


  def submit_registration(self, **event_args):
    """
    Handles the choice from Step 3.
    - If "Create", it moves to Step 4.
    - Otherwise, it finalizes registration immediately.
    """
    choice = self.call_js("getRadioValueByName", "structure-choice")
    self.registration_data['structure_choice'] = choice

    if choice == "create":
      # Move to the new structure creation modal
      self.call_js("hideModal", "modal-step3")
      self.call_js("showModal", "modal-step4")

    elif choice == "join":
      join_code = self.call_js("getValueById", "join-code-input")
      if not join_code:
        alert("Please enter the structure join code.")
        return
      self.registration_data['join_code'] = join_code
      self.finalize_registration()

    else: # Independent
      self.finalize_registration()

  def finish_registration_with_structure(self, **event_args):
    """
    Called from the final "Finish" button in Step 4.
    Gathers structure details and finalizes registration.
    """
    structure_details = {
      "name": self.call_js("getValueById", "reg-structure-name"),
      "phone": self.call_js("getValueById", "reg-structure-phone"),
      "email": self.call_js("getValueById", "reg-structure-email"),
    }
    if not structure_details.get("name"):
      alert("Please enter a name for your new structure.")
      return

    self.registration_data['structure_details'] = structure_details
    self.finalize_registration()

  def finalize_registration(self):
    """
    Makes the single, consolidated server call to complete the registration process.
    """
    try:
      result = anvil.server.call("register_user_and_setup", self.registration_data)

      if result.get("success"):
        alert("Registration successful!")
        open_form("Production.AudioManagerForm")
      else:
        # Display the specific error message from the server
        alert(f"Registration failed: {result.get('message', 'An unknown error occurred.')}")

    except Exception as e:
      alert(f"An error occurred during registration: {str(e)}")