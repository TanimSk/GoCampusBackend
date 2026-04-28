from sslcommerz_lib import SSLCOMMERZ
from utils.redis_handler import get_sync_redis
from uuid import uuid4
import json


def payment(payload: dict):
    BASE_URL = "http://localhost:8000"

    # dummy payment info
    """
    payload = {
        "customer_name": "John Doe",
        "amount": 5000.00
    }
    """

    settings = {
        "store_id": "ongsh66c071035e11c",
        "store_pass": "ongsh66c071035e11c@ssl",
        "issandbox": True,
    }
    tran_id = str(uuid4())

    # store payload in cache
    payment_info_store_in_cache(payload, tran_id)

    sslcz = SSLCOMMERZ(settings)
    post_body = {}
    post_body["total_amount"] = payload["amount"]
    post_body["currency"] = "BDT"
    post_body["tran_id"] = tran_id
    post_body["success_url"] = (
        f"{BASE_URL}/payment-ops/?trans-id={tran_id}&status=success"
    )
    post_body["fail_url"] = f"{BASE_URL}/payment-ops/?status=failed"
    post_body["cancel_url"] = f"{BASE_URL}/payment-ops/?status=cancelled"
    post_body["emi_option"] = 0
    post_body["cus_name"] = payload["customer_name"]
    post_body["cus_email"] = "sktanim5800@gmail.com"
    post_body["cus_phone"] = "01760001377"
    post_body["cus_add1"] = "Kazla, Rajshahi"
    post_body["cus_add2"] = "Rajshahi, Bangladesh"
    post_body["cus_city"] = "Rajshahi"
    post_body["cus_country"] = "BD"
    post_body["shipping_method"] = "NO"
    post_body["multi_card_name"] = ""
    post_body["num_of_item"] = 1
    post_body["product_name"] = f"GoCampus - {tran_id}"
    post_body["product_category"] = "cart_fee"
    post_body["product_profile"] = "general"

    response = sslcz.createSession(post_body)

    # pretty print post_body
    print(json.dumps(post_body, indent=4))

    return response


def payment_info_store_in_cache(payload: dict, tran_id: str):
    expiry_time = 900  # 15 minute
    redis_client = get_sync_redis()
    redis_client.setex(f"payment-{tran_id}", expiry_time, json.dumps(payload))
    print(f"Cache updated with payment info [payment-{tran_id}]")