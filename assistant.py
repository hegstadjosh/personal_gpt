import inspect
import os
import openai
from openai import OpenAI
import requests
from tenacity import retry, wait_random_exponential, stop_after_attempt
from termcolor import colored
import assistant_db
from datetime import datetime
import fitz
import json 
import pprint 

client = OpenAI()
openai.api_key =  (assistant_db.check_api_key())
GPT_MODEL = assistant_db.get_model()

func_dict = {
    "set_reminder": assistant_db.set_reminder
}

assistant_tools = [{
    "type": "function",
    "function": {
        "name": "set_reminder",
        "description": "Schedule a reminder for the user. Only call when you are certain of the reminder details.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The message of the reminder."
                },
                "scheduled_time": {
                    "type": "string",
                    "description": "The reminder time (YYYY-MM-DD HH:MI:SS)."
                }, 
                "offset_time": {
                    "type": "integer",
                    "description": "The number of minutes from now to schedule the reminder."
                }
            },
            "required": ["content"]
        }
    }
}]

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


#chat_completion_request taken from https://cookbook.openai.com/examples/how_to_call_functions_with_chat_models#how-to-call-functions-with-model-generated-arguments
@retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
def chat_completion_request(messages, tools=None, tool_choice=None, model=GPT_MODEL):
    #
    # This function sends a chat completion request to the OpenAI API.

    # Parameters:
    # messages (list): A list of message objects. Each object should have a 'role' and 'content'.
    # tools (list, optional): A list of tools to be used. Defaults to None.
    # tool_choice (str, optional): The chosen tool. Defaults to None.
    # model (str, optional): The model to be used for the chat completion. Defaults to GPT_MODEL.

    # Returns:
    # dict: The response from the OpenAI API.
    # 

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + openai.api_key,
    }
    json_data = {"model": model, "messages": messages}
    if tools is not None:
        json_data.update({"tools": tools})
    if tool_choice is not None:
        json_data.update({"tool_choice": tool_choice})
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=json_data,
        )
        return response
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        return e
    
def conversation_to_file(messages, file_name):
    current_date = datetime.now().strftime("%m_%d_%y")
    file_path = current_date + "_" + file_name  + ".txt"
    #file_path = "/Users/socce/Desktop/Personal GPT/Conversations/" + file_name + "_" + current_date + ".txt"
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for message in messages:
                if message["role"] == "system":
                    f.write(f"\nsystem: {message['content']}\n")
                    f.write(f"\n-----------------------------------------------------\n")
                elif message["role"] == "user":
                    f.write(f"user: {message['content']}\n")
                elif message["role"] == "assistant" and message.get("function_call"):
                    f.write(f"assistant: {message['function_call']}\n")
                elif message["role"] == "assistant" and not message.get("function_call"):
                    f.write(f"assistant: {message['content']}\n\n")
                elif message["role"] == "tool":
                    f.write(f"function ({message['name']}): {message['content']}\n")
            print(f"File has been written to: {os.path.abspath(file_path)}")
    except IOError as e:
        print(f"An IOError occurred: {e}")

def assistant_loop(messages):
    print("AI ASSISTANT AT YOUR SERVICE.")
    print("'continue' to load a previous conversation.")
    print("'system' to change the AI's system message.")
    print("'model' to change the AI's model.")
    print("'key' to change the API key.")
    print("'file' to interact with a txt file.")
    print("'exit' to end the conversation (auto-saves to database).")
    print("'save' to save the conversation to .txt file.")
    print("'single' to query a separate AI (won't be stored).")

    convo_id = assistant_db.get_max_id() + 1

    while True:
        user_input = input("> ")
        if(user_input == "continue"):
            old_messages = assistant_db.continue_convo()
            if old_messages:
                messages = old_messages
                print("\n\n------------------------------Conversation loaded.\n\n")
            continue
        if(user_input == "model"):
            global GPT_MODEL 
            print("Current model: " + GPT_MODEL)
            GPT_MODEL = assistant_db.change_model()
            continue
        if(user_input == "key"):
            openai.api_key = assistant_db.change_api_key()
            continue
        if(user_input == "system"):
            messages = change_system_message(messages)
            user_input = input("> ")
        if(user_input == "file"):
            file_interaction(messages)
            continue
        if(user_input == "exit"):
            assistant_db.add_entry(messages, name_convo(messages))
            break
        if(user_input == "save"):
            assistant_db.add_entry(messages, name_convo(messages))
            save_to_file(messages)
            break
        if(user_input == "single"):
            message = input("msg > ")
            single_response(message)
            continue

        messages.append({"role": "user", "content": user_input})
        chat_response = chat_completion_request(
            messages=messages,
            tools=assistant_tools
        )
        
        assistant_message = chat_response.json()["choices"][0]["message"]

        #check if the message contains a function call, and if it does, run execute_function_call() 
        if "tool_calls" in assistant_message:
            tool_call = assistant_message["tool_calls"][0]
            function_name = tool_call["function"]["name"]
            results = execute_function_call(convo_id, function_name, tool_call)
            messages.append({"role": "function", "tool_call_id": tool_call["id"], "name": function_name, "content": results})
        else: 
            messages.append(assistant_message)
            pretty_print_message(assistant_message)

        

