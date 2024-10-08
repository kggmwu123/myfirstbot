import re
import telebot
from telebot import types
from dotenv import load_dotenv
import os
import logging
from flask import Flask
from threading import Thread

# Load environment variables from .env file
load_dotenv()

# Load Telegram token and group ID from environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GROUP_ID = os.getenv('GROUP_ID')

# Check if the token and group ID are loaded
if not TELEGRAM_TOKEN or not GROUP_ID:
    raise ValueError("Telegram token or group ID is not defined in the environment variables.")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Group chat ID where data will be sent
group_id = GROUP_ID

# In-memory storage for user data
user_data = {}
FIRST_NAME, LAST_NAME, EMAIL, COLLEGE, DEPARTMENT = range(5)

# Regex for validation
email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
name_regex = r'^[a-zA-Z]+$'

# List of colleges and departments
colleges = {
    "College of Engineering": ["Civil Engineering", "Electrical Engineering", "Mechanical Engineering"],
    "College of Business and Economics": ["Accounting", "Marketing", "Finance"],
    "College of Social Science": ["History", "Philosophy", "Civic"],
    "College of Computing": ["Information Science", "Computer Science", "Information System", "Information Technology"],
    "College of Behavioral Science": ["Psychology", "EDPM"],
    "College of Health Science": ["Nursing", "Pharmacy", "Midwifery"],
    "College of Natural and Computational Science": ["Biology", "Chemistry", "Math"]
}

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to check if the user is already registered
def is_user_registered(first_name, last_name):
    for data in user_data.values():
        if data.get('first_name') == first_name and data.get('last_name') == last_name:
            return True
    return False

# Function to handle the /start command
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_data[chat_id] = {}
    welcome_text = (
        "Welcome to the Staff Registration Bot!\n\n"
        "This bot will guide you through the process of registering your details.\n"
        "You will be asked to provide the following information:\n"
        "1. First Name\n"
        "2. Last Name\n"
        "3. Email\n"
        "4. College\n"
        "5. Department\n\n"
        "Available commands:\n"
        "/start - Begin the registration process\n"
        "/edit - Edit your registration details\n"
        "/cancel - Cancel the current registration\n"
        "/help - Display this help message\n\n"
        "To begin, please enter your first name:"
    )
    bot.send_message(chat_id, welcome_text)
    bot.register_next_step_handler(message, get_first_name)

def get_first_name(message):
    chat_id = message.chat.id
    first_name = message.text.strip()
    if re.match(name_regex, first_name):
        user_data[chat_id]['first_name'] = first_name
        bot.send_message(chat_id, "Please enter your last name:")
        bot.register_next_step_handler(message, get_last_name)
    else:
        bot.send_message(chat_id, "Invalid first name. Please enter a valid first name (only letters):")
        bot.register_next_step_handler(message, get_first_name)

def get_last_name(message):
    chat_id = message.chat.id
    last_name = message.text.strip()
    if re.match(name_regex, last_name):
        user_data[chat_id]['last_name'] = last_name
        bot.send_message(chat_id, "Please enter your email:")
        bot.register_next_step_handler(message, get_email)
    else:
        bot.send_message(chat_id, "Invalid last name. Please enter a valid last name (only letters):")
        bot.register_next_step_handler(message, get_last_name)

