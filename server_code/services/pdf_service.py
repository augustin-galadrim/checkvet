import anvil.server
from anvil.tables import app_tables
from ..logging_server import get_logger
import io
import base64

try:
  from weasyprint import HTML, CSS
except ImportError:
  raise ImportError(
    "The 'weasyprint' library is not installed in the server environment."
  )

logger = get_logger(__name__)


def _get_image_data_uri(asset_name):
  """
  Helper function to fetch an image from the app_assets table and convert it to a Data URI.
  Returns None if the asset is not found.
  """
  asset_row = app_tables.assets.get(name=asset_name)
  if asset_row and asset_row["file"]:
    media = asset_row["file"]
    content_type = media.get_content_type()
    base64_data = base64.b64encode(media.get_bytes()).decode("ascii")
    return f"data:{content_type};base64,{base64_data}"
  logger.warning(f"Asset '{asset_name}' not found in 'app_assets' table.")
  return None


@anvil.server.callable(require_user=True)
def generate_pdf_from_html(html_content):
  """
  Generates a PDF from HTML, with a full-width header and footer on every page,
  and a left-aligned signature at the end of the document body.
  """
  logger.info("Starting PDF generation with header, footer, and signature.")

  try:
    # --- Step 1: Fetch all required assets ---
    header_data_uri = _get_image_data_uri("default_header")
    footer_data_uri = _get_image_data_uri("default_footer")
    signature_data_uri = _get_image_data_uri("default_signature")

    # --- Step 2: Build the HTML for the signature block ---
    signature_html = ""
    if signature_data_uri:
      signature_html = f"""
            <div class="signature-section">
                <img src="{signature_data_uri}" alt="Signature">
                <p class="signature-line">Signature</p>
            </div>
            """

      # --- Step 3: Combine user content and signature into a full document ---
    full_html_document = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body>
            {html_content}
            {signature_html}
        </body>
        </html>
        """

    # --- Step 4: Build the CSS dynamically ---
    css_string = """
            /* --- 1. GLOBAL TYPOGRAPHY & RESET --- */
            body { font-family: 'Helvetica', 'Arial', sans-serif; font-size: 11pt; line-height: 1.4; color: #333333; }
            h1, h2, h3, p, ul, li { margin: 0; padding: 0; font-weight: normal; }
            h1 { font-size: 1.6em; text-align: center; margin-bottom: 25px; color: #111111; font-weight: bold; }
            h2 { font-size: 1.3em; margin-top: 25px; padding-bottom: 6px; border-bottom: 1px solid #cccccc; color: #111111; font-weight: bold; }
            h3 { font-size: 1.1em; margin-top: 20px; margin-left: 5px; color: #222222; font-weight: bold; }
            p { margin-top: 8px; margin-left: 10px; }
            p b, p strong { color: #000000; }
            ul { margin-top: 8px; margin-left: 25px; list-style-type: disc; }
            li { margin-bottom: 5px; }
            ul ul { list-style-type: circle; margin-top: 5px; }
            .signature-section { margin-top: 50px; padding-top: 15px; page-break-inside: avoid; text-align: left; }
            .signature-section img { max-width: 200px; height: auto; }
            .signature-section p.signature-line { margin-top: 5px; border-top: 1px solid #333; padding-top: 5px; font-size: 10pt; text-align: center; width: 200px; }
        """

    # Define the page layout with space for header and footer
    css_string += """
            /* --- 3. PAGE SETUP & MARGINS --- */
            @page {
                size: A4;
                margin: 3.5cm 2cm 3cm 2cm; 
                
                /* Set empty content for the margin boxes so they render */
                @top-center { content: ''; }
                @bottom-center { content: ''; }
            }
        """

    # Dynamically add the header image if it exists
    if header_data_uri:
      css_string += f"""
                @page {{
                    @top-center {{
                        /* --- THIS IS THE FIX --- */
                        background-image: url('{header_data_uri}');
                        background-repeat: no-repeat;
                        background-size: contain; /* Scale image to fit within the margin box */
                        background-position: center;
                    }}
                }}
            """

      # Dynamically add the footer image if it exists
    if footer_data_uri:
      css_string += f"""
                @page {{
                    @bottom-center {{
                        /* --- THIS IS THE FIX --- */
                        background-image: url('{footer_data_uri}');
                        background-repeat: no-repeat;
                        background-size: contain; /* Scale image to fit within the margin box */
                        background-position: center bottom; /* Align to the bottom of the margin box */
                    }}
                }}
            """

      # --- Step 5: Render the complete document to PDF ---
    pdf_buffer = io.BytesIO()
    html = HTML(string=full_html_document)
    html.write_pdf(pdf_buffer, stylesheets=[CSS(string=css_string)])

    pdf_bytes = pdf_buffer.getvalue()

    pdf_media = anvil.BlobMedia(
      content_type="application/pdf", content=pdf_bytes, name="report.pdf"
    )

    logger.info("PDF generation with header, footer, and signature successful.")
    return pdf_media

  except Exception as e:
    logger.error(f"Failed to generate PDF with WeasyPrint: {e}", exc_info=True)
    raise Exception(f"PDF generation failed on the server: {e}")
