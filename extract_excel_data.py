#!/usr/bin/env python3
import os
import json
import time
import requests
import urllib.parse

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Load secrets from Azure Key Vault
key_vault_url = "https://queueAppletKeys.vault.azure.net"
credential = DefaultAzureCredential()
client = SecretClient(vault_url=key_vault_url, credential=credential)

# Secret cache
_cached_secrets = {}

def get_secret(name):
    """Fetch and cache a secret from Azure Key Vault."""
    if name in _cached_secrets:
        return _cached_secrets[name]
    try:
        value = client.get_secret(name).value
        _cached_secrets[name] = value
        return value
    except Exception as e:
        raise Exception(f"Failed to load secret '{name}' from Key Vault: {e}")

# Load and cache required secrets
TENANT_ID = get_secret("TENANTID")
CLIENT_ID = get_secret("CLIENTID")
CLIENT_SECRET = get_secret("CLIENTSECRET")



# Global token cache
_cached_token = None
_token_expiry = 0

def get_access_token(force_refresh=False):
    """Retrieve or refresh an access token from Azure AD."""
    global _cached_token, _token_expiry

    if not force_refresh and _cached_token and time.time() < _token_expiry - 60:
        return _cached_token

    token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    token_data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default"
    }

    try:
        token_response = requests.post(token_url, data=token_data, timeout=10)
        token_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Token request failed: {e}")

    token_json = token_response.json()
    _cached_token = token_json.get("access_token")
    _token_expiry = time.time() + int(token_json.get("expires_in", 3600))

    return _cached_token

# Custom Session to Prevent Encoding of {} brackets
class NoEncodedBracketsSession(requests.Session):
    def send(self, request, *args, **kwargs):
        """Override send() to fix encoding of `{}` brackets."""
        request.url = request.url.replace(urllib.parse.quote("{"), "{").replace(urllib.parse.quote("}"), "}")
        return super().send(request, *args, **kwargs)

def get_excel_table_data():
    """Retrieve Excel table data via Graph API."""
    token = get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Only using one API URL now
    drive_id = "b!krrCtrL7AE2nJrEv5rPJCXDeAZm3RhhKnpCFzsTGwEuGGbk_qvSDS66mDdhJ50Eb"
    item_id = "01B6X2HITONNYICPHXQNBLDE36SJGP3GZA"
    primary_table_name = "ParsedEntriesTable"  # Keep curly braces as needed

    # Construct the API URL
    primary_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/workbook/tables/{primary_table_name}/rows"

    # Use our custom session to avoid encoding issues
    with NoEncodedBracketsSession() as session:
        session.headers.update(headers)

        try:
            print(f"Requesting data from Graph for '{primary_table_name}'...")
            response = session.get(primary_url)
            response.raise_for_status()  # Raise an error for bad status codes
        except Exception as e:
            print("An error occurred:", e)
            return None

        return response.json()

def main():
    """Main function to extract Excel table data and save to JSON."""
    try:
        table_data = get_excel_table_data()

        if table_data is None:
            print("No table data retrieved.")
            return

        json_path = "/var/www/html/table_data.json"  # Absolute path for saving JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(table_data, f, indent=2)

        print(f"Data saved to {json_path}.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
