from ._anvil_designer import RegistrationFlowTemplate
from anvil import *
import anvil.server
import anvil.users
from ..Cache import user_settings_cache
from .. import TranslationService as t
from ..AppEvents import events


class RegistrationFlow(RegistrationFlowTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.registration_data = {}
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Called when the form is shown. Displays the first step in the browser's language."""
    browser_lang = self.call_js("getBrowserLanguage")
    t.load_language(browser_lang)

    self.call_js("selectLanguageRadio", browser_lang)

    self.update_ui_texts()
    self.call_js("attachRegistrationEvents")
    self.call_js("showModal", "modal-step1")

  def update_ui_texts(self):
    """Sets all translatable text on the form based on the currently loaded language."""
    self.call_js("setElementText", "regFlow-h2-langTitle", t.t("regFlow_h2_langTitle"))
    self.call_js("setElementText", "regFlow-p-langDesc", t.t("regFlow_p_langDesc"))
    self.call_js("setElementText", "regFlow-span-langFr", t.t("language_fr"))
    self.call_js("setElementText", "regFlow-span-langEn", t.t("language_en"))
    self.call_js(
      "setElementText", "regFlow-button-langNext", t.t("regFlow_button_next")
    )
    self.call_js("setElementText", "regFlow-h2-infoTitle", t.t("regFlow_h2_infoTitle"))
    self.call_js("setElementText", "regFlow-p-infoDesc", t.t("regFlow_p_infoDesc"))
    self.call_js("setElementText", "regFlow-label-name", t.t("regFlow_label_name"))
    self.call_js("setElementText", "regFlow-label-phone", t.t("regFlow_label_phone"))
    self.call_js(
      "setElementText", "regFlow-button-infoBack", t.t("regFlow_button_back")
    )
    self.call_js(
      "setElementText", "regFlow-button-infoNext", t.t("regFlow_button_next")
    )
    self.call_js(
      "setElementText", "regFlow-h2-structTitle", t.t("regFlow_h2_structTitle")
    )
    self.call_js("setElementText", "regFlow-p-structDesc", t.t("regFlow_p_structDesc"))
    self.call_js(
      "setElementText", "regFlow-span-structIndep", t.t("regFlow_span_structIndep")
    )
    self.call_js(
      "setElementText", "regFlow-span-structJoin", t.t("regFlow_span_structJoin")
    )
    self.call_js(
      "setElementText", "regFlow-span-structCreate", t.t("regFlow_span_structCreate")
    )
    self.call_js(
      "setElementText", "regFlow-label-joinCode", t.t("regFlow_label_joinCode")
    )
    self.call_js(
      "setPlaceholder", "join-code-input", t.t("regFlow_placeholder_joinCode")
    )
    self.call_js(
      "setElementText", "regFlow-button-structBack", t.t("regFlow_button_back")
    )
    self.update_step3_button_text()
    self.call_js(
      "setElementText", "regFlow-h2-createTitle", t.t("regFlow_h2_createTitle")
    )
    self.call_js("setElementText", "regFlow-p-createDesc", t.t("regFlow_p_createDesc"))
    self.call_js(
      "setElementText", "regFlow-label-structName", t.t("regFlow_label_structName")
    )
    self.call_js(
      "setElementText", "regFlow-label-structPhone", t.t("regFlow_label_structPhone")
    )
    self.call_js(
      "setElementText", "regFlow-label-structEmail", t.t("regFlow_label_structEmail")
    )
    self.call_js(
      "setElementText", "regFlow-button-createBack", t.t("regFlow_button_back")
    )
    self.call_js(
      "setElementText", "regFlow-button-createFinish", t.t("regFlow_button_finish")
    )

  def update_step3_button_text(self, **event_args):
    """Dynamically updates the text of the main button in step 3."""
    choice = self.call_js("getRadioValueByName", "structure-choice")
    button_text = (
      t.t("regFlow_button_next") if choice == "create" else t.t("regFlow_button_finish")
    )
    self.call_js("setElementText", "regFlow-button-structFinish", button_text)

  def go_to_step(self, current_step, target_step, **event_args):
    is_moving_forward = target_step > current_step

    if is_moving_forward:
      if current_step == 1:
        chosen_lang = self.call_js("getRadioValueByName", "language")
        if not chosen_lang:
          alert(t.t("regFlow_alert_langRequired"))
          return
        self.registration_data["favorite_language"] = chosen_lang
        t.load_language(chosen_lang)
        self.update_ui_texts()

      elif current_step == 2:
        self.registration_data["name"] = self.call_js("getValueById", "reg-name")
        self.registration_data["phone"] = self.call_js("getValueById", "reg-phone")
        if not self.registration_data.get("name") or not self.registration_data.get(
          "phone"
        ):
          alert(t.t("regFlow_alert_infoRequired"))
          return

    self.call_js("hideModal", f"modal-step{current_step}")
    self.call_js("showModal", f"modal-step{target_step}")

  def submit_registration(self, **event_args):
    choice = self.call_js("getRadioValueByName", "structure-choice")
    self.registration_data["structure_choice"] = choice

    if choice == "create":
      self.call_js("hideModal", "modal-step3")
      self.call_js("showModal", "modal-step4")
    elif choice == "join":
      join_code = self.call_js("getValueById", "join-code-input")
      if not join_code:
        alert(t.t("regFlow_alert_joinCodeRequired"))
        return
      self.registration_data["join_code"] = join_code
      self.finalize_registration()
    else:
      self.finalize_registration()

  def finish_registration_with_structure(self, **event_args):
    structure_details = {
      "name": self.call_js("getValueById", "reg-structure-name"),
      "phone": self.call_js("getValueById", "reg-structure-phone"),
      "email": self.call_js("getValueById", "reg-structure-email"),
    }
    if not structure_details.get("name"):
      alert(t.t("regFlow_alert_structNameRequired"))
      return
    self.registration_data["structure_details"] = structure_details
    self.finalize_registration()

  def finalize_registration(self):
    try:
      result = anvil.server.call_s("register_user_and_setup", self.registration_data)
      if result.get("success"):
        user_settings_cache["additional_info"] = None
        alert(t.t("regFlow_alert_regSuccess"))
        open_form("Production.AudioManagerForm")
      else:
        alert(
          f"{t.t('regFlow_alert_regFailed')}: {result.get('message', 'An unknown error occurred.')}"
        )
    except Exception as e:
      alert(f"{t.t('regFlow_alert_regError')}: {str(e)}")
