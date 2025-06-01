from flask import Flask, render_template, request, redirect, url_for, jsonify, session,url_for
import requests
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import mysql.connector
import re
import google.generativeai as genai
from transformers import pipeline
from web3 import Web3
from contract_data import contract_abi, contract_address


app = Flask(__name__)

load_dotenv()  # Load the .env file here

# For DB
db_config = {
    'host': os.getenv("DB_HOST"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'database': os.getenv("DB_NAME")
}

# For Web3
infura_url = os.getenv("INFURA_URL")
private_key = os.getenv("PRIVATE_KEY")
wallet_address = os.getenv("WALLET_ADDRESS")
contract_address = os.getenv("CONTRACT_ADDRESS")

# For Gemini/HuggingFace
gemini_key = os.getenv("GEMINI_API_KEY")
hf_token = os.getenv("HUGGING_FACE")


HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
HUGGINGFACE_API_TOKEN = os.getenv("HUGGING_FACE")  # replace with your real token

# Load API key from .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini model
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )


JOURNAL_FILE = "journal_entries.json"

#@app.route('/')
#def landing_page():
#    return render_template('index.html')


from flask import request, jsonify, session, render_template
from web3 import Web3

@app.route('/simplify', methods=['GET', 'POST'])
def simplify():
    if request.method == 'POST':
        data = request.get_json()
        task = data.get('task', '').strip()
        if not task:
            return jsonify({"simplified": "Please enter a task."})

        simplified = call_gemini_api(task)  # Your existing function to simplify

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO simplified_tasks (task_text, simplified_text, created_at) VALUES (%s, %s, NOW())",
                (task, simplified)
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print("Error saving to DB:", e)

        return jsonify({"simplified": simplified})

    # For GET requests:
    wallet_address = session.get('wallet_address', '')  # Get from session

    # Validate and checksum the address if present
    if wallet_address and Web3.isAddress(wallet_address):
        wallet_address = Web3.toChecksumAddress(wallet_address)
    else:
        wallet_address = ''  # fallback to empty if invalid

    return render_template('simplify.html', wallet_address=wallet_address)



