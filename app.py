import gradio as gr
import os
import matplotlib.pyplot as plt
import numpy as np
import time
import requests
import json
from contextlib import closing

# Azure endpoint configuration
AZURE_ENDPOINT = os.environ.get("AZURE_ENDPOINT")
AZURE_API_KEY = os.environ.get("AZURE_API_KEY")

# Use the port specified by the environment variable WEBSITE_PORT, default to 7860 if not set.
port = int(os.environ.get("WEBSITE_PORT", 7860))

def chat_with_azure(message, history, file=None):
    """
    Send a message to Azure Promptflow and return the response.
    Properly handles streaming responses and ensures connections are closed.
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
        # Option 1: Non-streaming approach (more reliable)
        response = requests.post(AZURE_ENDPOINT, headers=headers, json=payload, timeout=60)
        
        # Check if the response was successful
        if response.status_code != 200:
            return f"❌ Fehler: HTTP Status {response.status_code}. {response.text}"
            
        # Try to parse JSON response
        try:
            result = response.json()
            # Adapt this to your specific Azure response format
            if isinstance(result, dict) and "answer" in result:
                return result["answer"]
            return response.text
        except json.JSONDecodeError:
            # Return raw text if it's not valid JSON
            return response.text
        
    except requests.exceptions.Timeout:
        return "❌ Zeitüberschreitung bei der Anfrage an Azure. Bitte versuchen Sie es später erneut."
    except requests.exceptions.ConnectionError:
        return "❌ Verbindungsfehler beim Zugriff auf Azure. Bitte überprüfen Sie Ihre Internetverbindung und Azure-Konfiguration."
    except Exception as e:
        return f"❌ Fehler beim Aufruf des Azure-Endpoints: {str(e)}"

def handle_file(file):
    """Handle uploaded files"""
    if file:
        # Process the file here if needed
        file_size = os.path.getsize(file.name) if file.name else 0
        return f"Datei '{file.name}' ({file_size} Bytes) erfolgreich hochgeladen."
    return ""

def generate_plot(message):
    """Generate a plot based on the message content"""
    # Check if message exists
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

def clear_interface():
    """Clear all elements of the interface"""
    return None, None

# Create the chat interface with additional inputs for file upload
with gr.Blocks() as demo:
    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(height=500, label="Azure Promptflow Chat")
            msg = gr.Textbox(
                placeholder="Geben Sie Ihre Nachricht ein...",
                container=False,
                scale=7,
                show_label=False
            )
            with gr.Row():
                submit = gr.Button("Senden", variant="primary")
                clear = gr.Button("Löschen")
        
        with gr.Column(scale=1):
            with gr.Accordion("Datei hochladen", open=False):
                file_upload = gr.File(label="Datei auswählen")
                file_status = gr.Textbox(label="Status", interactive=False)
            
            plot_output = gr.Plot(label="Grafische Darstellung")
            
            with gr.Accordion("Über diesen Chatbot", open=False):
                gr.Markdown("""
                # Azure Promptflow Chat
                
                Dieser Chatbot nutzt Azure Promptflow für die Generierung von Antworten.
                
                - Laden Sie optional Dateien hoch
                - Die Grafik zeigt eine Visualisierung basierend auf Ihrer Nachrichtenlänge
                """)
    
    # Set up the chat functionality
    msg_and_chatbot = msg.submit(
        chat_with_azure, 
        [msg, chatbot, file_upload], 
        [msg, chatbot],
        queue=True
    ).then(
        generate_plot,
        [msg],
        [plot_output]
    )
    
    submit.click(
        chat_with_azure, 
        [msg, chatbot, file_upload], 
        [msg, chatbot],
        queue=True
    ).then(
        generate_plot,
        [msg],
        [plot_output]
    )
    
    # Handle file uploads
    file_upload.change(
        handle_file,
        [file_upload],
        [file_status],
        queue=False
    )
    
    # Handle clearing
    clear.click(
        lambda: None,
        None,
        msg,
        queue=False
    )
    clear.click(
        lambda: [],
        None,
        chatbot,
        queue=False
    )
    clear.click(
        lambda: None,
        None,
        plot_output,
        queue=False
    )
    clear.click(
        lambda: None,
        None,
        file_status,
        queue=False
    )
    clear.click(
        lambda: None,
        None,
        file_upload,
        queue=False
    )

demo.launch(server_name="0.0.0.0", server_port=port)
