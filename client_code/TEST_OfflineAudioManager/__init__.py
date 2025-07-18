from ._anvil_designer import TEST_OfflineAudioManagerTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users
import json
import uuid
import time

class TEST_OfflineAudioManager(TEST_OfflineAudioManagerTemplate):
  def __init__(self, **properties):
    print("[DEBUG] Initializing OfflineAudioManager form...")
    # Initialize form components
    self.init_components(**properties)
    print("[DEBUG] Form components initialized.")

    # Initialize recording state
    self.recording_state = "idle"

    # Storage for the transcription
    self.transcription = None

    # Track selected patient for saves
    self.selected_patient = None

    # Selected language for transcription/report generation
    self.selected_language = "EN"  # Default to English

    # Selected template/prompt for report generation
    self.selected_template = None

    # Add event handler for when the form is shown
    self.add_event_handler("show", self.form_show)

    print("[DEBUG] OfflineAudioManager initialization complete.")

  def form_show(self, **event_args):
    """Runs when the form becomes visible"""
    print("[DEBUG] OfflineAudioManager form_show triggered")

    # Check connection status and update UI
    is_online = self.check_connection_status()

    # Initialize the queue display - even if offline
    self.call_js("updateQueueDisplay")

    # Check if we have pending items and we're online
    if is_online:
      self.process_audio_queue()

    print("[DEBUG] form_show completed")

  def refresh_session_relay(self, **event_args):
    """Relay method for refreshing the session when called from JS"""
    try:
      return anvil.server.call("check_and_refresh_session")
    except Exception as e:
      print(f"[DEBUG] Error in refresh_session_relay: {str(e)}")
      return False

  def check_connection_status(self):
    """Check if the application is online and update the UI"""
    try:
      # First get the browser's navigator.onLine status, as it's more reliable for client-side
      js_online_status = self.call_js("getBrowserOnlineStatus")
      print(f"[DEBUG] Browser reports online status: {js_online_status}")

      # Only check server if browser thinks we're online
      if js_online_status:
        try:
          is_online = anvil.server.is_app_online()
        except Exception as e:
          print(f"[DEBUG] Error checking anvil.server.is_app_online: {str(e)}")
          is_online = False
      else:
        is_online = False

      print(f"[DEBUG] Final online status: {is_online}")
      self.call_js("updateConnectionStatusIndicator", is_online)
      return is_online
    except Exception as e:
      print(f"[DEBUG] Error checking connection status: {str(e)}")
      self.call_js("updateConnectionStatusIndicator", False)
      return False

  def update_offline_status(self, **event_args):
    """Called from JavaScript when offline event is triggered"""
    print("[DEBUG] App went offline, updating status")
    self.call_js("updateConnectionStatusIndicator", False)

  def start_recording(self, **event_args):
    """Called when recording starts"""
    self.recording_state = "recording"
    print("[DEBUG] Recording started")

  def pause_recording(self, **event_args):
    """Called when recording is paused"""
    self.recording_state = "paused"
    print("[DEBUG] Recording paused")

  def stop_recording(self, **event_args):
    """Called when recording stops"""
    self.recording_state = "stopped"
    print("[DEBUG] Recording stopped")

  def process_recording(self, audio_blob, **event_args):
    """Process a recording - either directly or by queueing"""
    print("[DEBUG] process_recording called")
    try:
      # First check browser's online status directly
      js_online_status = self.call_js("getBrowserOnlineStatus")
      print(f"[DEBUG] Browser reports online status: {js_online_status}")

      # If browser says we're offline, don't even try server check
      if not js_online_status:
        print("[DEBUG] Browser reports offline - open title modal for metadata")
        # Open modal to collect title before queueing
        self.call_js("openTitleModal")
        # Store the blob temporarily
        self.current_audio_blob = audio_blob
        return "PENDING_TITLE"

      # Browser thinks we're online, let's check server
      try:
        is_online = anvil.server.is_app_online()
      except Exception:
        is_online = False

      if is_online:
        # Online - process directly
        print("[DEBUG] Online mode - opening title modal before processing")
        # Open modal to collect title before processing
        self.call_js("openTitleModal")
        # Store the blob temporarily
        self.current_audio_blob = audio_blob
        return "PENDING_TITLE"
      else:
        # Offline - open modal for title before queueing
        print("[DEBUG] Server check failed - open title modal before queueing")
        self.call_js("openTitleModal")
        # Store the blob temporarily
        self.current_audio_blob = audio_blob
        return "PENDING_TITLE"
    except Exception as e:
      print(f"[ERROR] Error in process_recording: {str(e)}")
      self.call_js("displayBanner", f"Error processing recording: {str(e)}", "error")
      return None

  def save_recording_with_title(self, title, **event_args):
    """Called after user provides a title for the recording"""
    print(f"[DEBUG] save_recording_with_title called with title: {title}")

    try:
      # Create patient data and template info with defaults
      patient_data = {
        "name": title,  # Use title as the patient name
        "type": "Unknown",
        "proprietaire": "Unknown"
      }

      template_info = {
        "template": "Horse",  # Default template
        "language": "EN"      # Default language
      }

      # Check if we're online
      js_online_status = self.call_js("getBrowserOnlineStatus")

      if js_online_status:
        try:
          is_online = anvil.server.is_app_online()
        except Exception:
          is_online = False
      else:
        is_online = False

      if is_online:
        # Process directly
        print("[DEBUG] Online - processing recording directly with provided title")
        return self._process_audio_with_info(self.current_audio_blob, patient_data, template_info)
      else:
        # Queue with title
        print("[DEBUG] Offline - queueing recording with provided title")
        recording_id = self.save_audio_to_queue(self.current_audio_blob, patient_data, template_info, title)
        self.call_js("displayBanner", "Recording saved to offline queue", "success")
        return "QUEUED"

    except Exception as e:
      print(f"[ERROR] Error in save_recording_with_title: {str(e)}")
      self.call_js("displayBanner", f"Error saving recording: {str(e)}", "error")
      return None
    finally:
      # Clear the temporary blob
      self.current_audio_blob = None

  def _process_audio_with_info(self, audio_blob, patient_data, template_info):
    """Internal method to process audio directly with patient and template info"""
    print("[DEBUG] Processing audio with patient and template info")
    try:
      # 1. Transcribe audio based on language
      language = template_info.get("language", "EN")
      if language == "EN":
        transcription = anvil.server.call("EN_process_audio_whisper", audio_blob)
      else:
        transcription = anvil.server.call("process_audio_whisper", audio_blob)

      if not transcription:
        self.call_js("displayBanner", "Failed to process audio", "error")
        return None

      # Save the raw transcription
      self.transcription = transcription

      # 2. Get the template prompt
      template_name = template_info.get("template")
      prompt_header = "prompt_fr" if language == "FR" else "prompt_en"
      template_prompt = anvil.server.call("pick_template", template_name, prompt_header)

      # Fallback if language-specific prompt not found
      if not template_prompt:
        template_prompt = anvil.server.call("pick_template", template_name, "prompt")

      if not template_prompt:
        self.call_js("displayBanner", f"Template '{template_name}' not found", "error")
        return None

      # 3. Generate report using GPT-4
      report_content = anvil.server.call("generate_report", template_prompt, transcription)

      # 4. Format report based on language
      if language == "FR":
        report_final = anvil.server.call("format_report", report_content)
      else:
        report_final = anvil.server.call("EN_format_report", report_content)

      # 5. Save the report
      # Handle patient data
      animal_name = patient_data.get("name", "Unknown")
      unique_id = patient_data.get("unique_id")

      # Create new patient if needed
      if not unique_id:
        animal_type = patient_data.get("type", "Unknown")
        proprietaire = patient_data.get("proprietaire", "Unknown")
        unique_id = anvil.server.call("write_animal_first_time",
                                       animal_name,
                                       type=animal_type,
                                       proprietaire=proprietaire)

      # Save the report with the generated content
      result = anvil.server.call(
        "write_report_first_time",
        animal_name=animal_name,
        report_rich=report_final,
        statut="transcribed",
        unique_id=unique_id,
        transcript=transcription
      )

      if result:
        self.call_js("displayBanner", "Recording processed and archived successfully", "success")
        # Make sure to show the transcription container
        self.call_js("showTranscriptionContainer")
        self.call_js("updateTranscriptionDisplay", transcription)
        return "OK"
      else:
        self.call_js("displayBanner", "Failed to save report", "error")
        return None
    except Exception as e:
      print(f"[ERROR] Error processing audio with info: {str(e)}")
      self.call_js("displayBanner", f"Error: {str(e)}", "error")
      return None

  def save_audio_to_queue(self, audio_blob, patient_data=None, template_info=None, title=None):
    """Save audio to local queue when offline with patient and template info"""
    print("[DEBUG] Saving audio to queue with metadata")
    try:
        # Generate a unique ID for this recording
      recording_id = str(uuid.uuid4())

      # Create metadata for the recording, including patient and template info
      metadata = {
          "id": recording_id,
          "timestamp": time.time(),
          "status": "pending",
          "type": "audio_processing",  # Mark this as audio processing task
          "patient_data": patient_data,
          "template_info": template_info,
          "title": title or patient_data.get("name", "Untitled Recording")
      }

      # Call JavaScript to store the audio blob and metadata
      print("[DEBUG] Calling storeAudioInQueue JavaScript function")
      result = self.call_js("storeAudioInQueue", audio_blob, metadata)
      print(f"[DEBUG] storeAudioInQueue result: {result}")

      if result:
        # Force queue section display
        self.call_js("displayQueueSection")
        self.call_js("displayBanner", "Recording saved to offline queue", "success")
        return recording_id
      else:
        print("[ERROR] storeAudioInQueue returned False")
        self.call_js("displayBanner", "Failed to save recording to queue", "error")
        return None
    except Exception as e:
      print(f"[ERROR] Error in save_audio_to_queue: {str(e)}")
      self.call_js("displayBanner", f"Error saving to queue: {str(e)}", "error")
      return None

  def process_queued_audio(self, item_id, audio_data, item_metadata):
    """Process a single queued audio item with its ID, data, and metadata"""
    print(f"[DEBUG] Processing queued audio item {item_id}")
    try:
      # Log the type of audio_data for debugging
      print(f"[DEBUG] Audio data type: {type(audio_data)}, length: {len(audio_data) if hasattr(audio_data, '__len__') else 'unknown'}")

      # Extract title, patient and template info from metadata
      title = item_metadata.get("title", "Untitled Recording")
      patient_data = item_metadata.get("patient_data", {})
      template_info = item_metadata.get("template_info", {})

      # If patient_data is missing, create it from the title
      if not patient_data:
        patient_data = {
            "name": title,
            "type": "Unknown",
            "proprietaire": "Unknown"
        }

      # If template_info is missing, use default Horse template
      if not template_info:
        template_info = {
            "template": "Horse",
            "language": "EN"
        }

      # Convert to bytes - always use direct conversion
      audio_bytes = bytes(audio_data)
      print(f"[DEBUG] Successfully converted audio data to bytes, size: {len(audio_bytes)}")

      # Convert bytes to base64 string which the server function can handle
      import base64
      base64_audio = base64.b64encode(audio_bytes).decode('utf-8')
      print(f"[DEBUG] Converted to base64 string, length: {len(base64_audio)}")

      # 1. Transcribe the audio
      language = template_info.get("language", "EN")
      print(f"[DEBUG] Transcribing with language: {language}")

      if language == "EN":
        transcription = anvil.server.call("EN_process_audio_whisper", base64_audio)
      else:
        transcription = anvil.server.call("process_audio_whisper", base64_audio)

      if not transcription:
        print("[ERROR] Failed to get transcription")
        self.call_js("updateItemStatus", item_id, "error")
        return "ERROR"

      print(f"[DEBUG] Successfully transcribed audio, length: {len(transcription)}")

      # 2. Get the template prompt
      template_name = template_info.get("template")
      prompt_header = "prompt_fr" if language == "FR" else "prompt_en"
      template_prompt = anvil.server.call("pick_template", template_name, prompt_header)

      # Fallback if language-specific prompt not found
      if not template_prompt:
        template_prompt = anvil.server.call("pick_template", template_name, "prompt")

      if not template_prompt:
        print(f"[ERROR] Template '{template_name}' not found")
        self.call_js("updateItemStatus", item_id, "error")
        return "ERROR"

      print(f"[DEBUG] Got template prompt: {template_prompt[:50]}...")

      # 3. Generate report using GPT-4
      report_content = anvil.server.call("generate_report", template_prompt, transcription)

      if not report_content:
        print("[ERROR] Failed to generate report")
        self.call_js("updateItemStatus", item_id, "error")
        return "ERROR"

      print(f"[DEBUG] Generated report content, length: {len(report_content)}")

      # 4. Format report based on language
      if language == "FR":
        report_final = anvil.server.call("format_report", report_content)
      else:
        report_final = anvil.server.call("EN_format_report", report_content)

      if not report_final:
        print("[ERROR] Failed to format report")
        self.call_js("updateItemStatus", item_id, "error")
        return "ERROR"

      print(f"[DEBUG] Formatted report, length: {len(report_final)}")

      # 5. Save the report
      # Handle patient data
      animal_name = patient_data.get("name", "Unknown")
      unique_id = patient_data.get("unique_id")

      # Create new patient if needed
      if not unique_id:
        animal_type = patient_data.get("type", "Unknown")
        proprietaire = patient_data.get("proprietaire", "Unknown")
        try:
          unique_id = anvil.server.call("write_animal_first_time",
                                     animal_name,
                                     type=animal_type,
                                     proprietaire=proprietaire)
          print(f"[DEBUG] Created new patient with unique_id: {unique_id}")
        except Exception as e:
          print(f"[ERROR] Failed to create new patient: {str(e)}")
          self.call_js("updateItemStatus", item_id, "error")
          return "ERROR"

      # Save the report with the generated content
      try:
        result = anvil.server.call(
            "write_report_first_time",
            animal_name=animal_name,
            report_rich=report_final,
            statut="transcribed",
            unique_id=unique_id,
            transcript=transcription
        )

        if result:
          print(f"[DEBUG] Successfully saved report for {animal_name}")
          # Update queue item status
          self.call_js("updateItemStatus", item_id, "processed")
          return "OK"
        else:
          print("[ERROR] Failed to save report")
          self.call_js("updateItemStatus", item_id, "error")
          return "ERROR"
      except Exception as e:
        print(f"[ERROR] Error saving report: {str(e)}")
        self.call_js("updateItemStatus", item_id, "error")
        return "ERROR"
    except Exception as e:
      print(f"[ERROR] Error processing queued audio {item_id}: {str(e)}")
      self.call_js("updateItemStatus", item_id, "error")
      return "ERROR"

  def remove_queue_item(self, item_id):
    """Remove a specific item from the queue"""
    print(f"[DEBUG] Removing queue item {item_id}")
    result = self.call_js("removeQueueItem", item_id)
    return result

  def begin_queue_processing(self, queue_length):
    """Initialize the queue processing - called before processing individual items"""
    print(f"[DEBUG] Beginning queue processing for {queue_length} items")
    return True

  def process_audio_queue(self, **event_args):
    """Process all queued audio recordings when back online"""
    print("[DEBUG] Processing audio queue")
    if not self.check_connection_status():
      print("[DEBUG] Cannot process queue - app is offline")
      return False

    # This now delegates the queue processing to JavaScript for better item-by-item handling
    try:
      # We call processEntireQueue in JavaScript and let it handle everything
      result = self.call_js("processEntireQueue")
      print(f"[DEBUG] Queue processing completed: {result}")
      return True
    except Exception as e:
      print(f"[ERROR] Error processing queue: {str(e)}")
      self.call_js("displayBanner", f"Error processing queue: {str(e)}", "error")
      return False

  # Get available templates for dropdown
  def get_available_templates(self, **event_args):
    """Get available templates for the dropdown menu"""
    print("[DEBUG] get_available_templates called")
    try:
      # Get templates from server
      templates = anvil.server.call("read_templates")

      # Filter by priority if needed (e.g., only show templates with priority 1 or 2)
      filtered_templates = [t for t in templates if t.get('priority') in (1, 2)]

      print(f"[DEBUG] Retrieved {len(filtered_templates)} templates")
      return filtered_templates
    except Exception as e:
      print(f"[ERROR] Error getting templates: {str(e)}")
      return []

  # Patient search for modal
  def search_patients_relay(self, search_term, **event_args):
    """Relay for searching patients"""
    print(f"[DEBUG] search_patients_relay called with: {search_term}")
    try:
      results = anvil.server.call("search_patients", search_term)
      print(f"[DEBUG] search_patients_relay results: {len(results)} patients found")
      return results
    except Exception as e:
      print(f"[ERROR] Error in search_patients_relay: {str(e)}")
      return []

  # Create a new patient
  def create_new_patient(self, patient_details, **event_args):
    """Create a new patient from the patient selection modal"""
    print(f"[DEBUG] Creating new patient: {patient_details}")
    try:
      # Call server to create a new patient
      new_patient = anvil.server.call("create_new_animal",
                                      name=patient_details["name"],
                                      animal_type=patient_details["type"],
                                      proprietaire=patient_details["proprietaire"])

      if new_patient:
        self.call_js("displayBanner", "New patient created", "success")
        return new_patient
      else:
        self.call_js("displayBanner", "Failed to create new patient", "error")
        return None
    except Exception as e:
      print(f"[ERROR] Error creating new patient: {str(e)}")
      self.call_js("displayBanner", f"Error: {str(e)}", "error")
      return None

  # Navigation methods
  def open_production_form(self, **event_args):
    print("[DEBUG] Opening Production form")
    open_form("TEST_AudioManagerUltimate2")

  def open_templates_form(self, **event_args):
    print("[DEBUG] Opening Templates form")
    open_form("TEST_Templates")

  def open_archives_form(self, **event_args):
    print("[DEBUG] Opening Archives form")
    current_user = anvil.users.get_user()
    if current_user and current_user.get('supervisor'):
      open_form("TEST_ArchivesSecretariat")
    else:
      open_form("TEST_Archives")

  def open_settings_form(self, **event_args):
    print("[DEBUG] Opening Settings form")
    open_form("TEST_Settings")
