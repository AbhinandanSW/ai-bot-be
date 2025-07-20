# AI Bot Backend

This is the backend for an AI-powered chatbot application. It is organized as a Python project and provides authentication, chat, streaming, and rate-limiting functionalities.

## Project Structure
```
├── app/
│   ├── auth.py              # Authentication logic
│   ├── auth_dependencies.py # Auth-related dependencies
│   ├── chat.py              # Chat endpoints and logic
│   ├── config.py            # Configuration settings
│   ├── db.py                # Database connection and helpers
│   ├── gemini.py            # Gemini model integration
│   ├── models.py            # Database models
│   ├── rate_limiter.py      # Rate limiting logic
│   └── stream.py            # Streaming endpoints
├── database/
│   └── auth.sql             # SQL schema for authentication
├── main.py                  # Entry point for the backend server
├── requirements.txt         # Python dependencies
├── .env.example             # Example environment variables
```

## Getting Started

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd ai-bot-be
2. **Install dependecies:**
    ```bash
   pip install -r requirements.txt
4. **Set up environment variables:**
   ```bash
    Copy .env.example to .env and fill in the required values.
5. ** Set up the database:**
    ```
    Use the SQL schema in database/auth.sql to initialize your database.
6. **Run the server:**
   ```bash
   python main.py


## Features
- User authentication
- Chat endpoints
- Rate limiting
- Streaming responses
- Gemini model integration
