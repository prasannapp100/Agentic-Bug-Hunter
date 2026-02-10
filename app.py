import streamlit as st
import os
import subprocess
import re
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

# 1. Setup & Configuration
load_dotenv()
# Using st.secrets for Cloud deployment with a fallback to local .env
HF_TOKEN = st.secrets.get("HF_TOKEN") or os.getenv("HF_TOKEN")
MODEL_ID = "Qwen/Qwen2.5-Coder-32B-Instruct"

st.set_page_config(page_title="Multi-Lang Agentic Fixer", page_icon="🛠️", layout="wide")

if not HF_TOKEN:
    st.error("HF_TOKEN not found. Please add it to Streamlit Secrets or your .env file.")
    st.stop()

client = InferenceClient(token=HF_TOKEN)

# --- Helper Functions ---

def extract_code(text):
    """Extracts code blocks from the AI's markdown response."""
    # Look for code between triple backticks
    match = re.search(r"```(?:\w+)?\n(.*?)\n```", text, re.DOTALL)
    if match:
        return match.group(1)
    return text  # Fallback if no backticks are present

def run_syntax_check(file_path, language):
    """Executes the appropriate system compiler/interpreter for syntax validation."""
    if language == "C++":
        return subprocess.run(["g++", "-fsyntax-only", file_path], capture_output=True, text=True)
    elif language == "Python":
        # Checks syntax without executing
        return subprocess.run(["python3", "-m", "py_compile", file_path], capture_output=True, text=True)
    elif language == "Java":
        return subprocess.run(["javac", file_path], capture_output=True, text=True)
    return None

def process_fix(code, language):
    """Handles the full workflow: Save -> Check -> AI Analysis -> Cleanup."""
    ext_map = {"C++": ".cpp", "Python": ".py", "Java": ".java"}
    
    # Java handling: try to match filename to public class name
    filename = "temp_code"
    if language == "Java":
        match = re.search(r"public\s+class\s+(\w+)", code)
        if match:
            filename = match.group(1)
            
    temp_file = f"{filename}{ext_map[language]}"
    
    with open(temp_file, "w") as f:
        f.write(code)
    
    # Step 1: Run local syntax check
    result = run_syntax_check(temp_file, language)
    
    if result.returncode == 0:
        # Cleanup and return success
        if os.path.exists(temp_file): os.remove(temp_file)
        return None, f"✅ Your {language} code compiled successfully! No bugs detected."

    # Step 2: AI Fix if syntax check failed
    compiler_error = result.stderr if result.stderr else result.stdout
    messages = [
        {"role": "system", "content": f"You are a senior {language} expert specializing in debugging."},
        {"role": "user", "content": f"The following {language} code failed with this error:\n{compiler_error}\n\nSOURCE CODE:\n{code}\n\nPlease explain the error and provide the full corrected code."}
    ]
    
    try:
        response = client.chat_completion(
            model=MODEL_ID,
            messages=messages,
            max_tokens=1024,
            temperature=0.1
        )
        ai_response = response.choices[0].message.content
    except Exception as e:
        ai_response = f"❌ AI Analysis failed: {str(e)}"
    
    # Cleanup generated files
    if os.path.exists(temp_file): os.remove(temp_file)
    if language == "Java":
        class_file = f"{filename}.class"
        if os.path.exists(class_file): os.remove(class_file)
        
    return compiler_error, ai_response

# --- Streamlit UI ---

st.title("🛠️ Multi-Language Agentic Fixer")
st.markdown("Automated bug hunting for **C++**, **Python**, and **Java**.")

# Language Selector
lang_choice = st.selectbox("Select Language", ["C++", "Python", "Java"])

col_in, col_out = st.columns(2)

with col_in:
    st.subheader("Source Input")
    code_input = st.text_area(f"Paste your {lang_choice} code here:", height=450)
    
    if st.button("Analyze & Fix", use_container_width=True):
        if code_input:
            with st.spinner(f"Running {lang_choice} compiler..."):
                error, solution = process_fix(code_input, lang_choice)
                st.session_state['error'] = error
                st.session_state['solution'] = solution
        else:
            st.warning("Please provide code to analyze.")

with col_out:
    st.subheader("AI Feedback & Download")
    if 'solution' in st.session_state:
        if st.session_state['error']:
            st.error(f"⚠️ {lang_choice} Error Detected")
            st.code(st.session_state['error'], language="bash")
            
            st.markdown("### 💡 AI Fix")
            st.markdown(st.session_state['solution'])
            
            # Extract and Provide Download
            clean_code = extract_code(st.session_state['solution'])
            ext_map = {"C++": "fixed.cpp", "Python": "fixed.py", "Java": "Fixed.java"}
            
            st.download_button(
                label="📥 Download Fixed Code",
                data=clean_code,
                file_name=ext_map.get(lang_choice, "fixed.txt"),
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.success(st.session_state['solution'])
    else:
        st.info("The fixed code and analysis will appear here.")