import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import json
import openai

@anvil.server.callable
def get_user_reports():
  current_user = anvil.users.get_user()
  if not current_user:
    raise Exception("User not authenticated")

  reports = app_tables.reports.search(owner=current_user)

  # Log each row's fileName and report values
  for row in reports:
    print(f"DEBUG: Row: {row}, fileName: {row['fileName']}, report: {row['report']}")

  valid_reports = []
  for row in reports:
    file_name = row['fileName'] if row['fileName'] else 'Unnamed Report'
    report_data = row['report'] if row['report'] else {}
    valid_reports.append({'fileName': file_name, 'Report': report_data})

  return valid_reports







@anvil.server.callable
def get_report_content(file_name):
  print(f"Server: get_report_content called with file_name: {file_name}")
  user = anvil.users.get_user()
  if not user:
    print("Server: User not logged in")
    return None, "User not logged in"

  # Safeguard: Ensure file_name is a string
  if not isinstance(file_name, str):
    print("Server: Invalid file_name format")
    return None, "Invalid file name format"

  # Query using the 'fileName' column and the current user
  try:
    report = app_tables.reportstable.get(
        owner=user,
        fileName=file_name  # Query directly using the text column
    )
  except Exception as e:
    print(f"Server: Error during query - {e}")
    return None, "Error querying the database"

  if report:
    content = report.get('report', {}).get('content', "No content available")
    print(f"Server: Report found, returning content: {content[:100]}...")
    return content, None
  else:
    print(f"Server: No report found with fileName: {file_name}")
    return None, f"No report found with fileName: {file_name}"






# SELECTION

@anvil.server.callable
def get_horses_for_current_user():
  current_user = anvil.users.get_user()
  if current_user:
    horses = [(row['horseName'], row['horseName']) for row in app_tables.horsestable.search(vet=current_user)]
    # Add the default option and "All" option at the beginning of the list
    return [("Select a horse", None), ("All", "All")] + horses
  else:
    return [("Select a horse", None), ("All", "All")]




@anvil.server.callable
def get_filtered_user_reports(horse_name=None):
  current_user = anvil.users.get_user()

  if not current_user:
    raise Exception("User not authenticated")

  if horse_name and horse_name != "Select a horse":
    # First, get the horse Row object from HorsesTable
    horse_row = app_tables.horsestable.get(horseName=horse_name)

    if horse_row:
      # Query reports for the current user and specific horse
      reports = app_tables.reportstable.search(
          owner=current_user,
          horseName=horse_row
      )
    else:
      # If no matching horse is found, return an empty list
      return []
  else:
    # Query all reports for the current user
    reports = app_tables.reportstable.search(owner=current_user)

  # Return the filtered reports as a list of dictionaries
  return [{'Reports': r['reports'], 'horseName': r['horseName']['horseName'] if r['horseName'] else 'Unknown'} for r in reports]


@anvil.server.callable
def save_report_with_images(report_name, content, images):
  print(f"DEBUG: report_name = {report_name}")
  print(f"DEBUG: content received = {content}")
  print(f"DEBUG: images received = {images}")

  user = anvil.users.get_user()
  if not user:
    print("Server: User not logged in")
    return False

  try:
    # Parse the content as JSON
    rich_text_content = json.loads(content)
    print(f"DEBUG: Parsed rich_text_content = {rich_text_content}")

    # Get the report or create a new one if it doesn't exist
    report = app_tables.reportstable.get(owner=user, fileName=report_name)
    if not report:
      report = app_tables.reportstable.add_row(owner=user, fileName=report_name)
      print(f"Server: Created new report with name: {report_name}")

    # Update the report content
    report['report'] = rich_text_content
    report.update()

    # Handle embedded images if present
    if images:
      print(f"DEBUG: Processing images = {images}")
      # First remove any existing images for this report
      existing_images = app_tables.embeddedimagesreportstable.search(
          owner=user,
          report_id=report
      )
      for img in existing_images:
        img.delete()

      # Add new images
      for image in images:
        print(f"DEBUG: Adding image = {image}")
        app_tables.embeddedimagesreportstable.add_row(
            owner=user,
            media=image['media'],
            report_id=report,
            reference_id=image.get('reference_id', None),
            position=image.get('position', None)
        )

    print("Server: Report and embedded images saved successfully")
    return True
  except json.JSONDecodeError as e:
    print(f"Error decoding JSON content: {e}")
    return False
  except Exception as e:
    print(f"Error saving report: {str(e)}")
    return False


