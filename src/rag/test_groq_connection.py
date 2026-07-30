# File: src/rag/test_groq_connection.py

import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY not found. Check your .env file exists and is loaded correctly.")

client = Groq(api_key=api_key)

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "user", "content": "In one sentence, what is an Environmental Product Declaration (EPD)?"}
    ],
)

print("Response from Groq:")
print(response.choices[0].message.content)