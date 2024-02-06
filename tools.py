from termcolor import colored


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
