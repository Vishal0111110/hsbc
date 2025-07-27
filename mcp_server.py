import json
import asyncio
import google.generativeai as genai
import re
import google.api_core.exceptions
import os
from dotenv import load_dotenv

load_dotenv()

# Configure the Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class MCPServer:
    def __init__(self, users_db, transactions_db, charges_db, loan_programs_db, save_users_function):
        self.users_db = users_db
        self.transactions_db = transactions_db
        self.charges_db = charges_db
        self.loan_programs_db = loan_programs_db
        self.save_users = save_users_function

    async def handle_message(self, message: str):
        data = json.loads(message)
        text = data.get("text")
        user_id = data.get("user_id")

        if 'intent' in data:
            return await self.execute_action(user_id, data, text)

        prompt = f"""
        You are a highly intelligent banking assistant. Your primary role is to understand a user's request and respond with a structured JSON object that identifies their intent and extracts any relevant entities. **You must only respond with a valid JSON object and nothing else.**

        **Instructions:**
        1.  **Identify the user's intent.** The possible intents are: `get_balance`, `get_transactions`, `get_charges`, `apply_loan`, `get_loan_programs`, `block_card`, `general_banking_query`, `greeting`, `compliment`, `feedback`, and `unsupported`.
        2.  **Extract entities.** For the `apply_loan` intent, you must extract the `amount` and `loan_type`.
        3.  **Handle ambiguity and errors.**
            *   If the user asks a general banking question (e.g., "what are the benefits of a savings account?"), classify the intent as `general_banking_query`.
            *   If the user provides a greeting (e.g., "hello", "hi"), classify the intent as `greeting`.
            *   If the user gives a compliment (e.g., "you are great"), classify the intent as `compliment`.
            *   If the user gives feedback (e.g., "you are not working well"), classify the intent as `feedback`.
            *   If the user's intent is unclear, or if they ask an off-topic or absurd question, classify the intent as `unsupported`.
            *   If the user's message is poorly framed or contains errors, do your best to understand the intent. If you cannot, classify it as `unsupported`.
        4.  **Always respond with a valid JSON object.** Do not add any extra text, explanations, or markdown formatting.

        **Examples:**
        *   User: "what is my current balance" -> {{"intent": "get_balance"}}
        *   User: "show me my recent transactions" -> {{"intent": "get_transactions"}}
        *   User: "show me my recent charges" -> {{"intent": "get_charges"}}
        *   User: "I need a loan for 50000 dollars for a new car" -> {{"intent": "apply_loan", "amount": 50000, "loan_type": "car_loan"}}
        *   User: "I want to apply for a personal_loan" -> {{"intent": "apply_loan", "loan_type": "personal_loan"}}
        *   User: "show me available loans" -> {{"intent": "get_loan_programs"}}
        *   User: "can you block my card please" -> {{"intent": "block_card"}}
        *   User: "what are the different types of credit cards" -> {{"intent": "general_banking_query", "query": "what are the different types of credit cards"}}
        *   User: "hello" -> {{"intent": "greeting"}}
        *   User: "you are awesome" -> {{"intent": "compliment"}}
        *   User: "you are not working" -> {{"intent": "feedback"}}
        *   User: "what is the weather today" -> {{"intent": "unsupported"}}
        *   User: "I want to buy a car" -> {{"intent": "unsupported"}}
        *   User: "loan apply 20k" -> {{"intent": "apply_loan", "amount": 20000}}

        **User message:** "{text}"
        """
        try:
            response = await model.generate_content_async(prompt)
        except google.api_core.exceptions.ResourceExhausted:
            return "The service is currently busy, please try again later."
        
        try:
            # The response from Gemini might have markdown formatting, so we need to clean it
            cleaned_response = re.sub(r'```json\n|\n```', '', response.text)
            intent_data = json.loads(cleaned_response)
            return await self.execute_action(user_id, intent_data, text)
        except (json.JSONDecodeError, TypeError):
            # If JSON parsing fails, it's likely a general query that Gemini answered directly.
            return response.text

    async def execute_action(self, user_id, intent_data, original_text):
        intent = intent_data.get("intent")
        account_related_intents = ["get_balance", "get_transactions", "get_charges"]

        if intent in account_related_intents and len(self.users_db[user_id]["profile"]["accounts"]) > 1 and 'account_id' not in intent_data:
            return json.dumps({"action": "select_account", "accounts": self.users_db[user_id]["profile"]["accounts"], "original_intent": intent_data})

        account_id = intent_data.get("account_id")
        if not account_id and self.users_db[user_id]["profile"]["accounts"]:
            account_id = self.users_db[user_id]["profile"]["accounts"][0]["id"]

        if intent == "get_balance":
            for user in self.users_db.values():
                for account in user["profile"]["accounts"]:
                    if account["id"] == account_id:
                        balance = account['balance']
                        html = f"""
                        <div class="info-card">
                            <h4>Account Balance</h4>
                            <p>Account ID: {account_id}</p>
                            <p class="balance">₹{balance:,.2f}</p>
                        </div>
                        """
                        return json.dumps({"html": html})
            return json.dumps({"html": "<p>Account not found.</p>"})
        elif intent == "get_transactions":
            if account_id in self.transactions_db:
                html = f"<h4>Recent Transactions for {account_id}</h4>"
                html += "<table><thead><tr><th>Date</th><th>Description</th><th>Amount</th></tr></thead><tbody>"
                for t in self.transactions_db[account_id]:
                    html += f"<tr><td>{t['date']}</td><td>{t['description']}</td><td>₹{t['amount']:,.2f}</td></tr>"
                html += "</tbody></table>"
                return json.dumps({"html": html})
            return json.dumps({"html": "<p>No transactions found.</p>"})
        elif intent == "get_charges":
            if account_id in self.charges_db:
                html = f"<h4>Recent Charges for {account_id}</h4>"
                html += "<table><thead><tr><th>Date</th><th>Description</th><th>Amount</th></tr></thead><tbody>"
                for c in self.charges_db[account_id]:
                    html += f"<tr><td>{c['date']}</td><td>{c['description']}</td><td>₹{c['amount']:,.2f}</td></tr>"
                html += "</tbody></table>"
                return json.dumps({"html": html})
            return json.dumps({"html": "<p>No charges found.</p>"})
        elif intent == "get_loan_programs":
            return json.dumps({"action": "show_loan_programs", "programs": self.loan_programs_db})
        elif intent == "apply_loan":
            loan_type = intent_data.get("loan_type")
            amount = intent_data.get("amount")
            if not loan_type:
                return json.dumps({"action": "select_loan_program", "programs": self.loan_programs_db})
            
            user_score = self.users_db[user_id]["profile"]["credit_score"]
            program = self.loan_programs_db[loan_type]

            if user_score >= program["min_score"] and amount <= program["max_amount"]:
                interest_rate = program["base_rate"] - ((user_score - program["min_score"]) * 0.0001)
                return json.dumps({
                    "action": "confirm_loan",
                    "loan_type": loan_type,
                    "amount": amount,
                    "interest_rate": interest_rate,
                    "base_rate": program["base_rate"],
                    "user_score": user_score,
                    "min_score": program["min_score"]
                })
            else:
                return "You are not eligible for this loan."

        elif intent == "confirm_loan":
            loan_type = intent_data.get("loan_type")
            amount = intent_data.get("amount")
            interest_rate = intent_data.get("interest_rate")
            loan_id = f"loan{len(self.users_db[user_id]['profile']['loans']) + 1}"
            new_loan = {"id": loan_id, "type": loan_type, "amount": amount, "status": "approved", "interest_rate": interest_rate}
            self.users_db[user_id]["profile"]["loans"].append(new_loan)
            self.save_users('users.json', self.users_db)
            html = f"""
            <div class="info-card">
                <h4>Loan Approved!</h4>
                <p>Your loan for <strong>₹{amount:,.2f}</strong> has been approved.</p>
                <p>Interest Rate: <strong>{interest_rate:.2%}</strong></p>
                <p>Application ID: <strong>{loan_id}</strong></p>
            </div>
            """
            return json.dumps({"html": html})

        elif intent == "block_card":
            cards = self.users_db[user_id]["profile"]["cards"]
            if len(cards) > 1 and 'card_id' not in intent_data:
                return json.dumps({"action": "select_card", "cards": cards})
            
            card_id = intent_data.get("card_id")
            if not card_id and cards:
                card_id = cards[0]["id"]

            if not card_id:
                return "You have no cards to block."

            return json.dumps({"action": "confirm_block_card", "card_id": card_id})

        elif intent == "confirm_block_card":
            card_id = intent_data.get("card_id")
            for card in self.users_db[user_id]["profile"]["cards"]:
                if card["id"] == card_id:
                    card["status"] = "blocked"
                    self.save_users('users.json', self.users_db)
                    html = f"""
                    <div class="info-card">
                        <h4>Card Blocked</h4>
                        <p>The card <strong>{card_id}</strong> has been successfully blocked.</p>
                    </div>
                    """
                    return json.dumps({"html": html})
            return json.dumps({"html": "<p>Card not found.</p>"})
        elif intent == "general_banking_query":
            user_score = self.users_db[user_id]["profile"]["credit_score"]
            prompt = f"You are a helpful banking assistant. The user's credit score is {user_score}. Answer the following banking-related question based on this credit score: {original_text}"
            response = await model.generate_content_async(prompt)
            return response.text
        elif intent == "greeting":
            return "Hello! I'm your banking assistant. How can I help you today?"
        elif intent == "compliment":
            return "You're welcome! I'm glad I could help."
        elif intent == "feedback":
            return "Thank you for your feedback. I'm always working to improve."
        else:
            return "I'm sorry, I can't answer that. I can only assist with banking-related questions."
