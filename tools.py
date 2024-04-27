from termcolor import colored
#pretty_print_message derived from https://cookbook.openai.com/examples/how_to_call_functions_with_chat_models#how-to-call-functions-with-model-generated-arguments
def pretty_print_message(message):
  """
  Prints a formatted message based on the provided message object.

  Parameters:
  - message (dict): A message object .

  Returns:
  - None
  """

  role_to_color = {
    "system": "red",
    "user": "yellow",
    "assistant": "green",
    "tool": "magenta", 
  }
  if message["role"] == "system":
      print(colored(f"system: {message['content']}\n", role_to_color[message["role"]]))
  elif message["role"] == "user":
    print(colored(f"user: {message['content']}\n", role_to_color[message["role"]]))
  elif message["role"] == "assistant" and message.get("function_call"):
    print(colored(f"{message['function_call']}\n", role_to_color[message["role"]]))
  elif message["role"] == "assistant" and not message.get("function_call"):
    print(colored(f"assistant: {message['content']}\n", role_to_color[message["role"]]))
  elif message["role"] == "tool":
    print(colored(f"function ({message['name']}): {message['content']}\n", role_to_color[message["role"]]))

# def is_valid_api_key(api_key):
#     try:
#         openai.api_key = api_key
#         openai.Completion.create(engine="text-davinci-002", prompt="test", max_tokens=5)
#         return api_key
#     except openai.OpenAIError:
#         print("Invalid API key...")
#         return assistant_db.change_api_key()
