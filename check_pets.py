import requests
r = requests.post('http://127.0.0.1:5000/api/auth/login', json={'username': 'admin', 'password': 'admin123'})
token = r.json()['token']
h = {'Authorization': 'Bearer ' + token}
r = requests.get('http://127.0.0.1:5000/api/pets', headers=h)
for p in r.json()['data']:
    diag = p.get('recent_diagnosis') or '-'
    visits = p.get('total_visits') or 0
    print(f"  {p['name']:6s}  {p['species']:3s}  recent: {diag}  ({visits}次)")
