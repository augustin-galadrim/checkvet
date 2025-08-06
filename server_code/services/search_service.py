import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server


from anvil.tables import order_by


@anvil.server.callable
def search_reports_for_all_vets_in_structure(search_input):
  try:
    print(
      "search_reports_for_all_vets_in_structure called with search_input:", search_input
    )

    # Validate input type.
    if not isinstance(search_input, str):
      raise ValueError("Search input must be a string")

    search_term = search_input.strip()
    print("Processed search term:", search_term)

    # Get the current user's structure name (using your existing pick_user_info function)
    structure_name = anvil.server.call("pick_user_info", "structure")
    if not structure_name:
      raise Exception("No structure found for current user.")
    print("Structure name:", structure_name)

    # Look up the structure row.
    structure_row = app_tables.structures.get(name=structure_name)
    if not structure_row:
      print(f"No structure row found with name '{structure_name}'")
      return []
    print(f"Found structure row for '{structure_name}'")

    # Get all users (vets) in that structure.
    user_rows = list(app_tables.users.search(structure=structure_row))
    print(f"Found {len(user_rows)} user(s) in structure '{structure_name}'")
    if not user_rows:
      return []

    # Retrieve all reports whose 'vet' is in the list of user rows.
    reports_rows = list(app_tables.reports.search(vet=q.any_of(*user_rows)))
    print(f"Found {len(reports_rows)} report(s) in structure '{structure_name}'")

    # Apply search filtering if a search term was provided.
    if search_term:
      # First, filter by file_name.
      filtered_reports = [
        r for r in reports_rows if search_term.lower() in (r["file_name"] or "").lower()
      ]
      print(f"Reports matching file_name: {len(filtered_reports)}")

      # If none match by file_name, try filtering by the animal's name.
      if not filtered_reports:
        filtered_reports = [
          r
          for r in reports_rows
          if r["animal"] and search_term.lower() in (r["animal"]["name"] or "").lower()
        ]
        print(f"Reports matching animal name: {len(filtered_reports)}")
    else:
      filtered_reports = reports_rows

    # Format each report into a dictionary.
    results = []
    for r in filtered_reports:
      # Extract patient name from the animal row.
      # (Since table 'animals' stores the patient name in its 'name' header.)
      patient_name = r["animal"]["name"] if r["animal"] is not None else ""

      # Format last_modified as a string.
      dt_str = "N/A"
      if r["last_modified"]:
        try:
          dt_str = r["last_modified"].strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
          print("Error formatting last_modified for report", r.get_id(), ":", e)
          dt_str = "N/A"

      results.append({
        "id": r.get_id(),
        "file_name": r["file_name"],
        "name": patient_name,  # Patient name returned as 'name'
        "last_modified": dt_str,
        "owner_email": r["vet"]["email"] if r["vet"] else None,
        "report_rich": r["report_rich"],
        "statut": r["statut"],
      })

    print(
      f"Returning {len(results)} report(s) for search input '{search_input}' in structure '{structure_name}'"
    )
    return results

  except Exception as e:
    print("Error in search_reports_for_all_vets_in_structure:", e)
    return []


@anvil.server.callable
def search_reports(search_input):
  print("received search input:")
  print(search_input)
  try:
    # Validate the input type.
    if not isinstance(search_input, str):
      raise ValueError("Search input must be a string")

    search_term = search_input.strip()

    # Get the current user.
    current_user = anvil.users.get_user()
    if not current_user:
      raise Exception("No current user is logged in.")

    # Use the 'vet' column to filter the reports for the current user.
    if not search_term:
      # If there is no search term, fetch all reports for the current user.
      rows = app_tables.reports.search(vet=current_user)
    else:
      # First, try to find reports by searching within the file_name field.
      rows = [
        r
        for r in app_tables.reports.search(vet=current_user)
        if search_term.lower() in r["file_name"].lower()
      ]

      # If no results were found, then search within the animal field.
      if not rows:
        rows = [
          r
          for r in app_tables.reports.search(vet=current_user)
          # Check that r['animal'] exists before accessing ['name']
          if r["animal"] and search_term.lower() in r["animal"]["name"].lower()
        ]

    # Format the result rows into a list of dictionaries.
    return [
      {
        "id": r.get_id(),
        "file_name": r["file_name"],
        "name": r["animal"]["name"] if r["animal"] else None,
        "statut": r["statut"],
        "report_rich": r["report_rich"],
        "last_modified": r["last_modified"].strftime("%Y-%m-%d %H:%M:%S")
        if r["last_modified"]
        else "N/A",
      }
      for r in rows
    ]

  except Exception as e:
    print(f"Search error: {str(e)}")
    return []


