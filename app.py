import os.path
import base64
import email.mime.text
import google.generativeai as genai
from flask import Flask, render_template_string, jsonify, session, request, redirect, url_for
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_change_this' 
SCOPES = ["https://mail.google.com/"]

PROJECT_HOME = '/home/puneetkumarofficial/project-inbox-zero' # Make sure your username is correct
CREDENTIALS_PATH = os.path.join(PROJECT_HOME, 'credentials.json')
GOOGLE_AI_KEY_PATH = os.path.join(PROJECT_HOME, 'googleaikey.txt')

# --- All Python functions are unchanged ---
def get_email_body(payload):
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
    if "body" in payload and "data" in payload["body"]:
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
    return ""

def get_ai_summary(email_body):
    try:
        with open(GOOGLE_AI_KEY_PATH, "r") as f:
            google_api_key = f.read().strip()
        genai.configure(api_key=google_api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Summarize this email in one single, concise sentence for a user who is busy or driving:\n\n{email_body}"
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error with AI summarization: {e}"

def get_gmail_service():
    if 'credentials' not in session: return None
    creds = Credentials(**session['credentials'])
    return build("gmail", "v1", credentials=creds)

@app.route('/')
def home():
    if 'credentials' not in session: return redirect(url_for('authorize'))
    service = get_gmail_service()
    if service is None: return redirect(url_for('authorize'))
    try:
        results = service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=10).execute()
        messages = results.get("messages", [])
        session['messages'] = messages
        session['current_message_index'] = -1
    except HttpError as e:
        if e.resp.status in [401, 403]:
            session.pop('credentials', None)
            return redirect(url_for('authorize'))
        return f"An error occurred with the Gmail API: {e}"
    
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Project Inbox Zero</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f0f2f5; color: #1c1e21; display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }
            .container { background-color: white; padding: 30px 40px; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.1); text-align: center; width: 100%; max-width: 650px; }
            h1 { font-size: 1.8em; margin-bottom: 10px;}
            #summary-text { font-size: 1.1em; line-height: 1.6; margin-top: 15px; min-height: 50px; color: #606770; background-color: #f0f2f5; padding: 15px; border-radius: 8px;}
            .buttons { margin: 25px 0; display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; }
            button { background-color: #1877f2; color: white; border: none; padding: 12px 20px; font-size: 1em; border-radius: 6px; cursor: pointer; transition: background-color 0.2s, transform 0.1s; }
            button:hover { background-color: #166fe5; }
            button:active { transform: scale(0.97); }
            #status-container { margin-top: 20px; padding: 10px; border-radius: 6px; min-height: 20px; }
            #heard-text { color: #1877f2; font-weight: bold; }
            .instructions { margin-top: 30px; text-align: left; color: #606770; font-size: 0.9em; border-top: 1px solid #ddd; padding-top: 20px;}
            .instructions h3 { margin-top: 0; }
            .instructions ul { padding-left: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Project Inbox Zero</h1>
            <div id="summary-text">Click "Next Email" to start your session.</div>
            <div class="buttons">
                <button id="next-button">Next Email</button>
                <button id="archive-button">Archive</button>
                <button id="read-full-button">Read Full Email</button>
                <button id="flag-button">Flag Email</button>
                <button id="unread-button">Mark Unread</button>
                <button id="listen-button">Start Listening</button>
            </div>
            <div id="status-container">
                <div id="heard-text">...</div>
                <div id="status" style="font-style: italic;">Status: Idle</div>
            </div>
            <div class="instructions">
                <h3>How to Use</h3>
                <ul>
                    <li>Click <b>Next Email</b> to begin.</li>
                    <li>Click <b>Start Listening</b>, speak your command, then click <b>Stop Listening</b>.</li>
                    <li><b>Valid Commands:</b> "next", "archive", "read full email", "flag", "mark unread", "reply [your message]".</li>
                </ul>
            </div>
        </div>
        <script>
            const nextButton = document.getElementById('next-button');
            const archiveButton = document.getElementById('archive-button');
            const readFullButton = document.getElementById('read-full-button');
            const flagButton = document.getElementById('flag-button');
            const unreadButton = document.getElementById('unread-button');
            const listenButton = document.getElementById('listen-button');
            const summaryElement = document.getElementById('summary-text');
            const statusElement = document.getElementById('status');
            const heardTextElement = document.getElementById('heard-text');
            let recognition;
            let isListening = false;
            let final_transcript = '';

            function speak(text) { /* ... */ }
            async function replyToEmail(spokenText) { /* ... */ }

            listenButton.addEventListener('click', () => {
                if (isListening) {
                    recognition.stop();
                    return;
                }
                recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
                recognition.continuous = true;
                recognition.interimResults = true;
                recognition.lang = 'en-US';
                recognition.onstart = () => {
                    isListening = true;
                    final_transcript = '';
                    listenButton.textContent = 'Stop Listening';
                    listenButton.style.backgroundColor = '#e74c3c';
                    statusElement.textContent = 'Status: Listening...';
                };
                recognition.onresult = (event) => {
                    let interim_transcript = '';
                    for (let i = event.resultIndex; i < event.results.length; ++i) {
                        interim_transcript += event.results[i][0].transcript;
                    }
                    final_transcript = interim_transcript;
                    heardTextElement.textContent = `"${final_transcript}"`;
                };
                recognition.onerror = (event) => { statusElement.textContent = `Error: ${event.error}`; };
                recognition.onend = () => {
                    isListening = false;
                    listenButton.textContent = 'Start Listening';
                    listenButton.style.backgroundColor = '#1877f2';
                    statusElement.textContent = 'Status: Processing command...';
                    const command = final_transcript.toLowerCase().trim();
                    if (command) {
                        if (command.startsWith('reply')) {
                            const spokenMessage = command.substring('reply'.length).trim();
                            if (spokenMessage) { replyToEmail(spokenMessage); } 
                            else { const errorMsg = 'Please say "reply" followed by your message.'; statusElement.textContent = errorMsg; speak(errorMsg); }
                        } else if (command.includes('next')) { nextButton.click(); }
                        else if (command.includes('archive')) { archiveButton.click(); }
                        else if (command.includes('read')) { readFullButton.click(); }
                        else if (command.includes('flag')) { flagButton.click(); }
                        else if (command.includes('unread')) { unreadButton.click(); }
                        else {
                            const errorMsg = "Command not recognized.";
                            statusElement.textContent = errorMsg;
                            speak(errorMsg);
                        }
                    } else {
                        statusElement.textContent = 'Status: Idle (no command heard)';
                    }
                };
                recognition.start();
            });
            
            // Full implementation of all functions and event listeners
            function speak(text) {
                window.speechSynthesis.cancel();
                const utterance = new SpeechSynthesisUtterance(text);
                window.speechSynthesis.speak(utterance);
            }
            async function replyToEmail(spokenText) {
                statusElement.textContent = 'Drafting and sending reply...';
                const response = await fetch('/reply_to_email', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ spoken_text: spokenText }),
                });
                const data = await response.json();
                const replyStatus = data.status || data.error;
                statusElement.textContent = replyStatus;
                speak(replyStatus);
                if (data.status) { setTimeout(() => { nextButton.click(); }, 2000); }
            }
            nextButton.addEventListener('click', async () => {
                summaryElement.textContent = 'Fetching next email...';
                const response = await fetch('/next_email');
                const data = await response.json();
                summaryElement.textContent = data.summary || data.error;
                speak(data.summary || data.error);
            });
            archiveButton.addEventListener('click', async () => {
                statusElement.textContent = 'Archiving...';
                const response = await fetch('/archive_email');
                const data = await response.json();
                statusElement.textContent = data.status || data.error;
                setTimeout(() => { nextButton.click(); }, 1000); 
            });
            readFullButton.addEventListener('click', async () => {
                statusElement.textContent = 'Fetching full email...';
                const response = await fetch('/get_full_email');
                const data = await response.json();
                if (data.full_text) {
                    statusElement.textContent = 'Reading full email...';
                    speak(data.full_text);
                } else {
                    const errorMsg = data.error || 'Failed to fetch full email.';
                    statusElement.textContent = errorMsg;
                    speak(errorMsg);
                }
            });
            flagButton.addEventListener('click', async () => {
                statusElement.textContent = 'Flagging email...';
                const response = await fetch('/flag_email');
                const data = await response.json();
                statusElement.textContent = data.status || data.error;
                speak(data.status || data.error);
            });
            unreadButton.addEventListener('click', async () => {
                statusElement.textContent = 'Marking as unread...';
                const response = await fetch('/mark_unread');
                const data = await response.json();
                statusElement.textContent = data.status || data.error;
                speak(data.status || data.error);
            });
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template)

