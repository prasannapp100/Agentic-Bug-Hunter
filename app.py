import streamlit as st
import os
import subprocess
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

# 1. Setup & Config
load_dotenv()
HF_TOKEN = st.secrets.get("HF_TOKEN") or os.getenv("HF_TOKEN")
MODEL_ID = "Qwen/Qwen2.5-Coder-32B-Instruct"

st.set_page_config(page_title="Multi-Lang Auto-Fixer", page_icon="🛠️", layout="wide")

if not HF_TOKEN:
    st.error("HF_TOKEN not found. Please check your Secrets or .env file.")
    st.stop()

client = InferenceClient(token=HF_TOKEN)

# --- Logic Core ---
def run_syntax_check(file_path, language):
    """Runs the appropriate syntax check based on language."""
    if language == "C++":
        return subprocess.run(["g++", "-fsyntax-only", file_path], capture_output=True, text=True)
    elif language == "Python":
        # -m py_compile checks for syntax errors without executing the code
        return subprocess.run(["python3", "-m", "py_compile", file_path], capture_output=True, text=True)
    elif language == "Java":
        # javac compiles the code; we use a temp directory to avoid cluttering
        return subprocess.run(["javac", file_path], capture_output=True, text=True)
    return None

def process_fix(code, language):
    # Map languages to file extensions
    ext_map = {"C++": ".cpp", "Python": ".py", "Java": ".java"}
    temp_file = f"temp_code{ext_map[language]}"
    
    with open(temp_file, "w") as f:
        f.write(code)
    
    # Step 1: Check Syntax
    result = run_syntax_check(temp_file, language)
    
    if result.returncode == 0:
        if os.path.exists(temp_file): os.remove(temp_file)
        return None, f"✅ This {language} code is syntactically correct!"

    # Step 2: AI Fix if error exists
    error_msg = result.stderr if result.stderr else result.stdout
    messages = [
        {"role": "system", "content": f"You are a senior {language} expert."},
        {"role": "user", "content": f"The following {language} code failed check:\nERRORS:\n{error_msg}\n\nCODE:\n{code}\n\nExplain and fix."}
    ]
    
    try:
        response = client.chat_completion(model=MODEL_ID, messages=messages, max_tokens=1024)
        solution = response.choices[0].message.content
    except Exception as e:
        solution = f"❌ AI Analysis failed: {str(e)}"
    
    # Cleanup
    if os.path.exists(temp_file): os.remove(temp_file)
    # Special cleanup for Java class files
    if language == "Java" and os.path.exists("temp_code.class"):
        os.remove("temp_code.class")
        
    return error_msg, solution

# --- Streamlit UI ---
st.title("🛠️ Multi-Language Agentic Fixer")

# Language Selection
lang = st.selectbox("Select Programming Language:", ["C++", "Python", "Java"])

col_in, col_out = st.columns(2)

with col_in:
    code_input = st.text_area(f"Enter {lang} code:", height=400)
    if st.button("Check & Fix"):
        if code_input:
            with st.spinner(f"Testing {lang} syntax..."):
                err, sol = process_fix(code_input, lang)
                st.session_state['err'], st.session_state['sol'] = err, sol
        else:
            st.warning("Please enter code.")

with col_out:
    if 'sol' in st.session_state:
        if st.session_state['err']:
            st.error("⚠️ Syntax/Compilation Error")
            st.code(st.session_state['err'])
            st.markdown(st.session_state['sol'])
        else:
            st.success(st.session_state['sol'])