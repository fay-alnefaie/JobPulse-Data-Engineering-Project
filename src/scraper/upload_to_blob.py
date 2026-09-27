"""
Uploads every CSV file from the scraper output folder to Azure Blob Storage,
authenticating via an Azure AD Service Principal (Tenant ID / Client ID / Client Secret).

Required environment variables:
    AZURE_TENANT_ID
    AZURE_CLIENT_ID
    AZURE_CLIENT_SECRET
    AZURE_STORAGE_ACCOUNT_NAME

Usage:
    python upload_to_blob.py
"""

import os
import sys

from azure.identity import ClientSecretCredential
from azure.storage.blob import BlobServiceClient

RAW_DATA_DIR = os.environ.get("OUTPUT_DIR", "/App/data/raw_data")
CONTAINER_NAME = os.environ.get("AZURE_CONTAINER_NAME", "bronze")

# Maps a keyword found in the filename to its matching folder in the container.
PLATFORM_FOLDERS = {
    "sabbar": "platform=sabbar",
    "tanqeeb": "platform=tanqeeb",
    "gulftalent": "platform=golftalent",
    "jadarat": "platform=jadarat",
}


def get_target_folder(filename: str) -> str:
    lower_name = filename.lower()
    for keyword, folder in PLATFORM_FOLDERS.items():
        if keyword in lower_name:
            return folder
    return ""  # unknown source: falls back to the container root


def main():
    tenant_id = os.environ.get("AZURE_TENANT_ID")
    client_id = os.environ.get("AZURE_CLIENT_ID")
    client_secret = os.environ.get("AZURE_CLIENT_SECRET")
    account_name = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")

    missing = [
        name
        for name, value in [
            ("AZURE_TENANT_ID", tenant_id),
            ("AZURE_CLIENT_ID", client_id),
            ("AZURE_CLIENT_SECRET", client_secret),
            ("AZURE_STORAGE_ACCOUNT_NAME", account_name),
        ]
        if not value
    ]
    if missing:
        print(f"ERROR: missing required environment variable(s): {', '.join(missing)}")
        sys.exit(1)

    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )

    account_url = f"https://{account_name}.blob.core.windows.net"
    blob_service = BlobServiceClient(account_url=account_url, credential=credential)
    container_client = blob_service.get_container_client(CONTAINER_NAME)

    if not os.path.isdir(RAW_DATA_DIR):
        print(f"ERROR: {RAW_DATA_DIR} does not exist.")
        sys.exit(1)

    csv_files = [f for f in os.listdir(RAW_DATA_DIR) if f.endswith(".csv")]

    if not csv_files:
        print(f"No CSV files found in {RAW_DATA_DIR}. Nothing to upload.")
        return

    for filename in csv_files:
        file_path = os.path.join(RAW_DATA_DIR, filename)
        folder = get_target_folder(filename)
        blob_name = f"{folder}/{filename}" if folder else filename
        print(f"Uploading {filename} -> {blob_name} ...")
        with open(file_path, "rb") as data:
            container_client.upload_blob(name=blob_name, data=data, overwrite=True)
        
    print(f"Done. Uploaded {len(csv_files)} file(s) to container '{CONTAINER_NAME}'.")


if __name__ == "__main__":
    main()