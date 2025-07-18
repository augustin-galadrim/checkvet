import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server

# translations.py

# Base language (English) is the default.
# You can leave the English dictionary empty (or have keys mapping to themselves).
ENGLISH_LOCALE = {
    # (Using English as the key text)
}

FRENCH_LOCALE = {
    # Navigation & common labels
    "Production": "Production",
    "Templates/AI": "Templates/IA",  # You may choose "Modèles/IA" if preferred.
    "Archives": "Archives",
    "Settings": "Paramètres",
    "+ Create": "+ Créer",
    "Search": "Rechercher",
    "Language": "Langue",
    "English": "Anglais",
    "Français": "Français",
    "Español": "Espagnol",
    "Deutsch": "Allemand",
    # Status bar (from Archives)
    "Show all": "Afficher tout",
    "Needs correction": "À corriger",
    "Validated": "Validé",
    "Sent": "Envoyé",
    # Veterinarian filtering
    "Veterinarians": "Vétérinaires",
    "Sort by veterinarian": "Trier par vétérinaire",
    "Back": "Retour",
    "Add veterinarians": "Ajouter des vétérinaires",
    "Add a veterinarian": "Ajouter un vétérinaire",
    "Search for a user": "Rechercher un utilisateur",
    "No results.": "Aucun résultat.",
    # Audio & Editor section
    "Copy": "Copier",
    "Status": "Statut",
    "Archive": "Archiver",
    "Share": "Partager",
    "Retry processing my audio": "Relancer l'IA sur mon audio",
    "Select Patient": "Sélectionner un patient",
    "New patient": "Nouveau patient",
    "Select Template": "Sélectionner un template",
    "Edit Report": "Modifier le rapport",
    # Registration modal
    "Welcome!": "Bienvenue !",
    "Please enter your details to register:": "Veuillez entrer vos informations pour vous inscrire :",
    "Name": "Nom",
    "Phone": "Téléphone",
    "Cancel": "Annuler",
    "Next": "Suivant",
    "Select Your Specialité": "Sélectionnez votre spécialité",
    "Please select one of the following options:": "Veuillez sélectionner une des options suivantes :",
    "Equin": "Equin",
    "Chiens et Chats": "Chiens et Chats",
    "Patients divers": "Patients divers",
    "Submit": "Soumettre",
    # Settings form
    "Email": "Email",
    "Structure": "Structure",
    "Independent": "Indépendant",
    "Signature": "Signature",
    "Report Header": "En-tête du rapport",
    "Report Footer": "Pied de page du rapport",
    "Supervisor": "Superviseur",
    "Update Settings": "Mettre à jour les paramètres",
    # Templates / AI management
    "Personalize your AI": "Personaliser votre IA",
    "Welcome to template customization": "Bienvenue dans la personnalisation de templates",
    "Please select a PDF document:": "Veuillez sélectionner un document PDF :",
    "Template name:": "Nom du template :",
    "Transform into template": "Transformer en template",
    "Congratulations, you have a new template!": "Bravo, vous avez un nouveau template !"
}

