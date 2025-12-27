from voiceeval import Client, observe
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# OpenAI is auto-instrumented by Client()

def main():
    # 1. Initialize Client pointing to local proxy
    client = Client(
        api_key="your-api-key", 
        base_url="http://localhost:8000/v1/traces"
    )
    print("Client initialized.")

    # 2. Instrument a function calling OpenAI
    @observe(name_override="voice_agent_transaction")
    def run_agent_simulation(user_input):
        print(f"Agent received: {user_input}")
        
        client_openai = OpenAI()
        completion = client_openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful voice assistant."},
                {"role": "user", "content": user_input}
            ]
        )
        response = completion.choices[0].message.content
        return response

    # 3. Run
    # Ensure OPENAI_API_KEY is set
    if "OPENAI_API_KEY" not in os.environ:
        print("Please set OPENAI_API_KEY environment variable.")
        return

    print("Running simulation with OpenAI...")
    response = run_agent_simulation("What is the capital of France?")
    print(f"Agent response: {response}")
    print("Trace generated. Check server logs.")

if __name__ == "__main__":
    main()
