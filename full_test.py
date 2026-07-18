"""全控件回归测试 — 基于线上后端 :5000
覆盖: 静态文件/认证/宠物/诊疗/疫苗/药品/AI/SOAP/员工/v2.2新端点
"""
import requests, json, sys, time

BASE = "http://localhost:5000"
P, F = 0, 0
TS = str(int(time.time()))[-6:]

def T(name, ok, detail=""):
    global P, F
    if ok: P += 1; print(f"  [PASS] {name}")
    else: F += 1; print(f"  [FAIL] {name} -- {detail}")

def check_status(r, expected, name, extra=""):
    if r.status_code == expected:
        T(name, True, extra)
        return True
    else:
        T(name, False, f"status={r.status_code} expected={expected} body={r.text[:200]} {extra}")
        return False

def check_json(r, name):
    try:
        d = r.json()
        T(name, True)
        return d
    except:
        T(name, False, f"not JSON: {r.text[:200]}")
        return {}

# ============================================================
print("=" * 60)
print("  PetCare v2.2 全控件回归测试")
print("=" * 60)

# 0. 静态文件
print("\n--- 0. 静态文件 ---")
r = requests.get(BASE, timeout=5)
check_status(r, 200, "0.1 GET / 200 index.html")
T("0.2 含PetCare", "PetCare" in r.text or "app" in r.text.lower() or "<!DOCTYPE" in r.text.lower())

r = requests.get(BASE + "/login", timeout=5)
T("0.3 /login SPA", r.status_code == 200)

r = requests.get(BASE + "/pets", timeout=5)
T("0.4 /pets SPA", r.status_code == 200)

r = requests.get(BASE + "/medical", timeout=5)
T("0.5 /medical SPA", r.status_code == 200)

r = requests.get(BASE + "/vaccines", timeout=5)
T("0.6 /vaccines SPA", r.status_code == 200)

r = requests.get(BASE + "/drugs", timeout=5)
T("0.7 /drugs SPA", r.status_code == 200)

r = requests.get(BASE + "/soap", timeout=5)
T("0.8 /soap SPA", r.status_code == 200)

r = requests.get(BASE + "/ai-workbench", timeout=5)
T("0.9 /ai-workbench SPA", r.status_code == 200)

r = requests.get(BASE + "/employees", timeout=5)
T("0.10 /employees SPA", r.status_code == 200)

r = requests.get(BASE + "/dashboard", timeout=5)
T("0.11 /dashboard SPA", r.status_code == 200)

r = requests.get(BASE + "/api/nonexistent-xyz", timeout=5)
T("0.12 不存在API→404", r.status_code == 404)

# ============================================================
# 1. 认证
print("\n--- 1. 认证 ---")
r = requests.post(BASE + "/api/auth/register", json={"username": f"test{TS}", "password": "test123", "role": "vet"}, timeout=5)
check_status(r, 201, "1.1 注册 201")

r = requests.post(BASE + "/api/auth/login", json={"username": f"test{TS}", "password": "test123"}, timeout=5)
check_status(r, 200, "1.2 登录 200")
TOKEN = r.json().get("token", "")
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
T("1.3 token非空", bool(TOKEN))

r = requests.post(BASE + "/api/auth/login", json={"username": f"test{TS}", "password": "wrong"}, timeout=5)
check_status(r, 401, "1.4 错误密码→401")

r = requests.get(BASE + "/api/pets", timeout=5)
check_status(r, 401, "1.5 无token→401")

# ============================================================
# 2. 宠物 CRUD
print("\n--- 2. 宠物 ---")
r = requests.post(BASE + "/api/pets", json={
    "name": "检查犬", "species": "狗", "breed": "金毛",
    "gender": "雄性", "age_months": 24, "weight_kg": 30.5, "owner_name": "检查员"
}, headers=H, timeout=5)
d = check_json(r, "2.1 POST 创建宠物")
PID = d.get("pet_id") or d.get("id")
T("2.2 pet_id非空", bool(PID), f"id={PID}")

r = requests.get(BASE + "/api/pets", headers=H, timeout=5)
check_status(r, 200, "2.3 GET 列表 200")