# --- All Python routes, including the new ones, are here ---
@app.route('/authorize')
def authorize():
    flow = Flow.from_client_secrets_file(CREDENTIALS_PATH, scopes=SCOPES, redirect_uri=url_for('oauth2callback', _external=True))
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    session['state'] = state
    return redirect(authorization_url)
@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(CREDENTIALS_PATH, scopes=SCOPES, state=state, redirect_uri=url_for('oauth2callback', _external=True))
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials
    session['credentials'] = {'token': credentials.token, 'refresh_token': credentials.refresh_token, 'token_uri': credentials.token_uri, 'client_id': credentials.client_id, 'client_secret': credentials.client_secret, 'scopes': credentials.scopes}
    return redirect(url_for('home'))
@app.route('/next_email')
def next_email():
    service = get_gmail_service()
    if not service: return jsonify({"error": "Authentication required."})
    if 'messages' not in session or not session['messages']: return jsonify({"error": "No messages."})
    session['current_message_index'] += 1
    if session['current_message_index'] >= len(session['messages']): return jsonify({"summary": "End of inbox."})
    msg_id = session['messages'][session['current_message_index']]['id']
    try:
        msg = service.users().messages().get(userId="me", id=msg_id, format='full').execute()
        email_body = get_email_body(msg["payload"])
        if not email_body: return jsonify({"summary": "Skipping email with no body."})
        summary = get_ai_summary(email_body)
        return jsonify({"summary": summary})
    except Exception as e: return jsonify({"error": f"An error occurred: {e}"})
