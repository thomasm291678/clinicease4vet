import requests
BASE = 'http://127.0.0.1:5000'

# register + login
requests.post(BASE + '/api/auth/register', json={'username': 'admin', 'password': 'admin123', 'role': 'admin'})
r = requests.post(BASE + '/api/auth/login', json={'username': 'admin', 'password': 'admin123'})
token = r.json()['token']
h = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}

# create pet
r = requests.post(BASE + '/api/pets', json={
    'name': '大黄', 'species': '狗', 'breed': '土狗', 'gender': '公',
    'age_months': 48, 'weight_kg': 20, 'owner_name': '王五'
}, headers=h)
pet_id = r.json().get('pet_id')
print(f"Created pet id={pet_id}")

# create medical record WITH symptoms
r = requests.post(BASE + '/api/medical-records', json={
    'pet_id': pet_id,
    'vet_name': '李医生',
    'visit_date': '2026-07-13',
    'diagnosis': '皮肤病',
    'treatment': '外用药膏',
    'symptoms': '瘙痒、脱毛、皮肤红肿',
    'fee_charged': 200,
}, headers=h)
record_id = r.json().get('record_id')
print(f"Created record id={record_id}, status={r.status_code}")

# list records and check symptoms
r = requests.get(BASE + '/api/medical-records', headers=h)
for rec in r.json()['data']:
    print(f"  pet={rec['pet_id']} diag={rec.get('diagnosis','-')} symptoms={rec.get('symptoms','-')}")

# test transcribe-and-fill with symptoms keywords
r = requests.post(BASE + '/api/ai/transcribe-and-fill', json={
    'text': '一只3岁的狗，症状是呕吐腹泻食欲不振，诊断肠胃炎，治疗蒙脱石散，收费350元'
}, headers=h)
d = r.json()
mf = d.get('medical_form', {})
print(f"\nTranscribe-and-fill symptoms: {mf.get('symptoms','N/A')}")
print(f"  diagnosis: {mf.get('diagnosis','N/A')}")
print(f"  All OK!" if r.status_code == 200 else f"  FAIL: {r.status_code}")
