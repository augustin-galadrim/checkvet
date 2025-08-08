from ._anvil_designer import RegistrationFlowTemplate
from anvil import *
import anvil.server
import anvil.users


class RegistrationFlow(RegistrationFlowTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    # State variables to hold user data across steps
    self.user_language = "EN"  # Default value
    self.user_name = ""
    self.user_phone = ""
    self.structure_choice = "independent"  # Default value
    self.join_code = ""

    # Add a handler to show the first step when the form is opened
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Called when the form is shown. Displays the first step of the registration."""
    self.call_js("showModal", "modal-step1")

  def go_to_step(self, step_number, **event_args):
    """Handles navigation between steps, validating and saving data along the way."""
    if step_number == 2:
      # --- Moving from Step 1 (Language) to Step 2 (Info) ---
      self.user_language = self.call_js("getRadioValueByName", "language")
      if not self.user_language:
        alert("Please select a language.")
        return

      self.call_js("hideModal", "modal-step1")
      self.call_js("showModal", "modal-step2")

    elif step_number == 3:
      # --- Moving from Step 2 (Info) to Step 3 (Structure) ---
      self.user_name = self.call_js("getValueById", "reg-name")
      self.user_phone = self.call_js("getValueById", "reg-phone")
      if not self.user_name or not self.user_phone:
        alert("Please fill in both your name and phone number.")
        return

      self.call_js("hideModal", "modal-step2")
      self.call_js("showModal", "modal-step3")

    elif step_number == 1:
      # --- Going back from Step 2 to Step 1 ---
      self.call_js("hideModal", "modal-step2")
      self.call_js("showModal", "modal-step1")

  def submit_registration(self, **event_args):
    """
    Final step. Gathers all data and makes a single server call to register the user,
    handle their structure choice, and assign templates.
    """
    self.structure_choice = self.call_js("getRadioValueByName", "structure-choice")

    if self.structure_choice == "join":
      self.join_code = self.call_js("getValueById", "join-code-input")
      if not self.join_code:
        alert("Please enter the structure join code.")
        return

    if self.structure_choice == "create":
      # For this workflow, we'll open a new form to handle structure creation.
      # This keeps the registration flow clean.
      alert("You will now be taken to a new screen to create your structure.")
      # In a real scenario, you would pass the user data to the next form.
      # open_form('CreateStructureForm', user_data=self.get_registration_data())
      # For now, we will simulate completion.
      print("User chose to create a structure. This would navigate to a new form.")
      return

    try:
      # Consolidate all registration data into a single dictionary
      registration_data = {
        "name": self.user_name,
        "phone": self.user_phone,
        "favorite_language": self.user_language,
        "structure_choice": self.structure_choice,
        "join_code": self.join_code,
      }

      # --- SINGLE SERVER CALL ---
      # A new, consolidated server function should be created to handle this data.
      # This function will be responsible for:
      # 1. Calling `write_user` to save the user's info.
      # 2. If 'join', calling `join_structure_by_code`.
      # 3. Calling `assign_language_specific_base_templates`.

      # For now, we simulate the calls that would be inside the new server function.
      user = anvil.users.get_user(allow_remembered=True)

      # 1. Write basic user info
      anvil.server.call(
        "write_user",
        name=registration_data["name"],
        phone=registration_data["phone"],
        favorite_language=registration_data["favorite_language"],
        additional_info=True,
      )

      # 2. Handle structure choice
      if registration_data["structure_choice"] == "join":
        join_result = anvil.server.call(
          "join_structure_by_code", registration_data["join_code"]
        )
        if not join_result["success"]:
          alert(f"Failed to join structure: {join_result['message']}")
          return

      # 3. Assign templates based on language
      anvil.server.call(
        "assign_language_specific_base_templates",
        user,
        registration_data["favorite_language"],
      )

      alert("Registration successful!")
      open_form("Production.AudioManagerForm")

    except Exception as e:
      alert(f"An error occurred during registration: {str(e)}")
