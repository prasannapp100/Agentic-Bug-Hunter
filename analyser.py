import subprocess
import xml.etree.ElementTree as ET
import os

def get_code_context(file_path, line_number, window=3):
    """Grabs the buggy line plus a few lines above and below for context."""
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            # Convert 1-based line number to 0-based index
            idx = int(line_number) - 1
            
            # Define range (e.g., 3 lines above and 3 lines below)
            start = max(0, idx - window)
            end = min(len(lines), idx + window + 1)
            
            context_lines = lines[start:end]
            # Add a marker to the actual buggy line so the AI sees it clearly
            context_lines[idx - start] = ">>> " + context_lines[idx - start]
            
            return "".join(context_lines)
    except Exception as e:
        return f"Could not read code: {e}"

def run_analysis(file_path):
    print(f"--- Analyzing {file_path} ---")
    # Using 'cppcheck' now that it's in your PATH
    cmd = ["cppcheck", "--xml", "--enable=all", file_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    try:
        root = ET.fromstring(result.stderr)
        results = []
        
        for error in root.findall(".//error"):
            line = error.find("location").get("line") if error.find("location") is not None else None
            
            if line:
                bug_entry = {
                    "line": line,
                    "message": error.get("msg"),
                    "severity": error.get("severity"),
                    "code_snippet": get_code_context(file_path, line)
                }
                results.append(bug_entry)
        return results
    except Exception as e:
        return []

if __name__ == "__main__":
    # Create a test.cpp in the same folder first!
    bugs = run_analysis("test.cpp")
    
    for b in bugs:
        print(f"\nBUG FOUND ON LINE {b['line']}: {b['message']}")
        print("CONTEXT:")
        print(b['code_snippet'])
        print("-" * 30)