@app.route('/archive_email')
def archive_email():
    service = get_gmail_service()
    if not service: return jsonify({"error": "Authentication required."})
    if 'messages' not in session or session['current_message_index'] < 0: return jsonify({"error": "No email to archive."})
    msg_id = session['messages'][session['current_message_index']]['id']
    try:
        service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['INBOX']}).execute()
        return jsonify({"status": "Email archived."})
    except Exception as e: return jsonify({"error": f"Failed to archive: {e}"})
@app.route('/get_full_email')
def get_full_email():
    service = get_gmail_service()
    if not service: return jsonify({"error": "Authentication required."})
    if 'messages' not in session or session['current_message_index'] < 0: return jsonify({"error": "No email to read."})
    msg_id = session['messages'][session['current_message_index']]['id']
    try:
        msg = service.users().messages().get(userId="me", id=msg_id, format='full').execute()
        email_body = get_email_body(msg["payload"])
        if not email_body: return jsonify({"error": "Could not read email body."})
        return jsonify({"full_text": email_body})
    except Exception as e: return jsonify({"error": f"An error occurred: {e}"})
@app.route('/reply_to_email', methods=['POST'])
def reply_to_email():
    service = get_gmail_service()
    if not service: return jsonify({"error": "Authentication required."})
    data = request.json
    spoken_text = data.get('spoken_text')
    if not spoken_text: return jsonify({"error": "No spoken text received."}), 400
    if 'messages' not in session or session['current_message_index'] < 0: return jsonify({"error": "No email to reply to."})
    msg_id = session['messages'][session['current_message_index']]['id']
    try:
        original_msg = service.users().messages().get(userId="me", id=msg_id, format='metadata').execute()
        headers = original_msg['payload']['headers']
        to_address = next((d['value'] for d in headers if d['name'].lower() == 'from'), None)
        subject = next((d['value'] for d in headers if d['name'].lower() == 'subject'), 'No Subject')
        original_message_id = next((d['value'] for d in headers if d['name'].lower() == 'message-id'), None)
        if not to_address: return jsonify({"error": "Could not find original sender."})
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"A user wants to reply to an email. Their spoken message is: '{spoken_text}'. Convert this into a simple, polite, and professional email body. Do not include a subject line or greeting."
        response = model.generate_content(prompt)
        email_body = response.text
        mime_message = email.mime.text.MIMEText(email_body)
        mime_message['to'] = to_address
        mime_message['subject'] = f"Re: {subject}"
        if original_message_id:
            mime_message['In-Reply-To'] = original_message_id
            mime_message['References'] = original_message_id
        encoded_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()
        create_message = {'raw': encoded_message}
        service.users().messages().send(userId="me", body=create_message).execute()
        return jsonify({"status": "Reply sent successfully."})
    except Exception as e: return jsonify({"error": f"An error occurred: {e}"})
@app.route('/flag_email')
def flag_email():
    service = get_gmail_service()
    if not service: return jsonify({"error": "Authentication required."})
    if 'messages' not in session or session['current_message_index'] < 0: return jsonify({"error": "No active email to flag."})
    msg_id = session['messages'][session['current_message_index']]['id']
    try:
        service.users().messages().modify(userId='me', id=msg_id, body={'addLabelIds': ['STARRED']}).execute()
        return jsonify({"status": "Email flagged as important."})
    except Exception as e: return jsonify({"error": f"Failed to flag email: {e}"})
@app.route('/mark_unread')
def mark_unread():
    service = get_gmail_service()
    if not service: return jsonify({"error": "Authentication required."})
    if 'messages' not in session or session['current_message_index'] < 0: return jsonify({"error": "No active email to mark as unread."})
    msg_id = session['messages'][session['current_message_index']]['id']
    try:
        service.users().messages().modify(userId='me', id=msg_id, body={'addLabelIds': ['UNREAD']}).execute()
        return jsonify({"status": "Email marked as unread."})
    except Exception as e: return jsonify({"error": f"Failed to mark as unread: {e}"})

if __name__ == '__main__':
    app.run(debug=True)