@anvil.server.callable
def search_patients(search_input):
  try:
    # If search_input is None, default it to an empty string.
    if search_input is None:
      search_input = ""
    if not isinstance(search_input, str):
      raise ValueError("Search input must be a string")

    # Remove extra whitespace.
    search_term = search_input.strip()

    # Get the current user.
    current_user = anvil.users.get_user()
    if not current_user:
      raise Exception("No current user is logged in.")

    # Filter rows to include only those where 'vet' matches the current user.
    if not search_term:
      rows = app_tables.animals.search(vet=current_user)
    else:
      search_lower = search_term.lower()
      # First search in the 'name' field.
      rows = [
        r
        for r in app_tables.animals.search(vet=current_user)
        if search_lower in (r["name"] or "").lower()
      ]

      # If no results, then search in 'proprietaire'.
      if not rows:
        rows = [
          r
          for r in app_tables.animals.search(vet=current_user)
          if search_lower in (r["proprietaire"] or "").lower()
        ]

    return [
      {
        "id": r.get_id(),
        "name": r["name"],
        "type": r["type"],
        "proprietaire": r["proprietaire"],
        "unique_id": r["unique_id"],
      }
      for r in rows
    ]
  except Exception as e:
    print(f"Search error: {str(e)}")
    return []


@anvil.server.callable
def search_templates(search_input):
  try:
    if not isinstance(search_input, str):
      raise ValueError("Search input must be a string")

    # Get the current user.
    current_user = anvil.users.get_user()
    if not current_user:
      raise Exception("No current user is logged in.")

    search_term = search_input.strip()

    # If nothing was typed, return all records for the current user.
    if not search_term:
      rows = app_tables.custom_templates.search(owner=current_user)
    else:
      # Search for the term within name, limited to records owned by the current user.
      rows = [
        r
        for r in app_tables.custom_templates.search(owner=current_user)
        if search_term.lower() in r["name"].lower()
      ]

    # Build the return structure.
    return [
      {
        "id": r.get_id(),
        "name": r["name"],
        "owner": r["owner"],
        "html": r["html"],
        "display": r["display"],
      }
      for r in rows
    ]

  except Exception as e:
    print(f"Search error: {str(e)}")
    return []


@anvil.server.callable
def search_users(search_input):
  try:
    # Validate the input type
    if not isinstance(search_input, str):
      raise ValueError("Search input must be a string")

    search_term = search_input.strip().lower()

    # If there is no search term, fetch all users
    if not search_term:
      rows = app_tables.users.search()
    else:
      # Pull all users and filter them in Python for case-insensitive name/email matches
      all_users = app_tables.users.search()
      rows = [
        u
        for u in all_users
        if (u["name"] and search_term in u["name"].lower())
        or (u["email"] and search_term in u["email"].lower())
      ]

    # Return a list of hard-coded dictionaries for each row
    return [
      {
        "id": user_row.get_id(),  # Anvil row ID
        "email": user_row["email"],
        "enabled": user_row["enabled"],
        "last_login": user_row["last_login"],
        "password_hash": user_row["password_hash"],
        "n_password_failures": user_row["n_password_failures"],
        "confirmed_email": user_row["confirmed_email"],
        "signed_up": user_row["signed_up"],
        "name": user_row["name"],
        "phone": user_row["phone"],
        "additional_info": user_row["additional_info"],
        "signature_image": user_row["signature_image"],
        "report_header_image": user_row["report_header_image"],
        "report_footer_image": user_row["report_footer_image"],
        "structure": user_row["structure"],
        "supervisor": user_row["supervisor"],
        "specialite": user_row["specialite"],
      }
      for user_row in rows
    ]

  except Exception as e:
    print(f"Search error: {str(e)}")
    return []
