from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME="gemini-2.0-flash-lite-preview-02-05"
client = genai.Client(api_key=os.getenv("API_KEY"))

def generate_haiku(prompt):
    try:
        response = client.models.generate_content(
            model=MODEL_NAME, 
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Error generating content: {e}"


haiku = generate_haiku(input("How can I help? "))
print(f"Using model: {MODEL_NAME}")
#print("Generated Haiku:")
print(haiku)