SPANISH_LOCALE = {
    "Production": "Producción",
    "Templates/AI": "Plantillas/IA",
    "Archives": "Archivos",
    "Settings": "Configuración",
    "+ Create": "+ Crear",
    "Search": "Buscar",
    "Language": "Idioma",
    "English": "Inglés",
    "Français": "Francés",
    "Español": "Español",
    "Deutsch": "Alemán",
    # Status bar
    "Show all": "Mostrar todo",
    "Needs correction": "A corregir",
    "Validated": "Validado",
    "Sent": "Enviado",
    # Veterinarian filtering
    "Veterinarians": "Veterinarios",
    "Sort by veterinarian": "Ordenar por veterinario",
    "Back": "Volver",
    "Add veterinarians": "Agregar veterinarios",
    "Add a veterinarian": "Agregar un veterinario",
    "Search for a user": "Buscar un usuario",
    "No results.": "Sin resultados.",
    # Audio & Editor section
    "Copy": "Copiar",
    "Status": "Estado",
    "Archive": "Archivar",
    "Share": "Compartir",
    "Retry processing my audio": "Reiniciar la IA en mi audio",
    "Select Patient": "Seleccionar paciente",
    "New patient": "Nuevo paciente",
    "Select Template": "Seleccionar plantilla",
    "Edit Report": "Editar informe",
    # Registration modal
    "Welcome!": "¡Bienvenido!",
    "Please enter your details to register:": "Por favor, introduzca sus datos para registrarse:",
    "Name": "Nombre",
    "Phone": "Teléfono",
    "Cancel": "Cancelar",
    "Next": "Siguiente",
    "Select Your Specialité": "Seleccione su especialidad",
    "Please select one of the following options:": "Por favor, seleccione una de las siguientes opciones:",
    "Equin": "Equino",
    "Chiens et Chats": "Perros y Gatos",
    "Patients divers": "Pacientes diversos",
    "Submit": "Enviar",
    # Settings form
    "Email": "Email",
    "Structure": "Estructura",
    "Independent": "Independiente",
    "Signature": "Firma",
    "Report Header": "Encabezado del informe",
    "Report Footer": "Pie de página del informe",
    "Supervisor": "Supervisor",
    "Update Settings": "Actualizar configuración",
    # Templates / AI management
    "Personalize your AI": "Personaliza tu IA",
    "Welcome to template customization": "Bienvenido a la personalización de plantillas",
    "Please select a PDF document:": "Por favor seleccione un documento PDF:",
    "Template name:": "Nombre de la plantilla:",
    "Transform into template": "Transformar en plantilla",
    "Congratulations, you have a new template!": "¡Enhorabuena, tienes una nueva plantilla!"
}

GERMAN_LOCALE = {
    "Production": "Produktion",
    "Templates/AI": "Vorlagen/KI",
    "Archives": "Archive",
    "Settings": "Einstellungen",
    "+ Create": "+ Erstellen",
    "Search": "Suchen",
    "Language": "Sprache",
    "English": "Englisch",
    "Français": "Französisch",
    "Español": "Spanisch",
    "Deutsch": "Deutsch",
    # Status bar
    "Show all": "Alle anzeigen",
    "Needs correction": "Zu korrigieren",
    "Validated": "Bestätigt",
    "Sent": "Gesendet",
    # Veterinarian filtering
    "Veterinarians": "Tierärzte",
    "Sort by veterinarian": "Nach Tierarzt sortieren",
    "Back": "Zurück",
    "Add veterinarians": "Tierärzte hinzufügen",
    "Add a veterinarian": "Einen Tierarzt hinzufügen",
    "Search for a user": "Einen Benutzer suchen",
    "No results.": "Keine Ergebnisse.",
    # Audio & Editor section
    "Copy": "Kopieren",
    "Status": "Status",
    "Archive": "Archivieren",
    "Share": "Teilen",
    "Retry processing my audio": "Starte die KI für mein Audio neu",
    "Select Patient": "Patient auswählen",
    "New patient": "Neuer Patient",
    "Select Template": "Vorlage auswählen",
    "Edit Report": "Bericht bearbeiten",
    # Registration modal
    "Welcome!": "Willkommen!",
    "Please enter your details to register:": "Bitte geben Sie Ihre Daten zur Registrierung ein:",
    "Name": "Name",
    "Phone": "Telefon",
    "Cancel": "Abbrechen",
    "Next": "Weiter",
    "Select Your Specialité": "Wählen Sie Ihre Spezialität",
    "Please select one of the following options:": "Bitte wählen Sie eine der folgenden Optionen:",
    "Equin": "Pferd",  # You may adjust this as needed.
    "Chiens et Chats": "Hunde und Katzen",
    "Patients divers": "Verschiedene Patienten",
    "Submit": "Absenden",
    # Settings form
    "Email": "Email",
    "Structure": "Struktur",
    "Independent": "Unabhängig",
    "Signature": "Unterschrift",
    "Report Header": "Berichtsüberschrift",
    "Report Footer": "Berichtsfußzeile",
    "Supervisor": "Supervisor",
    "Update Settings": "Einstellungen aktualisieren",
    # Templates / AI management
    "Personalize your AI": "Passe deine KI an",
    "Welcome to template customization": "Willkommen zur Vorlagenanpassung",
    "Please select a PDF document:": "Bitte wählen Sie ein PDF-Dokument aus:",
    "Template name:": "Vorlagenname:",
    "Transform into template": "In Vorlage umwandeln",
    "Congratulations, you have a new template!": "Glückwunsch, Sie haben eine neue Vorlage!"
}
