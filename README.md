## 📦 Customer Service Chatbot (Flask + PostgreSQL + Anthropic)
This project is a Flask-based chatbot application that integrates:

Anthropic Claude API for SQL generation and customer-friendly insights.

PostgreSQL for user and order data.

SQLite (local) to maintain temporary conversation state.

Ngrok for tunneling requests to the development server.

It is designed as a customer service assistant that:

Accepts a mobile number to identify a user.

Fetches user-related order data from PostgreSQL.

Generates safe SQL queries dynamically.

Summarizes the query results into natural language responses.

Stores conversational context for continuity.
