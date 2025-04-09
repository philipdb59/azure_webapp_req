import gradio as gr
import os
import matplotlib.pyplot as plt
import numpy as np
import time
import requests
import json
import pandas as pd

# Azure endpoint configuration
AZURE_ENDPOINT = os.environ.get("AZURE_ENDPOINT")
AZURE_API_KEY = os.environ.get("AZURE_API_KEY")

# Use the port specified by the environment variable WEBSITE_PORT, default to 7860 if not set.
port = int(os.environ.get("WEBSITE_PORT", 7860))

def chat_with_azure(message, history, file=None):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AZURE_API_KEY}",
        "Accept": "application/json"
    }

    # Konvertiere Gradio-History in das vom Flow erwartete Format
    chat_history = []
    for i in range(0, len(history), 2):
        user_msg = history[i]["content"] if history[i]["role"] == "user" else ""
        bot_msg = history[i + 1]["content"] if i + 1 < len(history) and history[i + 1]["role"] == "assistant" else ""
        if user_msg.strip() and bot_msg.strip():
            chat_history.append({
                "inputs": {"question": user_msg},
                "outputs": {"answer": bot_msg}
            })

    # Falls CSV hochgeladen wurde, ergänze den Input-Text
    if file and file.name.endswith('.csv'):
        try:
            df = pd.read_csv(file.name)
            header_info = ", ".join(df.columns)
            preview = df.head().to_string(index=False)
            csv_text = f"\n\n[CSV-Daten hochgeladen]\nSpalten: {header_info}\nVorschau:\n{preview}"
            message += csv_text
        except Exception as e:
            return f"❌ Fehler beim Lesen der CSV-Datei: {str(e)}"

    payload = {
        "chat_input": message,
        "chat_history": chat_history
    }

    try:
        response = requests.post(AZURE_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        return response.json().get("chat_output", "⚠️ Keine Antwort erhalten.")
    except Exception as e:
        return f"❌ Fehler beim Aufruf des Azure-Endpoints: {str(e)}"

def handle_file(file):
    if file:
        if file.name.endswith('.csv'):
            return f"CSV-Datei {file.name} erfolgreich hochgeladen."
        else:
            return f"❌ Nur CSV-Dateien (.csv) werden unterstützt."
    return ""

def generate_plot(message):
    x = np.linspace(0, 10, 100)
    y = np.sin(x) * len(message)
    fig, ax = plt.subplots()
    ax.plot(x, y)
    ax.set_title("Plot based on message length")
    return fig

# GUI
with gr.Blocks() as demo:
    chatbot = gr.ChatInterface(
        chat_with_azure,
        type="messages",
        flagging_mode="manual",
        flagging_options=["Like", "Spam", "Inappropriate", "Other"],
        save_history=True,
    )

    with gr.Accordion("Upload a File", open=False):
        file_upload = gr.File(label="Upload a CSV File", file_types=[".csv"])

    plot_output = gr.Plot(label="Plot Output")
    clear = gr.Button("Clear")

    file_upload.change(handle_file, file_upload, chatbot, queue=False)
    clear.click(lambda: None, None, chatbot, queue=False)
    clear.click(lambda: None, None, plot_output, queue=False)

demo.launch(server_name="0.0.0.0", server_port=port)
