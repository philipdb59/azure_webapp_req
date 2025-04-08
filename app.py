import gradio as gr
import os
import matplotlib.pyplot as plt
import numpy as np
import time
import requests
import json
import traceback
import sys

# Azure endpoint configuration
AZURE_ENDPOINT = os.environ.get("AZURE_ENDPOINT")
AZURE_API_KEY = os.environ.get("AZURE_API_KEY")

# Use the port specified by the environment variable WEBSITE_PORT, default to 7860 if not set.
port = int(os.environ.get("WEBSITE_PORT", 7860))

def chat_with_azure(message, history):
    debug_info = f"🔍 Debug: Processing message: '{message}'\n"
    debug_info += f"🔍 History length: {len(history)}\n"
    
    # Convert chat history to the format Azure expects
    chat_history = []
    for user, bot in history:
        chat_history.append({
            "inputs": {"question": user},
            "outputs": {"answer": bot}
        })
    
    payload = {
        "chat_input": message,
        "chat_history": chat_history
    }
    
    debug_info += f"🔍 Sending request to Azure...\n"
    
    try:
        # Create a fresh session for each request
        session = requests.Session()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AZURE_API_KEY}",
            "Accept": "application/json"
        }
        
        response = session.post(
            AZURE_ENDPOINT, 
            headers=headers, 
            json=payload, 
            timeout=30
        )
        
        debug_info += f"🔍 Response status: {response.status_code}\n"
        
        # Force close the session
        session.close()
        
        if response.status_code != 200:
            return f"{debug_info}\n❌ Error: Server returned status code {response.status_code}\nResponse: {response.text}"
        
        try:
            response_data = response.json()
            chat_output = response_data.get("chat_output", "No chat_output in response")
            return chat_output  # Don't include debug in final successful output
        except json.JSONDecodeError:
            return f"{debug_info}\n❌ Error: Could not parse JSON response\nRaw response: {response.text[:500]}..."
            
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        stack_trace = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        return f"{debug_info}\n❌ Error: {str(e)}\n\nStack trace:\n{stack_trace}"

# Create the chat interface with minimal components
with gr.Blocks() as demo:
    chatbot = gr.ChatInterface(
        chat_with_azure,
        type="messages",
        examples=["Wie geht es dir?", "Was ist Prompt Flow?"],
        title="Azure Prompt Flow Chat (Debug Mode)",
        description="This interface includes debug information when errors occur.",
        save_history=True,
    )
    
    with gr.Accordion("Debug Options", open=False):
        test_button = gr.Button("Send Test Message")
        def send_test_message():
            return "Test message sent at " + time.strftime("%H:%M:%S")
        test_button.click(send_test_message, None, chatbot.inputbox)


demo.launch(server_name="0.0.0.0", server_port=port)
