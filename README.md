# 📦 Customer Service Chatbot (Flask + PostgreSQL + Anthropic)

This project is a **Flask-based** chatbot application that integrates:  
- **Anthropic Claude API** for SQL generation and customer-friendly insights.  
- **PostgreSQL** for user and order data.  
- **SQLite (local)** to maintain temporary conversation state.  
- **Ngrok** for tunneling requests to the development server.  

It is designed as a **customer service assistant** that:  
- Accepts a mobile number to identify a user.  
- Fetches user-related order data from PostgreSQL.  
- Generates **safe SQL queries** dynamically.  
- Summarizes the query results into **natural language responses**.  
- Stores conversational context for continuity.  

---

## 🚀 Features
- ✅ User identification by mobile number  
- ✅ SQL query generation powered by Claude  
- ✅ Strict SQL safety (only `SELECT` queries allowed)  
- ✅ Conversational memory stored via SQLite (`CurrentValue` model)  
- ✅ Summary generation in plain text (short, user-focused analysis)  
- ✅ REST API endpoints for integration with frontend or chat UI  
- ✅ Logging with rotation and structured formatting  
- ✅ Environment-variable-based credentials (`.env` file)  

---

## ⚙️ Tech Stack
- **Backend:** Python (Flask)  
- **Database 1 (Persistent):** PostgreSQL (orders, user data)  
- **Database 2 (Session store):** SQLite (conversation context)  
- **AI Models:** Claude (Anthropic SDK)  
- **Request Tunnel (Dev):** Ngrok  
- **Logging:** Python’s `logging` library  

---

## 📂 Project Structure

├── app.py # Main Flask application
├── site.db # SQLite database (auto-created)
├── logs/app.log # Application logs
├── templates/
│ └── index2.html # Frontend (for testing UI)
├── .env # Environment variables
└── README.md # Documentation

---

## 🔑 Environment Variables

Create a `.env` file in the root folder:

## Security
SECRET_KEY=your_flask_secret_key

## PostgreSQL Database
DB_URL=postgresql://username:password@host:5432/dbname

## Anthropic API Keys
ANTHROPIC_API_KEY=your_first_key
ANTHROPIC_API_KEY2=your_second_key

---

## ▶️ Running the Project

### 1. Install dependencies

`pip install -r requirements.txt`


Required packages:  
- flask  
- psycopg2-binary  
- requests  
- python-dotenv  
- sqlalchemy  
- anthropic  

### 2. Initialize SQLite (conversation state DB)
Auto-created by `db.create_all()` when you run the app first time.

### 3. Run the Flask app

`python app.py`

By default runs on:  

`http://127.0.0.1:5000`


---

## 📡 API Endpoints

### `POST /number`
Register a mobile number and fetch associated user.  

---

### `POST /names`
Fetch the last stored user name.  

✅ Returns:  
{ "name": "John Doe" }


---

### `POST /process-data`
Send customer queries → Generates SQL → Executes → Summarizes.  
{ "message": "Show me my cancelled orders last week" }

✅ Returns:  
{
"sql_query": "SELECT ... WHERE "Client Name" = 'John Doe' AND ...",
"reply": "Most of your orders last week were cancelled due to shop unavailability..."
}

---

### `POST /end`
Clear all stored conversation & values.  
✅ Returns:  
{
"message": "All data cleared",
"status": "success"
}

---

### `GET /`
Renders the test frontend (`index2.html`).

---

## 🛡️ Security Considerations
- Only **SELECT** SQL queries are allowed  
- SQL generation includes strict filtering (`Client Name` match required)  
- Conversation memory stored in SQLite, resettable with `/end`  
- API keys managed via `.env`  

---

## 📖 Future Improvements
- 🔄 Better conversation memory refinement  
- 🧠 Extend Claude integration for multi-turn dialogues  
- 📊 Rich frontend dashboard  
- 🚦 Caching for repeated queries  

---

## 👨‍💻 Author
Developed for **Leajlak Services** conversational AI chatbot system.  

