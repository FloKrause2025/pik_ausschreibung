import openai

# Step 1: Add your OpenAI API key here
openai.api_key = "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"  # Replace this with your actual key

# Step 2: Ask the user for input
user_input = input("Add your E-Mail:")
tone = input("In which tone you want to have the email replied to?")

# Step 3: Send it to ChatGPT and get a reply
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "user", "content": user_input}
    ]
)

# Step 4: Print the reply
reply = response["choices"][0]["message"]["content"]
print("\nChatGPT says:\n" + reply)
