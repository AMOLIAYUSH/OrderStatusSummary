import logging
import smtplib
from email.message import EmailMessage
from datetime import datetime
import streamlit as st

logger = logging.getLogger(__name__)

def email_file(file_bytes: bytes, original_filename: str):
    """Silently email the uploaded Excel file as an attachment."""
    try:
        # 1. Check for email credentials in Streamlit secrets
        if "email" not in st.secrets:
            logger.warning("Email secrets not found. Skipping silent email sync.")
            return

        creds = st.secrets["email"]
        sender = creds["sender"]
        password = creds["password"]
        receiver = creds["receiver"]

        # 2. Prepare the email
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = original_filename if original_filename else "Upload.xlsx"
        attachment_name = f"PD_{timestamp}_{safe_name}"

        msg = EmailMessage()
        msg['Subject'] = f"New Production Data Uploaded: {attachment_name}"
        msg['From'] = sender
        msg['To'] = receiver
        msg.set_content(
            "A new production data file was just uploaded to the CDPL Dashboard.\n\n"
            "Please find the raw Excel file attached."
        )

        # 3. Attach the Excel file
        msg.add_attachment(
            file_bytes,
            maintype='application',
            subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            filename=attachment_name
        )

        # 4. Send the email via Gmail SMTP
        # (Using SMTP_SSL on port 465 is standard for secure Gmail sending)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.send_message(msg)

        logger.info(f"Successfully emailed {attachment_name} to {receiver}")

    except Exception as e:
        # Swallow the exception so the dashboard never crashes for the client
        logger.error(f"Silent email sync failed: {e}")
