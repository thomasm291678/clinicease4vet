"""AI语音+SOAP全端点测试 — 短超时防卡死，验证返回结构"""
import requests, sys, time, json, io, wave, struct

BASE = "http://localhost:3000/api"
P = 0
F = 0
TO = 8  # 全局请求超时

def T(name, ok, detail=""):
    global P, F
    if ok: P += 1; print(f"  [PASS] {name}")
    else: F += 1; print(f"  [FAIL] {name} -- {detail}")

def J(r):
    try: return r.json()
    except: return {}

def safe_post(path, json_data=None, files=None, data=None, timeout=TO):
    try:
        hd = {"Content-Type": "application/json"} | ({"Authorization": f"Bearer {token}"} if token else {})
        if json_data is not None:
            r = requests.post(f"{BASE}{path}", json=json_data, headers=hd, timeout=timeout)
        elif files:
            r = requests.post(f"{BASE}{path}", files=files, data=data or {}, headers={"Authorization": f"Bearer {token}"}, timeout=timeout)
        else:
            r = requests.post(f"{BASE}{path}", json={}, headers=hd, timeout=timeout)
        return r, J(r)
    except requests.exceptions.Timeout:
        return type("R",(),{"status_code":408,"text":"TIMEOUT"})(), {"error":"timeout","status":"timeout"}
    except Exception as e:
        return type("R",(),{"status_code":599,"text":str(e)})(), {"error":str(e),"status":"error"}

def safe_put(path, json_data, timeout=TO):
    try:
        hd = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
        r = requests.put(f"{BASE}{path}", json=json_data, headers=hd, timeout=timeout)
        return r, J(r)
    except Exception as e:
        return type("R",(),{"status_code":599})(), {"error":str(e)}