@app.route('/notes', methods=['GET', 'POST'])
def notes():
    mood = None
    entry = None
    summary = None

    if request.method == 'POST':
        entry = request.form.get('mood')  # Or 'entry' depending on your form
        wallet = request.form.get('wallet')

        if entry:
            mood = detect_mood(entry)
            summary = summarize_note(entry)

            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO journal_entries (entry_text, mood, summary, wallet_address, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    """,
                    (entry, mood, summary, wallet)
                )
                conn.commit()
                cursor.close()
                conn.close()
                try:
                    reward_user_internal(wallet)
                    print("Token sent to:", wallet)
                except Exception as e:
                    print("Token transfer failed:", e)
            except Exception as e:
                print("Error saving to DB:", e)

    return render_template('notes.html', mood=mood, entry=entry, summary=summary)



def summarize_note(text):
    try:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        model = genai.GenerativeModel("gemini-1.5-flash")  # or "gemini-1.5-flash" if available

        prompt = f"""
        Summarize the following diary/journal entry clearly and meaningfully.
        Capture the person's mood and key emotional context:

        "{text}"
        """

        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as e:
        print("Gemini summarization error:", e)
        return "Error generating summary."



@app.route('/journal')
def journal():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT entry_text, mood, created_at FROM journal_entries ORDER BY created_at DESC")
        entries = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Error fetching from DB:", e)
        entries = []

    return render_template('journal.html', entries=entries)


@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if request.method == 'POST':
        user_message = request.form.get('prompt')  # match the name="prompt" in your HTML
        if user_message:
            bot_response = get_chat_response(user_message)
            return render_template('chat.html', response=bot_response)
        return render_template('chat.html', response="Please enter a message.")
    return render_template('chat.html')



@app.route('/story', methods=['GET'])
def story_form():
    return render_template("story.html")


@app.route('/story', methods=['POST'])
def generate_story():
    data = request.get_json()
    genre = data['genre']
    character = data['character']
    story_idea = data.get('story_idea', '').strip()  # Optional field

    # Constructing dynamic prompt
    prompt = f"""
    Write a complete and engaging fiction story in the "{genre}" genre.
    The main character is named {character}.

    Structure the story as follows:
    - Begin with a vivid introduction to the world and character.
    - Introduce a meaningful conflict or challenge in the middle.
    - Include a climax that creates tension or excitement.
    - End with a clear and satisfying resolution.
    - Make some own character.

    Write the story in well-structured paragraphs.
    Use descriptive language, natural dialogue (if needed), and emotional depth.
    Do not include any assistant-like phrases. Only return the story content.
    """

    if story_idea:
        prompt += f'\nIncorporate this user-provided idea into the story: "{story_idea}"'

    try:
        response = model.generate_content(prompt)
        story_text = clean_response(response.text)

        # ✅ Save to MySQL including the story idea
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO story_starters (genre, character_name, story_idea, story_text) VALUES (%s, %s, %s, %s)",
            (genre, character, story_idea, story_text)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"story": story_text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/code')
def code_page():
    return render_template('code.html')


@app.route('/explain_code', methods=['GET', 'POST'])
def explain_code():
    if request.method == 'POST':
        data = request.get_json()
        code = data.get('code', '').strip()

        if not code:
            return jsonify({'error': 'Please provide code to explain.'}), 400

        # Prompt for Gemini
        prompt = f"Explain the following code to a beginner with clear, line-by-line comments:\n\n{code}"
        explanation = call_gemini_api(prompt)

        # Save explanation to DB
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO code_explanations (code_input, explanation) VALUES (%s, %s)",
                (code, explanation)
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print("DB Error:", e)

        return jsonify({'explanation': explanation})

    # Render page on GET
    return render_template('code.html')



def detect_mood(entry_text):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": f"Analyze the mood of this journal entry in one word (e.g., happy, sad, anxious, relaxed, excited): {entry_text}"}]
        }]
    }
    params = {"key": GEMINI_API_KEY}

    try:
        response = requests.post(url, headers=headers, json=payload, params=params)
        data = response.json()

        if "candidates" in data:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            return "Unable to detect mood."

    except Exception as e:
        return f"Error: {str(e)}"


def get_chat_response(message):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": f"You are a helpful assistant for neurodivergent users. Respond kindly and clearly to: {message}"}]
        }]
    }
    params = {"key": GEMINI_API_KEY}

    try:
        response = requests.post(url, headers=headers, json=payload, params=params)
        data = response.json()

        if "candidates" in data:
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            return clean_response(raw_text)
        else:
            return "Sorry, I couldn't generate a response."

    except Exception as e:
        return f"Error: {str(e)}"


def call_gemini_api(task_text):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": f"Simplify this task for a neurodivergent user in clear points:\n\n{task_text}"}]
        }]
    }
    params = {"key": GEMINI_API_KEY}

    try:
        response = requests.post(url, headers=headers, json=payload, params=params)
        data = response.json()

        if "candidates" in data:
            raw = data["candidates"][0]["content"]["parts"][0]["text"]
            return clean_response(raw)
        else:
            return "Sorry, I couldn't simplify the task."

    except Exception as e:
        return f"Error: {str(e)}"


def clean_response(text):

    # Convert escaped newlines
    text = text.replace('\\n', '\n')

    # Remove markdown formatting
    text = re.sub(r'\*+', '', text)  # Remove *, **, etc.
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)  # Remove ##, ### headers
    text = re.sub(r'```+', '', text)  # Remove triple backticks from code blocks

    return text.strip()

########################## Blockchain ############# Web3 ######################


# Connect to Infura or Alchemy
web3 = Web3(Web3.HTTPProvider(os.getenv("INFURA_URL")))

# Load account from private key
private_key = os.getenv("PRIVATE_KEY")
deployer_address = os.getenv("WALLET_ADDRESS")

# Load contract (ensure contract_abi and contract_address are defined earlier)
contract = web3.eth.contract(address=contract_address, abi=contract_abi)

def reward_user_internal(wallet, amount=10):
    try:
        wallet = Web3.to_checksum_address(wallet)
        decimals = contract.functions.decimals().call()
        amount_wei = amount * (10 ** decimals)

        nonce = web3.eth.get_transaction_count(deployer_address)
        txn = contract.functions.rewardUser(wallet, amount_wei).build_transaction({
            'from': deployer_address,
            'nonce': nonce,
            'gas': 150000,
            'gasPrice': web3.to_wei('10', 'gwei')
        })

        signed_txn = web3.eth.account.sign_transaction(txn, private_key=private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        print(f"Auto-rewarded {amount} tokens to {wallet}: {web3.to_hex(tx_hash)}")
        return web3.to_hex(tx_hash)
    except Exception as e:
        print("Reward error:", str(e))
        return None



@app.route('/reward', methods=['POST'])
def reward_user():
    try:
        data = request.get_json()
        wallet_raw = data.get('wallet', '').strip()
        if not wallet_raw:
            return jsonify({"error": "Wallet address is required"}), 400

        try:
            wallet = Web3.to_checksum_address(wallet_raw)
        except ValueError:
            return jsonify({"error": "Invalid wallet address"}), 400

        amount_raw = data.get("amount", 10)
        try:
            amount = int(amount_raw)
        except (ValueError, TypeError):
            return jsonify({"error": "Amount must be an integer"}), 400
        
        if amount <= 0:
            return jsonify({"error": "Amount must be greater than zero"}), 400
        
        # Convert amount to wei (18 decimals)
        amount_wei = amount * 10**18

        nonce = web3.eth.get_transaction_count(deployer_address)
        txn = contract.functions.rewardUser(wallet, amount_wei).build_transaction({
            'from': deployer_address,
            'nonce': nonce,
            'gas': 150000,
            'gasPrice': web3.to_wei('10', 'gwei')
        })

        print("Rewarding:", wallet)
        signed_txn = web3.eth.account.sign_transaction(txn, private_key=private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)

        return jsonify({
            "message": "Reward sent!",
            "tx_hash": web3.to_hex(tx_hash)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

################################### login/signup #########################################
@app.route('/')
def login_page():
    return render_template('login.html')  # your login/signup page

@app.route('/check_wallet', methods=['POST'])
def check_wallet():
    data = request.get_json()
    wallet_raw = data.get('wallet', '').strip()
    try:
        wallet = Web3.to_checksum_address(wallet_raw)
    except ValueError:
        return jsonify({"error": "Invalid wallet address"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE wallet_address = %s", (wallet,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return jsonify({"exists": bool(user)})


@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    wallet_raw = data.get('wallet', '').strip()
    try:
        wallet = Web3.to_checksum_address(wallet_raw)
    except ValueError:
        return jsonify({"error": "Invalid wallet address"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if already exists to avoid duplicates
    cursor.execute("SELECT id FROM users WHERE wallet_address = %s", (wallet,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"message": "Wallet already registered."}), 400

    cursor.execute(
        "INSERT INTO users (wallet_address, created_at) VALUES (%s, %s)",
        (wallet, datetime.utcnow())
    )
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Signup successful."})


@app.route('/home')
def home():
    # Here you can add logic to check session or localStorage wallet if you want
    return render_template('index.html')  # Your NeuroBuddy welcome page


@app.route('/submit_journal', methods=['POST'])
def submit_journal():
    try:
        entry_text = request.form.get('entry_text', '').strip()
        mood = request.form.get('mood', '').strip()
        wallet = request.form.get('wallet', '').strip()

        if not entry_text or not mood or not wallet:
            return jsonify({"error": "All fields are required."}), 400

        # Save to DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO journal_entries (entry_text, mood, wallet_address, created_at) VALUES (%s, %s, %s, %s)",
            (entry_text, mood, wallet, datetime.utcnow())
        )
        conn.commit()
        cursor.close()
        conn.close()

        # ✅ Auto-Reward Tokens
        reward_user_internal(wallet, amount=5)

        return redirect('/journal')  # or jsonify({"message": "Saved and rewarded!"})

    except Exception as e:
        print("Journal submission error:", e)
        return jsonify({"error": "Something went wrong."}), 500



if __name__ == '__main__':
    app.run(debug=True)
