import gradio as gr
import os
import matplotlib.pyplot as plt
import numpy as np
import time
import requests
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Azure endpoint configuration
AZURE_ENDPOINT = os.environ.get("AZURE_ENDPOINT")
AZURE_API_KEY = os.environ.get("AZURE_API_KEY")

# Use the port specified by the environment variable WEBSITE_PORT, default to 7860 if not set.
port = int(os.environ.get("WEBSITE_PORT", 7860))

def chat_with_azure(message, history, file=None):
    logger.info(f"Function called with message: {message}")
    logger.info(f"History length: {len(history)}")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AZURE_API_KEY}",
        "Accept": "application/json"
    }
    
    # Convert chat history to the format Azure expects
    chat_history = []
    for user, bot in history:
        chat_history.append({
            "inputs": {"question": user},
            "outputs": {"answer": bot}
        })
    
    logger.info(f"Formatted chat history: {json.dumps(chat_history)}")
    
    payload = {
        "chat_input": message,
        "chat_history": chat_history
    }
    
    logger.info(f"Sending payload to Azure: {json.dumps(payload)}")
    
    try:
        logger.info(f"Making request to endpoint: {AZURE_ENDPOINT}")
        response = requests.post(AZURE_ENDPOINT, headers=headers, json=payload)
        
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response headers: {response.headers}")
        logger.info(f"Raw response: {response.text}")
        
        response_data = response.json()
        logger.info(f"Parsed JSON response: {json.dumps(response_data)}")
        
        # Extract the chat_output field from the response
        chat_output = response_data.get("chat_output", "No chat_output in response")
        logger.info(f"Extracted chat_output: {chat_output}")
        
        return chat_output
    except Exception as e:
        error_msg = f"❌ Fehler beim Aufruf des Azure-Endpoints: {str(e)}"
        logger.error(f"Error occurred: {str(e)}", exc_info=True)
        return error_msg

def handle_file(file):
    logger.info(f"File upload function called with file: {file}")
    if file:
        return f"File {file.name} uploaded successfully."
    return ""

def generate_plot(message):
    logger.info(f"Generate plot function called with message: {message}")
    x = np.linspace(0, 10, 100)
    y = np.sin(x) * len(message)
    fig, ax = plt.subplots()
    ax.plot(x, y)
    ax.set_title("Plot based on message length")
    return fig

# Create the chat interface with additional inputs for file upload
with gr.Blocks() as demo:
    with gr.Row():
        with gr.Column(scale=3):
            logger.info("Setting up chat interface")
            chatbot = gr.ChatInterface(
                chat_with_azure,
                type="messages",
                flagging_mode="manual",
                flagging_options=["Like", "Spam", "Inappropriate", "Other"],
                save_history=True,
            )
        
        with gr.Column(scale=1):
            debug_output = gr.Textbox(label="Debug Output", lines=10)
    
    with gr.Accordion("Upload a File", open=False):
        file_upload = gr.File(label="Upload a File")
        plot_output = gr.Plot(label="Plot Output")
    
    clear = gr.Button("Clear")
    
    # Add debug event handler
    def update_debug():
        log_contents = "DEBUG LOG:\n"
        try:
            with open("debug.log", "r") as f:
                log_contents += f.read()
        except:
            log_contents += "No log file found"
        return log_contents
    
    refresh_debug = gr.Button("Refresh Debug Log")
    refresh_debug.click(update_debug, None, debug_output)
    
    file_upload.change(handle_file, file_upload, chatbot, queue=False)
    clear.click(lambda: None, None, chatbot, queue=False)
    clear.click(lambda: None, None, plot_output, queue=False)
    clear.click(lambda: None, None, debug_output, queue=False)

logger.info("Launching Gradio app")
demo.launch(server_name="0.0.0.0", server_port=port)
