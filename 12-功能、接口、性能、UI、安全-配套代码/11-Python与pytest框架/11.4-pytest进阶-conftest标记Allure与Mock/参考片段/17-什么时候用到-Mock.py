# 你要测这个函数
def process_payment(order_id, amount):
    """调用第三方支付接口"""
    response = requests.post("https://pay.thirdparty.com/api/pay",
                            json={"order_id": order_id, "amount": amount})
    if response.status_code == 200:
        update_order_status(order_id, "paid")
        return True
    else:
        update_order_status(order_id, "failed")
        return False
