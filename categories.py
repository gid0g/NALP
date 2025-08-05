from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
import requests
import os  # Add this import
import urllib.parse
from dotenv import load_dotenv

load_dotenv()
BASE_URL = os.getenv("BASE_URL")
BASE_URL = os.getenv("BASE_URL", BASE_URL)

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ Place an Order", callback_data="Place an Order Menu"),
         InlineKeyboardButton("🛒 View Cart", callback_data="View cart")],

        [InlineKeyboardButton("👨‍🍳 Become a Waiter", callback_data="Become a Waiter"),
         InlineKeyboardButton("🆘 Customer Support", callback_data="Customer Support")],

        [InlineKeyboardButton("📜 Order History", callback_data="Order History"),
         InlineKeyboardButton("🚚 Weekend Special Delivery", callback_data="Weekend Special Delivery")],
         [InlineKeyboardButton("Checkout", callback_data="checkout")]
    ])


def place_order_keyboard():
    sections = requests.get(f"{BASE_URL}/sections").json() 
    keyboard = []
    for section in sections:
        keyboard.append([InlineKeyboardButton(section['name'], callback_data=section['name'])])
    keyboard.append([InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="Main Menu")])

    return InlineKeyboardMarkup(keyboard)


# Shopping Mall Subcategories
def shopping_mall_subcategories():
    category_name= "Shopping Mall"
    sections = requests.get(
        f"{BASE_URL}/subcategories/?category_name={urllib.parse.quote(category_name)}").json()

    keyboard = []

    for section in sections:
        keyboard.append([InlineKeyboardButton(section['name'], callback_data=section['name'])])
    keyboard.append([InlineKeyboardButton(
        "⬅️ Back to Place an Order", callback_data="Place an Order Menu")])
    return InlineKeyboardMarkup(keyboard)

    
# Food Delivery Subcategories
def food_delivery_subcategories():
    keyboard = [
        [InlineKeyboardButton("Cafe 1 Menu 🍔", callback_data="Cafe 1 Menu"),
         InlineKeyboardButton("Cafe 2 Menu 🥗", callback_data="Cafe 2 Menu")],
        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="Main Menu")]
    ]
    return InlineKeyboardMarkup(keyboard)



category_functions = {
        # Main categories
        "Main Menu": main_menu_keyboard,
        "Place an Order Menu": place_order_keyboard,
        "Food delivery": food_delivery_subcategories,
        "Shopping Mall": shopping_mall_subcategories,
        
    }

def cafe_1_delivery_fee(amount):
    """Return the delivery fee based on the total amount."""
    if amount < 1000:
        return 250
    elif amount < 2000:
        return 350
    elif amount < 3000:
        return 450
    elif amount < 4000:
        return 550
    elif amount < 5000:
        return 650
    elif amount < 6000:
        return 750
    elif amount < 7000:
        return 850
    elif amount < 8000:
        return 950
    elif amount < 9000:
        return 1000
    elif amount < 10000:
        return 1100
    elif amount < 11000:
        return 1200
    elif amount < 12000:
        return 1300
    elif amount < 13000:
        return 1400
    elif amount < 14000:
        return 1500
    elif amount < 15000:
        return 1600
    elif amount < 16000:
        return 1700
    elif amount < 17000:
        return 1800
    elif amount < 18000:
        return 1900
    elif amount < 19000:
        return 2000
    elif amount < 20000:
        return 2100
    elif amount > 20000:
        return 3000
    else:
        return None  # or some default value if the amount exceeds the range

def cafe_2_delivery_fee(amount):
    """Return the delivery fee based on the total amount."""
    if amount < 1500:
        return 350
    elif amount < 3000:
        return 500
    elif amount < 4500:
        return 600
    elif amount < 6000:
        return 700
    elif amount < 7500:
        return 800
    elif amount < 9000:
        return 900
    elif amount < 10000:
        return 1000
    elif amount < 11000:
        return 1100
    elif amount < 12000:
        return 1200
    elif amount < 13000:
        return 1300
    elif amount < 14000:
        return 1400
    elif amount < 15000:
        return 1500
    elif amount < 16000:
        return 1600
    elif amount < 17000:
        return 1700
    elif amount < 18000:
        return 1800
    elif amount < 19000:
        return 1900
    elif amount < 20000:
        return 2000
    elif amount > 20000:
        return 2500
    else:
        return None  # or some default value if the amount exceeds the range

def shopping_mall_delivery_fee(amount):
    """Return the delivery fee based on the total amount."""
    if amount < 100:
        return None  # or some default value if the amount is below the minimum
    elif amount < 3000:
        return 300
    elif amount < 5000:
        return 500
    elif amount < 10000:
        return 1000
    elif amount < 15000:
        return 1500
    elif amount < 20000:
        return 2000
    elif amount < 25000:
        return 2500
    elif amount < 30000:
        return 3000
    elif amount < 35000:
        return 3500
    elif amount < 40000:
        return 4000
    elif amount < 45000:
        return 4500
    elif amount < 50000:
        return 5000
    elif amount > 50000:
        return 5500
    else:
        return None  # or some default value if the amount exceeds the range
