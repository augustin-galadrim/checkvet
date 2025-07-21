from ._anvil_designer import EN_TemplatesTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import base64

class EN_Templates(EN_TemplatesTemplate):
  def __init__(self, **properties):
    print("Initializing EN_Templates form...")
    # Initialize form components
    self.init_components(**properties)
    print("Form components initialized.")

    # Attach the "show" event handler
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Once the form is shown, fetch the templates from the server and populate the HTML list."""
    print("EN_Templates form_show triggered.")
    templates = anvil.server.call("EN_read_templates")
    print(f"Server returned {len(templates)} templates.")
    # Push the list of templates to the JavaScript code
    self.call_js("populateTemplates", templates)

  def refresh_session_relay(self, **event_args):
    """Relay method for refreshing the session when called from JS"""
    try:
      return anvil.server.call("check_and_refresh_session")
    except Exception as e:
      print(f"[DEBUG] Error in refresh_session_relay: {str(e)}")
      return False
  # ----------------------
  # Navigation methods
  # ----------------------
  def open_production_form(self, **event_args):
    """Open the EN_AudioManager form from the 'Production' tab."""
    open_form("AudioManager.AudioManagerForm")

  def open_archives_form(self, **event_args):
    """Open the Archives form from the 'Archives' tab."""
    current_user = anvil.users.get_user()
    if current_user['supervisor']:
      open_form("Archives.EN_ArchivesSecretariat")
    else:
      open_form("Archives.EN_Archives")

  def open_settings_form(self, **event_args):
    """Open the EN_Settings form from the 'Settings' tab."""
    open_form("Settings.EN_Settings")

  def open_create_form(self, **event_args):
    """
    Old method which opened EN_AudioManager,
    now replaced by our custom modal.
    (Kept here for reference.)
    """
    open_form("AudioManager.AudioManagerForm")

  # --------------------------------------
  # Logic for PDF to template conversion modal
  # --------------------------------------
  def show_pdf_modal(self, **event_args):
    """
    Called from JS when the "+ Create" button is clicked.
    Displays the PDF upload modal.
    """
    print("Displaying PDF modal...")
    self.call_js("openPdfModal")

  def transform_pdf_to_template(self, base64_pdf, template_name, **event_args):
    """
    1) Convert base64_pdf to anvil.BlobMedia.
    2) Process the PDF using a first prompt then reprocess with a second prompt.
    3) Save the final result in the database.
    4) Display a success banner.
    """
    print(f"Calling transform_pdf_to_template with template_name={template_name}")

    # 1) Convert the Base64 string to a BlobMedia PDF
    pdf_bytes = base64.b64decode(base64_pdf)
    pdf_file = anvil.BlobMedia(content_type="application/pdf", content=pdf_bytes, name="uploaded.pdf")

    # 2) Define the prompts in English
    first_prompt = """
Role

You are an expert in structured document analysis, specializing in extracting the structure and organization of information in technical and medical reports. Your mission is to dissect and present the detailed structure of a veterinary report by identifying its sections, headings, and the organization of the information—without including case-specific details.

Task

    Identification of main sections: Identify and name the major parts of the report (e.g., Introduction, Clinical Examination, Diagnosis, etc.).
    Analysis of internal organization: Determine the hierarchy within each section (e.g., subheadings, paragraphs, tables).
    Definition of information categories: Classify the data contained in each section (e.g., administrative information, observed symptoms, prescribed treatments).
    Presentation in structured form: Provide a clear and organized outline of the report by listing its sections and expected content, without revealing specific details.

Context

Analyzing the structure of a veterinary report is essential for quickly and effectively understanding its contents. This task is carried out with utmost rigor and recognized expertise, following veterinary documentation standards. It ensures logical and smooth data organization, making the information more accessible to professionals. This analysis helps improve the standardization of medical reports and optimize their readability.
    """
    second_prompt = """
# Role
You are a leading expert in writing specialized *system prompts*, tasked with structuring precise and optimized directives for an AI that transforms the transcription of a veterinary exam into a detailed report. Your expertise enables you to produce *system prompts* that are clear, rigorous, and adapted to the provided format, ensuring a smooth and professional presentation of medical information.

# Task
Your mission is to draft a *system prompt* that will guide an AI in converting a raw transcription of a veterinary exam into a structured report that conforms to the specified model. To do so, you must:
1. **Analyze the expected structure of the report** to extract the key sections.
2. **Identify the relevant elements in the transcription** and specify how to organize them.
3. **Write a clear and detailed *system prompt*** that enforces compliance with the format, tone, and medical requirements.
4. **Include strict instructions on handling medical data**, ensuring precision and thoroughness.
5. **Demand an output that conforms to the provided model**, with no addition of superfluous information or omission of critical elements.

# Context
Handling veterinary exams requires absolute scientific rigor. The goal is to transform notes that may be disorganized or dictated on the fly into a final professional document usable by clinicians, pet owners, or veterinary institutions. This work demands terminological precision, structured logic, and a complete understanding of the expected format. Your *system prompt* must ensure that the AI delivers a report faithful to the medical observations, well-organized and impeccably written.

# Examples
*(If a report model has been provided, refer to it to adapt the *system prompt*.)*
Below are three examples of sections that might be requested in the *system prompt*:

1. **Introduction and Identification**
   - Animal name, species, breed, age, gender
   - Owner: name and contact information
   - Reason for consultation

2. **Clinical Examination**
   - Temperature, weight, heart rate, and respiratory rate
   - General condition (mucous membranes, hydration, behavior)
   - Nervous, digestive, locomotor systems, etc.

3. **Conclusion and Recommendations**
   - Diagnosis or diagnostic hypotheses
   - Proposed treatment
   - Recommended follow-up
    """
    try:
      # Process the PDF with the first prompt
      initial_result = anvil.server.call("process_pdf", first_prompt, pdf_file)
      print("Initial processing result (truncated):", initial_result[:100])

      # Reprocess with the second prompt
      final_result = anvil.server.call("reprocess_output_with_prompt", initial_result, second_prompt)

      # 3) Save the final result in the database
      anvil.server.call("store_final_output_in_db", final_result, template_name)
    except Exception as e:
      print("Error transforming PDF to template:", e)
      alert(f"Error: {str(e)}")
      return

    # 4) Display the success banner in the modal
    self.call_js("showSuccessBanner")

  # ----------------------
  # New: Priority management
  # ----------------------
  def set_priority(self, template_name, new_priority, **event_args):
    """
    Called from JavaScript when the star icon of a template is clicked.
    This method updates the template's priority in the database.
    """
    print(f"Updating priority of template {template_name} to {new_priority}")
    try:
      anvil.server.call("set_priority", template_name, new_priority)
      print("Priority successfully updated on the server.")
    except Exception as e:
      print("Error updating priority:", e)
      alert(f"Error updating priority: {str(e)}")

  # ----------------------
  # New: Search functionality
  # ----------------------
  def search_templates_client(self, query, **event_args):
    print(f"search_templates_client() called with query: {query}")
    if not query:
      print("Empty query; returning initial templates.")
      templates = anvil.server.call("read_templates")
      self.call_js("populateTemplates", templates)
      return
    try:
      results = anvil.server.call("search_templates", query)
      print(f"Search returned {len(results)} results.")
      self.call_js("populateTemplates", results)
    except Exception as e:
      print("Search failed:", e)
