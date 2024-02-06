from datetime import datetime
import sqlite3
import json
import tools

conn = sqlite3.connect('personal_gpt.db')
c = conn.cursor()

# Create table
c.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_data TEXT NOT NULL,
    name TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

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
    c.execute('SELECT id, timestamp, conversation_data, name FROM conversations ORDER BY timestamp DESC')
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

        print("Enter the ID of the conversation you'd like to continue or type 'cancel':")
        user_input = input("> ").strip().lower()
        if user_input == 'cancel':
            break
        try:
            convo_id = int(user_input)
            # Check if the ID is in the conversations
            if any(convo_id == convo[0] for convo in conversations):
                # Fetch and display the selected conversation
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
                        conn.close()
                        return conversation_data
                    else:
                        continue
                break
            else:
                print("Invalid ID. Please try again or type 'cancel'.")
        except ValueError:
            print("Please enter a valid ID or 'cancel'.")
    
    conn.close()
    return None