def get_email(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        bot.send_message(chat_id, "Your registration session has expired. Please restart the registration process using /start.")
        return

    email = message.text.strip()
    if re.match(email_regex, email):
        first_name = user_data[chat_id].get('first_name')
        last_name = user_data[chat_id].get('last_name')

        if is_user_registered(first_name, last_name):
            bot.send_message(chat_id, "This user is already registered with the given first name and last name. Please use a different name or contact support.")
            user_data.pop(chat_id)
            return

        user_data[chat_id]['email'] = email
        bot.send_message(chat_id, "Please select your college:", reply_markup=create_college_keyboard())
    else:
        bot.send_message(chat_id, "Invalid email address. Please enter a valid email address:")
        bot.register_next_step_handler(message, get_email)

def create_college_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    for college in colleges.keys():
        keyboard.add(types.InlineKeyboardButton(text=college, callback_data=f"college_{college}"))
    return keyboard

def create_department_keyboard(college):
    keyboard = types.InlineKeyboardMarkup()
    for department in colleges[college]:
        keyboard.add(types.InlineKeyboardButton(text=department, callback_data=f"department_{department}"))
    return keyboard

@bot.callback_query_handler(func=lambda call: call.data.startswith('college_'))
def handle_college_selection(call):
    chat_id = call.message.chat.id
    college = call.data.split('college_')[1]
    user_data[chat_id]['college'] = college
    bot.send_message(chat_id, "Please select your department:", reply_markup=create_department_keyboard(college))

@bot.callback_query_handler(func=lambda call: call.data.startswith('department_'))
def handle_department_selection(call):
    chat_id = call.message.chat.id
    department = call.data.split('department_')[1]
    user_data[chat_id]['department'] = department

    # Confirm all data before sending
    first_name = user_data[chat_id]['first_name']
    last_name = user_data[chat_id]['last_name']
    email = user_data[chat_id]['email']
    college = user_data[chat_id]['college']
    department = user_data[chat_id]['department']

    confirmation_text = (
        f"Please confirm your details:\n\n"
        f"First Name: {first_name}\n"
        f"Last Name: {last_name}\n"
        f"Email: {email}\n"
        f"College: {college}\n"
        f"Department: {department}\n"
    )

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Confirm", callback_data="confirm_yes"))
    keyboard.add(types.InlineKeyboardButton(text="Edit", callback_data="confirm_no"))

    bot.send_message(chat_id, confirmation_text, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data in ["confirm_yes", "confirm_no"])
def handle_confirmation(call):
    chat_id = call.message.chat.id
    if call.data == "confirm_yes":
        # Send data to group
        first_name = user_data[chat_id]['first_name']
        last_name = user_data[chat_id]['last_name']
        email = user_data[chat_id]['email']
        college = user_data[chat_id]['college']
        department = user_data[chat_id]['department']

        message_text = (
            f"New staff member registered:\n\n"
            f"First Name: {first_name}\n"
            f"Last Name: {last_name}\n"
            f"Email: {email}\n"
            f"College: {college}\n"
            f"Department: {department}"
        )

        bot.send_message(group_id, message_text)
        bot.send_message(chat_id, "Thank you! Your details have been recorded.")
        user_data.pop(chat_id)
    else:
        bot.send_message(chat_id, "You can now edit your details using /edit.")

# Function to handle /edit command
@bot.message_handler(commands=['edit'])
def edit(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        bot.send_message(chat_id, "You need to register first using the /start command.")
        return

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Edit First Name", "Edit Last Name", "Edit Email", "Edit College", "Edit Department", "Cancel")
    bot.send_message(chat_id, "What would you like to edit?", reply_markup=keyboard)

@bot.message_handler(
    func=lambda message: message.text in ["Edit First Name", "Edit Last Name", "Edit Email", "Edit College",
                                          "Edit Department", "Cancel"])
def handle_edit_choice(message):
    chat_id = message.chat.id
    choice = message.text

    if choice == 'Edit First Name':
        bot.send_message(chat_id, "Please enter your new first name:")
        bot.register_next_step_handler(message, edit_first_name)
    elif choice == 'Edit Last Name':
        bot.send_message(chat_id, "Please enter your new last name:")
        bot.register_next_step_handler(message, edit_last_name)
    elif choice == 'Edit Email':
        bot.send_message(chat_id, "Please enter your new email:")
        bot.register_next_step_handler(message, edit_email)
    elif choice == 'Edit College':
        bot.send_message(chat_id, "Please select your new college:", reply_markup=create_college_keyboard())
    elif choice == 'Edit Department':
        if 'college' not in user_data[chat_id]:
            bot.send_message(chat_id, "Please select your college first:")
            bot.register_next_step_handler(message, edit_college)
        else:
            college = user_data[chat_id]['college']
            bot.send_message(chat_id, "Please select your new department:", reply_markup=create_department_keyboard(college))
    elif choice == 'Cancel':
        bot.send_message(chat_id, "Your editing process has been canceled.")
        user_data.pop(chat_id, None)

def edit_first_name(message):
    chat_id = message.chat.id
    first_name = message.text.strip()
    if re.match(name_regex, first_name):
        user_data[chat_id]['first_name'] = first_name
        bot.send_message(chat_id, "Your first name has been updated.")
    else:
        bot.send_message(chat_id, "Invalid first name. Please enter a valid first name (only letters):")
        bot.register_next_step_handler(message, edit_first_name)

def edit_last_name(message):
    chat_id = message.chat.id
    last_name = message.text.strip()
    if re.match(name_regex, last_name):
        user_data[chat_id]['last_name'] = last_name
        bot.send_message(chat_id, "Your last name has been updated.")
    else:
        bot.send_message(chat_id, "Invalid last name. Please enter a valid last name (only letters):")
        bot.register_next_step_handler(message, edit_last_name)

def edit_email(message):
    chat_id = message.chat.id
    email = message.text.strip()
    if re.match(email_regex, email):
        user_data[chat_id]['email'] = email
        bot.send_message(chat_id, "Your email has been updated.")
    else:
        bot.send_message(chat_id, "Invalid email address. Please enter a valid email address:")
        bot.register_next_step_handler(message, edit_email)

def edit_college(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Please select your new college:", reply_markup=create_college_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith('college_'))
def edit_college_selection(call):
    chat_id = call.message.chat.id
    college = call.data.split('college_')[1]
    user_data[chat_id]['college'] = college
    bot.send_message(chat_id, "Please select your new department:", reply_markup=create_department_keyboard(college))

def edit_department(message):
    chat_id = message.chat.id
    college = user_data[chat_id].get('college')
    if college:
        bot.send_message(chat_id, "Please select your new department:", reply_markup=create_department_keyboard(college))
    else:
        bot.send_message(chat_id, "You need to select a college first. Use /edit to select a college.")

# Function to handle /cancel command
@bot.message_handler(commands=['cancel'])
def cancel(message):
    chat_id = message.chat.id
    if chat_id in user_data:
        user_data.pop(chat_id)
        bot.send_message(chat_id, "Your registration process has been canceled.")
    else:
        bot.send_message(chat_id, "You don't have an ongoing registration process.")

# Function to handle /help command
@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = (
        "Available commands:\n"
        "/start - Begin the registration process\n"
        "/edit - Edit your registration details\n"
        "/cancel - Cancel the current registration\n"
        "/help - Display this help message\n"
        "To begin, please use /start to register."
    )
    bot.send_message(message.chat.id, help_text)

# Flask application to keep the bot running on PythonAnywhere
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running!"

def run_flask_app():
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    # Start the Flask app in a separate thread
    thread = Thread(target=run_flask_app)
    thread.start()
    
    # Start polling for new messages
    bot.polling(none_stop=True)
