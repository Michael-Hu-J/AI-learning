const BASE_URL = __ENV.BASE_URL || 'http://localhost:5001';

export default function () {
    http.get(`${BASE_URL}/api/products`);
}
