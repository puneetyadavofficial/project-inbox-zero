import os.path
import base64
import google.generativeai as genai # New Google AI import
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def get_email_body(payload):
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
    if "body" in payload and "data" in payload["body"]:
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
    return ""

def main():
    """Connects to Gmail, fetches the latest email, and gets a Gemini summary."""
    
    # --- Start of New Google AI Code ---
    try:
        # Read the Google AI API key from the file
        with open("googleaikey.txt", "r") as f:
            google_api_key = f.read().strip()
        genai.configure(api_key=google_api_key)
    except FileNotFoundError:
        print("Error: googleaikey.txt not found. Please save your Google AI API key in this file.")
        return
    # --- End of New Google AI Code ---

    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)
        
        results = service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=1).execute()
        messages = results.get("messages", [])

        if not messages:
            print("No new messages found.")
            return

        msg = service.users().messages().get(userId="me", id=messages[0]["id"], format='full').execute()
        
        headers = msg["payload"]["headers"]
        subject = next((d['value'] for d in headers if d['name'] == 'Subject'), 'No Subject')
        
        email_body = get_email_body(msg["payload"])

        if not email_body:
            print(f"Could not find the body for email with subject: '{subject}'")
            return
            
        print(f"--- Fectched Email ---\nSubject: {subject}\n------------------------")

        # --- Start of New Google AI Code ---
        print("\n>>> Asking Google AI for a summary...")
        
        # Call the Google Gemini API for a summary
        model = genai.GenerativeModel('gemini-1.5-flash') # A powerful and fast model
        prompt = f"Summarize this email in one single, concise sentence for a user who is busy or driving:\n\n{email_body}"
        response = model.generate_content(prompt)
        
        summary = response.text
        
        print(f"\n--- AI Summary ---\n{summary}\n------------------")
        # --- End of New Google AI Code ---

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()