from datetime import datetime, timedelta
import pprint
import sqlite3
import json
import tools

conn = sqlite3.connect('personal_gpt.db')
c = conn.cursor()

# Create api key table
c.execute('''
    CREATE TABLE IF NOT EXISTS api_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL,
    model TEXT NOT NULL
)
''')

# Create conversation table
c.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_data TEXT NOT NULL,
    name TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

# Create notifcations table
c.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    scheduled_time DATETIME NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'sent')),
    FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
)
''')

conn.commit()


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
def get_conversation(id):
    c.execute("SELECT * FROM conversations WHERE id=?", (id,))
    return c.fetchone()
def get_max_id():
    # Connect to the SQLite database
    conn = sqlite3.connect('personal_gpt.db')
    # Create a cursor object
    c = conn.cursor()
    # Execute the query to find the maximum conversation id
    c.execute("SELECT MAX(id) FROM conversations")
    # Fetch the result
    max_id = c.fetchone()[0]
    # Close the connection
    conn.close()
    # Return the current conversation id
    return max_id if max_id else 0

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

#NOTIFICATION FUNCTIONS
# Schedule a reminder into the database
def set_reminder(conversation_id, content, scheduled_time = 0, offset_time = 0):
    """Function to schedule a reminder with given content at a scheduled time."""
    try:
        if offset_time:
            scheduled_time = (datetime.now() + timedelta(minutes=offset_time)).strftime("%Y-%m-%d %H:%M:%S")
        
        with sqlite3.connect('personal_gpt.db') as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO notifications (conversation_id, content, scheduled_time, status)
                VALUES (?, ?, ?, 'pending')
            """, (conversation_id, content, scheduled_time))
            conn.commit()
        return "Reminder scheduled successfully."
    except Exception as e:
        return f"Failed to schedule reminder with error: {e}"

# Function to get pending notifications
def get_pending_notifications(current_time):
    with sqlite3.connect('personal_gpt.db') as conn:
        c = conn.cursor()
        c.execute("SELECT id, content FROM notifications WHERE scheduled_time <= ? AND status = 'pending'", (current_time,))
        return c.fetchall()
    
# Function to mark a notification as sent
def mark_notification_as_sent(notification_id):
    with sqlite3.connect('personal_gpt.db') as conn:
        c = conn.cursor()
        c.execute("UPDATE notifications SET status = 'sent' WHERE id = ?", (notification_id,))
        conn.commit()

from plyer import notification

def send_notification(title, message):
    # Show the notification
    notification.notify(
        title=title,
        message=message,
        app_name='Assistant',
        timeout=20,  # Notification stays
    )

def send_ready_notifications():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pending_notifications = get_pending_notifications(current_time)
    for notification_id, content in pending_notifications:
        send_notification('Reminder', content)
        mark_notification_as_sent(notification_id)
    return len(pending_notifications)

send_ready_notifications()
