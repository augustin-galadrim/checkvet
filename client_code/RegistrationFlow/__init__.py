from ._anvil_designer import RegistrationFlowTemplate
from anvil import *
import anvil.server
import anvil.users


class RegistrationFlow(RegistrationFlowTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.registration_data = {}
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Called when the form is shown. Displays the first step."""
    self.call_js("showModal", "modal-step1")

  def go_to_step(self, current_step, target_step, **event_args):
    """
    Handles all navigation between steps. Validates data only when moving forward.
    """
    is_moving_forward = target_step > current_step

    # --- Data Gathering and Validation (Only for Forward Movement) ---
    if is_moving_forward:
      if current_step == 1:  # Moving from 1 to 2
        self.registration_data["favorite_language"] = self.call_js(
          "getRadioValueByName", "language"
        )
        if not self.registration_data.get("favorite_language"):
          alert("Please select a language.")
          return  # Stop navigation

      elif current_step == 2:  # Moving from 2 to 3
        self.registration_data["name"] = self.call_js("getValueById", "reg-name")
        self.registration_data["phone"] = self.call_js("getValueById", "reg-phone")
        if not self.registration_data.get("name") or not self.registration_data.get(
          "phone"
        ):
          alert("Please fill in both your name and phone number.")
          return  # Stop navigation

    # --- Navigation Logic ---
    # This now correctly hides the current modal before showing the next one.
    self.call_js("hideModal", f"modal-step{current_step}")
    self.call_js("showModal", f"modal-step{target_step}")

  def submit_registration(self, **event_args):
    """Handles the choice from Step 3."""
    choice = self.call_js("getRadioValueByName", "structure-choice")
    self.registration_data["structure_choice"] = choice

    if choice == "create":
      self.call_js("hideModal", "modal-step3")
      self.call_js("showModal", "modal-step4")

    elif choice == "join":
      join_code = self.call_js("getValueById", "join-code-input")
      if not join_code:
        alert("Please enter the structure join code.")
        return
      self.registration_data["join_code"] = join_code
      self.finalize_registration()
    else:  # Independent
      self.finalize_registration()

  def finish_registration_with_structure(self, **event_args):
    """Gathers structure details and finalizes registration."""
    structure_details = {
      "name": self.call_js("getValueById", "reg-structure-name"),
      "phone": self.call_js("getValueById", "reg-structure-phone"),
      "email": self.call_js("getValueById", "reg-structure-email"),
    }
    if not structure_details.get("name"):
      alert("Please enter a name for your new structure.")
      return

    self.registration_data["structure_details"] = structure_details
    self.finalize_registration()

  def finalize_registration(self):
    """Makes the single, consolidated server call."""
    try:
      result = anvil.server.call("register_user_and_setup", self.registration_data)
      if result.get("success"):
        alert("Registration successful!")
        open_form("Production.AudioManagerForm")
      else:
        alert(
          f"Registration failed: {result.get('message', 'An unknown error occurred.')}"
        )
    except Exception as e:
      alert(f"An error occurred during registration: {str(e)}")
