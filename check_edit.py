import requests
BASE = 'http://127.0.0.1:5000'
r = requests.post(BASE + '/api/auth/login', json={'username': 'admin', 'password': 'admin123'})
token = r.json()['token']
h = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}

r = requests.get(BASE + '/api/pets', headers=h)
for p in r.json()['data']:
    rid = p.get('recent_record_id') or '-'
    print(f"  {p['name']:6s}  id={p['id']}  record_id={rid}  diag={p.get('recent_diagnosis') or '-'}  treatment={p.get('recent_treatment') or '-'}")

# Test editing a diagnosis
if rid != '-':
    r = requests.put(f"{BASE}/api/medical-records/{rid}", json={
        'pet_id': p['id'],
        'diagnosis': '修改后的猫瘟',
        'treatment': '新方案：补液+干扰素',
        'visit_date': p.get('recent_visit_date', '2026-07-10'),
    }, headers=h)
    print(f"\n  Update result: HTTP {r.status_code}")
