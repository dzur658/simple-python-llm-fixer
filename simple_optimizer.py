import ollama
import subprocess
import sys
import os

# --- Configuration ---
TARGET_SCRIPT = "target_script.py"
MODEL_NAME = "llama3" 
MAX_ITERATIONS = 1000

# Add system prompt
SYS_PROMPT = """You are an extremely knowledgeable Senior Developer who specializes in debugging and fixing Python code. 
                Your sole task is to ensure the Python script performs its intended function avoiding any logical, syntax, or runtime errors.
                **DO NOT** under any circumstances completely rewrite the script or change its fundamental purpose.
            """

# Prompt, add any specific details about your current script to this generic prompt.
PROMPT = """
Here is a Python script that has a bug. Your task is to fix it.
Only output the raw, complete Python code. Do not add any explanation,
markdown backticks, or other text.
--- SCRIPT ---
"""
# --- End Configuration ---

def clean_llm_output(raw_text):
    """
    Cleans the LLM's output by removing markdown backticks
    and other common conversational padding.
    """
    # find ```python index
    start_index = raw_text.find("```python")

    # find end index
    end_index = raw_text.find("```")

    # Remove markdown code blocks
    if start_index != -1 and end_index != -1 and end_index > start_index:
        raw_text = raw_text[start_index + len("```python"):end_index]
        print("✅  LLM  🤖 responded with valid markdown, attempting new solution...")
    else:
        print("⚠️  LLM  🤖 responded with the following invalid markdown, response will attempt to be executed...")
        print("-"*80)
        print(raw_text)
        print("-"*80)

    return raw_text.strip()

def run_script(temp_script):
    """
    Runs the target script and captures its stdout and stderr.
    Returns (True, stdout) on success, or (False, stderr) on failure.
    """
    try:
        # Use sys.executable to ensure we use the same Python interpreter
        result = subprocess.run(
            [sys.executable, temp_script],
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=10  # Add a timeout for safety
        )
        
        # Traceback heading indicates an error
        if "Traceback (most recent call last)" in result.stderr:
            return (False, result.stderr)
        
        # Success if no traceback heading is detected
        return (True, result.stdout)
        
    except Exception as e:
        # This catches errors in the subprocess call itself
        return (False, f"Subprocess execution failed: {e}")

# --- Main Loop ---

# 1. Read the initial buggy code
if __name__ == "__main__":

    # Create safe temporary script to not overwrite original during testing
    temp_script = f"{TARGET_SCRIPT}_{MODEL_NAME}_fix.py"

    try:
        with open(TARGET_SCRIPT, 'r') as f:
            current_code = f.read()
    except FileNotFoundError:
        print(f"Error: Target script '{TARGET_SCRIPT}' not found.")
        sys.exit(1)

    last_error = ""

    for i in range(MAX_ITERATIONS):
        print(f"\n--- Iteration {i+1}/{MAX_ITERATIONS} ---")
        
        # 2. Prepare the prompt for the LLM
        if not last_error:
            # First iteration prompt
            prompt = PROMPT + "\n\n" + current_code
            print("Initial prompt being sent to LLM 🤖 as...")
            print("-"*80)
            print(prompt)
        else:
            # Subsequent iteration prompt
            prompt = (
                f"The last attempt to run the script failed with this error:\n\n"
                f"--- TRACEBACK ---\n{last_error}\n\n"
                f"Here is the complete code that caused the error:\n\n"
                f"--- SCRIPT ---\n{current_code}\n\n"
                f"Fix this code. Only output the raw, complete Python code. "
                f"Do not add any explanation, markdown backticks, or other text."
            )

        # 3. Call the Ollama API
        print("📞 Calling Ollama...")
        try:
            response = ollama.chat(
                model=MODEL_NAME,
                messages=[
                    {'role': 'system', 'content': SYS_PROMPT},
                    {'role': 'user', 'content': prompt}
                ]
            )
            
            llm_response_text = response.message.content
            current_code = clean_llm_output(llm_response_text)

            # 4. Overwrite the target script with the new code
            with open(temp_script, 'w') as f:
                f.write(current_code)
            print(f"LLM provided new code. Overwriting {temp_script} with new attempt...")

        except Exception as e:
            print(f"Error calling Ollama API: {e}")
            print("Stopping loop.")
            break
            
        # 5. Run the new script and check for errors
        print(f"Running new version of {temp_script}...")
        success, output = run_script(temp_script=temp_script)
        
        if success:
            print("\n🎉 Success! Script ran without errors.")
            print("\n--- Final Script Output ---")
            print(output)
            break
        else:
            # 6. If it failed, store the error for the next loop
            print("Script failed. Capturing traceback...")
            last_error = output
            print("\n--- Captured Error ---")
            print("-"*80)
            print(last_error)
            print("-"*80)

    else:
        # This 'else' block runs if the 'for' loop completes without 'break'
        print(f"\n {MODEL_NAME} failed to fix the script after {MAX_ITERATIONS} iterations  😔.")