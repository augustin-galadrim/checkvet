from ._anvil_designer import EN_SettingsTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class EN_Settings(EN_SettingsTemplate):
  def __init__(self, **properties):
    print("Debug: Initializing Settings form...")
    self.init_components(**properties)
    print("Debug: Form components initialized.")
    self.add_event_handler("show", self.on_form_show)

  def on_form_show(self, **event_args):
    """
    Runs after the form is visible. We will retrieve the user data,
    fill the fields using self.call_js(...), and load the modals.
    """
    print("Debug: The Settings form is now visible. Loading veterinarian data...")
    self.load_vet_data()
    print("Debug: Veterinarian data loaded into the form.")
    print("Debug: Loading the structure modal data...")
    self.load_structure_modal()
    print("Debug: Structure modal data loaded.")
    print("Debug: Loading the preferred language modal data...")
    self.load_favorite_language_modal()
    print("Debug: Preferred language modal data loaded.")

  def refresh_session_relay(self, **event_args):
    """Relay method for refreshing the session when called from JS"""
    try:
      return anvil.server.call("check_and_refresh_session")
    except anvil.server.SessionExpiredError:
      anvil.server.reset_session()
      return anvil.server.call("check_and_refresh_session")
    except Exception as e:
      print(f"[DEBUG] Error in refresh_session_relay: {str(e)}")
      return False

  def load_vet_data(self):
    """
    Retrieves user data from the server and fills the fields
    in the HTML form via self.call_js(...).
    """
    try:
      current_user = anvil.users.get_user()
      if not current_user:
        print("Debug: No user logged in.")
        alert("No user is currently logged in.")
        return

      print(f"Debug: Current user retrieved: {current_user}")

      try:
        user_data = anvil.server.call("read_user")  # e.g. { name, email, phone, structure, signature_image, ... }
      except anvil.server.SessionExpiredError:
        anvil.server.reset_session()
        user_data = anvil.server.call("read_user")

      print(f"Debug: User data from server: {user_data}")

      if user_data:
        # For text fields:
        self.call_js("setValueById", "name", user_data.get("name", ""))
        self.call_js("setValueById", "email", user_data.get("email", ""))
        self.call_js("setValueById", "phone", user_data.get("phone", ""))
        # Set the structure: update the hidden input and display button
        structure = user_data.get("structure")
        if not structure:
          structure = "Independent"
        self.call_js("setValueById", "structure", structure)
        self.call_js("setButtonTextById", "structure-button", structure)

        # Set the preferred language: update the hidden input and display button.
        favorite_language = user_data.get("favorite_language")
        if not favorite_language:
          favorite_language = "EN"
        mapping = {"FR": "French", "EN": "English", "ES": "Spanish", "DE": "German"}
        display_text = mapping.get(favorite_language, "English")
        self.call_js("setValueById", "favorite-language", favorite_language)
        self.call_js("setButtonTextById", "favorite-language-button", display_text)

        # For the checkbox
        self.call_js("setCheckedById", "supervisor", user_data.get("supervisor", False))

        # File labels for existing images
        if user_data.get("signature_image"):
          self.call_js("setFileNameById", "signature", user_data["signature_image"].name)
        if user_data.get("report_header_image"):
          self.call_js("setFileNameById", "report-header", user_data["report_header_image"].name)
        if user_data.get("report_footer_image"):
          self.call_js("setFileNameById", "report-footer", user_data["report_footer_image"].name)

        # Check if the user is an admin and show/hide button accordingly
        is_admin = self.is_admin_user()
        self.call_js("showAdminButton", is_admin)
      else:
        alert("Unable to retrieve user data. Please contact support.")
    except Exception as e:
      print(f"Debug: Error in load_vet_data: {str(e)}")
      alert(f"An error occurred while loading the data: {str(e)}")

  def load_structure_modal(self):
    """
    Uses the relay function to retrieve structures from the server and
    fills the modal with the structure names.
    """
    try:
      try:
        structures = relay_read_structures()
      except anvil.server.SessionExpiredError:
        anvil.server.reset_session()
        structures = relay_read_structures()

      print(f"Debug: Structures retrieved: {structures}")
      # Extract the structure name for each structure
      options = [s['structure'] for s in structures]
      # Ensure "Independent" is always available
      if "Independent" not in options:
        options.append("Independent")
      # Get the user's current structure, or use "Independent" as default
      try:
        user_data = anvil.server.call("read_user")
      except anvil.server.SessionExpiredError:
        anvil.server.reset_session()
        user_data = anvil.server.call("read_user")

      current_structure = user_data.get("structure") if user_data and user_data.get("structure") else "Independent"
      # Update the hidden input and structure button
      self.call_js("setValueById", "structure", current_structure)
      self.call_js("setButtonTextById", "structure-button", current_structure)
      # Fill the modal with options and highlight the current value
      self.call_js("populateStructureModal", options, current_structure)
    except Exception as e:
      print(f"Debug: Error loading structure modal: {str(e)}")
      alert(f"An error occurred while loading structures: {str(e)}")

  def load_favorite_language_modal(self):
    """
    Fills the preferred language modal with predefined options.
    """
    try:
      options = [
        {"display": "French", "value": "FR"},
        {"display": "English", "value": "EN"},
        {"display": "Spanish", "value": "ES"},
        {"display": "German", "value": "DE"}
      ]

      try:
        user_data = anvil.server.call("read_user")
      except anvil.server.SessionExpiredError:
        anvil.server.reset_session()
        user_data = anvil.server.call("read_user")

      current_fav = user_data.get("favorite_language") if user_data and user_data.get("favorite_language") else "EN"
      mapping = {"FR": "French", "EN": "English", "ES": "Spanish", "DE": "German"}
      display_text = mapping.get(current_fav, "English")
      self.call_js("setValueById", "favorite-language", current_fav)
      self.call_js("setButtonTextById", "favorite-language-button", display_text)
      self.call_js("populateFavoriteLanguageModal", options, current_fav)
    except Exception as e:
      print(f"Debug: Error loading preferred language modal: {str(e)}")
      alert(f"An error occurred while loading preferred languages: {str(e)}")

  def submit_click(self, **event_args):
    """
    Called when the user clicks "Update Settings".
    """
    try:
      print("Debug: Submit button clicked. Retrieving form data...")

      form_data = {
        "name": self.call_js("getValueById", "name"),
        "phone": self.call_js("getValueById", "phone"),
        "structure": self.call_js("getValueById", "structure"),
        "supervisor": self.call_js("getCheckedById", "supervisor"),
        "favorite_language": self.call_js("getValueById", "favorite-language"),
      }

      # Get file data for each field if a file was selected
      signature_file = self.get_file_data("signature")
      if signature_file:
        form_data["signature_image"] = signature_file

      report_header_file = self.get_file_data("report-header")
      if report_header_file:
        form_data["report_header_image"] = report_header_file

      report_footer_file = self.get_file_data("report-footer")
      if report_footer_file:
        form_data["report_footer_image"] = report_footer_file

      print(f"Debug: Form data retrieved: {form_data}")

      # Call the server to update the user record
      try:
        success = anvil.server.call("write_user", **form_data)
      except anvil.server.SessionExpiredError:
        anvil.server.reset_session()
        success = anvil.server.call("write_user", **form_data)

      print(f"Debug: Server response for update: {success}")

      if success:
        self.call_js("displayBanner", "Veterinarian settings have been successfully updated!", "success")
        open_form("StartupForm")
      else:
        alert("Failed to update veterinarian settings. Please try again.")
    except Exception as e:
      print(f"Debug: Error during submission: {str(e)}")
      alert(f"An error occurred during submission: {str(e)}")

  def cancel_click(self, **event_args):
    """
    Called when the user clicks "Cancel".
    """
    open_form("Production.AudioManagerForm")

  def logout_click(self, **event_args):
    """
    Called when the user clicks "Logout".
    """
    anvil.users.logout()
    open_form('StartupForm')

  def get_file_data(self, input_id):
    """
    Retrieves file data from JavaScript and creates a BlobMedia.
    """
    file_data_promise = self.call_js("getFileData", input_id)
    if file_data_promise:
      try:
        file_data = file_data_promise
        return anvil.BlobMedia(
          content_type=file_data["content_type"],
          content=file_data["content"],
          name=file_data["name"]
        )
      except Exception as e:
        print(f"Debug: Error reading file data for {input_id}: {e}")
    return None

  def openProduction(self, **event_args):
    """Called from the top tab 'Production'"""
    open_form("Production.AudioManagerForm")

  def openTemplates(self, **event_args):
    """Called from the top tab 'Templates/AI'"""
    open_form("Templates.EN_Templates")

  def openArchives(self, **event_args):
    """Called from the top tab 'Archives'"""
    current_user = anvil.users.get_user()
    if current_user['supervisor']:
      open_form("Archives.EN_ArchivesSecretariat")
    else:
      open_form("Archives.EN_Archives")

  def openMicrophoneTest(self, **event_args):
    """Called when user clicks 'Test my microphone'."""
    open_form("MicrophoneTest")

  def check_structure_authorization(self, structure, **event_args):
    """
    Checks if the user is authorized for the given structure.
    """
    return relay_check_vet_authorization(structure)

  def is_admin_user(self):
    """Check if the current user has admin privileges."""
    try:
      current_user = anvil.users.get_user()
      if not current_user:
        print("Debug: No current user found")
        return False

      admin_emails = ["cristobal.navarro@me.com", "biffy071077@gmail.com"]

      # Use square bracket notation to access properties of LiveObjectProxy
      try:
        user_email = current_user["email"].lower()
        print(f"Debug: User email: {user_email}")
        is_admin = user_email in [email.lower() for email in admin_emails]
        print(f"Debug: Is admin: {is_admin}")
        return is_admin
      except (KeyError, AttributeError):
        print("Debug: Could not access user email")
        return False
    except Exception as e:
      print(f"Debug: Error checking admin status: {str(e)}")
      return False

  def openAdmin(self, **event_args):
    """Opens the Admin form when clicked."""
    open_form("Admin")

# Relay functions
def relay_read_structures():
  try:
    return anvil.server.call("read_structures")
  except anvil.server.SessionExpiredError:
    anvil.server.reset_session()
    return anvil.server.call("read_structures")

def relay_check_vet_authorization(structure):
  try:
    return anvil.server.call("check_vet_authorization", structure)
  except anvil.server.SessionExpiredError:
    anvil.server.reset_session()
    return anvil.server.call("check_vet_authorization", structure)