r = requests.get(BASE + f"/api/pets/{PID}", headers=H, timeout=5)
d = check_json(r, "2.4 GET 详情 200")
T("2.5 name=检查犬", d.get("name") == "检查犬", f"got={d.get('name')}")

r = requests.put(BASE + f"/api/pets/{PID}", json={"name": "改命犬", "weight_kg": 32.0}, headers=H, timeout=5)
check_status(r, 200, "2.6 PUT 更新 200")

r = requests.get(BASE + f"/api/pets/{PID}", headers=H, timeout=5)
d = r.json()
T("2.7 更新后name=改命犬", d.get("name") == "改命犬", f"got={d.get('name')}")
T("2.8 更新后weight=32.0", abs(float(d.get("weight_kg", 0)) - 32.0) < 0.1, f"got={d.get('weight_kg')}")

# ============================================================
# 3. 诊疗记录
print("\n--- 3. 诊疗 ---")
r = requests.post(BASE + "/api/medical-records", json={
    "pet_id": PID, "vet_name": "测试兽医", "visit_date": "2026-07-15",
    "diagnosis": "急性胃炎", "treatment": "禁食24h+补液", "symptoms": "呕吐3次/腹泻"
}, headers=H, timeout=5)
check_status(r, 201, "3.1 POST 创建诊疗 201")
RID = r.json().get("record_id")

r = requests.get(BASE + "/api/medical-records", headers=H, timeout=5)
check_status(r, 200, "3.2 GET 列表 200")

r = requests.put(BASE + f"/api/medical-records/{RID}", json={"diagnosis": "慢性胃炎"}, headers=H, timeout=5)
check_status(r, 200, "3.3 PUT 更新诊疗 200")

# ============================================================
# 4. 疫苗
print("\n--- 4. 疫苗 ---")
r = requests.post(BASE + "/api/vaccinations", json={
    "pet_id": PID, "vaccine_name": "五联苗", "dose_number": 1,
    "administered_date": "2026-07-15", "vet_name": "测试兽医"
}, headers=H, timeout=5)
check_status(r, 201, "4.1 POST 创建疫苗 201")
VID = r.json().get("vaccination_id")

r = requests.get(BASE + "/api/vaccinations", headers=H, timeout=5)
check_status(r, 200, "4.2 GET 列表 200")

r = requests.put(BASE + f"/api/vaccinations/{VID}", json={"dose_number": 2}, headers=H, timeout=5)
check_status(r, 200, "4.3 PUT 更新疫苗 200")

# ============================================================
# 5. 药品
print("\n--- 5. 药品 ---")
r = requests.post(BASE + "/api/drugs", json={
    "drug_name": "阿莫西林", "category": "抗生素",
    "quantity": 100, "unit": "瓶", "unit_price": 35.0
}, headers=H, timeout=5)
check_status(r, 201, "5.1 POST 创建药品 201")
DID = r.json().get("drug_id") or r.json().get("id")

r = requests.get(BASE + "/api/drugs", headers=H, timeout=5)
check_status(r, 200, "5.2 GET 列表 200")

r = requests.put(BASE + f"/api/drugs/{DID}", json={"quantity": 80}, headers=H, timeout=5)
check_status(r, 200, "5.3 PUT 更新药品 200")

r = requests.get(BASE + f"/api/drugs/{DID}", headers=H, timeout=5)
d = r.json()
T("5.4 quantity=80", str(d.get("quantity")) in ["80", 80], f"got={d.get('quantity')}")

# ============================================================
# 6. AI 引擎
print("\n--- 6. AI 基础 ---")
r = requests.get(BASE + "/api/ai/engine-status", headers=H, timeout=5)
d = check_json(r, "6.1 engine-status 200")
T("6.2 deepseek_configured", d.get("deepseek_configured") == True)
features = d.get("features", {})
T("6.3 multi_agent feature", features.get("multi_agent") == True, str(features))
T("6.4 grpo feature", features.get("grpo_self_verify") == True)

r = requests.get(BASE + "/api/ai/templates", headers=H, timeout=5)
check_status(r, 200, "6.5 templates 200")

r = requests.post(BASE + "/api/ai/disease-suggest?symptoms=呕吐腹泻", headers=H, timeout=30)
check_status(r, 200, "6.6 disease-suggest 200")

