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

# Use the port specified by the environment variable WEBSITE_PORT, default to 7860 if not set.
port = int(os.environ.get("WEBSITE_PORT", 7860))

# Globale Variable zum Zwischenspeichern des hochgeladenen Files
uploaded_file = None

def chat_with_azure(message, history, simulate_mode):
    global uploaded_file

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

    # Falls eine Datei übergeben wurde, ergänze den Input-Text
    if uploaded_file and uploaded_file.name.endswith('.csv'):
        try:
            df = pd.read_csv(uploaded_file)
            header_info = ", ".join(df.columns)
            preview = df.to_string(index=False)
            csv_text = f"\n\n[CSV-Daten hochgeladen]\nSpalten: {header_info}\nVorschau:\n{preview}"
            message = f"{message.strip()}\n{csv_text}"
        except Exception as e:
            return f"❌ Fehler beim Lesen der CSV-Datei: {str(e)}"

    # Payload zusammenbauen
    payload = {
        "chat_input": message,
        "chat_history": chat_history
    }

    print("📤 Gesendeter Payload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    # Entweder simulieren oder echt senden
    if simulate_mode:
        return f"🧪 **Simulierter Azure-Call:**\n```json\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n```"

    try:
        response = requests.post(AZURE_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        return response.json().get("chat_output", "⚠️ Keine Antwort erhalten.")
    except Exception as e:
        return f"❌ Fehler beim Aufruf des Azure-Endpoints: {str(e)}"

def handle_file(file):
    global uploaded_file
    uploaded_file = file
    if file:
        if file.name.endswith('.csv'):
            return f"✅ CSV-Datei **{file.name}** erfolgreich hochgeladen."
        else:
            return f"❌ Nur CSV-Dateien (.csv) werden unterstützt."
    return "📂 Keine Datei hochgeladen."

# GUI
with gr.Blocks(css="""
    .blue-textbox textarea {
        background-color: #e0f0ff !important;  /* hellblauer Hintergrund */
        color: #000000 !important;             /* schwarzer Text */
    }
""") as demo:
    gr.Markdown("## 💬 Chat mit Azure + Datei-Upload")

    simulate_toggle = gr.Checkbox(label="🧪 Simulationsmodus (kein echter API-Call)", value=False)

    # Wrapper-Funktion für ChatInterface mit Zugriff auf Checkbox-Zustand
    def chat_wrapper(message, history):
        return chat_with_azure(message, history, simulate_toggle.value)

    chatbot = gr.ChatInterface(
        chat_wrapper,
        type="messages",
        flagging_mode="manual",
        flagging_options=["Like", "Spam", "Inappropriate", "Other"],
        save_history=True,
    )

    with gr.Accordion("📎 Datei hochladen", open=False):
        file_upload = gr.File(label="Upload a CSV File", file_types=[".csv"])
        upload_status = gr.Textbox(label="Status", interactive=False, elem_classes="blue-textbox")

    clear = gr.Button("❌ Alles zurücksetzen")

    # Event Handler
    file_upload.change(handle_file, file_upload, upload_status, queue=False)
    clear.click(lambda: None, None, chatbot, queue=False)
    clear.click(lambda: "", None, upload_status, queue=False)


demo.launch(server_name="0.0.0.0", server_port=port)
