from datetime import datetime
import sqlite3
import json
import tools

conn = sqlite3.connect('personal_gpt.db')
c = conn.cursor()

# Create table for API keys
c.execute('''
    CREATE TABLE IF NOT EXISTS api_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL,
    model TEXT NOT NULL
)
''')

# Create table
c.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_data TEXT NOT NULL,
    name TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

conn.commit()

# def check_model():
#     c.execute("SELECT model FROM api_values")
#     data = c.fetchone()
#     if data is None:
#         return change_model()
#     else:
#         return data[2]

def get_model():
    c.execute("SELECT model FROM api_values WHERE id = 1")
    data = c.fetchone()
    if data is not None:
        return data[0]
    else:
        print("No model found.")
        return None
    
def change_model():
    print("Enter the model you'd like to use")
    print("ex. gpt-4-0125-preview (turbo), gpt-3.5-turbo-0125	")
    model = input("> ")
    if(model.strip() == ""):
        return get_model()
    c.execute("UPDATE api_values SET model = ? WHERE id = 1", (model,))
    conn.commit()
    return model

def check_api_key():
    c.execute("SELECT * FROM api_values")
    data = c.fetchone()
    if data is None:
        return change_api_key(1)
    else:
        return data[1]

def change_api_key(x = 0): #if initializing, pass x = 1
    api_key = input("Please enter your API key: ")
    if(x == 1):
        c.execute("INSERT INTO api_values (key, model) VALUES (?, ?)", (api_key, "gpt-4-0125-preview"))
    else:
        c.execute("UPDATE api_values SET key = ? WHERE id = 1",  (api_key,))
    conn.commit()
    return api_key

# Function to add entry
def add_entry(messages, convo_name):
    if messages[-1]["role"] == "system":
        return 
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO conversations (conversation_data, name, timestamp) VALUES (?, ?, ?)", (json.dumps(messages), convo_name, timestamp))
    conn.commit()

# Function to get entries
def get_entries():
    c.execute("SELECT * FROM chats")
    return c.fetchall()

def continue_convo():
    conn = sqlite3.connect('personal_gpt.db')
    c = conn.cursor()

    # Fetch all conversations ordered by most recent first
    c.execute('SELECT id, timestamp, conversation_data, name FROM conversations ORDER BY id DESC')
    conversations = c.fetchall()

    if not conversations:
        print("No past conversations found.")
        return

    while True:
        for i, convo in enumerate(conversations):
            # Deserialize conversation data to get the name (assuming the 'system' role initiates the conversation)
            conversation_data = json.loads(convo[2])
            name = convo[3] if convo[3] else 'no name'
            #first_message = conversation_data[0]['content'] if conversation_data else 'No Content'
            print(f"{convo[0]}: {convo[3]}")

        print("Enter the ID of the conversation you'd like to continue or type 'exit':")
        user_input = input("> ").strip().lower()
        if user_input == 'exit':
            break
        try:
            convo_id = int(user_input)
            # Check if the ID is in the conversations
            if any(convo_id == convo[0] for convo in conversations):
                # Fetch and display te selected conversation
                c.execute('SELECT conversation_data FROM conversations WHERE id = ?', (convo_id,))
                selected_convo = c.fetchone()
                if selected_convo:
                    conversation_data = json.loads(selected_convo[0])
                    print("Here's the conversation you selected:")
                    for msg in conversation_data:
                        tools.pretty_print_message(msg)
                        #print(f"{msg['role'].title()}: {msg['content']}\n")
                    
                    print(f"\nLoad data into assistant? (yes/no)")
                    user_input = input("> ").strip().lower()
                    if user_input == 'yes':
                        c.execute('DELETE FROM conversations WHERE id = ?', (convo_id,))
                        conn.commit()
                        conn.close()
                        return conversation_data
                    else:
                        continue
                break
            else:
                print("Invalid ID. Please try again or type 'exit'.")
        except ValueError:
            print("Please enter a valid ID or 'exit'.")
    
    conn.close()
    return None
