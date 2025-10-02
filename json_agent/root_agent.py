import json
import logging
from typing import Dict, Any, List
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from .topdesk_service import TopdeskService

# Setup Logger
logger = logging.getLogger(__name__)

# Initialize Topdesk service
topdesk_service = TopdeskService()

# Custom functions voor Topdesk API
def get_knowledge_items(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Haal knowledge items op van Topdesk.
    
    Args:
        limit: Maximum aantal knowledge items om op te halen (default: 5)
    
    Returns:
        Een lijst van knowledge items met title, description, content etc.
    """
    try:
        items = topdesk_service.load_knowledge_items(limit=limit)
        return items
    except Exception as e:
        logger.error(f"Error in get_knowledge_items: {str(e)}")
        return [{"error": f"Kon knowledge items niet ophalen: {str(e)}"}]

def get_public_knowledge_items(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Haal alleen publieke knowledge items op van Topdesk.
    
    Args:
        limit: Maximum aantal knowledge items om op te halen (default: 5)
    
    Returns:
        Een lijst van publieke knowledge items
    """
    try:
        items = topdesk_service.load_knowledge_items(limit=limit, public_only=True)
        return items
    except Exception as e:
        return [{"error": f"Kon publieke knowledge items niet ophalen: {str(e)}"}]

def get_knowledge_item_by_id(identifier: str) -> Dict[str, Any]:
    """
    Haal een specifiek knowledge item op via ID.
    
    Args:
        identifier: ID van het knowledge item
    
    Returns:
        Het knowledge item als dictionary of None als niet gevonden
    """
    try:
        item = topdesk_service.load_knowledge_item_by_identifier(identifier)
        if item:
            return item
        else:
            return {"error": f"Knowledge item met ID {identifier} niet gevonden"}
    except Exception as e:
        return {"error": f"Kon knowledge item {identifier} niet ophalen: {str(e)}"}

def search_knowledge_items(search_term: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Zoek knowledge items op basis van een zoekterm.
    Deze functie voert een full-text search uit op titel, content en trefwoorden.
    
    Args:
        search_term: Zoekterm om te gebruiken.
        limit: Maximum aantal resultaten (default: 10)
    
    Returns:
        Een lijst van gevonden knowledge items.
    """
    try:
        # DEFINITIEVE CORRECTIE 2: Dit API endpoint gebruikt de 'searchTerm' parameter
        # voor een full-text search, in plaats van een FIQL query op het 'title' veld.
        items = topdesk_service.load_knowledge_items(
            limit=limit,
            search_term=search_term, # Aangepast van 'query' naar 'search_term'
            fields="title,description,keywords,creationDate,modificationDate"
        )
        if not items:
            return [{"message": f"Geen kennisartikelen gevonden die '{search_term}' bevatten."}]
        return items
    except Exception as e:
        return [{"error": f"Kon knowledge items niet doorzoeken met zoekterm '{search_term}': {str(e)}"}]

def get_recent_knowledge_items(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Haal recent aangemaakte of gewijzigde knowledge items op.
    
    Args:
        limit: Maximum aantal items om op te halen (default: 5)
    
    Returns:
        Een lijst van recent aangepaste knowledge items
    """
    try:
        items = topdesk_service.load_modification_date(
            limit=limit,
            fields="title,description,creationDate,modificationDate"
        )
        return items
    except Exception as e:
        return [{"error": f"Kon recente knowledge items niet ophalen: {str(e)}"}]

def get_concept_knowledge_items(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Haal knowledge items op die nog in concept status zijn.
    
    Args:
        limit: Maximum aantal items om op te halen (default: 10)
    
    Returns:
        Een lijst van knowledge items in concept status
    """
    try:
        items = topdesk_service.load_modification_date(
            limit=limit,
            query="status.name==in=(Concept)",
            fields="title,description,creationDate,modificationDate"
        )
        return items
    except Exception as e:
        return [{"error": f"Kon concept knowledge items niet ophalen: {str(e)}"}]

def get_knowledge_item_content(identifier: str) -> Dict[str, Any]:
    """
    Haal de volledige content van een knowledge item op.
    
    Args:
        identifier: ID van het knowledge item
    
    Returns:
        Het knowledge item met volledige content
    """
    try:
        item = topdesk_service.load_knowledge_item_by_identifier(
            identifier,
            fields="title,description,content,keywords,creationDate,modificationDate"
        )
        if item:
            return item
        else:
            return {"error": f"Knowledge item met ID {identifier} niet gevonden"}
    except Exception as e:
        return {"error": f"Kon knowledge item content {identifier} niet ophalen: {str(e)}"}


def get_incidents_by_caller(caller_email: str, status: str = "open") -> List[Dict[str, Any]]:
    """
    Haal incidenten (tickets) op voor een specifieke medewerker op basis van e-mailadres.
    Standaard worden alleen openstaande tickets opgehaald.

    Args:
        caller_email: Het e-mailadres van de medewerker (aanmelder).
        status: De status van de tickets om op te filteren ('open' of 'closed'). Default is 'open'.

    Returns:
        Een lijst van incidenten die voldoen aan de criteria.
    """
    try:
        # FIQL query om te filteren op e-mailadres van de aanmelder en status
        if status == "open":
            status_query = "processingStatus.name!=in=(Afgehandeld,Gesloten)"
        else:
            status_query = "processingStatus.name==in=(Afgehandeld,Gesloten)"
        
        query = f"caller.emailAddress=='{caller_email}' and {status_query}"
        
        incidents = topdesk_service.load_incidents(
            query=query,
            fields="number,briefDescription,processingStatus.name,operator.name,creationDate,targetDate",
            limit=20
        )
        if not incidents:
            return [{"message": f"Geen {status}e tickets gevonden voor {caller_email}."}]
        return incidents
    except Exception as e:
        logger.error(f"Error in get_incidents_by_caller: {str(e)}")
        return [{"error": f"Kon incidenten niet ophalen voor {caller_email}: {str(e)}"}]

def get_incident_by_number(incident_number: str) -> Dict[str, Any]:
    """
    Haal een specifiek incident (ticket) op basis van het ticketnummer.

    Args:
        incident_number: Het volledige nummer van het incident (bv. 'I-2403-0012').

    Returns:
        De details van het gevonden incident of een foutmelding.
    """
    try:
        query = f"number=='{incident_number}'"
        incidents = topdesk_service.load_incidents(
            query=query,
            fields="number,briefDescription,detailedDescription,processingStatus.name,operator.name,caller.dynamicName,creationDate,targetDate,action"
        )
        return incidents[0] if incidents else {"error": f"Incident {incident_number} niet gevonden."}
    except Exception as e:
        logger.error(f"Error in get_incident_by_number: {str(e)}")
        return {"error": f"Kon incident {incident_number} niet ophalen: {str(e)}"}

# Definieer de agent (ADK verwacht 'root_agent')
root_agent = LlmAgent(
    name="TopdeskLaurensAgent",
    model="gemini-2.5-flash",
    instruction="""
Je bent een slimme en behulpzame Topdesk assistent voor Zorgstichting Laurens. Jouw doel is om medewerkers snel en efficiënt te helpen met hun vragen over IT en facilitaire zaken door informatie uit Topdesk op te halen.

Je hebt twee hoofdtaken:
1.  **Kennis verschaffen**: Doorzoek de Kennisbank (Knowledge Base) voor handleidingen, procedures en antwoorden op veelgestelde vragen.
2.  **Inzicht geven in Meldingen (Tickets)**: Geef medewerkers statusupdates over hun ingediende meldingen (incidenten).

**BELANGRIJKE REGELS VOOR INTERACTIE:**
-   **Identificeer de gebruiker voor tickets**: Als een gebruiker vraagt naar "mijn tickets", "de status van mijn melding" of iets vergelijkbaars, vraag dan ALTIJD eerst naar hun e-mailadres. Zeg bijvoorbeeld: "Natuurlijk, ik kijk het graag voor je na. Wat is je e-mailadres?". Gebruik dit e-mailadres vervolgens met de `get_incidents_by_caller` tool.
-   **Wees duidelijk en beknopt**: Geef antwoorden in helder Nederlands. Gebruik lijsten of opsommingen om informatie overzichtelijk te presenteren.
-   **Verwijs naar de bron**: Als je informatie uit een kennisartikel haalt, vermeld dan de titel van het artikel. Als je ticketinformatie geeft, vermeld dan altijd het ticketnummer.
-   **Denk stapsgewijs**: Bepaal eerst of de vraag over de Kennisbank of over een Ticket gaat. Kies daarna de juiste tool.

**Beschikbare Tools:**

**// Kennisbank Tools**
- `search_knowledge_items(search_term, limit)`: Doorzoek de kennisbank op een trefwoord. Gebruik dit voor algemene vragen zoals "hoe installeer ik een printer?".
- `get_knowledge_item_by_id(identifier)`: Haal een specifiek artikel op als het ID bekend is.
- `get_recent_knowledge_items(limit)`: Toon de meest recent gewijzigde kennisartikelen.
- `get_public_knowledge_items(limit)`: Haal publieke kennisartikelen op.

**// Incidenten (Tickets) Tools**
- `get_incidents_by_caller(caller_email, status)`: Haal openstaande of gesloten tickets op voor een medewerker via hun e-mailadres. Gebruik `status='open'` voor actieve tickets en `status='closed'` voor afgeronde tickets.
- `get_incident_by_number(incident_number)`: Haal de details van één specifiek ticket op aan de hand van het nummer (bv. 'I-2403-0012').
    """,
    description="Een agent die medewerkers van Zorgstichting Laurens helpt met de Topdesk Kennisbank en hun tickets.",
    tools=[
        # Kennisbank tools (bestaand)
        FunctionTool(get_knowledge_items),
        FunctionTool(get_public_knowledge_items),
        FunctionTool(get_knowledge_item_by_id),
        FunctionTool(search_knowledge_items),
        FunctionTool(get_recent_knowledge_items),
        FunctionTool(get_concept_knowledge_items),
        FunctionTool(get_knowledge_item_content),
        
        # NIEUWE Incident tools
        FunctionTool(get_incidents_by_caller),
        FunctionTool(get_incident_by_number)
    ]
)

def main():
    """
    Start de agent in development modus
    """
    print("🚀 Topdesk Agent voor Zorgstichting Laurens gestart!")
    print("✅ Deze agent kan nu:")
    print("   - Knowledge items ophalen van Topdesk")
    print("   - Publieke knowledge items tonen")
    print("   - Specifieke artikelen opzoeken via ID")
    print("   - Knowledge base doorzoeken op titel")
    print("   - Recente wijzigingen tonen")
    print("   - Concept artikelen ophalen")
    print("   - Volledige content van artikelen ophalen")
    print("   - Tickets opvragen per medewerker (op e-mail)")
    print("   - Specifieke tickets opzoeken via ticketnummer")
    print()
    print("🌐 Start de ADK development UI met:")
    print("   adk dev json_agent/root_agent.py")
    print()
    print("🧪 Of test lokaal met een vraag over tickets:")
    print('   python -c "from json_agent.root_agent import root_agent; print(root_agent.run(\'Wat zijn mijn openstaande tickets? Mijn email is medewerker@laurens.nl\'))"')

if __name__ == "__main__":
    main()