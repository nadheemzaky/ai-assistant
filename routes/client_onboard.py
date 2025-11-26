import re
from core.openrouter_client import call_openrouter
import logging
from core.session_manager import session_manager
import random
from .onboard.onboard_preset_messages import client_onboarding_replies,name_retry_replies,mobile_retry_replies,password_retry_replies,email_retry_replies
from dotenv import load_dotenv
import os
import requests
import json
from core.audit_logger import append_onboard_async

load_dotenv()
API_TOKEN = os.getenv("BEARER_TOKEN")

def start_onboard(session_id,user_message):# ask name
    logging.info('started onboarding')
    try:
        reply = random.choice(client_onboarding_replies)
        try:
            session_manager.update_state(session_id,'verify_name')
        except Exception as e:
            logging.error({e})
        return reply
    except Exception as e:
        logging.error(f'get order id route error:{e}')

def verify_name(session_id,user_message): # ask mobile
    logging.info("Verifying name")

    try:
        if len(user_message.strip()) < 2:
            return random.choice(name_retry_replies)

        name = user_message.strip()
        session_manager.update_name(session_id, name)
        logging.info(f"Valid name detected: {name}")

        try:
            session_manager.update_state(session_id,'verify_mobile')
        except Exception as e:
            logging.error({e})

        return f"Thank you, {name}! We're almost done. Could you please share your mobile number"
    except Exception as e:
        logging.error(f'Verify name route error: {e}')

def verify_mobile(session_id,user_message): # ask email
    logging.info("Verifying mobile number")

    try:
        match = re.search(r"\b\d{10}\b", user_message)

        if not match:
            return random.choice(mobile_retry_replies)
        mobile_number = match.group(0)

        try:
            mob=session_manager.update_mobile(session_id, mobile_number)
            logging.info(f"Valid mobile number detected: {mobile_number}")
        except Exception as e:
            logging.error({e})

        try:
            session_manager.update_state(session_id,'verify_email')
        except Exception as e:
            logging.error({e})
            
        return f"Thank you! Your mobile number {mobile_number} has been verified. Please provide your email address."
    except Exception as e:
        logging.error(f'Verify mobile route error: {e}')                                                                    


def verify_email(session_id,user_message):#ask password
    logging.info("Verifying email")

    try:
        match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", user_message)
        if not match:
            return random.choice(email_retry_replies)

        email = match.group(0)
        try:
            session_manager.update_email(session_id, email)
        except Exception as e:
            logging.error({e})
        logging.info(f"Valid email detected: {email}")
        try:
            session_manager.update_state(session_id,'password_set')
        except Exception as e:
            logging.error({e})

        return f"Thank you! Your email address {email} has been verified. Please create a password using 8 characters (letters A-Z/a-z and digits 0-9)."
    except Exception as e:
        logging.error(f'Verify email route error: {e}')

def verify_password(session_id,user_message):
    logging.info("Verifying password")

    try:
        match = re.fullmatch(r"[A-Za-z0-9]{8}", user_message.strip())
        if not match:
            return random.choice(password_retry_replies)

        password = user_message.strip()
        try:
            session_manager.update_password(session_id, password)
        except Exception as e:
            logging.error({e})
        logging.info(f"password set.")    

        try:
            session_manager.update_state(session_id,'confirm_password')
        except Exception as e:
            logging.error({e})
        return "Please re-enter your password to complete the onboarding process."
    except Exception as e:
        logging.error(f'Verify password route error: {e}')

def confirm_password(session_id, user_message):
    logging.info("Confirming password")

    try:
        session = session_manager.get_onboard_data(session_id)

        if session is None:
            logging.error(f"No onboard data found for session: {session_id}")
            return "We couldn't find your onboarding session. Please restart the process."

        stored_password = session.get('password')

        if not stored_password:
            logging.error(f"No stored password found for session: {session_id}")
            return "It looks like you haven't set a password yet. Please enter your password again."

        if user_message.strip() != stored_password:
            return "The passwords do not match. Please re-enter your password."

        # Passwords match
        try:
            session_manager.update_state(session_id, 'completed')
        except Exception as e:
            logging.error(f"Failed to update session state: {e}")
            return "Your password was confirmed but we could not complete onboarding. Contact support."
        try:
            get_onboard=session_manager.get_onboard_data(session_id)
            name=str(get_onboard.get('name'))
            mobile_number=str(get_onboard.get('mobile'))
            email=str(get_onboard.get('email'))
            password=str(get_onboard.get('password'))
            create_client(API_TOKEN, name, mobile_number, email, password, password)
            append_onboard_async(name, mobile_number, email, password, password)

        except Exception as e:
            logging.error(f"Failed to create client: {e}")

        return "🎉 Congratulations! Your onboarding is complete. You can now access all features."

    except Exception as e:
        logging.error(f"Confirm password route error: {e}")
        return "An unexpected error occurred. Please try again."


import requests
import logging

def create_client(api_token, name, mobile_number, email, password, password_confirmation):
    url = "https://sandbox.4ulogistic.com/api/client/create"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_token}"
    }

    payload = json.dumps({
    "name": name,
    "mobile_number": mobile_number,
    "email": email,
    "password": password,
    "password_confirmation": password_confirmation
    })
    try:
        response = requests.post(url, headers=headers, data=payload)

        logging.info(f"API Status Code: {response.status_code}")

        # Check response success
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"API Error: {response.text}")
            return {
                "success": False,
                "status_code": response.status_code,
                "error": response.text
            }

    except Exception as e:
        logging.error(f"Request failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }
