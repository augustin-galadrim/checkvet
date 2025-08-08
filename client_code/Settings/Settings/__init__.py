from ._anvil_designer import SettingsTemplate
from anvil import *
import anvil.server
import anvil.users
from ... import TranslationService as t


class Settings(SettingsTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.add_event_handler("show", self.on_form_show)

  def on_form_show(self, **event_args):
    """
    Called when the form is shown. Fetches user data and populates the form fields
    and modals with up-to-date information.
    """
    print("Settings form is visible. Loading user and modal data...")
    self.load_vet_data()
    self.load_structure_modal()
    self.load_favorite_language_modal()
    print("Data loading complete.")

  def refresh_session_relay(self, **event_args):
    """Relay method for refreshing the session when called from JS."""
    try:
      return anvil.server.call("check_and_refresh_session")
    except anvil.server.SessionExpiredError:
      anvil.server.reset_session()
      return anvil.server.call("check_and_refresh_session")
    except Exception as e:
      print(f"[ERROR] Session refresh failed: {str(e)}")
      return False

  def load_vet_data(self):
    """
    Retrieves the current user's data from the server and updates the UI.
    """
    try:
      user_data = anvil.server.call("read_user")
      if not user_data:
        alert("Could not retrieve your user data. Please try logging in again.")
        return

      # Populate text fields
      self.call_js("setValueById", "name", user_data.get("name", ""))
      self.call_js("setValueById", "email", user_data.get("email", ""))
      self.call_js("setValueById", "phone", user_data.get("phone", ""))

      # Handle the 'structure' field with translation for the 'independent' key
      structure_value = user_data.get("structure", "independent")
      if structure_value == "independent":
        display_text = t.t("independent_structure_label")
      else:
        display_text = structure_value

      self.call_js("setValueById", "structure", structure_value)
      self.call_js("setButtonTextById", "structure-button", display_text)

      # Handle favorite language
      favorite_language = user_data.get("favorite_language", "EN")
      lang_map = {"FR": "Français", "EN": "English"}
      lang_display_text = lang_map.get(favorite_language, "English")
      self.call_js("setValueById", "favorite-language", favorite_language)
      self.call_js("setButtonTextById", "favorite-language-button", lang_display_text)

      # Handle checkbox
      self.call_js("setCheckedById", "supervisor", user_data.get("supervisor", False))

      # Set file names for existing media
      if user_data.get("signature_image"):
        self.call_js("setFileNameById", "signature", user_data["signature_image"].name)
      if user_data.get("report_header_image"):
        self.call_js(
          "setFileNameById", "report-header", user_data["report_header_image"].name
        )
      if user_data.get("report_footer_image"):
        self.call_js(
          "setFileNameById", "report-footer", user_data["report_footer_image"].name
        )

      # Show/hide admin button
      self.call_js("showAdminButton", self.is_admin_user())

    except Exception as e:
      alert(f"An error occurred while loading your data: {str(e)}")

  def load_structure_modal(self):
    """
    Fetches all available structures and populates the selection modal.
    """
    try:
      # This server call should return a list of all structure names
      structures = relay_read_structures()

      # The server returns dicts, so we extract the names
      structure_names = [s["structure"] for s in structures]

      # Add the 'independent' option as a dictionary for the JS
      options = [
        {
          "key": "independent",
          "display": t.t("independent_structure_label"),
        }
      ]
      options.extend([{"key": name, "display": name} for name in structure_names])

      current_structure_key = anvil.server.call("get_user_info", "structure")

      # Populate the modal with the options and the user's current selection
      self.call_js("populateStructureModal", options, current_structure_key)
    except Exception as e:
      alert(f"An error occurred while loading structures: {str(e)}")

  def load_favorite_language_modal(self):
    """
    Populates the favorite language selection modal with predefined options.
    """
    options = [
      {"display": "Français", "value": "FR"},
      {"display": "English", "value": "EN"},
    ]
    current_fav = anvil.server.call("get_user_info", "favorite_language") or "EN"
    self.call_js("populateFavoriteLanguageModal", options, current_fav)

  def submit_click(self, **event_args):
    """
    Gathers all data from the form and calls the server to update the user's record.
    """
    try:
      form_data = {
        "name": self.call_js("getValueById", "name"),
        "phone": self.call_js("getValueById", "phone"),
        "structure": self.call_js("getValueById", "structure"),
        "supervisor": self.call_js("getCheckedById", "supervisor"),
        "favorite_language": self.call_js("getValueById", "favorite-language"),
      }

      # Handle file uploads if new files were selected
      for field in ["signature", "report-header", "report-footer"]:
        file = self.get_file_data(field)
        if file:
          form_data[f"{field.replace('-', '_')}_image"] = file

      success = anvil.server.call("write_user", **form_data)

      if success:
        self.call_js("displayBanner", "Settings updated successfully!", "success")
        self.load_vet_data()  # Refresh the form to show the saved changes
      else:
        alert("Failed to update settings. Please try again.")
    except Exception as e:
      alert(f"An error occurred during submission: {str(e)}")

  def cancel_click(self, **event_args):
    """Discards any changes by reloading the user data from the server."""
    self.load_vet_data()
    self.call_js("displayBanner", "Changes have been discarded.", "info")

  def logout_click(self, **event_args):
    """Logs the user out and returns to the startup form."""
    anvil.users.logout()
    open_form("StartupForm")

  def get_file_data(self, input_id):
    """Retrieves file data from a file input element via JavaScript."""
    file_data = self.call_js("getFileData", input_id)
    if file_data:
      return anvil.BlobMedia(
        content_type=file_data["content_type"],
        content=file_data["content"],
        name=file_data["name"],
      )
    return None

  def openMicrophoneTest(self, **event_args):
    """Navigates to the microphone test form."""
    open_form("Settings.MicrophoneTest")

  def show_install_guide_click(self, **event_args):
    """Navigates to the mobile installation guide form."""
    open_form("MobileInstallationFlow")

  def is_admin_user(self):
    """Checks if the current user is in the hardcoded list of administrators."""
    user = anvil.users.get_user()
    if not user:
      return False

    admin_emails = [
      "cristobal.navarro@me.com",
      "biffy071077@gmail.com",
      "augustincramer.galadrim@gmail.com",
    ]
    return user["email"].lower() in admin_emails

  def openAdmin(self, **event_args):
    """Navigates to the Administration panel."""
    open_form("Settings.Admin")


# Relay function to ensure server calls can be made after a session refresh.
def relay_read_structures():
  try:
    return anvil.server.call("read_structures")
  except anvil.server.SessionExpiredError:
    anvil.server.reset_session()
    return anvil.server.call("read_structures")
