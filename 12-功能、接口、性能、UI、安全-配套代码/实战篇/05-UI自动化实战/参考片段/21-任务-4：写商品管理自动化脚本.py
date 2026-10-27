class ProductPage:
    def __init__(self, page):
        self.page = page
    
    def goto_products(self):
        self.page.click('text=商品管理')
        self.page.wait_for_url("**/products")
    
    def search_product(self, keyword):
        self.page.fill('input[name="keyword"]', keyword)
        self.page.click('button[type="submit"]')
        self.page.wait_for_selector('.product-list')
    
    def verify_product_exists(self, keyword):
        products = self.page.locator('.product-item')
        assert products.count() > 0, f"没找到商品：{keyword}"
