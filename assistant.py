import os
import openai
from openai import OpenAI
import json
import requests
from tenacity import retry, wait_random_exponential, stop_after_attempt
from termcolor import colored
import g4f
import assistant_db
import tools
from datetime import datetime

client = OpenAI()
GPT_MODEL = "gpt-4-0125-preview"

openai.api_key =  ""
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
    file_path = "Conversations/" + current_date + "_" + file_name  + ".txt"
    #file_path = "/Users/socce/Desktop/Personal GPT/Conversations/" + file_name + "_" + current_date + ".txt"
    with open(file_path, 'w') as f:
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



def assistant_loop(messages):
    print("AI ASSISTANT AT YOUR SERVICE.")
    print("'continue' to load a previous conversation.")
    print("'system' to change the AI's system message.")
    print("'file' to interact with a txt file.")
    print("'exit' to end the conversation (auto-saves to database).")
    print("'save' to save the conversation to .txt file.")

    while True:
        user_input = input("> ")
        if(user_input == "continue"):
            old_messages = assistant_db.continue_convo()
            if old_messages:
                messages = old_messages
                print("\n\n------------------------------Conversation loaded.\n\n")
            continue
        if(user_input == "exit"):
            assistant_db.add_entry(messages, name_convo(messages))
            break
        if(user_input == "save"):
            assistant_db.add_entry(messages, name_convo(messages))
            save_to_file(messages)
            break
        if(user_input =="system"):
            messages = change_system_message(messages)
            user_input = input("...")
        if(user_input == "file"):
            file_interaction(messages)
            continue
        messages.append({"role": "user", "content": user_input})
        chat_response = chat_completion_request(
            messages=messages
        )

        assistant_message = chat_response.json()["choices"][0]["message"]
        messages.append(assistant_message)
        
        #assistant_db.add_entry(user_input, assistant_message["content"])
        tools.pretty_print_message(assistant_message)

        #print(f"\n\n-----------------------------------\n\n{messages}\n\n-----------------------------------\n\n")


def read_file(messages, file_path):
    if not os.path.exists(file_path):
      print("File does not exist.")
      return -1
    with open(file_path, 'r') as file:
        messages.append({"role": "user", "content": "<START_FILE>" + file.read() + "<END_FILE>"})
  
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
    tools.pretty_print_message(assistant_message)

def name_convo(messages):
    if(messages[-1]["role"] == "system"):
        return None
    messages.append({"role": "system", "content": "return a short file  name for the conversation (no quotes or file extensions): "})
    chat_response = chat_completion_request(
        messages=messages
    )
    
    file_name = chat_response.json()["choices"][0]["message"]["content"]
    del messages[-1]
    return file_name

def save_to_file(messages):
    file_name = name_convo(messages)

    conversation_to_file(messages, file_name)

def change_system_message(messages):
   new_msg = input("Enter new system message: ")
   messages = [
    {"role": "system", "content": new_msg},
   ]
   return messages







sys_msg = "You are a smart and creative assistant for software developers. Your mission is to help users with \
    their coding projects, from brainstorming ideas, to writing and debugging code, to deploying and testing \
    applications. You can also generate original and innovative content, such as poems, stories, songs, or \
    jokes, on demand. \
    You can communicate in multiple languages, and you can adapt to the user’s preferences and needs. Also, you \
    have a classic nerd sense of humor (as in Hitchhiker's Guide to the Galaxy, not The Big Bang Theory) and no \
    dark humor is off the table."
messages=[
    {"role": "system", "content": sys_msg},
  ]

assistant_loop(messages)