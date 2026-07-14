import requests, json

BASE = 'http://127.0.0.1:5000'
r = requests.post(BASE + '/api/auth/login', json={'username': 'admin', 'password': 'admin123'})
token = r.json()['token']
h = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}

tests = 0
ok = 0

print("=== 1. Template detail (4 of 14) ===")
for tid in ['t01', 't03', 't07', 't14']:
    r = requests.get(f'{BASE}/api/ai/templates/{tid}', headers=h)
    tests += 1
    d = r.json()
    name = d.get('name', '')
    clen = len(d.get('content', ''))
    passed = r.status_code == 200 and clen > 100
    ok += 1 if passed else 0
    status = 'PASS' if passed else 'FAIL'
    print(f'  [{status}] {tid}: {name} ({clen} chars)')

r = requests.get(f'{BASE}/api/ai/templates/t99', headers=h)
tests += 1
passed = r.status_code == 404
ok += 1 if passed else 0
print(f'  [{"PASS" if passed else "FAIL"}] t99: HTTP {r.status_code} (expected 404)')

print()
print("=== 2. Transcribe-and-fill ===")
r = requests.post(f'{BASE}/api/ai/transcribe-and-fill', json={
    'text': '3岁英短猫呕吐腹泻三天，体温39.5度，诊断为猫瘟，治疗补液+抗生素，收费500元'
}, headers=h)
tests += 1
d = r.json()
mf = d.get('medical_form')
diag = mf.get('diagnosis', 'N/A') if mf else 'N/A'
conf = d.get('confidence', 0)
passed = r.status_code == 200 and bool(mf and mf.get('diagnosis'))
ok += 1 if passed else 0
print(f'  [{"PASS" if passed else "FAIL"}] diagnosis={diag}, confidence={conf}%, engine={d.get("engine")}')

print()
print("=== 3. Pet summary ===")
r = requests.post(BASE + '/api/pets', json={
    'name': '小花', 'species': '猫', 'breed': '英短',
    'gender': '母', 'age_months': 36, 'weight_kg': 4, 'owner_name': '李四'
}, headers=h)
pet_id = r.json().get('pet_id')

requests.post(BASE + '/api/medical-records', json={
    'pet_id': pet_id, 'vet_name': '王医生', 'visit_date': '2026-07-10',
    'diagnosis': '猫瘟', 'treatment': '补液+抗生素', 'fee_charged': 500
}, headers=h)
requests.post(BASE + '/api/vaccinations', json={
    'pet_id': pet_id, 'vaccine_name': '猫三联', 'administered_date': '2026-07-10'
}, headers=h)

r = requests.get(f'{BASE}/api/ai/pet-summary?pet_id={pet_id}', headers=h)
tests += 1
d = r.json()
passed = r.status_code == 200 and d.get('total_visits', 0) > 0
ok += 1 if passed else 0
summary_preview = d.get('summary', '')[:100]
print(f'  [{"PASS" if passed else "FAIL"}] {d.get("pet_name")}: {d.get("total_visits")} visits, {d.get("total_vaccines")} vaccines')
print(f'  Summary: {summary_preview}...')

print()
print(f"=== Results: {ok}/{tests} passed ===")
if ok == tests:
    print("ALL PASSED")
else:
    print(f"{tests - ok} FAILED")
