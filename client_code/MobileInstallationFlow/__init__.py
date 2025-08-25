from ._anvil_designer import MobileInstallationFlowTemplate
from anvil import *
import anvil.server
from ..Cache import user_settings_cache
from .. import TranslationService as t
from ..LoggingClient import ClientLogger

class MobileInstallationFlow(MobileInstallationFlowTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.logger = ClientLogger(self.__class__.__name__)
    self.add_event_handler('show', self.form_show)

  def form_show(self, **event_args):
    """
    Called when the form is shown. Orchestrates the dynamic guide retrieval and rendering,
    all on the client-side.
    """
    self.logger.info("Form showing. Preparing installation guide.")
    try:
      # 1. Get user language preference from the TranslationService
      lang = t.CURRENT_LANG
      self.logger.debug(f"Using language: {lang}")

      # 2. Detect the user's environment via JavaScript
      environment = self.call_js('detect_environment')
      os = environment.get('os')
      browser = environment.get('browser')
      self.logger.debug(f"Detected environment: OS='{os}', Browser='{browser}'")

      # 3. Apply fallback logic
      # Industry standard: If on iOS, Safari is the most common and reliable target for PWA installation.
      if os == 'ios' and browser not in ['safari', 'chrome']:
        self.logger.debug(f"iOS browser '{browser}' not recognized, falling back to 'safari'.")
        browser = 'safari'
      # On Android, Chrome is the standard.
      elif os == 'android' and browser != 'chrome':
        self.logger.debug(f"Android browser '{browser}' not recognized, falling back to 'chrome'.")
        browser = 'chrome'

      # 4. Programmatically build the steps list
      steps = []
      step_index = 1
      while True:
        # Construct the translation key for the current step's title
        title_key = f"install_{os}_{browser}_step{step_index}_title"
        title = t.t(title_key)

        # Infer the number of steps: if the translation service returns the key itself,
        # it means the translation was not found, so we've reached the end of the guide.
        if title == f"<{title_key}>":
          self.logger.debug(f"Inferred end of guide. Found {len(steps)} steps for {os}/{browser}.")
          break

          # If title exists, get the text and image path
        text_key = f"install_{os}_{browser}_step{step_index}_text"
        text = t.t(text_key)

        image_path = f"_/theme/imgs/install/{lang}/{os}_{browser}_step_{step_index}.jpg"

        steps.append({
          "title": title,
          "text": text,
          "image": image_path
        })
        step_index += 1

      if not steps:
        # Handle cases where no guide is found (e.g., no keys for android_firefox)
        self.logger.warning(f"No installation guide steps found for {os}/{browser}. Aborting.")
        alert(t.t("install_guide_unavailable_alert"))
        open_form("Production.AudioManagerForm")
        return

      # 5. Pass the structured steps and translated button text to JavaScript to build the guide
      button_texts = {
        "back": t.t("install_guide_back_button"),
        "next": t.t("install_guide_next_button"),
        "finish": t.t("install_guide_finish_button"),
      }
      self.logger.info(f"Passing {len(steps)} steps to JavaScript renderer.")
      self.call_js('render_guide', steps, button_texts)

    except Exception as e:
      self.logger.error(f"An error occurred while preparing the installation guide: {str(e)}")
      alert(f"An error occurred while preparing the installation guide: {str(e)}")
      open_form("Production.AudioManagerForm")

  def installation_complete_click(self, **event_args):
    """
    Called from JavaScript when the user clicks the final "I've installed it" button.
    """
    self.logger.info("'Installation complete' button clicked. Attempting to save to server.")
    try:
      success = anvil.server.call_s("write_user", mobile_installation=True)
      if success:
        self.logger.info("Successfully recorded mobile installation on server.")
        user_settings_cache["mobile_installation"] = None
        alert("Installation recorded successfully! You can now close this tab and open the app from your home screen.")
        open_form("Production.AudioManagerForm")
      else:
        self.logger.warning("Server returned failure while recording mobile installation.")
        alert("Failed to record installation. Please try again.")
    except Exception as e:
      self.logger.error(f"An error occurred during installation recording: {str(e)}")
      alert(f"An error occurred during installation recording: {str(e)}")