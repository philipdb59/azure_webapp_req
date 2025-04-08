import gradio as gr
import os
import matplotlib.pyplot as plt
import numpy as np
import requests
import json
import re
import subprocess
import tempfile
import io
 
# =========================================
# Global variables
# =========================================
 
# Track the uploaded file contents globally so that
# the chat function can access them on every request.
uploaded_file_contents = None  
 
# Azure endpoint configuration
AZURE_ENDPOINT = os.environ.get("AZURE_ENDPOINT")
AZURE_API_KEY = os.environ.get("AZURE_API_KEY")
 
# Use the port specified by WEBSITE_PORT, otherwise default to 7860.
port = int(os.environ.get("WEBSITE_PORT", 7860))
 
# =========================================
# Helper functions
# =========================================
 
def generate_diagram_from_plantuml(uml_code: str) -> "bytes":
    """
    Given a string containing valid PlantUML code, runs PlantUML locally and returns PNG bytes.
    This requires:
       1) A 'plantuml.jar' file in the same folder.
       2) Java installed in the Docker image.
    """
    # Create a temp file with .puml extension
    with tempfile.NamedTemporaryFile(suffix=".puml", delete=False) as f:
        f.write(uml_code.encode("utf-8"))
        puml_file_path = f.name
 
    # Generate a PNG using plantuml.jar
    try:
        cmd = ["java", "-jar", "plantuml.jar", "-tpng", puml_file_path]
        subprocess.run(cmd, check=True)
        # The output will be puml_file_path with .png extension
        png_file_path = puml_file_path.replace(".puml", ".png")
        with open(png_file_path, "rb") as f:
            png_data = f.read()
        return png_data
    except subprocess.CalledProcessError as e:
        print("Error generating PlantUML diagram:", e)
        return None
    finally:
        # Cleanup temp files if you like (optional or OS-handled)
        pass
 
def plantuml_bytes_to_matplotlib_figure(png_data: bytes):
    """
    Convert raw PNG bytes into a matplotlib Figure so it can be displayed in gr.Plot.
    """
    import matplotlib.image as mpimg
 
    if png_data is None:
        return None
 
    # Read PNG bytes into an in-memory buffer
    buf = io.BytesIO(png_data)
    image = mpimg.imread(buf, format='png')
 
    fig, ax = plt.subplots()
    ax.imshow(image)
    ax.axis('off')
    return fig
 
# =========================================
# File handling
# =========================================
 
def handle_file(file):
    """
    When a file is uploaded, store its contents in 'uploaded_file_contents'.
    Also return a short info message in the chat.
    """
    global uploaded_file_contents
    if file is not None:
        try:
            # Read the raw bytes and convert to string (assuming UTF-8)
            content = file.read().decode("utf-8", errors="replace")
            uploaded_file_contents = content
            return f"File '{file.name}' uploaded successfully."
        except Exception as e:
            return f"Error reading file: {str(e)}"
    else:
        uploaded_file_contents = None
        return "No file uploaded."
 
# =========================================
# LLM Chat Logic
# =========================================
 
def chat_with_azure(message, history, file=None):
    """
    Sends the user message and the global 'uploaded_file_contents' to Azure. 
    Expects a JSON response with 'chat_output' containing the LLM's answer.
    Returns the text to display in the chatbot.
    """
    # Build the conversation from Gradio’s "history" (which is a list of messages).
    # For ChatInterface, each message is a dict like {"role": "user"/"assistant", "content": "..."}.
    chat_history = []
    for i in range(0, len(history), 2):
        user_msg = history[i]["content"] if history[i]["role"] == "user" else ""
        bot_msg = ""
        if i+1 < len(history) and history[i+1]["role"] == "assistant":
            bot_msg = history[i+1]["content"]
        chat_history.append(
            {"inputs": {"question": user_msg}, "outputs": {"answer": bot_msg}}
        )
 
    # Append file contents to user message if available:
    global uploaded_file_contents
    if uploaded_file_contents:
        message += f"\n\n[Here is the uploaded file content (if needed):]\n{uploaded_file_contents}"
 
    payload = {
        "chat_input": message,
        "chat_history": chat_history
    }
 
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AZURE_API_KEY}",
        "Accept": "application/json"
    }
 
    try:
        response = requests.post(AZURE_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        # The endpoint is expected to return {"chat_output": "..."}
        answer = result.get("chat_output", "⚠️ Keine Antwort erhalten.")
        return answer
    except Exception as e:
        return f"❌ Fehler beim Aufruf des Azure-Endpoints: {str(e)}"
 
# =========================================
# Diagram Generation after Chat
# =========================================
 
def parse_plantuml_and_plot(chat_history):
    """
    1) Looks at the last assistant message in the chat_history.
    2) Searches for a block that starts with '@startuml' and ends with '@enduml'.
    3) Renders that PlantUML code into a PNG with local plantuml.jar + Java, 
       and returns a matplotlib Figure for display in gr.Plot.
    """
    # Get the last assistant message
    assistant_message = None
    # chat_history is a list of dict: [{"role": "user"/"assistant", "content": "..."}]
    for msg in reversed(chat_history):
        if msg["role"] == "assistant":
            assistant_message = msg["content"]
            break
 
    if not assistant_message:
        return None  # no assistant message found
 
    # Regex to find a chunk from @startuml to @enduml
    pattern = re.compile(r'@startuml(.*?)@enduml', re.DOTALL)
    match = pattern.search(assistant_message)
    if not match:
        print("No @startuml/@enduml block found in assistant message.")
        return None
 
    plantuml_code = "@startuml" + match.group(1) + "@enduml"
    print("Extracted PlantUML code:\n", plantuml_code)
 
    # Generate PNG
    png_data = generate_diagram_from_plantuml(plantuml_code)
    if not png_data:
        return None
 
    # Convert PNG to matplotlib figure
    fig = plantuml_bytes_to_matplotlib_figure(png_data)
    return fig
 
# =========================================
# Gradio UI
# =========================================
 
with gr.Blocks() as demo:
    chatbot = gr.ChatInterface(
        fn=chat_with_azure,
        type="messages",
        flagging_mode="manual",
        flagging_options=["Like", "Spam", "Inappropriate", "Other"],
        save_history=True,
    )
 
    with gr.Accordion("Upload a File", open=False):
        file_upload = gr.File(label="Upload a File")
    # We’ll display the UML diagram in this plot after the user clicks “Generate Diagram”
    diagram_plot = gr.Plot(label="Generated UML Diagram")
 
    # Button to clear the chat or diagram
    clear = gr.Button("Clear Chat/Diagram")
 
    # When a file is uploaded, call handle_file to store its contents in a global var
    file_upload.change(fn=handle_file, inputs=file_upload, outputs=chatbot, queue=False)
 
    # Button to parse the last assistant message for @startuml...@enduml code and display
    generate_diagram_btn = gr.Button("Generate Diagram from Last Chat Response")
 
    # The click event will pass the entire chat history (which is `chatbot` in ChatInterface)
    # to parse_plantuml_and_plot, and display the figure in `diagram_plot`.
    generate_diagram_btn.click(fn=parse_plantuml_and_plot, inputs=chatbot, outputs=diagram_plot)
 
    # Clear button: reset chat + diagram
    clear.click(lambda: None, None, chatbot, queue=False)
    clear.click(lambda: None, None, diagram_plot, queue=False)
 
demo.launch(server_name="0.0.0.0", server_port=port)
