import anvil.server
import anvil.media
from ..logging_server import get_logger
import io

try:
  from weasyprint import HTML, CSS
except ImportError:
  raise ImportError(
    "The 'weasyprint' library is not installed in the server environment."
  )

logger = get_logger(__name__)


@anvil.server.callable(require_user=True)
def generate_pdf_from_html(html_content):
  """
  Generates a temporary PDF from HTML content using the WeasyPrint library.

  Args:
    html_content (str): The HTML string from the TextEditor component.

  Returns:
    Anvil Media Object: A temporary, in-memory PDF file.
  """
  logger.info("Starting PDF generation from HTML content using WeasyPrint.")

  try:
    # Create a BytesIO buffer to hold the PDF data in memory
    pdf_buffer = io.BytesIO()

    # Basic CSS for printing, like setting margins.
    # This makes the output look more professional.
    css = CSS(
      string="""
            /* --- 1. PAGE SETUP --- */
            @page {
                size: A4; /* Standard document size */
                margin: 2cm; /* Professional margins */
            }

            /* --- 2. GLOBAL TYPOGRAPHY & RESET --- */
            body {
                font-family: 'Helvetica', 'Arial', sans-serif; /* Common, professional fonts */
                font-size: 11pt; /* Standard document font size, more predictable than px */
                line-height: 1.4; /* Tighter, more readable line spacing than 1.6 */
                color: #333333; /* Softer than pure black */
            }

            /* Resetting defaults for consistency */
            h1, h2, h3, p, ul, li {
                margin: 0;
                padding: 0;
                font-weight: normal; /* Solves the "bold titles" issue */
            }

            /* --- 3. HEADINGS & STRUCTURE --- */
            h1 {
                font-size: 1.6em; /* 1.6 * 11pt = ~17.6pt */
                text-align: center;
                margin-bottom: 25px;
                color: #111111;
                font-weight: bold; /* Make the main title bold explicitly */
            }

            h2 {
                font-size: 1.3em; /* 1.3 * 11pt = ~14.3pt */
                margin-top: 25px;
                padding-bottom: 6px;
                border-bottom: 1px solid #cccccc;
                color: #111111;
                font-weight: bold; /* Make section titles bold explicitly */
            }

            h3 {
                font-size: 1.1em; /* 1.1 * 11pt = ~12.1pt */
                margin-top: 20px;
                margin-left: 5px; /* Slight indent for sub-sections */
                color: #222222;
                font-weight: bold; /* Sub-headings can also be bold */
            }

            /* --- 4. CONTENT ELEMENTS --- */
            p {
                margin-top: 8px; /* Space between paragraphs */
                margin-left: 10px;
            }
            
            /* Make text inside <p> that is marked as bold stand out */
            p b, p strong {
                color: #000000;
            }

            ul {
                margin-top: 8px;
                margin-left: 25px; /* Standard indentation for lists */
                list-style-type: disc; /* Use standard bullets for clarity */
            }

            li {
                margin-bottom: 5px; /* Space between list items */
            }

            /* Nested lists get a different style */
            ul ul {
                list-style-type: circle;
                margin-top: 5px;
            }

            /* --- 5. TABLE STYLING (Proactive for future use) --- */
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }
            
            th, td {
                border: 1px solid #dddddd;
                text-align: left;
                padding: 8px;
            }
            
            th {
                background-color: #f2f2f2;
                font-weight: bold;
            }
        """
    )

    # Create a WeasyPrint HTML object from the string content
    html = HTML(string=html_content)

    # Render the PDF into the in-memory buffer, applying the CSS
    html.write_pdf(pdf_buffer, stylesheets=[css])

    # Get the raw bytes from the buffer
    pdf_bytes = pdf_buffer.getvalue()

    # Create and return an Anvil Media Object
    # The client will receive this and can initiate a download.
    # --- THIS IS THE CORRECTED LINE ---
    pdf_media = anvil.BlobMedia(
      content_type="application/pdf", content=pdf_bytes, name="report.pdf"
    )

    logger.info("PDF generation with WeasyPrint successful.")
    return pdf_media

  except Exception as e:
    logger.error(f"Failed to generate PDF with WeasyPrint: {e}", exc_info=True)
    # Re-raise the exception so the client can show an alert
    raise Exception(f"PDF generation failed on the server: {e}")
