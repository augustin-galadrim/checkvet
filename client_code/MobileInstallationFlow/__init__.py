from ._anvil_designer import MobileInstallationFlowTemplate
from anvil import *
import anvil.server
from ..Cache import user_settings_cache
from .. import TranslationService as t
from ..LoggingClient import ClientLogger

# This constant is now the single source of truth for the number of steps.
GUIDE_STEP_COUNT = 3


class MobileInstallationFlow(MobileInstallationFlowTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.logger = ClientLogger(self.__class__.__name__)
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """
    Builds the installation guide using a hardcoded step count.
    No server call is needed to determine the guide structure.
    """
    self.logger.info(
      f"Form showing. Preparing installation guide with a fixed step count of {GUIDE_STEP_COUNT}."
    )
    try:
      lang = t.CURRENT_LANG
      self.logger.debug(f"Using language: {lang}")

      environment = self.call_js("detect_environment")
      os = environment.get("os")
      browser = environment.get("browser")
      self.logger.debug(f"Detected environment: OS='{os}', Browser='{browser}'")

      # Apply fallback logic for browser/OS combination
      if os == "ios" and browser not in ["safari", "chrome"]:
        self.logger.debug(
          f"iOS browser '{browser}' not recognized, falling back to 'safari'."
        )
        browser = "safari"
      elif os == "android" and browser != "chrome":
        self.logger.debug(
          f"Android browser '{browser}' not recognized, falling back to 'chrome'."
        )
        browser = "chrome"

      # Build the steps list based on the hardcoded constant
      steps = []
      for i in range(1, GUIDE_STEP_COUNT + 1):
        base_key = f"install_{os}_{browser}_step{i}"

        steps.append({
          "title": t.t(f"{base_key}_title"),
          "text": t.t(f"{base_key}_text"),
          "image": f"_/theme/imgs/install/{lang}/{os}_{browser}_step_{i}.jpg",
        })

      # Pass the steps and translated button text to JavaScript
      button_texts = {
        "back": t.t("install_guide_back_button"),
        "next": t.t("install_guide_next_button"),
        "finish": t.t("install_guide_finish_button"),
      }
      self.logger.info(f"Passing {len(steps)} steps to JavaScript renderer.")
      self.call_js("render_guide", steps, button_texts)

    except Exception as e:
      self.logger.error(
        f"An error occurred while preparing the installation guide: {str(e)}"
      )
      alert(f"An error occurred while preparing the installation guide: {str(e)}")
      open_form("Production.AudioManagerForm")

  def installation_complete_click(self, **event_args):
    """
    Called from JavaScript when the user clicks the final "I've installed it" button.
    This function's logic does not change.
    """
    self.logger.info(
      "'Installation complete' button clicked. Attempting to save to server."
    )
    try:
      success = anvil.server.call_s("write_user", mobile_installation=True)
      if success:
        self.logger.info("Successfully recorded mobile installation on server.")
        user_settings_cache["mobile_installation"] = None
        alert(
          "Installation recorded successfully! You can now close this tab and open the app from your home screen."
        )
        open_form("Production.AudioManagerForm")
      else:
        self.logger.warning(
          "Server returned failure while recording mobile installation."
        )
        alert("Failed to record installation. Please try again.")
    except Exception as e:
      self.logger.error(f"An error occurred during installation recording: {str(e)}")
      alert(f"An error occurred during installation recording: {str(e)}")
