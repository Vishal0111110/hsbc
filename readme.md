## HSBC Banking Chatbot System

## Overview
This project is a modular, web-based banking assistant designed for hackathons and rapid prototyping. It features a conversational chatbot UI, powered by FastAPI, Google Gemini LLM, and a custom MCP server. The backend simulates banking operations using mock APIs and JSON data files. The system supports multi-turn dialogue, context retention, multilingual support, and accessibility features.

---

## Architecture

- **Presentation Layer**: Web UI (HTML/CSS/JS)
  - Chat interface, login modal, history panel
  - Real-time messaging via WebSocket
- **API Layer**: FastAPI
  - REST endpoints for login, user profile, accounts, loans, cards
  - WebSocket endpoint for chat
- **Service Layer**:
  - **NLU/Intent Detection**: Gemini LLM (Google Generative AI)
  - **Dialogue Manager**: Orchestrates multi-turn conversations, slot-filling, context management
  - **MCP Server**: Handles business logic, intent routing, and integration
  - **Translator**: Multilingual support (can be extended)
  - **Accessibility Module**: Text-to-speech, sign language, screen reader support (UI ready for extension)
- **Data Access Layer**:
  - Mock APIs (FastAPI endpoints)
  - JSON files for users, transactions, charges, loan programs
  - External API integration (e.g., TrueLayer)

---

## Features

- **User Authentication**: JWT-based login
- **Chatbot UI**: Modern, responsive, supports file upload and voice input
- **Multi-turn Dialogue**: Handles complex flows (loan application, card block, account queries)
- **Context Retention**: Remembers user state, slots, and previous answers
- **Mock Banking Operations**: Simulates balance checks, transactions, loan applications, card blocking
- **LLM Integration**: Uses Gemini 1.5 Flash for NLU and response generation
- **Accessibility**: UI designed for screen readers, keyboard navigation, and future sign language/video support
- **Multilingual Support**: Ready for translation pipeline integration

---

## File Structure

```
├── main.py                # FastAPI server, API endpoints, WebSocket
├── mcp_server.py          # MCP server, intent handling, LLM integration
├── chat.html              # Chatbot UI
├── login.html             # Login UI
├── static/
│   ├── style.css          # UI styles
│   ├── script.js          # Chat UI logic
│   └── login.js           # Login logic
├── users.json             # User profiles and credentials
├── transactions.json      # Account transactions
├── charges.json           # Account charges
├── loan_programs.json     # Loan program definitions
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (Gemini API key)
└── uploads/               # File uploads
```

---

## Setup & Installation

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd hsbc
   ```
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure environment**
   - Add your Gemini API key to `.env`:
     ```
     GEMINI_API_KEY="<your-gemini-api-key>"
     ```
4. **Run the server**
   ```bash
   uvicorn main:app --reload
   ```
5. **Access the UI**
   - Open `http://localhost:8000/` in your browser.

---

## Usage

- **Login**: Enter username and password (see `users.json` for sample users)
- **Chat**: Interact with the bot for banking queries, loan applications, card blocking, etc.
- **History**: View and search previous conversations
- **File Upload**: Attach files in chat
- **Voice Input**: Use microphone for speech-to-text

---

## Example Flows

### Loan Application
1. User: "I want to apply for a home loan."
2. Bot: "How much would you like to borrow?"
3. User: "₹200,000."
4. Bot: "Over how many years will you repay it?"
5. User: "7 years."
6. Bot: "Confirm application?"
7. User: "Yes."
8. Bot: "Your loan application is being submitted..."

### Card Blocking
1. User: "Block my credit card."
2. Bot: "Which card?"
3. User: "Visa ending 6789."
4. Bot: "Please provide OTP."
5. User: "123456."
6. Bot: "Card blocked."

### Account Query
1. User: "What's my account balance?"
2. Bot: "Which account?"
3. User: "Savings."
4. Bot: "Your savings account balance is ₹15,000."

---

## Extending the System

- **Add new intents**: Update MCP server and LLM prompt
- **Integrate real APIs**: Replace mock endpoints in `main.py`
- **Enhance accessibility**: Add sign language/video modules
- **Multilingual**: Integrate translation pipeline
- **Security**: Implement OAuth2, MFA, encryption for production

---

## References & Credits
- [FastAPI](https://fastapi.tiangolo.com/)
- [Google Generative AI (Gemini)](https://ai.google.dev/)
- [TrueLayer Mock API](https://docs.truelayer.com/reference/welcome-api-reference)
- [draw.io](https://app.diagrams.net/) for architecture diagrams

---



