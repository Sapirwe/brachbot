import openai
import tokens

# Set your OpenAI API key
openai.api_key = tokens.API_gpt_token

# Function to make a simple API call to GPT
def get_gpt_response(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Updated to use gpt-3.5-turbo
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"An error occurred: {e}"

# Example usage
prompt = "Tell me a joke about programming."
output = get_gpt_response(prompt)
print(output)