@anvil.server.callable
def save_report_with_images_and_meta_data(report_name, content, images, horse_row):
  print("DEBUG: Entered save_report_with_images_and_meta_data")
  print(f"DEBUG: report_name = {report_name}")
  print(f"DEBUG: Content type = {type(content)} | Content length = {len(content) if content else 'N/A'}")
  print(f"DEBUG: Images count = {len(images) if images else 0}")
  print(f"DEBUG: horse_row = {horse_row}")

  user = anvil.users.get_user()
  if not user:
    print("ERROR: User not logged in")
    return False

  try:
    # Parse content as JSON
    try:
      rich_text_content = json.loads(content)
      print(f"DEBUG: Parsed rich_text_content keys = {list(rich_text_content.keys())}")
    except json.JSONDecodeError as e:
      print(f"ERROR: JSONDecodeError - Content is not valid JSON: {e}")
      return False

    # Fetch or create the report
    report = app_tables.reportstable.get(owner=user, fileName=report_name)
    if not report:
      report = app_tables.reportstable.add_row(
          owner=user,
          fileName=report_name,
          horseName=horse_row  # Link the horse_row
      )
      print(f"DEBUG: Created new report: {report_name}")
    else:
      print(f"DEBUG: Existing report found: {report_name}")
      report.update(horseName=horse_row)

    # Update report content
    report['report'] = rich_text_content
    report.update()
    print(f"DEBUG: Updated report content for: {report_name}")

    # Process images
    if images:
      print(f"DEBUG: Processing {len(images)} images")
      # Remove existing images
      existing_images = app_tables.embeddedimagesreportstable.search(
          owner=user,
          report_id=report
      )
      for img in existing_images:
        print(f"DEBUG: Deleting existing image: {img['reference_id']}")
        img.delete()

      # Add new images
      for idx, image in enumerate(images):
        print(f"DEBUG: Adding image {idx + 1}: {image}")
        app_tables.embeddedimagesreportstable.add_row(
            owner=user,
            media=image['media'],
            report_id=report,
            reference_id=image.get('reference_id', f"img_{idx}"),
            position=image.get('position', None)
        )

    print("SUCCESS: Report and associated images saved successfully")
    return True
  except Exception as e:
    print(f"ERROR: Exception occurred while saving report: {str(e)}")
    return False






@anvil.server.callable
def load_report_content(clicked_value):
  print(f"Server: load_report_content called with report_name: {clicked_value}")

  # Validate input
  if not isinstance(clicked_value, dict) or 'fileName' not in clicked_value:
    print("Server: Invalid clicked_value format")
    return None, "Invalid report selection"

  # Extract fileName
  file_name = clicked_value['fileName']

  # Query the database
  user = anvil.users.get_user()
  if not user:
    print("Server: User not logged in")
    return None, "User not logged in"

  try:
    # Query ReportsTable by fileName
    report_row = app_tables.reportstable.get(owner=user, fileName=file_name)
  except Exception as e:
    print(f"Server: Error during query - {e}")
    return None, "Error querying the database"

  if report_row:
    report_content = report_row['report'].get('content', "No content available")
    print(f"Server: Report found, returning content: {report_content[:100]}...")
    return report_content, None
  else:
    print(f"Server: No report found with fileName: {file_name}")
    return None, f"No report found with fileName: {file_name}"




@anvil.server.callable
def get_reports_by_structure(structure_name):
  print(f"DEBUG: Entering get_reports_by_structure with structure_name='{structure_name}'")

  try:
    # 1) Look up the structure row
    structure_row = app_tables.structures.get(name=structure_name)
    if not structure_row:
      print(f"DEBUG: No 'structures' row found with name '{structure_name}'")
      return []

    # 2) Get all users in that structure
    users_in_structure = app_tables.users.search(structure=structure_row)
    user_rows = list(users_in_structure)  # convert to a list for re-use

    print(f"DEBUG: Found {len(user_rows)} user(s) in structure '{structure_name}'")

    if not user_rows:
      return []

    # 3) Search for reports whose 'vet' is in the user_rows list
    reports_query = app_tables.reports.search(vet=q.any_of(*user_rows))

    # 4) Build a list of dicts to return
    results = []
    for report_row in reports_query:
      # Safely pull the animal's name
      animal_row = report_row['animal']
      animal_name = animal_row['name'] if animal_row else None

      # Format last_modified as a string (optional)
      dt_str = None
      if report_row['last_modified']:
        dt_str = report_row['last_modified'].strftime("%Y-%m-%d %H:%M:%S")

      results.append({
          "file_name": report_row["file_name"],
          # Add the animal name
          "name": animal_name,
          # Use formatted last_modified
          "last_modified": dt_str,
          "owner_email": report_row["vet"]["email"] if report_row["vet"] else None,
          "report_rich": report_row["report_rich"],
          "statut": report_row["statut"],
      })

    print(f"DEBUG: Returning {len(results)} report(s) for structure '{structure_name}'")
    return results

  except Exception as e:
    print(f"ERROR: Unexpected error in get_reports_by_structure: {e}")
    return []
