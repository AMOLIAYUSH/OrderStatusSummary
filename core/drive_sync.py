import json
import logging
from datetime import datetime
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

logger = logging.getLogger(__name__)

def upload_to_drive(file_bytes: bytes, original_filename: str):
    """Silently upload the raw Excel file to Google Drive."""
    try:
        # 1. Load credentials from Streamlit Secrets
        if "gcp_service_account" not in st.secrets or "drive_folder_id" not in st.secrets:
            logger.warning("Google Drive secrets not found. Skipping silent upload.")
            return

        creds_info = st.secrets["gcp_service_account"]
        folder_id = st.secrets["drive_folder_id"]

        # 2. Authenticate
        credentials = service_account.Credentials.from_service_account_info(
            creds_info, scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        service = build("drive", "v3", credentials=credentials)

        # 3. Prepare file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = original_filename if original_filename else "Upload.xlsx"
        new_filename = f"PD_{timestamp}_{safe_name}"

        file_metadata = {
            "name": new_filename,
            "parents": [folder_id]
        }
        
        media = MediaIoBaseUpload(
            io.BytesIO(file_bytes),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            resumable=True
        )

        # 4. Upload
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()
        
        logger.info(f"Successfully uploaded {new_filename} to Drive with ID: {file.get('id')}")

    except Exception as e:
        # We catch all exceptions because this is a silent background task.
        # We NEVER want a Drive API failure to crash the client's dashboard!
        logger.error(f"Silent Drive upload failed: {e}")
