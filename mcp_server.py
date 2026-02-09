import os
import subprocess
from dotenv import load_dotenv
from fastmcp import FastMCP
from google import genai

# 1. Initialize the MCP Server
mcp = FastMCP("CppFixer")

# 2. Initialize the Gemini Client GLOBALLY
# Make sure your API key is set in your environment variables or .env file
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file.")

client = genai.Client(api_key=API_KEY)

@mcp.tool()
def auto_fix_compilation_errors(file_path: str):
    """
    Automated Agentic Tool:
    1. Runs the compiler on the file.
    2. If it fails, automatically reads the source code.
    3. Calls Gemini to explain and fix the error based on the actual file content.
    """
    # Step 1: Run the compiler
    result = subprocess.run(["g++", "-fsyntax-only", file_path], capture_output=True, text=True)
    
    if result.returncode == 0:
        return f"✅ {file_path} compiled successfully. No action needed."

    # Step 2: Automation - Read the file content internally
    try:
        with open(file_path, "r") as f:
            code_context = f.read()
    except Exception as e:
        return f"❌ Error reading file {file_path}: {str(e)}"

    # Step 3: Call Gemini with the captured context
    compiler_error = result.stderr
    prompt = f"""
    The C++ file '{file_path}' failed to compile with this error:
    {compiler_error}

    FULL SOURCE CODE:
    {code_context}

    Analyze the error, explain it simply, and provide the full corrected code.
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt
        )
        return f"🔍 BUG DETECTED:\n{compiler_error}\n\n💡 AI EXPLANATION & FIX:\n{response.text}"
    except Exception as e:
        return f"❌ AI Analysis failed: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="stdio")