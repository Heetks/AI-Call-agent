from flask import Flask, request, jsonify
from openai import OpenAI
from langdetect import detect, DetectorFactory
import os

# Initialize your OpenAI client using the secret key
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

# Initialize Flask app
app = Flask(__name__)

# This is your webhook endpoint that Retell will call
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        print("Received data from Retell:", data)

        # Extract the user's latest speech
        user_transcript = data["transcript"]
        conversation_history = data["conversation_history"]

        # 1) DETECT THE LANGUAGE
        try:
            DetectorFactory.seed = 0
            lang_code = detect(user_transcript)
        except:
            lang_code = "en"  # Default to English

        # Map code to language name
        lang_map = {"hi": "Hindi", "gu": "Gujarati", "en": "English"}
        detected_language = lang_map.get(lang_code, "English")

        # 2) PREPARE THE PROMPT - THIS IS YOUR "TEMPLATE"
        system_prompt = f"""
        You are 'Priya', a friendly and professional virtual assistant for Sunshine Realty.
        **IMPORTANT: You MUST speak in {detected_language} only. Do not switch languages.**

        Your goal is to qualify real estate leads who inquired about a property online.
        Follow these steps:
        1.  Introduce yourself and confirm who you are speaking to.
        2.  Say you are following up on their inquiry about a property.
        3.  Ask if they are still actively looking to buy a home.
        4.  If yes, qualify them by asking about:
            - Their budget range.
            - Preferred locations or neighborhoods.
            - If they are also selling a current property.
        5.  Try to book a viewing appointment with a human agent.
        6.  If they are not interested, be polite and end the call gracefully.

        Always be helpful, patient, and sound genuinely interested in helping them.
        """
        # Build the list of messages for GPT-4
        messages = [{"role": "system", "content": system_prompt}]

        # Add the conversation history
        for turn in conversation_history:
            role = "assistant" if turn["role"] == "agent" else "user"
            messages.append({"role": role, "content": turn["content"]})

        # Add the latest user message
        messages.append({"role": "user", "content": user_transcript})

        # 3) GET THE AI'S RESPONSE
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Good for testing, you can change to "gpt-4" later
            messages=messages,
            max_tokens=300,
        )

        ai_response = response.choices[0].message.content

        # 4) SEND THE RESPONSE BACK TO RETELL
        response_payload = {
            "response": ai_response,
            "end_call": False  # Don't hang up
        }
        print("Sending response to Retell:", response_payload)
        return jsonify(response_payload)

    except Exception as e:
        print("Error:", e)
        return jsonify({"response": "I apologize, I'm having trouble right now. Please try again later.", "end_call": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)