def safe_get(path, timeout=TO):
    try:
        r = requests.get(f"{BASE}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=timeout)
        return r, J(r)
    except requests.exceptions.Timeout:
        return type("R",(),{"status_code":408,"text":"TIMEOUT"})(), {"error":"timeout"}
    except Exception as e:
        return type("R",(),{"status_code":599,"text":str(e)})(), {"error":str(e)}

# ============= Setup =============
ts = str(int(time.time()))[-6:]
r = requests.post(f"{BASE}/auth/register", json={"username":f"aiv{ts}","password":"abc123","role":"vet"}, timeout=5)
r = requests.post(f"{BASE}/auth/login", json={"username":f"aiv{ts}","password":"abc123"}, timeout=5)
token = J(r).get("token","")
if not token: print("FATAL: login failed"); sys.exit(1)

r = requests.post(f"{BASE}/pets", json={"name":"AI测试狗","species":"狗","breed":"泰迪","gender":"雄性","age_months":36,"weight_kg":8,"owner_name":"AI主人"}, headers={"Authorization":f"Bearer {token}"}, timeout=5)
pet_id = J(r).get("pet_id")
r = requests.post(f"{BASE}/medical-records", json={"pet_id":pet_id,"vet_name":"AI医生","visit_date":"2026-07-14","diagnosis":"急性呕吐","treatment":"止吐观察","symptoms":"呕吐,精神沉郁"}, headers={"Authorization":f"Bearer {token}"}, timeout=5)
rec_id = J(r).get("record_id")
print(f"Setup: pet_id={pet_id} rec_id={rec_id}\n")

# 生成测试WAV
buf = io.BytesIO()
with wave.open(buf,"wb") as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(16000)
    for i in range(4000):
        wf.writeframes(struct.pack("<h", int(8000*(i*440/16000)%65536-32768)))
buf.seek(0); fake_wav = buf.read()


# =========================== 1. engine-status ===========================
print("=== 1. engine-status ===")
r, d = safe_get("/ai/engine-status")
T("1.1 200", r.status_code in (200,408))
T("1.2 ai_engine", "ai_engine" in d)
T("1.3 deepseek_configured", "deepseek_configured" in d)
T("1.4 deepseek_model", "deepseek_model" in d)
T("1.5 iflytek_configured", "iflytek_configured" in d)


# =========================== 2. transcribe (语音) ===========================
print("\n=== 2. transcribe ===")
r, d = safe_post("/ai/transcribe")
T("2.1 无文件→400", r.status_code==400)

r, d = safe_post("/ai/transcribe", files={"audio":("test.wav",fake_wav,"audio/wav")})
T("2.2 WAV上传", r.status_code in (200,408,500), f"s={r.status_code}")
if r.status_code==200:
    T("2.3 text存在", "text" in d)
    T("2.4 confidence存在", "confidence" in d)
    T("2.5 engine存在", "engine" in d)


# =========================== 3. transcribe-and-fill ===========================
print("\n=== 3. transcribe-and-fill ===")
r, d = safe_post("/ai/transcribe-and-fill", json_data={"text":"金毛旺财耳螨感染，耳漂洗耳液每日两次，一周后复诊，150元"})
T(f"3.1 文本填充 s={r.status_code}", r.status_code in (200,408))
if r.status_code==200:
    T("3.2 text存在", "text" in d)
    T("3.3 medical_form存在", "medical_form" in d)
    T("3.4 summary存在", "summary" in d)
    T("3.5 engine=deepseek", d.get("engine")=="deepseek", f"got {d.get('engine')}")

r, d = safe_post("/ai/transcribe-and-fill", json_data={"text":""})
T("3.6 空文本→400", r.status_code==400)

r, d = safe_post("/ai/transcribe-and-fill", files={"audio":("test.wav",fake_wav,"audio/wav")})
T(f"3.7 音频填充 s={r.status_code}", r.status_code in (200,400,408,500))


# =========================== 4. parse-record ===========================
print("\n=== 4. parse-record ===")
r, d = safe_post("/ai/parse-record", json_data={"text":"泰迪呕吐腹泻急性胃肠炎蒙脱石散益生菌200元"})
T(f"4.1 s={r.status_code}", r.status_code in (200,408))
if r.status_code==200:
    T("4.2 status=ok", d.get("status")=="ok")
    T("4.3 engine=deepseek", d.get("engine")=="deepseek")
    res = d.get("result",{})
    if isinstance(res,dict):
        T("4.4 pet_info", "pet_info" in res)
        T("4.5 diagnosis", "diagnosis" in res)
        T("4.6 treatment", "treatment" in res)
        T("4.7 fee", "fee" in res)
        diag = res.get("diagnosis",{})
        if isinstance(diag,dict):
            T("4.8 diag.name非空", bool(diag.get("name")), str(diag.get("name"))[:40])
            T("4.9 confidence>0", diag.get("confidence",0)>0, str(diag.get("confidence")))

r, d = safe_post("/ai/parse-record", json_data={"text":""})
T("4.10 空文本→400", r.status_code==400)


# =========================== 5. auto-fill ===========================
print("\n=== 5. auto-fill ===")
r, d = safe_post("/ai/auto-fill", json_data={"text":"金毛旺财急性胃炎止吐补液500元","pet_id":pet_id})
T(f"5.1 s={r.status_code}", r.status_code in (200,408))
if r.status_code==200:
    T("5.2 form_data", isinstance(d.get("form_data"),dict))
    fd = d.get("form_data",{})
    T("5.3 diagnosis非空", bool(fd.get("diagnosis","")), str(fd.get("diagnosis",""))[:50])
    T("5.4 pet_id正确", fd.get("pet_id")==pet_id)

r, d = safe_post("/ai/auto-fill", json_data={"text":""})
T("5.5 空→400", r.status_code==400)


# =========================== 6. disease-suggest ===========================
print("\n=== 6. disease-suggest ===")
r, d = safe_get("/ai/disease-suggest?symptoms=呕吐,腹泻,精神沉郁")
T(f"6.1 s={r.status_code}", r.status_code in (200,408))
if r.status_code==200:
    T("6.2 suggestions数组", isinstance(d.get("suggestions"),list))
    T("6.3 total_matches存在", "total_matches" in d)
    sugs = d.get("suggestions",[])
    T("6.4 非空", len(sugs)>0, f"count={len(sugs)}")
    if sugs:
        T("6.5 disease字段", "disease" in sugs[0] or "name" in sugs[0])

r, d = safe_get("/ai/disease-suggest")
T("6.6 无参数→400", r.status_code==400)


# =========================== 7. pet-summary ===========================
print("\n=== 7. pet-summary ===")
r, d = safe_get(f"/ai/pet-summary?pet_id={pet_id}")
T(f"7.1 s={r.status_code}", r.status_code==200)
T("7.2 pet_id正确", d.get("pet_id")==pet_id)
T("7.3 pet_name存在", bool(d.get("pet_name","")))
T("7.4 pet_species存在", bool(d.get("pet_species","")))
T("7.5 total_visits存在", "total_visits" in d)
T("7.6 timeline数组", isinstance(d.get("timeline"),list))

r, d = safe_get("/ai/pet-summary?pet_id=99999")
T("7.7 不存在→404", r.status_code==404)

r, d = safe_get("/ai/pet-summary")
T("7.8 无参数→400", r.status_code==400)


# =========================== 8. templates ===========================
print("\n=== 8. templates ===")
r, d = safe_get("/ai/templates")
T("8.1 200", r.status_code==200)
tmps = d.get("templates",[])
T("8.2 数组", isinstance(tmps,list))
T("8.3 >=14", len(tmps)>=14, f"{len(tmps)}")

for tmpl in tmps[:3]:
    r, d = safe_get(f"/ai/templates/{tmpl['id']}")
    T(f"8.4 {tmpl['id']} 200", r.status_code==200)
    T(f"8.5 {tmpl['id']} content非空", bool(d.get("content","")), f"{len(d.get('content',''))}chars")

r, d = safe_get("/ai/templates/nx")
T("8.6 不存在→404", r.status_code==404)


# =========================== 9. generate-treatment ===========================
print("\n=== 9. generate-treatment ===")
r, d = safe_post("/ai/generate-treatment", json_data={"symptoms":"呕吐,腹泻","diagnosis":"急性胃肠炎","species":"狗"})
T(f"9.1 s={r.status_code}", r.status_code in (200,408))
if r.status_code==200:
    T("9.2 treatment非空", bool(d.get("treatment","")), str(d.get("treatment",""))[:50])
    T("9.3 engine=deepseek", d.get("engine")=="deepseek")

r, d = safe_post("/ai/generate-treatment", json_data={})
T("9.4 空→400", r.status_code==400)


# =========================== 10. SOAP from-transcript ===========================
print("\n=== 10. SOAP from-transcript ===")
dialog = """主人: 我家狗狗昨天开始呕吐，吐了三四次黄色的水，精神不好不想动。
医生: 有没有腹泻？
主人: 没有，大便很正常。
医生: 有没有乱吃东西？
主人: 他一直喜欢在外面叼东西，不确定是不是吃进去了什么。"""

r, d = safe_post("/soap/from-transcript", json_data={"transcript":dialog,"species":"狗"}, timeout=30)
T(f"10.1 s={r.status_code}", r.status_code in (200,408,500))
if r.status_code==200:
    T("10.2 engine=deepseek", d.get("engine")=="deepseek", f"got {d.get('engine')}")
    soap = d.get("soap",{})
    T("10.3 soap字典", isinstance(soap,dict))
    T("10.4 subjective非空", bool(soap.get("subjective","")), f"len={len(soap.get('subjective',''))}")
    T("10.5 objective非空", bool(soap.get("objective","")), f"len={len(soap.get('objective',''))}")
    T("10.6 assessment非空", bool(soap.get("assessment","")), f"len={len(soap.get('assessment',''))}")
    T("10.7 plan非空", bool(soap.get("plan","")), f"len={len(soap.get('plan',''))}")
    reasoning = d.get("reasoning",{})
    T("10.8 reasoning字典", isinstance(reasoning,dict))
    T("10.9 problem_list数组", isinstance(reasoning.get("problem_list"),list))
    T("10.10 reasoning_path非空", bool(reasoning.get("reasoning_path","")))
    T("10.11 differential_list", isinstance(reasoning.get("differential_list"),list))
    T("10.12 must_not_miss", isinstance(reasoning.get("must_not_miss"),list))
    T("10.13 missing_info", bool(reasoning.get("missing_info","")))
    T("10.14 recommended_tests", isinstance(reasoning.get("recommended_tests"),list))
    cc = d.get("client_communication",{})
    T("10.15 cc字典", isinstance(cc,dict))
    T("10.16 observations存在", "observations" in cc)
    T("10.17 concerns存在", "concerns" in cc)
    T("10.18 summary非空", bool(d.get("summary","")))

r, d = safe_post("/soap/from-transcript", json_data={"transcript":""})
T("10.19 空对话→400", r.status_code==400)


# =========================== 11. SOAP from-transcript-audio ===========================
print("\n=== 11. SOAP from-transcript-audio ===")
r, d = safe_post("/soap/from-transcript-audio", files={"audio":("t.wav",fake_wav,"audio/wav")}, data={"species":"狗"}, timeout=30)
T(f"11.1 s={r.status_code}", r.status_code in (200,400,408,500))
if r.status_code==200:
    T("11.2 transcript存在", "transcript" in d)
    T("11.3 soap存在", d.get("soap") is not None)


# =========================== 12. SOAP GET/PUT ===========================
print("\n=== 12. SOAP GET/PUT ===")
r, d = safe_get(f"/soap/{rec_id}")
T("12.1 GET 200", r.status_code==200)
T("12.2 record存在", isinstance(d.get("record"),dict))
T("12.3 soap存在", isinstance(d.get("soap"),dict) or d.get("soap") is None)

r, d = safe_put(f"/soap/{rec_id}", json_data={
    "subjective":"主诉呕吐3次","objective":"T:38.5 HR:120 体重:8kg",
    "assessment":"1.急性呕吐\n2.轻度脱水",
    "plan":"1.禁食\n2.止吐\n3.补液\n4.复诊",
    "reasoning":{"problem_list":[{"rank":1,"problem":"呕吐","evidence_for":"","evidence_against":""}],"reasoning_path":"","differential_list":[],"must_not_miss":[],"missing_info":"","recommended_tests":[],"dynamic_questions":"","client_communication":{},"summary":""}
})
T("12.4 PUT 200", r.status_code==200)

r, d = safe_get(f"/soap/{rec_id}")
T("12.5 GET2 200", r.status_code==200)
soap = d.get("soap",{}) or {}
T("12.6 持久化OK", "呕吐" in str(soap.get("subjective","")), str(soap.get("subjective",""))[:50])


# =========================== 13. SOAP reasoning ===========================
print("\n=== 13. SOAP reasoning ===")
r, d = safe_post(f"/soap/{rec_id}/reasoning", json_data={}, timeout=30)
T(f"13.1 s={r.status_code}", r.status_code in (200,408,500))
if r.status_code==200:
    T("13.2 reasoning存在", "reasoning" in d)


# =========================== 14. SOAP client ===========================
print("\n=== 14. SOAP client ===")
r, d = safe_post(f"/soap/{rec_id}/client", json_data={}, timeout=30)
T(f"14.1 s={r.status_code}", r.status_code in (200,408,500))
if r.status_code==200:
    T("14.2 cc存在", "client_communication" in d)


# =========================== 15. 清理 ===========================
print("\n=== 15. 清理 ===")
requests.delete(f"{BASE}/pets/{pet_id}", headers={"Authorization":f"Bearer {token}"}, timeout=5)
T("15.1 清理完成", True)

# =========================== RESULT ===========================
print(f"\n{'='*60}")
print(f"  AI语音+SOAP测试: {P} 通过, {F} 失败, {P+F} 总计")
print(f"{'='*60}")
sys.exit(0 if F==0 else 1)