# def execute_function_call(convo_id, tool_call):
#     if tool_call['function']['name'] == "set_reminder":
#         arguments = json.loads(tool_call['function']['arguments'])
#         content = arguments['content']
#         scheduled_time = arguments['scheduled_time']

#         # You may want to validate or parse the scheduled_time if it's in a natural language format
#         # This depends on the format the time is given

#         result = assistant_db.set_reminder(convo_id, content, scheduled_time)
#     else:
#         result = f"Error: function {tool_call['function']['name']} does not exist"
#     return result

def execute_function_call(convo_id, function_name, tool_call):
    if function_name in func_dict:
        func = func_dict[function_name]
        arguments = json.loads(tool_call['function']['arguments'])

        # Check if the number of arguments is less than or equal to the number of parameters
        sig = inspect.signature(func)
        num_params = len(sig.parameters)
        if len(arguments) <= num_params:
            result = func(convo_id, **arguments)
            print("running", function_name, "with", arguments)
        else:
            result = f"Error: function {function_name} received too many arguments"
    else:
        result = f"Error: function {function_name} does not exist"

    return result

def read_file(messages, file_path):
    file_path = file_path.replace("\\", "/")
    file_path = file_path.replace('"', "")
    if not os.path.exists(file_path):
      print("File does not exist.")
      return -1
    
    if file_path.endswith(".pdf"):
        txt_output_path = file_path.replace(".pdf", ".txt")
        parse_pdf_to_txt(file_path, txt_output_path)
        try:
            with open(txt_output_path, 'r', encoding='utf-8') as file:
                messages.append({"role": "user", "content": "<START_FILE>" + file.read() + "<END_FILE>"})
        except IOError as e:
            print(f"An IOError occurred: {e}")  
    else: 
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                messages.append({"role": "user", "content": "<START_FILE>" + file.read() + "<END_FILE>"})
        except IOError as e:
            print(f"An IOError occurred: {e}")

def file_interaction(messages):
    file_name = input("File path: ")
    instructions = input("Instructions: ")
    
    messages.append({"role": "user", "content": instructions})
    if(read_file(messages, file_name) == -1):
      return
    chat_response = chat_completion_request(
        messages=messages
    )
  
    assistant_message = chat_response.json()["choices"][0]["message"]
    messages.append(assistant_message)
    pretty_print_message(assistant_message)

def name_convo(messages):
    if(messages[-1]["role"] == "system"):
        return None
    messages.append({"role": "system", "content": "return a short file name for the conversation (ONLY THE NAME, no quotes or file extensions): "})
    chat_response = chat_completion_request(
        messages=messages
    )
    
    file_name = chat_response.json()["choices"][0]["message"]["content"]
    del messages[-1]
    return file_name

def parse_pdf_to_txt(pdf_file_path, txt_output_path):
    # Open the PDF file
    pdf_document = fitz.open(pdf_file_path)

    text_content = ""

    # Iterate through each page in the PDF document
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        text_content += page.get_text()

    # Write the extracted text content to a .txt file
    try:
        with open(txt_output_path, 'w', encoding='utf-8') as txt_file:
            txt_file.write(text_content)
    except IOError as e:
        print(f"An IOError occurred: {e}")

    pdf_document.close()

def save_to_file(messages):
    file_name = name_convo(messages)

    conversation_to_file(messages, file_name)

def change_system_message(messages):
   new_msg = input("Enter new system message: ")
   messages = [
    {"role": "system", "content": new_msg},
   ]
   return messages

def single_response(message):
    messages=[
    {"role": "user", "content": message},
    ]
    chat_response = chat_completion_request(
        messages=messages,
    )
    assistant_message = chat_response.json()["choices"][0]["message"]
    pretty_print_message(assistant_message)
    
def array_io(messages, input_array):
    responses = []
    for user_input in input_array:
        print(user_input)
        messages.append({"role": "user", "content": user_input})
        chat_response = chat_completion_request(
            messages=messages,
            tools=assistant_tools
        )

        assistant_message = chat_response.json()["choices"][0]["message"]
        #messages.append(assistant_message)
        messages.pop() 
        responses.append(assistant_message["content"])
    return responses

#top level code to start the assistant
sys_msg = "You are a smart and creative assistant for software developers. \
    You can also generate original and innovative content, such as poems, \
    stories, songs, or jokes on demand. \
    you adapt to the user’s preferences and needs."
messages=[
    {"role": "system", "content": sys_msg},
  ]

assistant_loop(messages)

