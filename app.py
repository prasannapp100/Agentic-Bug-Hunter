import streamlit as st
import os
import subprocess
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

# 1. Setup & Config
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")
MODEL_ID = "Qwen/Qwen2.5-Coder-32B-Instruct"

st.set_page_config(page_title="MCP C++ Auto-Fixer", page_icon="🛠️", layout="wide")

# Initialize HF Client
if not HF_TOKEN:
    st.error("HF_TOKEN not found. Please check your .env file.")
    st.stop()

client = InferenceClient(token=HF_TOKEN)

# --- Logic Core (Adapted from mcp_server.py) ---
def run_auto_fix(file_path):
    # Step 1: Run the compiler
    result = subprocess.run(["g++", "-fsyntax-only", file_path], capture_output=True, text=True)
    
    if result.returncode == 0:
        return None, "✅ Code compiled successfully. No action needed."

    # Step 2: Read the file content
    try:
        with open(file_path, "r") as f:
            code_context = f.read()
    except Exception as e:
        return None, f"❌ Error reading file: {str(e)}"

    # Step 3: Call Hugging Face
    compiler_error = result.stderr
    messages = [
        {"role": "system", "content": "You are a senior C++ expert specializing in debugging and code repair."},
        {"role": "user", "content": f"The file '{file_path}' failed to compile with this error:\n{compiler_error}\n\nFULL SOURCE CODE:\n{code_context}\n\nPlease explain why this happened and provide the corrected code."}
    ]
    
    try:
        response = client.chat_completion(
            model=MODEL_ID,
            messages=messages,
            max_tokens=1024,
            temperature=0.1
        )
        return compiler_error, response.choices[0].message.content
    except Exception as e:
        return compiler_error, f"❌ AI Analysis failed: {str(e)}"

# --- Streamlit UI ---
st.title("🛠️ MCP C++ Auto-Fixer")
st.markdown("Submit your C++ code to detect compilation errors and receive AI-powered fixes.")

col_input, col_output = st.columns([1, 1])

with col_input:
    st.subheader("Source Code")
    code_input = st.text_area("Paste C++ code here:", height=400, placeholder="int main() { return 0 } // Missing semicolon")
    
    if st.button("Compile & Fix", use_container_width=True):
        if code_input:
            # Save temp file for g++
            temp_file = "web_test.cpp"
            with open(temp_file, "w") as f:
                f.write(code_input)
            
            with st.spinner("Compiling and consulting Qwen AI..."):
                error, solution = run_auto_fix(temp_file)
            
            # Store in session state to display in the right column
            st.session_state['error'] = error
            st.session_state['solution'] = solution
            
            # Clean up
            if os.path.exists(temp_file):
                os.remove(temp_file)
        else:
            st.warning("Please enter some code first.")

with col_output:
    st.subheader("Analysis & Fix")
    if 'solution' in st.session_state:
        if st.session_state['error']:
            st.error("⚠️ Compilation Error Found")
            st.code(st.session_state['error'], language="bash")
            st.markdown("### 💡 AI Explanation & Corrected Code")
            st.markdown(st.session_state['solution'])
        else:
            st.success(st.session_state['solution'])
    else:
        st.info("Results will appear here after analysis.")