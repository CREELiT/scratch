import os
import uuid
import logging
from flask import Flask, request, jsonify, send_from_directory
from google.cloud import dialogflowcx
from twilio.twiml.voice_response import VoiceResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.')

# Configuration
PROJECT_ID = os.environ.get("PROJECT_ID")
LOCATION = os.environ.get("LOCATION", "global")
AGENT_ID = os.environ.get("DIALOGFLOW_AGENT_ID")

if not all([PROJECT_ID, AGENT_ID]):
    logger.warning("Missing required environment variables: PROJECT_ID or DIALOGFLOW_AGENT_ID")

def detect_intent_text(session_id, text, language_code="en"):
    """Returns the result of detect intent with texts as inputs."""
    
    # Create a client
    client_options = None
    if LOCATION != "global":
        api_endpoint = f"{LOCATION}-dialogflow.googleapis.com:443"
        client_options = {"api_endpoint": api_endpoint}
        
    session_client = dialogflowcx.SessionsClient(client_options=client_options)

    # Construct the session path
    # If AGENT_ID contains the full path "projects/.../agents/...", use it as base
    if "projects/" in AGENT_ID:
         # Assuming AGENT_ID is the full resource name of the agent
         session_path = f"{AGENT_ID}/sessions/{session_id}"
    else:
         session_path = session_client.session_path(
            project=PROJECT_ID,
            location=LOCATION,
            agent=AGENT_ID,
            session=session_id
        )

    logger.info(f"Session path: {session_path}")

    text_input = dialogflowcx.TextInput(text=text)
    query_input = dialogflowcx.QueryInput(text=text_input, language_code=language_code)
    request_obj = dialogflowcx.DetectIntentRequest(
        session=session_path, query_input=query_input
    )

    response = session_client.detect_intent(request=request_obj)
    return response

@app.route("/")
def index():
    return send_from_directory('.', 'index.html')

@app.route("/chat", methods=["POST"])
def chat():
    if not all([PROJECT_ID, AGENT_ID]):
        return jsonify({"message": "Server misconfigured: Missing DIALOGFLOW_AGENT_ID"}), 500

    data = request.get_json()
    message = data.get("message")
    session_id = data.get("sessionId", str(uuid.uuid4()))

    if not message:
        return jsonify({"error": "Message is required"}), 400

    try:
        response = detect_intent_text(session_id, message)
        
        # Extract the response text
        reply_texts = []
        for message in response.query_result.response_messages:
            if message.text:
                reply_texts.append(message.text.text[0])
        
        reply = " ".join(reply_texts) if reply_texts else "I didn't get that."
        
        return jsonify({"reply": reply})

    except Exception as e:
        logger.error(f"Error calling Dialogflow: {e}")
        return jsonify({"message": "Error communicating with AI agent"}), 500

# --- Twilio Voice Integration ---
@app.route("/twilio/voice", methods=["POST", "GET"])
def twilio_voice():
    """Handles the initial incoming call."""
    resp = VoiceResponse()
    resp.say("Hello! Thanks for calling Ren 360 Support. How can I help you today?")
    resp.gather(input="speech", action="/twilio/input", timeout=3, speechTimeout="auto")
    resp.say("I didn't hear anything. Goodbye.")
    return str(resp)

@app.route("/twilio/input", methods=["POST"])
def twilio_input():
    """Handles speech input from the user."""
    resp = VoiceResponse()
    speech_text = request.values.get("SpeechResult")
    
    # Use session ID from CallSid to maintain context per call
    session_id = request.values.get("CallSid")

    if speech_text:
        try:
            # Call Dialogflow
            response = detect_intent_text(session_id, speech_text)
            
            # Extract response text
            reply_texts = []
            for message in response.query_result.response_messages:
                if message.text:
                    reply_texts.append(message.text.text[0])
            
            reply = " ".join(reply_texts) if reply_texts else "I'm not sure how to help with that."
            
            resp.say(reply)
            
            # Loop back to listen for next command
            resp.gather(input="speech", action="/twilio/input", timeout=3)
            
        except Exception as e:
            logger.error(f"Error calling Dialogflow: {e}")
            resp.say("Sorry, I'm having trouble connecting to the brain. Please try again later.")
    else:
        resp.say("I didn't catch that.")
        resp.gather(input="speech", action="/twilio/input", timeout=3)

    return str(resp)

# Catch-all route must be last
@app.route("/<path:path>")
def static_files(path):
    return send_from_directory('.', path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
