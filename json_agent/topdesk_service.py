import os
import requests
from dotenv import load_dotenv
import logging
import json

# Setup Logger
logger = logging.getLogger(__name__)


class TopdeskService:
    def __init__(self):
        """
        Initializes the Topdesk Service with environment variables and token settings.

        Gets the Topdesk API key and URL from environment variables.
        """

        # Intialize env varibles
        load_dotenv()

        # Set env variables
        self.api_key = os.environ["topdesk-key"]
        self.api_url = os.environ["topdesk-api-url"]

        # Token variables
        self.token = None

        # Create token
        self.get_token()

    def get_token(self):
        """
        Creates an authentication token using the Topdesk API-key.
        """

        # Below url to get active token:
        url = f"{self.api_url}/tas/api/login/operator"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.api_key}",
        }
        # logger.info(f"Requesting authentication token from: {url}")

        response = requests.get(url, headers=headers)

        # When green flag (200), save token
        if response.status_code == 200:
            self.token = response.text
            # logger.info(f"Authentication token retrieved successfully: {self.token}")
        else:
            raise Exception(
                f"Something went wrong while creating the token: {response.status_code} - {response.text}"
            )

    def get_headers(self):
        """
        Generates the request headers.

        Passes the token to the header.

        Returns:
            dict: Headers to use in the API request.
        """

        return {
            "Content-Type": "application/json",
            "Authorization": f'TOKEN id="{self.token}", APIKEY {self.api_key}',
        }

    def _load_paginated_data(self, endpoint_path: str, params: dict, limit: int = None):
        """
        Generic helper to load paginated data from a TOPdesk endpoint.

        Args:
            endpoint_path (str): The path for the API endpoint (e.g., "/services/knowledge-base-v1/knowledgeItems").
            params (dict): A dictionary of query parameters for the request.
            limit (int, optional): Maximum number of items to return. Defaults to None.

        Returns:
            list: A list of items from the API.
        """
        items = []
        headers = self.get_headers()
        
        while True:
            logger.info(f"Requesting data from endpoint '{endpoint_path}' with parameters: {params}")
            response = requests.get(
                f"{self.api_url}{endpoint_path}",
                headers=headers,
                params=params,
            )

            if response.status_code in [200, 206]: # 200 OK, 206 Partial Content
                try:
                    data = response.json()
                    # The knowledgeItems endpoint returns a list under the 'item' key
                    new_items = data.get("item", []) if isinstance(data, dict) else data
                    items.extend(new_items)

                    if limit is not None and len(items) >= limit:
                        return items[:limit]

                    if response.status_code == 200: # Last page
                        break

                    # 206 means more pages are available, update 'start' for next request
                    params["start"] = params.get("start", 0) + params.get("page_size", 1000)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON response: {response.text}")
                    break
            else:
                logger.error(f"API request to '{endpoint_path}' failed: {response.status_code} - {response.text}")
                raise Exception(f"API request failed: {response.status_code} - {response.text}")
        return items

    def load_knowledge_items(
            self,
            limit=None,
            fields="title,description,content,keywords,creationDate,modificationDate,translation.content",
            query: str = None,
            page_size=1000,
            public_only: bool = False,
    ):
        """
        Loads knowledge items from TOPdesk, including specified fields, with pagination.

        Args:
            limit (int, optional): Maximum number of items. Defaults to None (no limit).
            fields (str, optional): List of fields to get from server.
                Defaults to "title,description,content,keywords,creationDate,modificationDate".
            query (str, optional): An FIQL query to filter the response.
            page_size (int): The number of item per page. max 1000.

        Returns:
            list: A list of knowledge items.

        Raises:
            Exception: If API request fails.
        """
        # Ensure visibility field is requested if public_only is true
        if public_only and "visibility" not in fields:
            fields = f"{fields},visibility"

        params = {"fields": fields, "page_size": page_size, "start": 0}

        if query:
            params["query"] = query

        if public_only:
            public_query = "visibility.publicKnowledgeItem==true"
            params["query"] = f"{params['query']} and {public_query}" if params.get("query") else public_query

        return self._load_paginated_data(
            endpoint_path="/services/knowledge-base-v1/knowledgeItems", params=params, limit=limit
        )

    def load_modification_date(
            self, limit=None, fields="creationDate,modificationDate", query: str = None, page_size=1000, public_only: bool = False
    ):
        """
        Loads knowledge creationdate and modificationdate from TOPdesk with pagination.

        Args:
            limit (int, optional): Maximum number of items. Default None.
            fields (str, optional): Comma-separated list of fields to get from server.
                Defaults to "creationDate,modificationDate".
            query (str, optional): Query to filter the response.
                See TOPdesk API documentation for available fields and query syntax. Defaults to None.
            page_size (int): The number of item per page. max 1000.

        Returns:
            list: A list of knowledge items.

        Raises:
            Exception: If API request fails.
        """
        # Ensure visibility field is requested if public_only is true
        if public_only and "visibility" not in fields:
            fields = f"{fields},visibility"

        params = {"fields": fields, "page_size": page_size, "start": 0}

        if query:
            params["query"] = query
        if public_only:
            public_query = "visibility.publicKnowledgeItem==true"
            params["query"] = f"{params['query']} and {public_query}" if params.get("query") else public_query
        return self._load_paginated_data(
            endpoint_path="/services/knowledge-base-v1/knowledgeItems", params=params, limit=limit
        )

    def load_knowledge_item_by_identifier(
            self, identifier: str, fields: str = "content,title,description,keywords,translation.creationDate,translation.modificationDate"
    ):
        """
        Loads a specific knowledge item from TOPdesk based on ID.

        Args:
            identifier (str): The ID or number from the knowledge item.
            fields (str): Comma-separated list of fields to retrieve.

        Returns:
            dict: The knowledge item as a dictionary, or None if not found.

        Raises:
            Exception: If API request fails.
        """
        headers = self.get_headers()
        params = {"fields": fields}
        # logger.info(f"Requesting knowledge item by identifier '{identifier}' with parameters: {params}")

        response = requests.get(
            f"{self.api_url}/services/knowledge-base-v1/knowledgeItems/{identifier}",
            headers=headers,
            params=params,
        )

        if response.status_code == 200:
            data = response.json()
            return data
        elif response.status_code == 404:
            logger.warning(f"Knowledge item with identifier '{identifier}' not found.")
            return None
        elif response.status_code == 400:
            logger.warning(f"Bad request, controleer de parameters.  '{identifier}'.")
            logger.error(f"Bad request: {response.status_code} - {response.text}")
            return None
        else:
            raise Exception(
                f"API request failed: {response.status_code} - {response.text}"
            )


# ONLY FOR FAST TESTING
if __name__ == "__main__":
    try:
        topdesk = TopdeskService()
        # Test load_knowledge_items
        ids = ['']  # Add ID's
        for id in ids:
            data = topdesk.load_knowledge_item_by_identifier(identifier=id)
            if data:
                print("Data received (load_knowledge_items):")
                print(data)
            else:
                print("No data returned (load_knowledge_items).")

            # Test load_knowledge_creation_date
            creation_data = topdesk.load_modification_date(limit=10)
            if creation_data:
                print("Data received (load_knowledge_creation_date):")
                print(creation_data)
            else:
                print("No data returned (load_knowledge_creation_date).")

            creation_data = topdesk.load_modification_date(limit=10, query="status.name==in=(Concept)")
            if creation_data:
                print(creation_data)
    except Exception as e:
        print(f"An error has occurred: {e}")