import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_database():
    print("Testing Neon database connection...")
    try:
        # Import the engine and models from db.py
        from db import engine, init_db, LoggedDecision, SessionLocal
        
        # Test connection
        with engine.connect() as connection:
            print("  [OK] Database connection established successfully!")
            
        # Test querying the table
        db = SessionLocal()
        try:
            count = db.query(LoggedDecision).count()
            print(f"  [OK] Database query succeeded. Found {count} logged decisions in the table.")
        finally:
            db.close()
            
        return True
    except Exception as e:
        print(f"  [FAIL] Database test failed: {e}")
        return False

def test_gemini():
    print("Testing Google Gemini API connection...")
    try:
        from google import genai
        
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("  [FAIL] GEMINI_API_KEY environment variable is not set.")
            return False
            
        client = genai.Client(api_key=api_key)
        
        models_to_try = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-2.0-flash-lite']
        working_model = None
        
        for model_name in models_to_try:
            try:
                print(f"Trying to connect using model '{model_name}'...")
                response = client.models.generate_content(
                    model=model_name,
                    contents="Say 'Pong' to verify connection."
                )
                reply = response.text.strip()
                print(f"  [OK] Successfully connected using '{model_name}'! Response: '{reply}'")
                working_model = model_name
                break
            except Exception as gen_err:
                print(f"  [FAIL] Model '{model_name}' failed: {gen_err}")
        
        if working_model:
            print(f"\nFound working model: '{working_model}'. Please update your gemini.py if it is not using this model.")
            return True
        else:
            print("\nAll tested models failed. Let's list the available models to see if you have access to other models:")
            try:
                models = list(client.models.list())
                if models:
                    print("Available models:")
                    for m in models[:10]:
                        print(f"  - {m.name}")
                else:
                    print("No models returned for this API key.")
            except Exception as list_err:
                print(f"Could not list models: {list_err}")
            return False
            
    except Exception as e:
        print(f"  [FAIL] Gemini API test execution failed: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "="*50)
    print("=== DECISIONLOG SETUP VERIFICATION ===")
    print("="*50)
    
    db_ok = test_database()
    print("-"*50)
    gemini_ok = test_gemini()
    print("="*50)
    
    if db_ok and gemini_ok:
        print("SUCCESS: All automated connection checks passed!")
        sys.exit(0)
    else:
        print("ERROR: One or more checks failed. Please check your .env settings.")
        sys.exit(1)
