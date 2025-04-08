import gradio as gr
import os
import matplotlib.pyplot as plt
import numpy as np
import requests
import json
# Read environment variables
AZURE_ENDPOINT = os.environ.get("AZURE_ENDPOINT")
AZURE_API_KEY = os.environ.get("AZURE_API_KEY")
print("DEBUG: AZURE_ENDPOINT:", AZURE_ENDPOINT)
print("DEBUG: AZURE_API_KEY is set:", bool(AZURE_API_KEY))
# Use the port specified by the environment variable WEBSITE_PORT, default to 7860 if not set.
port = int(os.environ.get("WEBSITE_PORT", 7860))
print("DEBUG: Server starting on port:", port)
def chat_with_azure(message, history, file=None):
    """
    This function sends the user message + history to your Azure endpoint and streams back the response.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AZURE_API_KEY}",
        "Accept": "application/json"
    }
    print("\n\n=== chat_with_azure CALLED ===")
    print("DEBUG: message:", message)
    print("DEBUG: history:", history)
    print("DEBUG: file argument:", file)
    # Convert chat history to the format your endpoint expects.
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
    # Log the exact payload to ensure it’s valid JSON.
    print("DEBUG: Payload being sent to Azure:")
    print(json.dumps(payload, indent=2))
    try:
        # Perform the POST request to Azure with streaming
        response = requests.post(AZURE_ENDPOINT, headers=headers, json=payload, stream=True)
        print("DEBUG: Response status code from Azure:", response.status_code)
        # If the status code is not 200, you might want to handle it:
        if response.status_code != 200:
            print("WARNING: Received a non-200 status code:", response.status_code)
            yield f"❌ Fehler beim Aufruf des Azure-Endpoints, Status Code: {response.status_code}"
            return
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode("utf-8")
                print("DEBUG: Decoded line from Azure stream:", decoded_line)
                yield decoded_line
    except Exception as e:
        print("DEBUG: Exception caught while calling Azure endpoint:", str(e))
        yield f"❌ Fehler beim Aufruf des Azure-Endpoints: {str(e)}"
def handle_file(file):
    """
    Simple helper function to log file uploads.
    """
    if file:
        print("DEBUG: File uploaded:", file.name)
        return f"File {file.name} uploaded successfully."
    print("DEBUG: No file uploaded.")
    return ""
def generate_plot(message):
    """
    Generates a simple sine plot whose amplitude is determined by the length of the user message.
    """
    print("DEBUG: Generating plot for message:", message)
    x = np.linspace(0, 10, 100)
    y = np.sin(x) * len(message)
    fig, ax = plt.subplots()
    ax.plot(x, y)
    ax.set_title("Plot based on message length")
    return fig
# Build the Gradio interface
with gr.Blocks() as demo:
    chatbot = gr.ChatInterface(
        fn=chat_with_azure,
        type="messages",
        flagging_mode="manual",
        flagging_options=["Like", "Spam", "Inappropriate", "Other"],
        save_history=True
    )
    with gr.Accordion("Upload a File", open=False):
        file_upload = gr.File(label="Upload a File")
    plot_output = gr.Plot(label="Plot Output")
    clear = gr.Button("Clear")
    # When a file is uploaded, call handle_file
    file_upload.change(handle_file, file_upload, chatbot, queue=False)
    # When the clear button is clicked, reset both the chatbot and plot
    clear.click(lambda: None, None, chatbot, queue=False)
    clear.click(lambda: None, None, plot_output, queue=False)
# Launch the Gradio demo
demo.launch(server_name="0.0.0.0", server_port=port)
