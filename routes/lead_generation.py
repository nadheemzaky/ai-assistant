import re
import random
import logging
from core.session_manager import session_manager
import os
from dotenv import load_dotenv
from .lead_gen.lead_prompts import (lead_branches_retry,lead_brand_retry,lead_email_retry,lead_name_retry,lead_phone_retry,lead_sector_retry,lead_start_replies)
from .lead_gen.lead_gen_api import create_lead  # API call file

load_dotenv()
API_TOKEN = os.getenv("LEAD_TOKEN")

def start_lead(session_id, user_message):
    logging.info("Started lead onboarding")
    reply = random.choice(lead_start_replies)

    try:
        session_manager.update_state(session_id, "lead_verify_name")
    except Exception as e:
        logging.error(e)

    return reply


def lead_verify_name(session_id, user_message):
    name = user_message.strip()

    if len(name) < 2:
        return random.choice(lead_name_retry)

    session_manager.update_value(session_id,"name", name)
    session_manager.update_state(session_id, "lead_verify_phone")

    return f"Thanks {name}! Please share your phone number."


def lead_verify_phone(session_id, user_message):
    match = re.search(r"\b\d{10}\b", user_message)
    logging.info('phone verification func active')

    if not match:
        return random.choice(lead_phone_retry)

    phone = match.group(0)
    session_manager.update_value(session_id, "mobile", phone)
    session_manager.update_state(session_id, "lead_verify_email")

    return "Got it! Now please provide your email address."


def lead_verify_email(session_id, user_message):
    match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}", user_message)

    if not match:
        return random.choice(lead_email_retry)

    email = match.group(0)
    session_manager.update_value(session_id, "email", email)
    session_manager.update_state(session_id, "lead_verify_brand")

    return "Perfect! What's your brand name?"


def lead_verify_brand(session_id, user_message):
    brand = user_message.strip()

    if len(brand) < 2:
        return random.choice(lead_brand_retry)

    session_manager.update_value(session_id, "brand", brand)
    session_manager.update_state(session_id, "lead_verify_sector")

    return "Nice! Please tell me your business sector."


def lead_verify_sector(session_id, user_message):
    sector = user_message.strip()

    if len(sector) < 2:
        return random.choice(lead_sector_retry)

    session_manager.update_value(session_id, "sector", sector)
    session_manager.update_state(session_id, "lead_verify_branches")

    return "Great! How many branches do you have?"


def lead_verify_branches(session_id, user_message):
    if not user_message.isdigit():
        return random.choice(lead_branches_retry)

    branches = int(user_message)
    session_manager.update_value(session_id, "branches", branches)
    session_manager.update_state(session_id, "INITIAL")
#/////////////////////////////////////check here , is the problem session manager dont have funciton!!!/////////////////////////////////////
    # Fetch stored data
    data = session_manager.get_lead_values(session_id)
    logging.info(f"Lead Data Collected: {data}")
    name = data.get("name")
    phone = data.get("mobile")
    email = data.get("email")
    brand = data.get("brand")
    sector = data.get("sector")
    branches = data.get("branches")

    # Send to API
    create_lead(
        API_TOKEN,
        name,
        phone,
        email,
        brand,
        sector,
        branches
    )

    return "🎉 Your lead has been submitted successfully! Our team will contact you soon."
