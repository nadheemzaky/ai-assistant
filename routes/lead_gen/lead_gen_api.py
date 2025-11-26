import requests
import json
import logging

def create_lead(api_token, name, phone, email, brand_name, sector, number_of_branches):
    url = "https://sandbox.4ulogistic.com/api/leads"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_token}"
    }

    payload = {
        "client": {
            "contact": {
                "phone": phone,
                "email": email,
                "authorized_person": name
            },
            "cr": {
                "number": "",
                "name": "",
                "manager": "",
                "city": ""
            },
            "vat_number": "",
            "number_of_branches": number_of_branches
        },

        "brand": {
            "name": brand_name,
            "logo_url": "",
            "sector": sector
        },

        "branches": []
    }
    print(payload)
#response = requests.request("POST", url, headers=headers, data=payload)

    try:
        response = requests.post(url, headers=headers, json=payload)
        logging.info(f"Lead API Status Code: {response.status_code}")

        if response.status_code in [200, 201]:
            return {"success": True, "data": response.json()}

        logging.error(f"Lead API Error: {response.text}")
        return {"success": False, "status_code": response.status_code, "error": response.text}

    except Exception as e:
        logging.error(f"Lead request failed: {e}")
        return {"success": False, "error": str(e)}
