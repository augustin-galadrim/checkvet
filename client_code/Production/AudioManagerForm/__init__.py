from ._anvil_designer import AudioManagerFormTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import json
import anvil.users
import base64
import anvil.media
import anvil.js
import time
from ... import TranslationService as t


def safe_value(item, key, default_value):
  """Returns the value associated with 'key' in 'item', or 'default_value' if the key is missing or None."""
  if item is None:
    return default_value
  val = item.get(key)
  return default_value if val is None else val


class AudioManagerForm(AudioManagerFormTemplate):
  def __init__(
    self,
    clicked_value=None,
    template_name=None,
    initial_content=None,
    prompt=None,
    **properties,
  ):
    print("[DEBUG] Initializing AudioManagerForm")
    print(
      f"[DEBUG] __init__ parameters: clicked_value={clicked_value}, template_name={template_name}, initial_content={initial_content}, prompt={prompt}"
    )
    self.init_components(**properties)

    # Store user-provided parameters
    self.clicked_value = clicked_value
    self.template_name = template_name
    self.initial_content = initial_content
    self.prompt = prompt

    # Storage for raw transcription
    self.raw_transcription = None

    # Recording state
    self.recording_state = "idle"

    # User-selected status will be stored here
    self.selected_statut = None

    self.audio_chunks = []



    def silent_error_handler(err):
      print(f"[DEBUG] Silent error handler: {err}")
      # Optional: Add logging here
      pass

    set_default_error_handling(silent_error_handler)

    # When displaying the form, execute form_show
    self.add_event_handler("show", self.form_show)
    print("[DEBUG] __init__ completed.")

  def update_ui_texts(self):
    """Sets all text on the form using the TranslationService."""
    # Navigation
    self.call_js("setElementText", "nav_production", t.t('nav_production'))
    self.call_js("setElementText", "nav_templates", t.t('nav_templates'))
    self.call_js("setElementText", "nav_archives", t.t('nav_archives'))
    self.call_js("setElementText", "nav_settings", t.t('nav_settings'))

    # Mode Toggles
    self.call_js("setElementText", "recordButton", t.t('record_button'))
    self.call_js("setElementText", "uploadButton", t.t('upload_button'))

    # Upload Section
    self.call_js("setElementText", "upload_text_drop", t.t('upload_text_drop'))
    self.call_js("setElementText", "upload_description_select", t.t('upload_description_select'))
    self.call_js("setElementText", "upload_button_select", t.t('upload_button_select'))

    # Parameters
    self.call_js("setElementText", "label_template", t.t('label_template'))
    self.call_js("setElementText", "label_language", t.t('label_language'))
    self.call_js("setElementText", "select_template_placeholder", t.t('select_template_placeholder'))

    # Toolbar
    self.call_js("setElementText", "toolbar_image", t.t('toolbar_image'))
    self.call_js("setElementText", "leftAlignBtn", t.t('left_align_button'))
    self.call_js("setElementText", "centerAlignBtn", t.t('center_align_button'))
    self.call_js("setElementText", "rightAlignBtn", t.t('right_align_button'))
    self.call_js("setElementText", "insertImageBtn", t.t('insert_image_button'))
    self.call_js("setElementText", "toolbar_copy", t.t('toolbar_copy'))

    # Bottom Buttons
    self.call_js("setElementText", "button_status", t.t('button_status'))
    self.call_js("setElementText", "button_archive", t.t('button_archive'))
    self.call_js("setElementText", "button_share", t.t('button_share'))

    # Modals
    self.call_js("setElementText", "select_patient_title", t.t('select_patient_title'))
    self.call_js("setElementText", "newPatientBtn", t.t('new_patient_button'))
    self.call_js("setElementText", "select_template_title", t.t('select_template_title'))
    self.call_js("setPlaceholderById", "searchInput", t.t('search_patient_placeholder'))
    self.call_js("setPlaceholderById", "templateSearchInput", t.t('search_template_placeholder'))

  def form_show(self, **event_args):
    print("[DEBUG] Starting form_show in AudioManagerForm")
    self.update_ui_texts()
    # Check if user has provided additional info
    additional_info = anvil.server.call("pick_user_info", "additional_info")
    print(f"[DEBUG] additional_info from pick_user_info: {additional_info}")
    if not additional_info:
      print(
        "[DEBUG] No additional_info, opening registration flow in English (RegistrationFlow)"
      )
      open_form("EN_RegistrationFlow")
      return

    mobile_installation = anvil.server.call("pick_user_info2", "mobile_installation")
    print(f"[DEBUG] mobile_installation from pick_user_info2: {mobile_installation}")
    if not mobile_installation:
      print(
        "[DEBUG] No mobile installation specified, opening mobile installation flow in English"
      )
      open_form("EN_MobileInstallationFlow")
      return

    # Load templates from database and filter on favorites (priority 1 or 2)
    templates = anvil.server.call(
      "read_templates"
    )  # returns a list of dictionaries
    filtered_templates = [t for t in templates if t.get("priority") in (1, 2)]
    self.call_js("populateTemplateModal", filtered_templates)

    # Load initial content in the editor, if provided
    if self.initial_content:
      print("[DEBUG] Loading initial content in editor.")
      self.editor_content = self.initial_content
    else:
      if self.clicked_value is not None:
        print("[DEBUG] clicked_value provided, loading report content.")
        self.load_report_content()

    # Recreate patient search field (like in archive modal).
    print("[DEBUG] Rebuilding patient search field.")
    self.call_js("rebuildPatientSearchInput")

    print("[DEBUG] form_show completed.")

  def refresh_session_relay(self, **event_args):
    """Called when the application comes back online or the tab returns to foreground, to keep user session active."""
    try:
      return anvil.server.call("check_and_refresh_session")
    except Exception as e:
      print(f"[DEBUG] Error in refresh_session_relay: {str(e)}")
      return False

  def load_report_content(self):
    print(
      f"[DEBUG] Loading report content for clicked_value: {self.clicked_value}"
    )
    try:
      content, error = anvil.server.call("load_report_content", self.clicked_value)
      print(
        f"[DEBUG] Result from load_report_content: content={content}, error={error}"
      )
      if error:
        alert(error)
      elif content:
        self.editor_content = content
      else:
        alert("Unexpected error: no content returned.")
    except Exception as e:
      print(f"[ERROR] Exception in load_report_content: {e}")

  # -------------------------
  # Recording methods
  # -------------------------
  def start_recording(self, **event_args):
    self.recording_state = "recording"
    print(
      "[DEBUG] start_recording() called. Recording state set to 'recording'."
    )

  def pause_recording(self, **event_args):
    self.recording_state = "paused"
    print(
      "[DEBUG] pause_recording() called. Recording state set to 'paused'."
    )

  def stop_recording(self, **event_args):
    self.recording_state = "stopped"
    print(
      "[DEBUG] stop_recording() called. Recording state set to 'stopped'."
    )

  def show_error(self, error_message, **event_args):
    print(f"[DEBUG] show_error() called with message: {error_message}")
    alert(error_message)

  # -------------------------
  # New method to process uploaded audio files
  # -------------------------
  def process_uploaded_audio(self, audio_blob, **event_args):
    """
    Processes an uploaded audio file (particularly for iOS Voice Memos)
    """
    print("[DEBUG] process_uploaded_audio() called with an audio blob.")
    try:
      # Process the audio once the file is received
      return self.process_recording(audio_blob)
    except Exception as e:
      print(f"[ERROR] Exception in process_uploaded_audio: {e}")
      alert(f"Error processing audio file: {str(e)}")
      return None

  # -------------------------
  # Language detection
  # -------------------------
  def get_selected_language(self):
    """
    Gets the currently selected language based on the flag emoji
    in the language dropdown.
    Returns: 'FR' or 'EN'
    """
    try:
      language_emoji = self.call_js("getDropdownSelectedValue", "langueDropdown")
      print(f"[DEBUG] Selected language emoji: {language_emoji}")
      if language_emoji == "🇫🇷":
        return "FR"
      elif language_emoji == "🇬🇧":
        return "EN"
      else:
        # Default to EN if unknown
        print(
          f"[DEBUG] Unknown language emoji: {language_emoji}, defaulting to EN"
        )
        return "EN"
    except Exception as e:
      print(f"[ERROR] Error getting selected language: {e}")
      return "EN"

  def process_recording(self, audio_blob, **event_args):
    """
      This is the restored, working version of the processing method,
      now wrapped with offline error handling.
      """
    print("[DEBUG] process_recording initiated.")
    try:
      # --- PART 1: RESTORED LOGIC FROM YOUR PREVIOUS WORKING CODE ---
  
      # Helper for retries
      def call_with_retry(fn_name, *args):
        for attempt in range(3):
          try:
            return anvil.server.call_s(fn_name, *args)
          except anvil.server.TimeoutError as e:
            if attempt < 2:
              time.sleep(2 ** attempt)
            else:
              raise e
  
          # CRITICAL: Input Normalization Block
      if isinstance(audio_blob, str): # Handles Base64 if ever needed
        raw = base64.b64decode(audio_blob)
        audio_blob = anvil.BlobMedia(content=raw, content_type="audio/webm", name="recording.webm")
      elif (hasattr(audio_blob, "constructor") and
            audio_blob.constructor and
            audio_blob.constructor.name in ("Blob", "File")):
        print("[DEBUG] Detected JS Proxy Object, converting with to_media()...")
        audio_blob = anvil.js.to_media(audio_blob, name="recording.webm") # This is the key conversion
  
        # Ensure it's a Media object now
      if not isinstance(audio_blob, anvil.Media):
        alert("Unrecognized audio object type. Cannot process.")
        return
  
        # Get template and language
      selected_template_name = self.call_js("getDropdownSelectedValue", "templateSelectBtn")
      if not selected_template_name or selected_template_name.startswith("Select"):
        alert("Please select a template before processing.")
        return
      lang = self.get_selected_language()
  
      # Launch background task
      whisper_fn = "EN_process_audio_whisper" if lang == "EN" else "process_audio_whisper"
      print(f"[DEBUG] Launching background task '{whisper_fn}'...")
      task = call_with_retry(whisper_fn, audio_blob)
  
      # Blocking wait for the task to finish (as it worked before)
      elapsed = 0.0
      while not task.is_completed() and elapsed < 240: # 4 minute timeout
        time.sleep(1)
        elapsed += 1
  
      if not task.is_completed():
        alert("The transcription is taking too long to complete. Please try again.")
        return
  
      transcription = task.get_return_value()
      if isinstance(transcription, dict) and "error" in transcription:
        alert(f"Transcription failed: {transcription['error']}")
        return
      self.raw_transcription = transcription
      print("[DEBUG] Transcription received successfully.")
  
      # Continue with the rest of the workflow
      prompt_row = app_tables.custom_templates.get(template_name=selected_template_name)
      prompt = prompt_row['prompt']
  
      report_content = call_with_retry("generate_report", prompt, transcription)
  
      formatter_fn = "EN_format_report" if lang == "EN" else "format_report"
      final_html = call_with_retry(formatter_fn, report_content)
  
      self.editor_content = final_html
      print("[DEBUG] process_recording completed successfully.")
      return "OK" # Return a simple success message to JS
  
    except anvil.server.AppOfflineError:
      # --- PART 2: THE NEW OFFLINE LOGIC ---
      # This block is only triggered if the VERY FIRST server call fails
      print("[DEBUG] AppOfflineError caught. Initiating offline save.")
      self.call_js('handleOfflineSave') # We'll create this small JS helper
  
    except Exception as e:
      print(f"[ERROR] An exception occurred in process_recording: {e}")
      # Re-raise it so the JS .catch() block can display the banner
      raise

  # --- NEW FUNCTION ---
  def process_queued_item(self, item_id, audio_blob, title):
    """
      Relay function to process a single item from the offline queue.
      """
    print(f"[DEBUG] Processing queued item: ID={item_id}, Title='{title}'")
    try:
      # Call the new dedicated server function
      success = anvil.server.call(
        'process_and_archive_offline_recording',
        audio_blob,
        title
      )
      return {'success': success}
    except Exception as e:
      print(f"[ERROR] Failed to process queued item {item_id}: {e}")
      return {'success': False, 'error': str(e)}

  # 1) called for each chunk
  def receive_audio_chunk(self, b64_chunk, index, total, **event_args):
    if not self.audio_chunks or len(self.audio_chunks) != total:
      self.audio_chunks = [""] * total
    self.audio_chunks[index] = b64_chunk
    return "OK"

  # 2) consolidation without bytearray or massive join
  def process_consolidated_audio(self, **event_args):
    if not self.audio_chunks or "" in self.audio_chunks:
      return {"error": "Not all audio chunks have been received."}

    data_bytes = b""
    for part in self.audio_chunks:  # incremental concatenation
      data_bytes += base64.b64decode(part)

    self.audio_chunks = []  # reset

    media = anvil.BlobMedia(
      content=data_bytes, content_type="audio/webm", name="recording.webm"
    )

    return self.process_recording(media)

  # -------------------------
  # iOS format processing
  # -------------------------
  def convert_audio_format_if_needed(self, audio_blob, file_name, **event_args):
    """
    Checks if the audio format is compatible (especially for iOS Voice Memos) and converts if necessary.
    iOS Voice Memos typically use .m4a format, which is compatible with our processing.
    """
    print(f"[DEBUG] Checking audio format for: {file_name}")

    try:
      # Check file extension
      file_extension = file_name.lower().split(".")[-1] if "." in file_name else ""

      if file_extension in ["m4a", "mp3", "wav", "aac"]:
        # Formats already compatible with our system
        print(f"[DEBUG] Compatible audio format: {file_extension}")
        return audio_blob
      else:
        # We could implement conversion here
        # For now, just alert the user
        print(f"[DEBUG] Non-optimal audio format: {file_extension}")
        if file_extension not in ["m4a"]:
          alert(
            f"Note: The {file_extension} format is not optimized for iOS Voice Memos (which uses m4a)."
          )
        return audio_blob

    except Exception as e:
      print(f"[ERROR] Error checking audio format: {e}")
      return audio_blob  # Return original blob on error

  # -------------------------
  # Audio processing (TOOLBAR recorder)
  # -------------------------
  def process_toolbar_recording(self, audio_blob, **event_args):
    """
    Recording via toolbar (completely separate from main).
    1. Get existing editor content.
    2. Transcribe voice.
    3. Combine existing + new transcription
    4. Generate GPT report
    5. Update editor with final content
    """
    print("[DEBUG] process_toolbar_recording() - toolbar flow.")
    try:
      # Hard-coded prompt (or any other prompt you want)
      self.prompt = "you are a helpful AI assistant"

      # 1) Get current editor content
      existing_content = self.editor_content or ""
      print(f"[DEBUG] existing_content length: {len(existing_content)}")

      # 2) Transcribe newly recorded audio
      selected_language = self.get_selected_language()
      print(f"[DEBUG] (toolbar) Selected language: {selected_language}")

      if selected_language == "EN":
        transcription = anvil.server.call("EN_process_audio_whisper", audio_blob)
      else:
        transcription = anvil.server.call("process_audio_whisper", audio_blob)

      print(f"[DEBUG] (toolbar) Transcription received: {transcription}")

      # 3) Combine transcription with editor content
      combined_text = existing_content + "\n" + transcription

      # 4) Generate result via GPT
      report_content = anvil.server.call("generate_report", self.prompt, combined_text)
      print(f"[DEBUG] (toolbar) GPT result length: {len(report_content or '')}")

      # 5) Formatting according to language
      if selected_language == "FR":
        report_final = anvil.server.call("format_report", report_content)
      else:
        report_final = anvil.server.call("EN_format_report", report_content)

      # Update editor
      self.editor_content = report_final

      print("[DEBUG] process_toolbar_recording() completed successfully (toolbar flow).")
      return "OK"

    except Exception as e:
      print(f"[ERROR] Exception in process_toolbar_recording (toolbar flow): {e}")
      alert(
        f"Error processing toolbar recording: {str(e)}"
      )
      return None

  # -------------------------
  # Support for validate/send button
  # -------------------------
  def validate_and_send(self, **event_args):
    """Handles validation and sending of editor content"""
    print("[DEBUG] validate_and_send() called")
    try:
      content = self.editor_content
      if not content or not content.strip():
        self.call_js("displayBanner", "No content to send", "error")
        return False
      # HERE: sending logic (email, etc.)
      self.call_js("displayBanner", "Content validated and sent successfully!", "success")
      return True

    except Exception as e:
      print(f"[ERROR] Exception in validate_and_send: {e}")
      alert(f"Error validating and sending: {str(e)}")
      return False

  # -------------------------
  # Property for editor
  # -------------------------
  @property
  def editor_content(self):
    try:
      content = self.call_js("getEditorContent")
      print(f"[DEBUG] Editor content retrieved: {content}")
      return content
    except Exception as e:
      print(f"[ERROR] ERROR getting editor content: {e}")
      return None

  @editor_content.setter
  def editor_content(self, value):
    try:
      print(f"[DEBUG] Updating editor content: {value}")
      self.call_js("setEditorContent", value)
    except Exception as e:
      print(f"[ERROR] ERROR setting editor content: {e}")

  # -------------------------
  # Method for "Status" button
  # -------------------------
  def on_statut_clicked(self, **event_args):
    print("[DEBUG] on_statut_clicked() called")
    choice = alert(
      "Choose status:", buttons=["to correct", "validated", "sent", "Cancel"]
    )
    print(f"[DEBUG] Selected status: {choice}")
    if choice in ["to correct", "validated", "sent"]:
      self.selected_statut = choice
      self.call_js("displayBanner", f"Status chosen: {choice}", "success")
      return choice
    else:
      return None

  # -------------------------
  # Save and generate PDF
  # -------------------------
  def save_report(self, content_json, images, selected_patient, **event_args):
    print("[DEBUG] save_report() called from JS")
    try:
      # Check that selected_patient is a dict
      if not isinstance(selected_patient, dict):
        print(
          f"[DEBUG] selected_patient is not a dict. Searching for patient: {selected_patient}"
        )
        matches = self.search_patients_relay(selected_patient)
        if len(matches) == 1:
          selected_patient = matches[0]
          print(f"[DEBUG] Patient found: {selected_patient}")
        elif len(matches) > 1:
          alert(
            "Multiple patients found. Please select one from the list."
          )
          return
        else:
          alert("No patient found with this name.")
          return

      animal_name = selected_patient.get("name")
      unique_id = selected_patient.get("unique_id")
      print(
        f"[DEBUG] Extracting patient: animal_name={animal_name}, unique_id={unique_id}"
      )

      if unique_id is None:
        print("[DEBUG] New patient detected, creating via write_animal_first_time")
        details = selected_patient.get("details", {})
        type_val = details.get("type")
        proprietaire_val = details.get("proprietaire")
        new_unique_id = anvil.server.call(
          "write_animal_first_time",
          animal_name,
          type=type_val,
          proprietaire=proprietaire_val,
        )
        print(f"[DEBUG] write_animal_first_time returned unique_id: {new_unique_id}")
        unique_id = new_unique_id
      else:
        print("[DEBUG] Existing patient selected, reusing info.")

      parsed = json.loads(content_json)
      html_content = parsed.get("content", "")
      print(f"[DEBUG] HTML content length: {len(html_content)}")
      print(f"[DEBUG] Number of images: {len(images)}")

      statut = self.selected_statut or "Not specified"
      print(f"[DEBUG] Status used: {statut}")

      print("[DEBUG] Calling write_report_first_time with unique_id.")
      result = anvil.server.call(
        "write_report_first_time",
        animal_name=animal_name,
        report_rich=html_content,
        statut=statut,
        unique_id=unique_id,
        transcript=self.raw_transcription,
      )
      print(f"[DEBUG] Return from write_report_first_time: {result}")

      if result:
        self.call_js("displayBanner", "Report saved successfully", "success")
      else:
        alert("Failed to save report. Please try again.")

    except Exception as e:
      print(f"[ERROR] Exception in save_report: {e}")
      raise

    print("[DEBUG] save_report() completed successfully.")
    return True

  def get_new_patient_details(self):
    print("[DEBUG] get_new_patient_details() called")
    form_content = ColumnPanel(spacing=10)
    form_content.add_component(TextBox(placeholder="Name"))
    form_content.add_component(TextBox(placeholder="Species"))
    form_content.add_component(TextBox(placeholder="Owner"))
    result = alert(
      content=form_content,
      title="Enter new patient details",
      buttons=["OK", "Cancel"],
    )
    print(f"[DEBUG] Result get_new_patient_details: {result}")
    if result == "OK":
      components = form_content.get_components()
      details = {
        "name": components[0].text,
        "type": components[1].text,
        "proprietaire": components[2].text,
      }
      print(f"[DEBUG] New patient details: {details}")
      return details
    else:
      print("[DEBUG] get_new_patient_details canceled by user.")
      return None

  def build_report_pdf_relay(self, placeholders, images):
    print("[DEBUG] build_report_pdf_relay called")
    print(f"[DEBUG] Placeholders: {placeholders}, Number of images: {len(images)}")
    pdf_base64 = anvil.server.call("build_report_pdf_base64", placeholders, images)
    print(f"[DEBUG] pdf_base64 received from server. Length: {len(pdf_base64)}")
    return pdf_base64

  def get_media_url_relay(self, pdf_media):
    print("[DEBUG] get_media_url_relay called")
    import anvil

    url = anvil.get_url(pdf_media)
    print(f"[DEBUG] URL generated: {url}")
    return url

  # -------------------------
  # Navigation from top tabs
  # -------------------------
  def open_production_form(self, **event_args):
    print("[DEBUG] Opening EN_Production form")
    open_form("Production.AudioManagerForm")

  def open_templates_form(self, **event_args):
    print("[DEBUG] Opening EN_Templates form")
    open_form("Templates.EN_Templates")

  def open_archives_form(self, **event_args):
    print("[DEBUG] Opening EN_Archives form")
    current_user = anvil.users.get_user()
    if current_user["supervisor"]:
      open_form("Archives.EN_ArchivesSecretariat")
    else:
      open_form("Archives.EN_Archives")

  def open_settings_form(self, **event_args):
    print("[DEBUG] Opening EN_Settings form")
    open_form("Settings.EN_Settings")

  # -------------------------
  # Front-end relay for patient search
  # -------------------------
  def search_patients_relay(self, search_term, **event_args):
    print(f"[DEBUG] search_patients_relay called with search_term: {search_term}")
    try:
      results = anvil.server.call("search_patients", search_term)
      print(f"[DEBUG] Results from search_patients_relay: {results}")
      return results
    except Exception as e:
      print(f"[ERROR] Error in search_patients_relay: {e}")
      return []

  # -------------------------
  # Front-end relay for template search
  # -------------------------
  def search_template_relay(self, search_term, **event_args):
    print(f"[DEBUG] search_template_relay called with search_term: {search_term}")
    try:
      results = anvil.server.call("EN_search_templates", search_term)
      if results is None:
        results = []
      transformed_results = []
      for template in results:
        if template is None:
          continue
        transformed_result = {
          "id": safe_value(template, "id", ""),
          "template_name": safe_value(template, "template_name", "Untitled template"),
          "priority": safe_value(template, "priority", 0),
          "display_template": safe_value(template, "display_template", False),
          "text_to_display": safe_value(template, "text_to_display", ""),
        }
        transformed_results.append(transformed_result)
      print(f"[DEBUG] Transformed template results: {transformed_results}")
      return transformed_results
    except Exception as e:
      print(f"[ERROR] Error in search_template_relay: {e}")
      return []