import gradio as gr
import os
import matplotlib.pyplot as plt
import numpy as np
import time
import requests
import json

# Azure endpoint configuration
AZURE_ENDPOINT = os.environ.get("AZURE_ENDPOINT")
AZURE_API_KEY = os.environ.get("AZURE_API_KEY")

# Use the port specified by the environment variable WEBSITE_PORT, default to 7860 if not set.
port = int(os.environ.get("WEBSITE_PORT", 7860))

def chat_with_azure(message, history, file=None):
    """
    Send a message to Azure Promptflow and return the response.
    The Azure response contains a 'chat_output' field with the answer.
    """
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

    payload = {
        "chat_input": message,
        "chat_history": chat_history
    }

    try:
        # Send the request to Azure
        response = requests.post(AZURE_ENDPOINT, headers=headers, json=payload, timeout=60)
        
        # Check if the response was successful
        if response.status_code != 200:
            return f"❌ Fehler: HTTP Status {response.status_code}. {response.text}"
        
        # Try to parse the JSON response
        try:
            response_data = response.json()
            # Extract the chat_output field
            if "chat_output" in response_data:
                return response_data["chat_output"]
            else:
                # Fallback in case the structure changes
                return f"Antwort erhalten, aber kein 'chat_output' gefunden. Rohantwort: {response.text[:500]}..."
        except json.JSONDecodeError:
            # If not valid JSON, return the raw text
            return f"Konnte Antwort nicht als JSON verarbeiten: {response.text[:500]}..."
        
    except requests.exceptions.Timeout:
        return "❌ Zeitüberschreitung bei der Anfrage an Azure. Bitte versuchen Sie es später erneut."
    except requests.exceptions.ConnectionError:
        return "❌ Verbindungsfehler beim Zugriff auf Azure. Bitte überprüfen Sie Ihre Internetverbindung und Azure-Konfiguration."
    except Exception as e:
        return f"❌ Fehler beim Aufruf des Azure-Endpoints: {str(e)}"

def handle_file(file):
    """Handle uploaded files"""
    if file:
        file_size = os.path.getsize(file.name) if file.name else 0
        return f"Datei '{file.name}' ({file_size} Bytes) erfolgreich hochgeladen."
    return ""

def generate_plot(message):
    """Generate a plot based on the message content"""
    if not message:
        return None
        
    x = np.linspace(0, 10, 100)
    y = np.sin(x) * len(message)
    
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(x, y, linewidth=2)
    ax.set_title(f"Plot basierend auf Nachrichtenlänge ({len(message)} Zeichen)")
    ax.set_xlabel("X-Achse")
    ax.set_ylabel("Y-Achse")
    ax.grid(True, linestyle='--', alpha=0.7)
    
    return fig

# Create the chat interface with additional inputs for file upload
with gr.Blocks() as demo:
    chatbot = gr.ChatInterface(
        chat_with_azure,
        chatbot=gr.Chatbot(height=500, label="Azure Promptflow Chat"),
        textbox=gr.Textbox(placeholder="Geben Sie Ihre Nachricht ein...", container=False, scale=7),
        additional_inputs=[
            gr.File(label="Datei hochladen", visible=True)
        ],
        additional_outputs=[
            gr.Plot(label="Grafische Darstellung")
        ],
        submit_btn="Senden",
        retry_btn="Wiederholen",
        undo_btn="Rückgängig",
        clear_btn="Löschen",
    )
    
    # Generate plot when a message is sent
    chatbot.submit_btn.click(
        generate_plot,
        inputs=[chatbot.textbox],
        outputs=[chatbot.additional_outputs[0]]
    )
    
    # Add file handling
    chatbot.additional_inputs[0].change(
        handle_file,
        inputs=[chatbot.additional_inputs[0]],
        outputs=[chatbot.textbox]
    )

demo.launch(server_name="0.0.0.0", server_port=port)
