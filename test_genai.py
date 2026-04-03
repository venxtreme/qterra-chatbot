import os
from google import genai
from google.genai import types

def test_api():
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("No API key")
        return
        
    client = genai.Client(api_key=api_key)
    print("Client created.")
    
    SYSTEM_PROMPT = "You are a helpful assistant."
    history = [
        types.Content(role="user", parts=[types.Part(text="Hello")]),
        types.Content(role="model", parts=[types.Part(text="Hi there!")]),
    ]
    
    try:
        print("Testing gemini-2.0-flash...")
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents='test',
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)
        )
        print("Success 2.0:", response.text)
    except Exception as e:
        print("Error 2.0:", type(e), e)

    try:
        print("Testing gemini-1.5-flash...")
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents='test',
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)
        )
        print("Success 1.5:", response.text)
    except Exception as e:
        print("Error 1.5:", type(e), e)

if __name__ == "__main__":
    test_api()
