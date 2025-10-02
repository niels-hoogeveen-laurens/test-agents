import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
import logging

# Setup Logger
logger = logging.getLogger(__name__)


class ZenyaService:
    def __init__(self):
        """
        Initializes the Zenya Service with environment variables and token settings.

        Gets the Zenya API key, URL, and username from environment variables.
        Sets the token lifetime.
        """

        # Intialize env varibles
        load_dotenv()

        # Set env variables
        self.api_key = os.environ["zenya-api-key"]
        self.api_url = os.environ["zenya-api-url"]
        self.username = os.environ["zenya-username"]

        # Token variables
        self.token = None
        self.token_expiration = None
        self.token_lifetime = 60  # in seconds

    def get_token(self):
        """
        Creates a authentication token using the Zenya API-key.
        """

        # Below url to get active token, more info:
        # https://test.iprova.nl/Api/Swagger/index.html#/Tokens/GetTokenForUser
        url = f"{self.api_url}/tokens"

        payload = {"api_key": self.api_key, "username": self.username}
        headers = {"x-api-version": "5", "Content-Type": "application/json"}

        response = requests.post(url, json=payload, headers=headers)

        # When green flag (200), save token and create an expiration date
        if response.status_code == 200:
            self.token = response.json()
            self.token_expiration = datetime.now() + timedelta(
                seconds=self.token_lifetime
            )
        else:
            raise Exception(
                f"Something went wrong while creating the token: {response.status_code} - {response.text}"
            )

    def check_token_expired(self):
        """Check if token is expired.

        Returns:
            bool: True if the token is expired, False if alive.
        """

        return self.token is None or datetime.now() >= self.token_expiration

    def get_headers(self):
        """
        Generates the request headers.

        Passes the token to the header.

        If token expired, it refreshes the token before returning the headers.

        Returns:
            dict: Headers to use in the API request.
        """

        if self.check_token_expired():
            # Overwrite old token
            self.get_token()

        return {
            "Authorization": f"token {self.token}",
            "x-api-version": "5",
            "Content-Type": "application/json",
        }

    def load_content(self, limit=50, offset=0):
        """
        This function loads all content items from the Zenya API.

        Args:
            limit (int): The maximum number of items a page (default: 50).
            offset (int): Offset for pagination (default: 0).

        Returns:
            dict: The API response containing content data (items).

        Raises:
            Exception: If API request fails.
        """

        # Below url to get content from API, more info for extra params:
        # https://test.iprova.nl/Api/Swagger/index.html#/ContentItems/GetContentItems
        url = f"{self.api_url}/portals/content_items"

        params = {
            "limit": limit,
            "offset": offset,
            "include_content_type": "true",
            "content_type_ids": "1",
            "envelope": "true",
            "include_sub_type_field": "true",
        }

        response = requests.get(url, headers=self.get_headers(), params=params)

        # When the API sends something other than a 200 message
        if response.status_code != 200:
            raise Exception(
                f"API request failed: {response.status_code} - {response.text}"
            )

        return response.json()

    def collect_documents(self, max_results: int = None):
        """
        Retrieves a list documents from the Zenya API.

        Args:
            max_results(int, optional): maximum number of documents to retrieve. If none, all documents will be collected.

        Returns:
            list: List of document (meta)data.

        Raises:
            Exception: If the API call fails or function gives an error.
        """

        documents = []
        offset = 0
        limit = 50

        while True:
            data = self.load_content(limit=limit, offset=offset)
            items = data.get("data", [])

            # check if there are no items left.
            if not items:
                break

            # Add items to list of documents
            for item in items:
                documents.append(
                    {
                        "source_item_id": item["source_item_id"],
                        "title": item["title"],
                        "doc_type": item["sub_type_field"]["name"],
                        "doc_type_id": item["sub_type_field"]["value_id"],
                        "last_modified_date_time": item.get("last_modified_date_time"),
                    }
                )
            # Stop when max is reached
            if max_results is not None and len(documents) >= max_results:
                break

            # Update offset for next page
            offset += limit

        logger.debug(
            f"Document collection completed, found {len(documents)} documents."
        )
        return documents

    def download_document(self, document_id):
        """Download document based on the document_id

        Args:
            document_id (str): ID of the document to download.

        Returns:
            bytes: Resonse content.

        Raises:
            Exception: If an error occurs during download.
        """
        url = f"{self.api_url}/documents/{document_id}/download"
        logger.debug(f"Downloading from URL: {url}")
        response = requests.get(url, headers=self.get_headers())

        if response.status_code == 200:
            logger.debug(f"Successfully downloaded document {document_id}.")
            return response.content
        else:
            logger.error(f"Can't download {document_id}: {response.status_code}")
            raise Exception(f"Can't download {document_id}: {response.status_code}")
        
    def execute_dedicated_search(self, 
                                 query: str, 
                                 portal_id: int = None,
                                 search_scope: str = None,
                                 collection_id: int = None,
                                 continuation_token: str = None, # For pagination
                                 extra_params: dict = None):
        """
        Performs a search via the dedicated Zenya /search endpoint.

        Args:
            query (str): The search term.
            portal_id (int, optional): The ID of the portal to search within.
            search_scope (str, optional): The scope of the search.
            collection_id (int, optional): The ID of the collection to search within.
            continuation_token (str, optional): Token for retrieving the next set of results.
            extra_params (dict, optional): Any additional parameters for the API.

        Returns:
            dict: De API response.

        Raises:
            Exception: If the API request fails.
        """
        url = f"{self.api_url}/search"
        
        params = {
            "searchText": query
        }

        # Checks
        if portal_id is not None:
            params["portalId"] = portal_id
        if search_scope:
            params["searchScope"] = search_scope
        if collection_id is not None:
            params["collectionId"] = collection_id
        if continuation_token:
            params["continuationToken"] = continuation_token
        
        if extra_params:
            params.update(extra_params)

        logger.debug(f"Uitvoeren dedicated search naar {url} met params: {params}")
        response = requests.get(url, headers=self.get_headers(), params=params)

        if response.status_code != 200:
            raise Exception(
                f"API verzoek via /search mislukt: {response.status_code} - {response.text}"
            )
        
        return response.json()

    def collect_dedicated_search_results(self, 
                                         query: str,
                                         portal_id: int = 119, 
                                         search_scope: str = "in_portal", 
                                         collection_id: int = None, 
                                         max_results: int = None,
                                         id_field: str = "source_item_id",
                                         title_field: str = "title",
                                         type_field_path: list = None,
                                         doc_type_path: list = None,
                                         doc_type_id_path: list = None,
                                         modified_date_path: list = None
                                        ):
        """
        Verzamelt zoekresultaten van het Zenya /search endpoint met token-gebaseerde paginering.

        Args:
            query (str): Search keywords.
            portal_id (int): ID of the portal.
            search_scope (str): Searchscope - in_portal or outside_portal.
            collection_id (int, optional): Collection ID.
            max_results (int, optioneel): Maximum number of results to collect.
        Returns:
            list: List of search results.
        """
        search_results = []
        current_continuation_token = None
        has_more_pages = True


        def get_nested_value(item, path):
            """
            Retrieves a value from a nested dictionary using a list of keys (path).

            Example: ["details", "contact", "email"] to get item["details"]["contact"]["email"].

            Returns:
                The value found at the specified path, or None if the path is invalid or the value is not found.
            """
            if not path: 
                return None
            current = item
            for key in path:
                # Check if the current level is a dictionary and the key exists.
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            return current # Return the value found at the end of the path.

        # Loop to get the search results for every page
        while has_more_pages:
            data = self.execute_dedicated_search(
                query=query,
                portal_id=portal_id,
                search_scope=search_scope,
                collection_id=collection_id,
                continuation_token=current_continuation_token
            )
            
            # logger.debug(f"Raw API response from /search: {data}")

            items = data.get("items", []) 
            if not isinstance(items, list):
                 logger.warning(f"Expected a list under 'items', but got: {type(items)}")
                 items = []

            for item in items:
                processed_item = {
                    "source_item_id": item.get(id_field),
                    "title": item.get(title_field),
                    "type": get_nested_value(item, type_field_path),
                    "doc_type": get_nested_value(item, doc_type_path),
                    "doc_type_id": get_nested_value(item, doc_type_id_path),
                    "last_modified_date_time": get_nested_value(item, modified_date_path),
                    "raw_item_details_for_debug": item if logger.level == logging.DEBUG else "Set logger to DEBUG"
                }
                search_results.append(processed_item)
                
                if max_results is not None and len(search_results) >= max_results:
                    has_more_pages = False # Stop with pagination when reaching max results
                    break 
            
            if not has_more_pages: # Break when max results is reached
                break

            next_token_candidate = data.get("continuationToken", data.get("nextContinuationToken"))

            if next_token_candidate:
                current_continuation_token = next_token_candidate
                # logger.debug(f"Next continuationToken obtained: {current_continuation_token}")
            else:
                has_more_pages = False
                # logger.debug("No next continuationToken found, end of pagination.")
            
            if not items and not next_token_candidate : # Final check to stop
                # logger.debug("No items on this page and no next token. Quit.")
                has_more_pages = False


        # logger.info(
        #     f"Dedicated search voor '{query}' voltooid, {len(search_results)} resultaten verzameld."
        # )
        return search_results


# ONLY FOR TESTING
if __name__ == "__main__":
    zenya_service = ZenyaService()
    search_query = "pensioen"

    try:

        logger.info(f"Testing collect_dedicated_search_results with query: '{search_query}' (using default portal/scope)")
        search_results = zenya_service.collect_dedicated_search_results(
            query=search_query, 
            max_results=5
        )
        
        print(f"Number of search results for '{search_query}': {len(search_results)}")
        for i, result in enumerate(search_results):
            print(f"Result {i+1}: {result}")
            
    except Exception as e:
        logger.error(f"An error occurred during the ZenyaService test: {e}", exc_info=True)