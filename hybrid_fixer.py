import os
import json
import subprocess
import xml.etree.ElementTree as ET
import time
from dotenv import load_dotenv
from google import genai

# --- CONFIGURATION ---
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file.")

MODEL_NAME = "gemini-2.5-flash" 

client = genai.Client(api_key=API_KEY)

def get_code_context(file_path, line_number, window=3):
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            idx = int(line_number) - 1
            start = max(0, idx - window)
            end = min(len(lines), idx + window + 1)
            context_lines = lines[start:end]
            context_lines[idx - start] = ">>> " + context_lines[idx - start]
            return "".join(context_lines)
    except Exception:
        return "Context unavailable"

def run_static_analysis(file_path):
    print(f"--- Step 1: Running Static Analysis on {file_path} ---")
    cmd = ["cppcheck", "--xml", "--enable=all", file_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    root = ET.fromstring(result.stderr)
    bug_list = []
    for error in root.findall(".//error"):
        loc = error.find("location")
        line = loc.get("line") if loc is not None else None
        if line:
            bug_list.append({
                "line": line,
                "message": error.get("msg"),
                "context": get_code_context(file_path, line)
            })
    return bug_list

def get_combined_ai_fix(bugs):
    prompt = f"""
    Analyze these C++ bugs found by Cppcheck. 
    Return a valid JSON array of objects. Each object must have:
    "line", "issue", "explanation", and "suggested_fix".
    
    BUGS TO ANALYZE:
    {json.dumps(bugs, indent=2)}
    """
    
    # Retry logic: Try up to 3 times if we get a 429
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            return response.text
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                print(f"Rate limit hit. Retrying in 20 seconds (Attempt {attempt+1}/3)...")
                time.sleep(20)
            else:
                raise e

if __name__ == "__main__":
    target_file = "test.cpp"
    all_bugs = run_static_analysis(target_file)
    
    if all_bugs:
        print(f"Sending {len(all_bugs)} bugs to AI for analysis...")
        try:
            # 1. Get the JSON string from Gemini
            raw_json_response = get_combined_ai_fix(all_bugs)
            
            # 2. Parse and save to a file
            parsed_data = json.loads(raw_json_response)
            with open("bug_report.json", "w") as f:
                json.dump(parsed_data, f, indent=4)
            
            print("Successfully generated bug_report.json!")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("No bugs found.")