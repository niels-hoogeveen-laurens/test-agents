import json
from typing import Dict, Any, List
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from .topdesk_service import TopdeskService

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
    Zoek knowledge items op basis van een zoekterm in de titel.
    
    Args:
        search_term: Zoekterm om in de titel te zoeken
        limit: Maximum aantal resultaten (default: 10)
    
    Returns:
        Een lijst van knowledge items die de zoekterm bevatten
    """
    try:
        # Topdesk gebruikt FIQL queries - zoek in titel
        query = f"title=like=*{search_term}*"
        items = topdesk_service.load_knowledge_items(
            limit=limit, 
            query=query,
            fields="title,description,content,keywords,creationDate,modificationDate"
        )
        return items
    except Exception as e:
        return [{"error": f"Kon knowledge items niet doorzoeken: {str(e)}"}]

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
            fields="title,description,content,keywords,translation.content,creationDate,modificationDate"
        )
        if item:
            return item
        else:
            return {"error": f"Knowledge item met ID {identifier} niet gevonden"}
    except Exception as e:
        return {"error": f"Kon knowledge item content {identifier} niet ophalen: {str(e)}"}

# Definieer de agent (ADK verwacht 'root_agent')
root_agent = LlmAgent(
    name="TopdeskAgent",
    model="gemini-2.5-flash",
    instruction="""
    Je bent een behulpzame assistent die informatie kan ophalen van Topdesk's Knowledge Base.
    
    Je hebt toegang tot de volgende tools:
    - get_knowledge_items(limit): Haal knowledge items op
    - get_public_knowledge_items(limit): Haal alleen publieke knowledge items op
    - get_knowledge_item_by_id(identifier): Haal een specifiek knowledge item op
    - search_knowledge_items(search_term, limit): Zoek knowledge items op titel
    - get_recent_knowledge_items(limit): Haal recent aangemaakte/gewijzigde items op
    - get_concept_knowledge_items(limit): Haal items in concept status op
    - get_knowledge_item_content(identifier): Haal volledige content van een item op
    
    Wanneer gebruikers vragen stellen over knowledge base artikelen, documentatie, 
    procedures of gerelateerde informatie, gebruik dan de juiste tools om de 
    gevraagde informatie op te halen.
    
    Geef altijd duidelijke, goed gestructureerde antwoorden in het Nederlands.
    Toon relevante details zoals titels, beschrijvingen, creation/modification dates etc.
    
    Als een gebruiker om een overzicht vraagt, haal dan zowel recente items als 
    publieke items op om een compleet beeld te geven.
    
    Voor specifieke zoekopdrachten, gebruik de search functie om relevante artikelen te vinden.
    """,
    description="Een agent die data ophaalt van Topdesk Knowledge Base voor artikelen, procedures en documentatie",
    tools=[
        FunctionTool(get_knowledge_items),
        FunctionTool(get_public_knowledge_items),
        FunctionTool(get_knowledge_item_by_id),
        FunctionTool(search_knowledge_items),
        FunctionTool(get_recent_knowledge_items),
        FunctionTool(get_concept_knowledge_items),
        FunctionTool(get_knowledge_item_content)
    ]
)

def main():
    """
    Start de agent in development modus
    """
    print("🤖 Topdesk Knowledge Base Agent gestart!")
    print("💡 Deze agent kan:")
    print("   - Knowledge items ophalen van Topdesk")
    print("   - Publieke knowledge items tonen")
    print("   - Specifieke artikelen opzoeken via ID")
    print("   - Knowledge base doorzoeken op titel")
    print("   - Recente wijzigingen tonen")
    print("   - Concept artikelen ophalen")
    print("   - Volledige content van artikelen ophalen")
    print()
    print("🌐 Start de ADK development UI met:")
    print("   adk dev json_agent/root_agent.py")
    print()
    print("🧪 Of test lokaal met:")
    print('   python -c "from json_agent.root_agent import root_agent; print(root_agent.run(\'Laat me de laatste knowledge items zien\'))"')

if __name__ == "__main__":
    main()