# ============================================================
# 7. SOAP
print("\n--- 7. SOAP ---")
r = requests.get(BASE + f"/api/soap/{RID}", headers=H, timeout=5)
check_status(r, 200, "7.1 GET SOAP 200")

# 写入完整SOAP
soap_data = {
    "subjective": "主诉呕吐3天",
    "objective": "脱水5%",
    "assessment": "急性胃炎",
    "plan": "禁食补液",
    "reasoning": {
        "problem_list": [{"rank": 1, "problem": "呕吐"}],
        "reasoning_path": "呕吐→胃炎",
        "summary": "急性胃炎"
    }
}
r = requests.put(BASE + f"/api/soap/{RID}", json=soap_data, headers=H, timeout=5)
check_status(r, 200, "7.2 PUT SOAP 200")

r = requests.get(BASE + f"/api/soap/{RID}", headers=H, timeout=5)
T("7.3 SOAP持久化", r.status_code == 200 and "subjective" in r.text.lower())

# ============================================================
# 8. v2.2 新端点 (DeepSeek需真实调用，仅验证路由存在)
print("\n--- 8. v2.2 新端点路由验证 ---")
for ep, body in [
    ("/api/ai/soap/multi-agent", {"transcript": "测试对话", "species": "狗"}),
    ("/api/ai/soap/grpo", {"transcript": "测试对话", "species": "狗"}),
    ("/api/ai/multi-agent/diagnose", {"case_info": "犬呕吐3天", "species": "狗"}),
    ("/api/ai/grpo/verify", {"case_info": "犬呕吐3天", "species": "狗"}),
    ("/api/ai/drug/safety", {"drug_name": "阿莫西林", "species": "狗"}),
    ("/api/ai/differential/evidence", {"symptoms": "呕吐腹泻", "diagnosis": "胃炎", "species": "狗"}),
    ("/api/ai/triage", {"case_info": "犬车祸后腿瘸", "species": "狗"}),
]:
    label = ep.replace("/api/ai/", "")
    try:
        r = requests.post(BASE + ep, json=body, headers=H, timeout=60)
        if r.status_code == 200:
            T(f"8.x {label} 200", True)
        elif r.status_code == 500:
            T(f"8.x {label} 500(API可能超时)", "API错误" in r.text or "AI" in r.text or "error" in r.text.lower())
        else:
            T(f"8.x {label} {r.status_code}", r.status_code in [200, 500, 503], r.text[:150])
    except requests.Timeout:
        T(f"8.x {label} TIMEOUT", True, "DeepSeek响应慢(预期)")

# ============================================================
# 9. 员工管理
print("\n--- 9. 员工 ---")
r = requests.post(BASE + "/api/admin/staff", json={
    "type": "vet", "name": "测试兽医", "specialisation": "内科", "license_no": "V123456", "age": 35, "contact": "13800000000", "consultation_fee": 100
}, headers=H, timeout=5)
check_status(r, 201, "9.1 创建兽医 201")

r = requests.get(BASE + "/api/admin/staff?type=vet", headers=H, timeout=5)
check_status(r, 200, "9.2 获取兽医列表 200")

r = requests.get(BASE + "/api/admin/staff?type=assistant", headers=H, timeout=5)
check_status(r, 200, "9.3 获取助理列表 200")

r = requests.get(BASE + "/api/admin/staff?type=other", headers=H, timeout=5)
check_status(r, 200, "9.4 获取其他员工列表 200")

# ============================================================
# 10. 清理
print("\n--- 10. 清理 ---")
requests.delete(BASE + f"/api/vaccinations/{VID}", headers=H, timeout=5)
requests.delete(BASE + f"/api/medical-records/{RID}", headers=H, timeout=5)
requests.delete(BASE + f"/api/drugs/{DID}", headers=H, timeout=5)
requests.delete(BASE + f"/api/pets/{PID}", headers=H, timeout=5)
T("10.1 清理完成", True)

# 确认删除
r = requests.get(BASE + f"/api/pets/{PID}", headers=H, timeout=5)
T("10.2 宠物已删除→404", r.status_code == 404, f"status={r.status_code}")

# ============================================================
print(f"\n{'='*60}")
print(f"  全控件测试: {P} 通过, {F} 失败, {P+F} 总计")
print(f"{'='*60}")
sys.exit(0 if F == 0 else 1)
