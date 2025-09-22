from ._anvil_designer import SettingsTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.js
from ... import TranslationService as t
from ...Cache import user_settings_cache, reports_cache_manager, template_cache_manager
from ...AppEvents import events
from ...AuthHelpers import setup_auth_handlers
from ...LoggingClient import ClientLogger


class Settings(SettingsTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    setup_auth_handlers(self)
    events.subscribe("language_changed", self.update_ui_texts)
    self.add_event_handler("show", self.on_form_show)
    self.logger = ClientLogger(self.__class__.__name__)

  def on_form_show(self, **event_args):
    self.header_nav_1.active_tab = "Settings"
    self.update_ui_texts()
    self.load_vet_data()
    self.load_favorite_language_modal()

  def update_ui_texts(self, **event_args):
    """Sets all translatable text on the form."""
    self.call_js(
      "setElementText", "settings-h2-vetInfoTitle", t.t("settings_h2_vetInfoTitle")
    )
    self.call_js("setElementText", "settings-label-name", t.t("settings_label_name"))
    self.call_js("setElementText", "settings-label-phone", t.t("settings_label_phone"))
    self.call_js("setElementText", "settings-label-email", t.t("settings_label_email"))
    self.call_js("setElementText", "settings-h2-orgTitle", t.t("settings_h2_orgTitle"))
    self.call_js(
      "setElementText", "settings-label-structure", t.t("settings_label_structure")
    )
    self.call_js(
      "setElementText",
      "settings-button-joinStructure",
      t.t("settings_button_joinStructure"),
    )
    self.call_js(
      "setElementText",
      "settings-span-supervisorMessage",
      t.t("settings_span_supervisorMessage"),
    )
    self.call_js(
      "setElementText", "settings-label-joinCode", t.t("settings_label_joinCode")
    )
    self.call_js(
      "setElementText", "settings-h2-prefsTitle", t.t("settings_h2_prefsTitle")
    )
    self.call_js(
      "setElementText", "settings-label-favLanguage", t.t("settings_label_favLanguage")
    )
    self.call_js(
      "setElementText", "settings-h2-toolsTitle", t.t("settings_h2_toolsTitle")
    )
    self.call_js(
      "setElementText", "settings-button-micTest", t.t("settings_button_micTest")
    )
    self.call_js(
      "setElementText",
      "settings-button-installGuide",
      t.t("settings_button_installGuide"),
    )
    self.call_js(
      "setElementText", "settings-button-cancel", t.t("settings_button_cancel")
    )
    self.call_js(
      "setElementText", "settings-button-submit", t.t("settings_button_submit")
    )
    self.call_js(
      "setElementText", "settings-button-admin", t.t("settings_button_admin")
    )
    self.call_js(
      "setElementText", "settings-button-logout", t.t("settings_button_logout")
    )
    self.call_js(
      "setElementText", "settings-h3-joinModalTitle", t.t("settings_h3_joinModalTitle")
    )
    self.call_js(
      "setElementText", "settings-p-joinModalDesc", t.t("settings_p_joinModalDesc")
    )
    self.call_js(
      "setElementText",
      "settings-label-joinCodeModal",
      t.t("settings_label_joinCodeModal"),
    )
    self.call_js(
      "setElementText",
      "settings-button-submitJoinCode",
      t.t("settings_button_submitJoinCode"),
    )
    self.call_js(
      "setElementText",
      "settings-h3-favLangModalTitle",
      t.t("settings_h3_favLangModalTitle"),
    )
    self.call_js(
      "setElementText",
      "settings-h2-pdfBrandingTitle",
      t.t("settings_h2_pdfBrandingTitle"),
    )
    self.call_js(
      "setElementText", "settings-h3-mySignature", t.t("settings_h3_mySignature")
    )
    self.call_js(
      "setElementText", "settings-p-signatureHelp", t.t("settings_p_signatureHelp")
    )
    self.call_js(
      "setElementText",
      "settings-label-uploadSignature",
      t.t("settings_label_uploadSignature"),
    )
    self.call_js(
      "setElementText",
      "settings-h3-structureBranding",
      t.t("settings_h3_structureBranding"),
    )
    self.call_js(
      "setElementText", "settings-p-headerHelp", t.t("settings_p_headerHelp")
    )
    self.call_js(
      "setElementText",
      "settings-label-uploadHeader",
      t.t("settings_label_uploadHeader"),
    )
    self.call_js(
      "setElementText", "settings-p-footerHelp", t.t("settings_p_footerHelp")
    )
    self.call_js(
      "setElementText",
      "settings-label-uploadFooter",
      t.t("settings_label_uploadFooter"),
    )
    self.call_js(
      "setElementText",
      "settings-p-brandingManagedBy",
      t.t("settings_p_brandingManagedBy"),
    )
    self.call_js(
      "setElementText", "signature-no-asset-msg", t.t("settings_msg_noSignature")
    )
    self.call_js("setElementText", "header-no-asset-msg", t.t("settings_msg_noHeader"))
    self.call_js("setElementText", "footer-no-asset-msg", t.t("settings_msg_noFooter"))
    self.call_js("setElementText", "signature-delete-btn", t.t("settings_btn_delete"))
    self.call_js("setElementText", "header-delete-btn", t.t("settings_btn_delete"))
    self.call_js("setElementText", "footer-delete-btn", t.t("settings_btn_delete"))

  def load_vet_data(self):
    """Retrieves the current user's data and their active assets, then updates the UI."""
    try:
      # This single call now gets all the data we need for this form
      user_data = anvil.server.call_s("read_user")
      if not user_data:
        alert("Could not retrieve your user data.")
        return

      # Populate standard user fields
      self.call_js("setValue", "settings-input-name", user_data.get("name", ""))
      self.call_js("setValue", "settings-input-email", user_data.get("email", ""))
      self.call_js("setValue", "settings-input-phone", user_data.get("phone", ""))

      # Populate structure and supervisor info
      is_independent = user_data.get("is_independent", True)
      display_text = (
        t.t("settings_structure_independent")
        if is_independent
        else user_data.get("structure")
      )
      self.call_js("setValue", "settings-input-structureDisplay", display_text)
      self.call_js("toggleJoinButton", is_independent)

      is_supervisor = user_data.get("supervisor", False)
      join_code = user_data.get("join_code")
      self.call_js("updateSupervisorView", is_supervisor, join_code)
      self.call_js("showAdminButton", self.is_admin_user())

      # Populate language info
      favorite_language = user_data.get("favorite_language", "en")
      lang_map = {
        "fr": t.t("language_fr"),
        "en": t.t("language_en"),
        "es": t.t("language_es"),
        "de": t.t("language_de"),
        "nl": t.t("language_nl"),
      }
      lang_display_text = lang_map.get(favorite_language, t.t("language_en"))
      self.call_js("setValue", "favorite-language", favorite_language)
      self.call_js("setElementText", "settings-button-favLanguage", lang_display_text)

      # ======================= NEW ASSET LOGIC =======================
      # Fetch and display the user's active branding assets
      active_assets_data = anvil.server.call("get_active_assets_for_user_with_ids")
      self.logger.info(f"Recieved assets: {active_assets_data}")
      self.active_asset_ids = {
        "signature": active_assets_data.get("signature").get("id")
        if active_assets_data.get("signature") is not None
        else None,
        "header": active_assets_data.get("header").get("id")
        if active_assets_data.get("header") is not None
        else None,
        "footer": active_assets_data.get("footer").get("id")
        if active_assets_data.get("footer") is not None
        else None,
      }
      self._update_asset_previews(active_assets_data)

      # Determine if the structure branding controls should be enabled
      can_edit_structure_branding = is_independent or is_supervisor
      self.call_js("toggleStructureBrandingControls", can_edit_structure_branding)
      # =============================================================

    except Exception as e:
      alert(f"An error occurred while loading your data: {str(e)}")

  def _update_asset_previews(self, assets):
    """Helper to update the src of preview images and visibility of messages."""

    signature_asset = (
      assets.get("signature").get("file")
      if assets.get("signature") is not None
      else None
    )
    header_asset = (
      assets.get("header").get("file") if assets.get("header") is not None else None
    )
    footer_asset = (
      assets.get("footer").get("file") if assets.get("footer") is not None else None
    )

    # Pass the URL string (or None) to the JavaScript function.
    self.call_js(
      "updateAssetPreview",
      "signature",
      signature_asset.get_url() if signature_asset else None,
    )
    self.call_js(
      "updateAssetPreview", "header", header_asset.get_url() if header_asset else None
    )
    self.call_js(
      "updateAssetPreview", "footer", footer_asset.get_url() if footer_asset else None
    )

  def attempt_to_join_structure(self, join_code, **event_args):
    """Called from JS to attempt joining a structure."""
    try:
      result = anvil.server.call_s("join_structure_as_vet", join_code)
      if result.get("success"):
        self.load_vet_data()
      return result
    except Exception as e:
      return {"success": False, "message": str(e)}

  def handle_asset_upload(self, file, asset_type, **event_args):
    """
    A single, generic handler called from JavaScript when any asset file is selected.
    """
    if not file:
      return

    try:
      anvil_media_file = anvil.js.to_media(file)
      # Determine a user-friendly name for the asset
      name_map = {
        "signature": "User Signature",
        "header": "Structure Header",
        "footer": "Structure Footer",
      }
      asset_name = name_map.get(asset_type, "Uploaded Asset")

      # Call the server function
      anvil.server.call("upload_asset", anvil_media_file, asset_type, asset_name)

      # Provide feedback and refresh the UI
      self.call_js(
        "displayBanner", f"{asset_type.capitalize()} updated successfully!", "success"
      )
      self.load_vet_data()  # Refresh to show the new image
    except Exception as e:
      self.call_js("displayBanner", f"Error uploading {asset_type}: {e}", "error")
      self.logger.error(f"Error during {asset_type} upload: {e}")

  def load_favorite_language_modal(self):
    """Populates the favorite language selection modal."""
    options = [
      {"display": t.t("language_fr"), "value": "fr"},
      {"display": t.t("language_en"), "value": "en"},
      {"display": t.t("language_es"), "value": "es"},
      {"display": t.t("language_de"), "value": "de"},
      {"display": t.t("language_nl"), "value": "nl"},
    ]
    current_fav = self.call_js("getValueById", "favorite-language") or "en"
    self.call_js("populateFavoriteLanguageModal", options, current_fav)

  def delete_asset_click(self, asset_type, **event_args):
    """Called from JavaScript when a delete button is clicked."""
    asset_id = self.active_asset_ids.get(asset_type)

    if not asset_id:
      self.call_js("displayBanner", f"No active {asset_type} to delete.", "info")
      return

    confirm_text = t.t("settings_confirm_delete_asset", asset_type=asset_type)
    if confirm(confirm_text):
      try:
        success = anvil.server.call("delete_asset", asset_id)
        if success:
          self.call_js(
            "displayBanner",
            f"{asset_type.capitalize()} deleted successfully.",
            "success",
          )
          self.load_vet_data()  # Refresh the UI
        else:
          self.call_js("displayBanner", f"Failed to delete {asset_type}.", "error")
      except Exception as e:
        self.call_js("displayBanner", f"An error occurred: {e}", "error")
        self.logger.error(f"Error deleting asset ID {asset_id}: {e}")

  def submit_click(self, **event_args):
    """Gathers data, saves it, and reloads translations if language changed."""
    try:
      form_data = {
        "name": self.call_js("getValueById", "settings-input-name"),
        "phone": self.call_js("getValueById", "settings-input-phone"),
        "favorite_language": self.call_js("getValueById", "favorite-language"),
      }
      new_language = form_data.get("favorite_language")
      success = anvil.server.call_s("write_user", **form_data)
      if success:
        user_settings_cache["language"] = None
        if new_language != t.CURRENT_LANG:
          t.load_language(new_language)
          events.publish("language_changed")
        self.call_js("displayBanner", t.t("settings_update_success_banner"), "success")
        self.load_vet_data()
      else:
        alert(t.t("settings_update_fail_alert"))
    except Exception as e:
      alert(f"{t.t('settings_submit_error_alert')}: {str(e)}")

  def cancel_click(self, **event_args):
    """Discards changes by reloading user data."""
    self.load_vet_data()
    self.call_js("displayBanner", t.t("settings_cancel_banner"), "info")

  def logout_click(self, **event_args):
    """Logs the user out."""
    reports_cache_manager.invalidate()
    template_cache_manager.invalidate()
    for key in user_settings_cache:
      user_settings_cache[key] = None

    anvil.users.logout()
    open_form("StartupForm")

  def openMicrophoneTest(self, **event_args):
    """Navigates to the microphone test form."""
    open_form("Settings.MicrophoneTest")

  def show_install_guide_click(self, **event_args):
    """Navigates to the mobile installation guide form."""
    open_form("MobileInstallationFlow")

  def is_admin_user(self):
    """Checks if the current user is an administrator."""
    user = anvil.users.get_user()
    if not user:
      return False
    admin_emails = [
      "augustincramer.galadrim@gmail.com",
      "biffy071077@gmail.com",
      "navetl@yahoo.com",
    ]
    return user["email"].lower() in admin_emails

  def openAdmin(self, **event_args):
    """Navigates to the Administration panel."""
    open_form("Settings.Admin")
