from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
import logging
import requests
import os
import urllib.parse
from dotenv import load_dotenv
import uuid
import time
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from categories import (
    main_menu_keyboard,
    place_order_keyboard,
    cafe_1_delivery_fee,
    cafe_2_delivery_fee,
    shopping_mall_delivery_fee,
    category_functions
)

# Load environment variables
load_dotenv()

# Environment variables
API_TOKEN = os.getenv("API_TOKEN")
BASE_URL = os.getenv("BASE_URL")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
REDIRECT_URL = os.getenv("REDIRECT_URL")
FLW_SECRET_KEY = os.getenv("FLW_SECRET_KEY")

# Validate required environment variables
if not API_TOKEN:
    raise ValueError("API_TOKEN environment variable is required")
if not BASE_URL:
    raise ValueError("BASE_URL environment variable is required")

print(f"Bot starting...")
print(f"Base URL: {BASE_URL}")

# Global variables
user_cart = {}
all_categories = []
all_subcategories = []
all_items = []
print(f"🔍 Using python-telegram-bot version: {telegram.__version__}")

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_QUANTITY = range(1)
HOSTEL, ROOM_NUMBER, RECIPIENT_NAME, EMAIL, DELIVERY_TIME = range(5)


async def call_all():
    """Fetch all categories, subcategories, and items from API"""
    global all_categories, all_subcategories, all_items

    try:
        # Fetch categories
        response = requests.get(f"{BASE_URL}/categories")
        if response.status_code == 200:
            categories = response.json()
            all_categories = [category['name'] for category in categories]
        else:
            all_categories = []

        # Fetch subcategories
        response = requests.get(f"{BASE_URL}/subcategories")
        if response.status_code == 200:
            subcategories = response.json()
            all_subcategories = [subcategory['name']
                                 for subcategory in subcategories]
        else:
            all_subcategories = []

        # Fetch items
        response = requests.get(f"{BASE_URL}/items")
        if response.status_code == 200:
            items = response.json()
            all_items = [item['name'] for item in items]
        else:
            all_items = []

        print("✅ Data fetched successfully")
    except Exception as e:
        logger.error(f"Error fetching data: {e}")


def number_pad_keyboard():
    """Generate number pad keyboard for quantity selection"""
    keyboard = [
        [InlineKeyboardButton("1", callback_data='1'),
         InlineKeyboardButton("2", callback_data='2'),
         InlineKeyboardButton("3", callback_data='3')],
        [InlineKeyboardButton("4", callback_data='4'),
         InlineKeyboardButton("5", callback_data='5'),
         InlineKeyboardButton("6", callback_data='6')],
        [InlineKeyboardButton("7", callback_data='7'),
         InlineKeyboardButton("8", callback_data='8'),
         InlineKeyboardButton("9", callback_data='9')],
        [InlineKeyboardButton("0", callback_data='0'),
         InlineKeyboardButton("OK", callback_data='confirm_quantity')]
    ]
    return InlineKeyboardMarkup(keyboard)


async def quantity_input_handler(update: Update, context: CallbackContext):
    """Handle quantity input from number pad"""
    query = update.callback_query
    await query.answer()

    current_quantity = context.user_data.get('quantity', "")

    if query.data.isdigit():
        current_quantity += query.data
        context.user_data['quantity'] = current_quantity
        await query.edit_message_text(
            f"Current quantity: {current_quantity}\nPlease select a quantity:",
            reply_markup=number_pad_keyboard()
        )
    elif query.data == 'confirm_quantity':
        if current_quantity.isdigit() and int(current_quantity) > 0:
            item_name = context.user_data.get('selected_item')
            quantity = int(current_quantity)
            item_price = context.user_data.get('item_price')
            branch = context.user_data.get('branch')

            if item_name and item_price is not None:
                add_to_cart(update.callback_query.from_user.id,
                            item_name, quantity, item_price, branch)
                await query.edit_message_text(f"Added {quantity} of {item_name} to your cart!")
                return ConversationHandler.END
            else:
                await query.edit_message_text("No item selected or price not available.", reply_markup=number_pad_keyboard())
        else:
            await query.edit_message_text("Please enter a valid quantity before confirming.", reply_markup=number_pad_keyboard())


