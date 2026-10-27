class SeckillPage:
    def __init__(self, page):
        self.page = page
    
    def goto_seckill(self):
        self.page.goto("http://localhost:5000/seckill")
        self.page.wait_for_url("**/seckill")
    
    def buy_seckill(self):
        self.page.click('text=立即购买')
        self.page.wait_for_timeout(1000)  # 等待响应
    
    def verify_order_success(self):
        # 验证下单成功
        assert "成功" in self.page.inner_text('body') or "订单" in self.page.url
