import gradio as gr
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import json

# Azure endpoint configuration
AZURE_ENDPOINT = os.environ.get("AZURE_ENDPOINT")
AZURE_API_KEY = os.environ.get("AZURE_API_KEY")

port = int(os.environ.get("WEBSITE_PORT", 7860))

# Globale Variablen
uploaded_file = None
csv_context_sent = False
csv_system_message = None

def chat_with_azure(message, history):
    global csv_context_sent
    global csv_system_message

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AZURE_API_KEY}",
        "Accept": "application/json"
    }

    # Konvertiere Gradio-History in das vom Flow erwartete Format
    chat_history = []
    # Wenn CSV noch nicht gesendet wurde, füge als System-Message hinzu
    if not csv_context_sent and csv_system_message:
        chat_history.append({
            "inputs": {"question": csv_system_message},
            "outputs": {"answer": ""}
        })
        csv_context_sent = True  # Nicht erneut senden

    # Bestehende Unterhaltung konvertieren
    for i in range(0, len(history), 2):
        user_msg = history[i]["content"] if history[i]["role"] == "user" else ""
        bot_msg = history[i + 1]["content"] if i + 1 < len(history) and history[i + 1]["role"] == "assistant" else ""
        if user_msg.strip() or bot_msg.strip():
            chat_history.append({
                "inputs": {"question": user_msg},
                "outputs": {"answer": bot_msg}
            })

    payload = {
        "chat_input": message,      # Nur die neue Nachricht
        "chat_history": chat_history
    }

    print("📤 Gesendeter Payload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    try:
        response = requests.post(AZURE_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        return response.json().get("chat_output", "⚠️ Keine Antwort erhalten.")
    except Exception as e:
        return f"❌ Fehler beim Aufruf des Azure-Endpoints: {str(e)}"

def handle_file(file):
    global uploaded_file, csv_context_sent, csv_system_message
    uploaded_file = file
    csv_context_sent = False
    csv_system_message = None

    if file and file.name.endswith('.csv'):
        try:
            df = pd.read_csv(file)
            header_info = ", ".join(df.columns)
            preview = df.head().to_string(index=False)
            csv_system_message = (
                f"[CSV-Daten wurden hochgeladen.]\n"
                f"Spalten: {header_info}\n"
                f"Vorschau:\n{preview}"
            )
            return f"✅ CSV-Datei **{file.name}** erfolgreich hochgeladen."
        except Exception as e:
            return f"❌ Fehler beim Lesen der CSV-Datei: {str(e)}"
    return "❌ Ungültige Datei. Nur .csv erlaubt."

def generate_plot(message):
    x = np.linspace(0, 10, 100)
    y = np.sin(x) * len(message)
    fig, ax = plt.subplots()
    ax.plot(x, y)
    ax.set_title("Plot based on message length")
    return fig

# GUI
with gr.Blocks() as demo:
    gr.Markdown("## 💬 Chat mit Azure + CSV-Datenintegration")

    chatbot = gr.ChatInterface(
        chat_with_azure,
        type="messages",
        flagging_mode="manual",
        flagging_options=["Like", "Spam", "Inappropriate", "Other"],
        save_history=True,
    )

    with gr.Accordion("📎 Datei hochladen", open=False):
        file_upload = gr.File(label="Upload a CSV File", file_types=[".csv"])
        upload_status = gr.Textbox(label="Status", interactive=False)

    plot_output = gr.Plot(label="Plot Output")
    clear = gr.Button("❌ Alles zurücksetzen")

    # Event Handler
    file_upload.change(handle_file, file_upload, upload_status, queue=False)
    clear.click(lambda: None, None, chatbot, queue=False)
    clear.click(lambda: None, None, plot_output, queue=False)
    clear.click(lambda: "", None, upload_status, queue=False)

demo.launch(server_name="0.0.0.0", server_port=port)