async def item_selection_handler(update: Update, context: CallbackContext):
    """Handle item selection and prompt for quantity"""
    query = update.callback_query
    await query.answer()
    data = query.data

    item_name, price_str, branch = data.split('|')
    price = int(price_str.replace("₦", "").replace(",", "").strip())

    context.user_data['selected_item'] = item_name
    context.user_data['item_price'] = price
    context.user_data['branch'] = branch

    await query.edit_message_text(
        f"You selected {item_name}. How many would you like to add to your cart?",
        reply_markup=number_pad_keyboard()
    )


def add_to_cart(user_id, item_name, quantity, price, branch):
    """Add an item to the user's cart"""
    if user_id not in user_cart:
        user_cart[user_id] = []
    user_cart[user_id].append((item_name, quantity, price, branch))


def call_keyboard_sub(data):
    """Generate subcategory keyboard"""
    sections = requests.get(
        f"{BASE_URL}/subcategories/?category_name={urllib.parse.quote(data)}").json()
    keyboard = []
    for section in sections:
        keyboard.append([InlineKeyboardButton(section['name'],
                        callback_data=section['callback_data'])])
    keyboard.append([InlineKeyboardButton(
        "⬅️ Back to Place an Order", callback_data="Place an Order Menu")])
    return InlineKeyboardMarkup(keyboard)


def call_keyboard_item(data):
    """Generate item keyboard"""
    sections = requests.get(
        f"{BASE_URL}/items/?subcategory_name={urllib.parse.quote(data)}").json()
    keyboard = []
    for section in sections:
        keyboard.append([InlineKeyboardButton(section['name'],
                        callback_data=section['callback_data'])])
    keyboard.append([InlineKeyboardButton(
        "⬅️ Back to Shopping Mall", callback_data="Shopping Mall")])
    return InlineKeyboardMarkup(keyboard)


def calculate_cost(cart_contents):
    """Calculate total cost including delivery fees"""
    branch_costs = {}
    lines = cart_contents.strip().split('\n')

    for line in lines:
        if '₦' in line and 'Qty(' in line:
            item_part, quantity_price_part = line.split(':')
            branch = item_part.split('(')[-1].split(')')[0].strip()
            quantity_str = quantity_price_part.split(
                'Qty(')[-1].split(')')[0].strip()
            quantity = int(quantity_str)
            price_str = quantity_price_part.split('-')[-1].strip()
            price = int(price_str.replace('₦', '').replace(',', '').strip())

            if branch not in branch_costs:
                branch_costs[branch] = 0
            branch_costs[branch] += price * quantity

    subtotal = sum(branch_costs.values())
    delivery_fees = {}
    total_delivery_fee = 0

    for branch, branch_subtotal in branch_costs.items():
        branch_fee = get_delivery_fee(branch_subtotal, branch)
        delivery_fees[branch] = branch_fee
        total_delivery_fee += branch_fee

    total_cost = subtotal + total_delivery_fee

    return {
        "subtotal": subtotal,
        "branch_costs": branch_costs,
        "delivery_fees": delivery_fees,
        "total_delivery_fee": total_delivery_fee,
        "total_cost": total_cost
    }


def remove_from_cart(user_id, item_and_branch):
    """Remove an item from the user's cart"""
    if user_id in user_cart:
        item_name, branch = item_and_branch.split("|")
        for item in user_cart[user_id][:]:
            if item[0] == item_name and item[3] == branch:
                user_cart[user_id].remove(item)
                return True
    return False


def view_cart_contents(user_id):
    """View cart contents as formatted string"""
    if user_id not in user_cart or not user_cart[user_id]:
        return "Your cart is empty."

    cart_items = user_cart[user_id]
    formatted_items = [
        f"{item_name} ({branch}): Qty({quantity}) - ₦{price}"
        for item_name, quantity, price, branch in cart_items
    ]
    return "\n".join(formatted_items)


def view_cart_contents_with_buttons(user_id):
    """View cart contents with remove buttons"""
    if user_id in user_cart and user_cart[user_id]:
        cart_items = user_cart[user_id]
        formatted_items = [
            f"{item_name}: Qty({quantity}) - ₦{price}"
            for item_name, quantity, price, branch in cart_items
        ]
        keyboard = [
            [InlineKeyboardButton(
                f"❌ Remove {item_name}", callback_data=f"remove_{item_name}|{branch}")]
            for item_name, _, _, branch in cart_items
        ]
        keyboard.append([InlineKeyboardButton(
            "⬅️ Back to Main Menu", callback_data="Main Menu")])
        return "\n".join(formatted_items), InlineKeyboardMarkup(keyboard)

    return "Your cart is empty.", InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Main Menu",
                              callback_data="Main Menu")]
    ])


