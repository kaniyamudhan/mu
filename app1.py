from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
import spacy
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, time
from dateutil.parser import parse
import os
import stripe
from io import BytesIO

app = Flask(__name__)

# Stripe keys (replace with your actual keys)
stripe.api_key = ""  # Your secret key
YOUR_DOMAIN = "http://localhost:5000"  # Replace with your actual domain

nlp = spacy.load("en_core_web_sm")
conversations = {}

def get_next_prompt(user_id):
    conversation = conversations.get(user_id, {})
    
    if 'name' not in conversation:
        return "What's your name?"
    elif 'date' not in conversation:
        return "What date would you like to visit the museum?"
    elif 'time' not in conversation:
        return "At what time would you like to visit?"
    elif 'tickets' not in conversation:
        return "How many tickets would you like to book?"

    return None

def extract_details(text, user_id):
    doc = nlp(text)
    conversation = conversations.setdefault(user_id, {})

    for ent in doc.ents:
        if ent.label_ == "PERSON" and 'name' not in conversation:
            conversation['name'] = ent.text
        elif ent.label_ == "DATE" and 'date' not in conversation:
            try:
                conversation['date'] = parse(ent.text, fuzzy=True).date().strftime("%Y-%m-%d")
            except ValueError:
                continue
        elif ent.label_ == "TIME" and 'time' not in conversation:
            try:
                conversation['time'] = parse(ent.text, fuzzy=True).time().strftime("%H:%M")
            except ValueError:
                continue
        elif ent.label_ == "CARDINAL" and 'tickets' not in conversation:
            conversation['tickets'] = ent.text

def validate_date_and_time(conversation):
    try:
        if 'date' in conversation:
            visit_date = datetime.strptime(conversation['date'], "%Y-%m-%d")
        else:
            return False, "Please provide a valid date."

        if 'time' in conversation:
            visit_time = datetime.strptime(conversation['time'], "%H:%M").time()
        else:
            return False, "Please provide a valid time."

        if visit_date.weekday() == 6:
            return False, "The museum is closed on Sundays. Please choose a different day."

        if not (time(9, 0) <= visit_time <= time(17, 0)):
            return False, "The museum is open only from 9 AM to 5 PM. Please choose a time within this range."

        return True, ""
    except ValueError:
        return False, "Invalid date or time format."

def generate_ticket_image(conversation, user_id):
    img = Image.new('RGB', (400, 200), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    d.text((10, 10), f"Ticket for {conversation['name']}", fill=(0, 0, 0), font=font)
    d.text((10, 40), f"Date: {conversation['date']}", fill=(0, 0, 0), font=font)
    d.text((10, 70), f"Time: {conversation['time']}", fill=(0, 0, 0), font=font)
    d.text((10, 100), f"Tickets: {conversation['tickets']}", fill=(0, 0, 0), font=font)

    ticket_path = f"ticket_{user_id}.png"
    img.save(ticket_path)
    return ticket_path

@app.route('/')
def index():
    return render_template('index.html')
@app.route('/get_response', methods=['POST'])
def get_response():
    user_message = request.form['message']
    user_id = request.form['user_id']

    extract_details(user_message, user_id)
    next_prompt = get_next_prompt(user_id)
    
    if next_prompt:
        response_message = next_prompt
    else:
        conversation = conversations[user_id]
        
        is_valid, validation_message = validate_date_and_time(conversation)
        if not is_valid:
            response_message = validation_message
        else:
            # Create a checkout session for payment
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Museum Ticket',
                        },
                        'unit_amount': 1000,  # 10 USD per ticket
                    },
                    'quantity': int(conversation['tickets']),
                }],
                mode='payment',
                success_url=YOUR_DOMAIN + f'/success/{user_id}',
                cancel_url=YOUR_DOMAIN + '/cancel',
            )
            
            # Generate the payment URL
            payment_url = session.url
            
            # Shortened display for the payment URL
            short_payment_url = f"{payment_url[:30]}...{payment_url[-5:]}"  # For visual shortening

            # Create a response message with JavaScript click function
            response_message = (
                f"Thank you {conversation['name']}! You have booked {conversation['tickets']} ticket(s) "
                f"for {conversation['date']} at {conversation['time']}. "
                f"Please proceed with payment using this link: <br>"
                f"<span style='color:blue; text-decoration:underline; cursor:pointer;' "
                f"onclick=\"window.open('{payment_url}', '_blank');\">Pay Now</span>"
            )

    return jsonify({"response": response_message})

# @app.route('/get_response', methods=['POST'])
# def get_response():
#     user_message = request.form['message']
#     user_id = request.form['user_id']

#     extract_details(user_message, user_id)
#     next_prompt = get_next_prompt(user_id)
    
#     if next_prompt:
#         response_message = next_prompt
#     else:
#         conversation = conversations[user_id]
        
#         is_valid, validation_message = validate_date_and_time(conversation)
#         if not is_valid:
#             response_message = validation_message
#         else:
#             # Create a checkout session for payment
#             session = stripe.checkout.Session.create(
#                 payment_method_types=['card'],
#                 line_items=[{
#                     'price_data': {
#                         'currency': 'usd',
#                         'product_data': {
#                             'name': 'Museum Ticket',
#                         },
#                         'unit_amount': 1000,  # 10 USD per ticket
#                     },
#                     'quantity': int(conversation['tickets']),
#                 }],
#                 mode='payment',
#                 success_url=YOUR_DOMAIN + f'/success/{user_id}',
#                 cancel_url=YOUR_DOMAIN + '/cancel',
#             )
            
#             # Instead of generating a QR code, create a payment link
#             payment_url = session.url
            
#             # Create a response message with a clickable link
#             # response_message = (
#             #     f"Thank you {conversation['name']}! You have booked {conversation['tickets']} ticket(s) "
#             #     f"for {conversation['date']} at {conversation['time']}. "
#             #     f"Please proceed with payment using the following link: <br>"
#             #     f"<a href='{payment_url}' target='_blank'>Pay for your tickets here</a>"
#             # )
#             response_message = (
#     f"Thank you {conversation['name']}! You have booked {conversation['tickets']} ticket(s) "
#     f"for {conversation['date']} at {conversation['time']}. "
#     f"Please proceed with payment using this link: "
#     f"{payment_url[:30]}... "
# )



#     return jsonify({"response": response_message})

@app.route('/success/<user_id>')
def success(user_id):
    ticket_path = generate_ticket_image(conversations[user_id], user_id)
    return redirect(url_for('download_ticket', user_id=user_id))

@app.route('/download_ticket/<user_id>')
def download_ticket(user_id):
    ticket_path = f"ticket_{user_id}.png"
    return send_file(ticket_path, as_attachment=True)

@app.route('/cancel')
def cancel():
    return "Payment was cancelled."

if __name__ == '__main__':
    app.run(debug=True)
