import os
import subprocess
from dotenv import load_dotenv
from fastmcp import FastMCP
from huggingface_hub import InferenceClient
    
# 1. Initialize the MCP Server
mcp = FastMCP("CppFixer")

# 2. Initialize Hugging Face Client
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN is not set. Add it to your .env file.")

# Keep the model but use the 'chat_completion' interface
client = InferenceClient(token=HF_TOKEN)
MODEL_ID = "Qwen/Qwen2.5-Coder-32B-Instruct"


@mcp.tool()
def auto_fix_compilation_errors(file_path: str):
    """
    Automated Agentic Tool:
    1. Runs the compiler on the file.
    2. If it fails, reads the source code.
    3. Uses a conversational AI task to explain and fix the error.
    """
    # Step 1: Run the compiler
    result = subprocess.run(["g++", "-fsyntax-only", file_path], capture_output=True, text=True)
    
    if result.returncode == 0:
        return f"✅ {file_path} compiled successfully. No action needed."

    # Step 2: Read the file content internally
    try:
        with open(file_path, "r") as f:
            code_context = f.read()
    except Exception as e:
        return f"❌ Error reading file {file_path}: {str(e)}"

    # Step 3: Call Hugging Face via Chat Completion
    compiler_error = result.stderr
    
    messages = [
        {"role": "system", "content": "You are a senior C++ expert specializing in debugging and code repair."},
        {"role": "user", "content": f"The file '{file_path}' failed to compile with this error:\n{compiler_error}\n\nFULL SOURCE CODE:\n{code_context}\n\nPlease explain why this happened and provide the corrected code."}
    ]
    
    try:
        # Use chat_completion instead of text_generation
        response = client.chat_completion(
            model=MODEL_ID,
            messages=messages,
            max_tokens=1024,
            temperature=0.1
        )
        # Extract the content from the response object
        ai_fix = response.choices[0].message.content
        return f"🔍 BUG DETECTED:\n{compiler_error}\n\n💡 AI EXPLANATION & FIX:\n{ai_fix}"
    except Exception as e:
        return f"❌ AI Analysis failed: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="stdio")