def generate_flutterwave_payment_link(user_id, order_details, amount, hostel=None, room_number=None, recipient_name=None, email=None):
    """Generate a Flutterwave payment link"""
    if not FLW_SECRET_KEY:
        logger.error("Flutterwave Secret Key is missing!")
        return None

    url = "https://api.flutterwave.com/v3/payments"
    headers = {
        "Authorization": f"Bearer {FLW_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    try:
        amount = float(amount)
        if amount <= 0:
            logger.error("Amount must be greater than zero!")
            return None
    except (ValueError, TypeError):
        logger.error(f"Invalid amount format! Value: {amount}")
        return None

    tx_ref = f"NALP_{user_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    customer_email = email if email else f"telegram_{user_id}@nalporders.com"

    payload = {
        "tx_ref": tx_ref,
        "amount": amount,
        "currency": "NGN",
        "redirect_url": REDIRECT_URL or "https://yourdomain.com/payment-success",
        "customer": {
            "email": customer_email,
            "name": recipient_name or f"Telegram User {user_id}",
        },
        "customizations": {
            "title": "NALP🚚🛍",
            "description": f"Order Payment for delivery to {hostel or 'Unknown Hostel'} Room {room_number or 'N/A'}",
        },
        "meta": {
            "telegram_user_id": str(user_id),
            "order_details": str(order_details),
            "hostel": str(hostel) if hostel else "",
            "room_number": str(room_number) if room_number else "",
            "recipient_name": str(recipient_name) if recipient_name else "",
            "telegram_deeplink": f"https://t.me/NALP_BOT?start=paid_{tx_ref}"
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        response_data = response.json()

        if response.status_code == 200 and "data" in response_data and "link" in response_data["data"]:
            payment_url = response_data["data"]["link"]
            logger.info("Payment Link Generated successfully")
            return payment_url
        else:
            error_message = response_data.get("message", "Unknown error")
            logger.error(f"Error response from Flutterwave: {error_message}")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error when contacting Flutterwave: {e}")
        return None


def get_delivery_fee(total_amount, branch):
    """Calculate delivery fee based on branch"""
    if branch == "Cafe 1":
        return cafe_1_delivery_fee(total_amount)
    elif branch == "Cafe 2":
        return cafe_2_delivery_fee(total_amount)
    elif branch == "Shopping Mall":
        return shopping_mall_delivery_fee(total_amount)
    else:
        return 0


def print_delivery_fees(delivery_fees):
    """Format delivery fees for display"""
    text = ""
    for branch, fee in delivery_fees.items():
        if branch != "total_delivery_fee":
            text += f"  {branch}: ₦{fee:,}\n"
    return text


async def button_click_handler(update: Update, context: CallbackContext):
    """Handle all button clicks"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data.strip()

    # Handle cart view
    if data == "View cart":
        cart_contents, keyboard = view_cart_contents_with_buttons(user_id)
        await query.edit_message_text(f"Your cart contains:\n{cart_contents}", reply_markup=keyboard)
        return

    # Handle checkout
    elif data == "checkout":
        cart_contents = view_cart_contents(user_id)
        if not cart_contents or cart_contents == "Your cart is empty.":
            await query.edit_message_text(
                "⚠️ Your cart is empty. Please add items to your cart before proceeding.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⬅️ Back to cart", callback_data="View cart")]])
            )
            return
        else:
            await query.edit_message_text(
                "Please provide your delivery information to proceed with checkout.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⬅️ Back to cart", callback_data="View cart")]])
            )
            return

    # Handle item removal
    elif data.startswith("remove_"):
        item_to_remove = data.split("remove_")[1]
        remove_from_cart(user_id, item_to_remove)
        cart_contents, keyboard = view_cart_contents_with_buttons(user_id)
        await query.edit_message_text(f"Your cart now contains:\n{cart_contents}", reply_markup=keyboard)

    # Handle checkout confirmation
    elif data == 'confirm_checkout':
        await confirm_checkout(update, context)
        return

    # Handle category functions
    elif data in category_functions:
        menu_function = category_functions[data]
        if data == "Main Menu":
            prompt_text = "Welcome back to the main menu!"
        elif data == "Place an Order Menu":
            prompt_text = "Choose a category:"
        elif data in ["Food delivery", "Shopping mall"]:
            prompt_text = "Choose a subcategory:"
        else:
            prompt_text = f"Choose an item from {data}:"

        try:
            await query.edit_message_text(prompt_text, reply_markup=menu_function())
        except Exception as e:
            logger.error(f"Error editing message: {e}")
        return

    # Handle categories
    elif data in all_categories:
        keyboard = call_keyboard_sub(data)
        await query.edit_message_text("Please select vendor", reply_markup=keyboard)
        return

    # Handle subcategories
    elif data in all_subcategories:
        keyboard = call_keyboard_item(data)
        await query.edit_message_text("Please select item", reply_markup=keyboard)
        return

    # Handle item selection
    elif "|₦" in data:
        try:
            await item_selection_handler(update, context)
            return
        except Exception as e:
            logger.error(f"Error in item_selection_handler: {e}")

    # Handle quantity selection
    elif data.isdigit():
        current_quantity = int(data)
        item_name = context.user_data.get('selected_item')
        item_price = context.user_data.get('item_price')
        branch = context.user_data.get('branch')

        if item_name and item_price is not None and branch is not None:
            add_to_cart(user_id, item_name,
                        current_quantity, item_price, branch)
            await query.edit_message_text(
                f"Added {current_quantity} of {item_name} to your cart!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "⬅️ Back to main menu", callback_data="Main Menu")],
                    [InlineKeyboardButton(
                        "🛒 View Cart", callback_data="View cart")],
                    [InlineKeyboardButton(
                        "Checkout", callback_data="checkout")]
                ])
            )
        else:
            await query.edit_message_text("No item selected. Please select an item first.", reply_markup=main_menu_keyboard())
        return


async def start(update: Update, context):
    """Start command handler"""
    await call_all()
    await update.message.reply_text("Welcome to the Food Bot!", reply_markup=main_menu_keyboard())

# Checkout conversation handlers


async def ask_hostel(update: Update, context):
    """Prompt the user to input their hostel"""
    await update.callback_query.message.reply_text("Please enter your hostel:")
    return HOSTEL


async def ask_room_number(update: Update, context):
    """Prompt the user to input their room number"""
    hostel = update.message.text
    context.user_data['hostel'] = hostel
    await update.message.reply_text("Please enter your room number:")
    return ROOM_NUMBER


async def ask_recipient_name(update: Update, context):
    """Prompt the user to input the recipient's name"""
    room_number = update.message.text
    context.user_data['room_number'] = room_number
    await update.message.reply_text("Please enter the name of the person the order is for:")
    return RECIPIENT_NAME


async def ask_email(update: Update, context: CallbackContext):
    """Prompt the user to input their email"""
    recipient_name = update.message.text
    context.user_data['recipient_name'] = recipient_name
    await update.message.reply_text("Almost there! Please enter your email address for order confirmation:")
    return EMAIL


async def ask_delivery_time(update: Update, context):
    """Prompt the user to select a delivery time"""
    email = update.message.text

    if '@' not in email or '.' not in email:
        await update.message.reply_text("That doesn't look like a valid email. Please enter a valid email address:")
        return EMAIL

    context.user_data['email'] = email
    keyboard = [
        [InlineKeyboardButton("4 PM - 5 PM", callback_data="4 PM - 5 PM")],
        [InlineKeyboardButton("5 PM - 6 PM", callback_data="5 PM - 6 PM")],
        [InlineKeyboardButton("6 PM - 7 PM", callback_data="6 PM - 7 PM")],
        [InlineKeyboardButton("7 PM - 8 PM", callback_data="7 PM - 8 PM")],
    ]

    await update.message.reply_text(
        "Please select your preferred delivery time:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return DELIVERY_TIME


async def handle_delivery_time(update: Update, context: CallbackContext):
    """Handle delivery time selection and show order summary"""
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_checkout":
        await confirm_checkout(update, context)
        return ConversationHandler.END
    elif query.data == "cancel_checkout":
        await query.edit_message_text(
            "Checkout cancelled. What would you like to do next?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "⬅️ Back to main menu", callback_data="Main Menu")],
                [InlineKeyboardButton(
                    "🛒 View Cart", callback_data="View cart")]
            ])
        )
        return ConversationHandler.END

    delivery_time = query.data
    context.user_data['delivery_time'] = delivery_time

    user_id = query.from_user.id
    hostel = context.user_data.get('hostel')
    room_number = context.user_data.get('room_number')
    recipient_name = context.user_data.get('recipient_name')
    cart_contents = view_cart_contents(user_id)
    result = calculate_cost(cart_contents)
    total_price = result["total_cost"]
    sub_total = result["subtotal"]
    delivery_fees = print_delivery_fees(result["delivery_fees"])

    if not cart_contents or cart_contents == "Your cart is empty.":
        await query.edit_message_text(
            "⚠️ Your cart is empty. Please add items to your cart before proceeding.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Back to cart", callback_data="View cart")]])
        )
        return ConversationHandler.END

    summary = (
        f"✅ Order Summary:\n"
        f"Hostel: {hostel}\n"
        f"Room Number: {room_number}\n"
        f"Recipient: {recipient_name}\n"
        f"Delivery Time: {delivery_time}\n"
        f"Cart Contents: {cart_contents}\n"
        f"Subtotal: ₦{sub_total:,}\n"
        f"Delivery Fees:\n{delivery_fees}\n"
        f"Total Amount: ₦{total_price:,}\n\n"
        "Please confirm to proceed with payment."
    )

    keyboard = [
        [InlineKeyboardButton("✅ Confirm checkout",
                              callback_data="confirm_checkout")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_checkout")]
    ]

    try:
        await query.edit_message_text(summary, reply_markup=InlineKeyboardMarkup(keyboard))
        return DELIVERY_TIME
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        await query.message.reply_text("⚠️ An error occurred while trying to display the summary.")
        return ConversationHandler.END


async def confirm_checkout(update: Update, context: CallbackContext):
    """Generate payment link and complete checkout"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    hostel = context.user_data.get('hostel')
    room_number = context.user_data.get('room_number')
    recipient_name = context.user_data.get('recipient_name')
    delivery_time = context.user_data.get('delivery_time')
    email = context.user_data.get('email', f"user{user_id}@example.com")

    cart_contents = view_cart_contents(user_id)
    if not cart_contents or cart_contents == "Your cart is empty.":
        await query.edit_message_text(
            "⚠️ Your cart is empty. Please add items to your cart before proceeding.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Back to cart", callback_data="View cart")]])
        )
        return

    result = calculate_cost(cart_contents)
    total_price = result["total_cost"]

    try:
        payment_link = generate_flutterwave_payment_link(
            user_id, cart_contents, total_price,
            hostel=hostel, room_number=room_number,
            recipient_name=recipient_name, email=email
        )

        if payment_link:
            await query.message.reply_text(
                f"✅ Your order has been placed!\n"
                f"Hostel: {hostel}\nRoom Number: {room_number}\nRecipient: {recipient_name}\n"
                f"Delivery Time: {delivery_time}\nCart Contents:\n{cart_contents}\n\n"
                f"Please complete your payment here: {payment_link}\n\n"
                f"Order confirmation details will be sent to: {email}"
            )
        else:
            await query.message.reply_text("⚠️ An error occurred while generating the payment link. Please try again later.")
    except Exception as e:
        logger.error(f"Error during checkout confirmation: {e}")
        await query.message.reply_text("⚠️ An error occurred while confirming your checkout. Please try again.")


def main():
    """Main function to set up and run the bot"""
    try:
        application = Application.builder().token(API_TOKEN).build()

        # Conversation handler for checkout flow
        conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(
                ask_hostel, pattern="^checkout$")],
            states={
                HOSTEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_room_number)],
                ROOM_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_recipient_name)],
                RECIPIENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)],
                EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_delivery_time)],
                DELIVERY_TIME: [CallbackQueryHandler(handle_delivery_time)],
            },
            fallbacks=[],
            per_message=False,
            per_chat=True,
            per_user=True
        )

        # Add handlers
        application.add_handler(conv_handler)
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_click_handler))

        # Start the bot with polling
        print("🚀 Starting bot in polling mode...")
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=['message', 'callback_query']
        )

    except Exception as e:
        logger.error(f"Error initializing application: {e}")
        raise

# Add a simple health check server for Render


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot is running')


def start_health_server():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    server.serve_forever()


if __name__ == "__main__":
    # Start health check server in background
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    print(
        f"🏥 Health check server started on port {os.environ.get('PORT', 8080)}")

    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"❌ Bot failed to start: {e}")

