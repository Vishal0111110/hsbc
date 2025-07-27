from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json
import os
from datetime import datetime, timedelta
import jwt

app = FastAPI()

# Secret key for JWT
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1 day

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load data from JSON files
def load_data(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def save_data(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

users_db = load_data('users.json')
transactions_db = load_data('transactions.json')
charges_db = load_data('charges.json')
loan_programs_db = load_data('loan_programs.json')

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.get("/")
async def get_login():
    with open("login.html", "r") as f:
        return HTMLResponse(f.read())

@app.get("/chat")
async def get_chat(request: Request):
    with open("chat.html", "r") as f:
        return HTMLResponse(f.read())

@app.post("/api/login")
async def login(data: dict):
    username = data.get("username")
    password = data.get("password")
    user = users_db.get(username)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "username": username}

@app.get("/api/users/{user_id}/profile")
async def get_user_profile(user_id: str):
    if user_id in users_db:
        return users_db[user_id]["profile"]
    raise HTTPException(status_code=404, detail="User not found")

@app.get("/api/accounts/{account_id}/balance")
async def get_account_balance(account_id: str):
    for user in users_db.values():
        for account in user["profile"]["accounts"]:
            if account["id"] == account_id:
                return {"balance": account["balance"]}
    raise HTTPException(status_code=404, detail="Account not found")

@app.get("/api/accounts/{account_id}/transactions")
async def get_transactions(account_id: str):
    if account_id in transactions_db:
        return transactions_db[account_id]
    return []

@app.get("/api/accounts/{account_id}/charges")
async def get_charges(account_id: str):
    if account_id in charges_db:
        return charges_db[account_id]
    return []

@app.get("/api/users/{user_id}/accounts")
async def get_user_accounts(user_id: str):
    if user_id in users_db:
        return users_db[user_id]["profile"]["accounts"]
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/api/loans/apply")
async def apply_for_loan(data: dict):
    user_id = data.get("user_id")
    loan_type = data.get("loan_type")
    amount = data.get("amount")
    if user_id in users_db:
        user_score = users_db[user_id]["profile"]["credit_score"]
        if loan_type in loan_programs_db:
            program = loan_programs_db[loan_type]
            if user_score >= program["min_score"] and amount <= program["max_amount"]:
                interest_rate = program["base_rate"] - ((user_score - program["min_score"]) * 0.0001)
                loan_id = f"loan{len(users_db[user_id]['profile']['loans']) + 1}"
                new_loan = {"id": loan_id, "type": loan_type, "amount": amount, "status": "approved", "interest_rate": interest_rate}
                users_db[user_id]["profile"]["loans"].append(new_loan)
                save_data('users.json', users_db)
                return {"application_id": loan_id, "status": "approved", "interest_rate": interest_rate}
            else:
                return {"application_id": None, "status": "rejected", "reason": "Credit score or loan amount out of range."}
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/api/cards/block")
async def block_card(data: dict):
    user_id = data.get("user_id")
    card_id = data.get("card_id")
    if user_id in users_db:
        for card in users_db[user_id]["profile"]["cards"]:
            if card["id"] == card_id:
                card["status"] = "blocked"
                save_data('users.json', users_db)
                return {"message": f"Card {card_id} has been blocked."}
    raise HTTPException(status_code=404, detail="Card not found")

import google.generativeai as genai
from mcp_server import MCPServer
import re
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

mcp_server = MCPServer(users_db, transactions_db, charges_db, loan_programs_db, save_data)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

async def handle_nlu(websocket: WebSocket, data: dict, token: str):
    start_time = datetime.now()
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = decoded_token.get("sub")
    except jwt.PyJWTError:
        await websocket.send_text(json.dumps({"message": "Authentication error. Please log in again."}))
        return
    
    data['user_id'] = user_id
    mcp_message = json.dumps(data)
    response = await mcp_server.handle_message(mcp_message)
    end_time = datetime.now()
    response_time = (end_time - start_time).total_seconds()
    await websocket.send_text(json.dumps({"message": response, "response_time": response_time}))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        data = json.loads(data)
        await handle_nlu(websocket, data, data['token'])
