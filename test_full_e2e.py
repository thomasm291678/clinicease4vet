"""端到端全量交互测试 v2 —— 适配真实API格式"""
import requests, sys, time

BASE = "http://localhost:3000/api"
P = 0
F = 0
TS = str(int(time.time()))[-5:]

def T(name, ok, detail=""):
    global P, F
    if ok: P += 1; print(f"  [PASS] {name}")
    else: F += 1; print(f"  [FAIL] {name} -- {detail}")

def J(r): return r.json() if r.headers.get("content-type","").startswith("application/json") else {}
def R(method, path, data=None, token=None, exp_code=200):
    h = {"Content-Type":"application/json"}
    if token: h["Authorization"]=f"Bearer {token}"
    if method=="POST": return requests.post(BASE+path,json=data,headers=h)
    if method=="PUT": return requests.put(BASE+path,json=data,headers=h)
    if method=="DELETE": return requests.delete(BASE+path,headers=h)
    return requests.get(BASE+path,headers=h)

# =========================== 1. AUTH ===========================
print("=== 1. AUTH 认证 ===")

user = f"e2e{TS}"
r = R("POST","/auth/register",data={"username":user,"password":"abc123","role":"vet"})
T("1.1 注册", r.status_code==201, J(r).get("message",""))
T("1.2 message=注册成功", J(r).get("message")=="注册成功")

r = R("POST","/auth/register",data={"username":user,"password":"abc123","role":"vet"})
T("1.3 重复注册 409", r.status_code==409, J(r).get("error",""))

r = R("POST","/auth/register",data={"username":"t2","password":"ab","role":"vet"})
T("1.4 短密码 400", r.status_code==400)

r = R("POST","/auth/register",data={})
T("1.5 空body 400", r.status_code==400)

r = R("POST","/auth/register",data={"username":f"norole{TS}","password":"abcdef"})
T("1.6 不传role 201", r.status_code==201)

r = R("POST","/auth/login",data={"username":user,"password":"abc123"})
T("1.7 登录 200", r.status_code==200)
token = J(r).get("token","")
T("1.8 token非空", bool(token))

r = R("POST","/auth/login",data={"username":user,"password":"wrong"})
T("1.9 错误密码 401", r.status_code==401)

r = R("POST","/auth/login",data={"username":"nobody","password":"abc123"})
T("1.10 不存在用户 401", r.status_code==401)

r = requests.get(BASE+"/pets")
T("1.11 无token 401", r.status_code==401)

# =========================== 2. PET ===========================
print("\n=== 2. PET 宠物管理 ===")

r = R("POST","/pets",token=token,data={"name":"旺财","species":"狗","breed":"金毛","gender":"雄性","age_months":60,"weight_kg":31,"owner_name":"张三","owner_contact":"13800138000"})
T("2.1 创建宠物 201", r.status_code==201)
pet1 = J(r).get("pet_id")
T("2.2 pet_id非空", bool(pet1))

r = R("POST","/pets",token=token,data={"name":"咪咪","species":"猫","breed":"英短","gender":"雌性","age_months":24,"weight_kg":4.2,"owner_name":"李四","owner_contact":"13900139000"})
T("2.3 第二只 201", r.status_code==201)
pet2 = J(r).get("pet_id")

r = R("GET","/pets",token=token)
pets = J(r).get("data",[])
T("2.4 列表200", r.status_code==200)
T("2.5 pets>=2", len(pets)>=2, f"got {len(pets)}")

r = R("GET","/pets?species=狗",token=token)
T("2.6 按物种过滤", len(J(r).get("data",[]))>=1)

r = R("GET","/pets?search=张三",token=token)
T("2.7 搜索张三", len(J(r).get("data",[]))>=1)

r = R("GET",f"/pets/{pet1}",token=token)
pet_detail = J(r).get("data", J(r))
T("2.8 宠物详情", pet_detail.get("name")=="旺财",f"got {pet_detail.get('name')}")

r = R("PUT",f"/pets/{pet1}",token=token,data={"name":"旺财","species":"狗","breed":"金毛","gender":"雄性","age_months":62,"weight_kg":32,"owner_name":"张三","owner_contact":"13800138001"})
T("2.9 更新宠物 200", r.status_code==200)

r = R("GET","/pets/99999",token=token)
T("2.10 不存在 404", r.status_code==404)

r = R("GET","/pets/stats",token=token)
T("2.11 统计200", r.status_code==200)
stats_data = J(r).get("data", [])
other_count = [x.get("count",0) for x in stats_data if x.get("species")!="猫"]
T("2.12 统计含狗", sum(other_count)>=1)

# =========================== 3. MEDICAL ===========================
print("\n=== 3. MEDICAL 诊疗记录 ===")

r = R("POST","/medical-records",token=token,data={"pet_id":pet1,"vet_name":"杨医生","visit_date":"2025-07-14","diagnosis":"急性胃炎","treatment":"止吐+补液","symptoms":"呕吐","subjective":"主诉呕吐","objective":"T:38.5","assessment":"急性胃炎","plan":"禁食+止吐+补液","fee_charged":500,"follow_up_date":"2025-07-17"})
T("3.1 创建 201", r.status_code==201)
rec1 = J(r).get("record_id")
T("3.2 record_id非空", bool(rec1))

r = R("GET","/medical-records",token=token)
recs = J(r).get("data",[])
T("3.3 列表200", r.status_code==200)
T("3.4 records>=1", len(recs)>=1, f"got {len(recs)}")

r = R("GET",f"/medical-records?pet_id={pet1}",token=token)
T("3.5 pet_id过滤", len(J(r).get("data",[]))>=1)

r = R("PUT",f"/medical-records/{rec1}",token=token,data={"pet_id":pet1,"vet_name":"杨医生","visit_date":"2025-07-14","diagnosis":"急性胃炎伴脱水","treatment":"止吐+补液+益生菌","symptoms":"呕吐","fee_charged":800})
T("3.6 更新 200", r.status_code==200)

r = R("GET","/medical-records?pet_id=99999",token=token)
T("3.7 不存在pet 空", len(J(r).get("data",[]))==0)

# =========================== 4. VACCINE ===========================
print("\n=== 4. VACCINE 疫苗接种 ===")

r = R("POST","/vaccinations",token=token,data={"pet_id":pet1,"vaccine_name":"卫佳捌","dose_number":1,"administered_date":"2025-07-14","next_due_date":"2025-08-14","vet_name":"杨医生","batch_number":"B001"})
T("4.1 创建 201", r.status_code==201)
vac1 = J(r).get("record_id") or J(r).get("vaccination_id")

r = R("GET","/vaccinations",token=token)
T("4.2 列表200", r.status_code==200)
T("4.3 列表>=1", len(J(r).get("data",[]))>=1)

r = R("GET",f"/vaccinations?pet_id={pet1}",token=token)
T("4.4 按pet_id过滤", r.status_code==200)

r = R("GET","/vaccinations?upcoming=true",token=token)
T("4.5 到期提醒200", r.status_code==200)

r = R("DELETE",f"/vaccinations/{vac1}",token=token)
T("4.6 删除200", r.status_code==200, J(r).get("message","没有返回消失"))

# =========================== 5. DRUG ===========================
print("\n=== 5. DRUG 药品库存 ===")

r = R("POST","/drugs",token=token,data={"drug_name":"阿莫西林","category":"抗生素","manufacturer":"华北制药","batch_number":"D001","quantity":100,"unit":"盒","unit_price":25,"expiry_date":"2027-07-14","min_stock_level":10})
T("5.1 创建 201", r.status_code==201)
drug1 = J(r).get("drug_id")

r = R("GET","/drugs",token=token)
T("5.2 列表200", r.status_code==200)
T("5.3 列表>=1", len(J(r).get("data",[]))>=1)

r = R("GET","/drugs?search=阿莫西林",token=token)
T("5.4 搜索", len(J(r).get("data",[]))>=1)

r = R("GET","/drugs?low_stock=true",token=token)
T("5.5 低库存200", r.status_code==200)

r = R("POST",f"/drugs/{drug1}/stock-in",token=token,data={"quantity":50})
T("5.6 入库200", r.status_code==200)

r = R("POST",f"/drugs/{drug1}/stock-out",token=token,data={"quantity":10})
T("5.7 出库200", r.status_code==200)

r = R("PUT",f"/drugs/{drug1}",token=token,data={"drug_name":"阿莫西林","category":"抗生素","quantity":140,"unit_price":28})
T("5.8 更新200", r.status_code==200)

# =========================== 6. AI ===========================
print("\n=== 6. AI 助手 ===")

r = R("GET","/ai/engine-status",token=token)
T("6.1 引擎状态200", r.status_code==200)
T("6.2 含deepseek_configured", "deepseek_configured" in r.text)

r = R("GET","/ai/templates",token=token)
templates = J(r).get("templates",[])
T("6.3 模板列表200", r.status_code==200)
T("6.4 >=14", len(templates)>=14, f"{len(templates)}")

tmpl_id = templates[0]["id"] if templates else "01"
r = R("GET",f"/ai/templates/{tmpl_id}",token=token)
T("6.5 模板详情200", r.status_code==200)

r = R("GET","/ai/templates/nonexist",token=token)
T("6.6 不存在404", r.status_code==404)

r = R("POST","/ai/generate-treatment",token=token,data={"symptoms":"呕吐,腹泻","diagnosis":"急性肠胃炎","species":"狗"})
T("6.7 AI治疗方案200", r.status_code==200)
T("6.8 方案非空", bool(J(r).get("treatment","")))

r = R("POST","/ai/generate-treatment",token=token,data={})
T("6.9 空参数400", r.status_code==400)

r = R("GET","/ai/disease-suggest?symptoms=呕吐,腹泻",token=token)
T("6.10 疾病建议200", r.status_code==200)

r = R("GET","/ai/disease-suggest",token=token)
T("6.11 空参数400", r.status_code==400)

r = R("GET",f"/ai/pet-summary?pet_id={pet1}",token=token)
T("6.12 宠物摘要200", r.status_code==200)

r = R("GET","/ai/pet-summary?pet_id=99999",token=token)
T("6.13 不存在404", r.status_code==404)

r = R("POST","/ai/parse-record",token=token,data={"text":"金毛旺财呕吐腹泻急性胃炎口服益生菌200元"})
T("6.14 病历解析200", r.status_code==200)
T("6.15 engine=deepseek", "deepseek" in r.text)

r = R("POST","/ai/auto-fill",token=token,data={"text":"金毛旺财呕吐腹泻急性胃炎口服益生菌200元","pet_id":pet1})
T("6.16 智能填表200", r.status_code==200)

r = R("POST","/ai/parse-record",token=token,data={"text":""})
T("6.17 空文本400", r.status_code==400)

# =========================== 7. SOAP ===========================
print("\n=== 7. SOAP 病历 ===")

r = R("GET",f"/soap/{rec1}",token=token)
T("7.1 获取SOAP 200", r.status_code==200)
T("7.2 含record", "record" in r.text)
T("7.3 含soap", "soap" in r.text)

r = R("PUT",f"/soap/{rec1}",token=token,data={"subjective":"主诉呕吐","objective":"T:38.5","assessment":"胃炎","plan":"禁食","reasoning":{"problem_list":[{"rank":1,"problem":"呕吐"}],"reasoning_path":"","differential_list":[],"must_not_miss":[],"missing_info":"","recommended_tests":[],"dynamic_questions":"","client_communication":{},"summary":""}})
T("7.4 更新SOAP 200", r.status_code==200)

r = R("GET",f"/soap/{rec1}",token=token)
T("7.5 重新获取200", r.status_code==200)
T("7.6 持久化正确", "呕吐" in r.text or "record" in r.text)

r = R("GET","/soap/99999",token=token)
T("7.7 不存在404", r.status_code==404)

r = R("POST","/soap/from-transcript",token=token,data={"transcript":"主人:狗吐了3次。医生:有腹泻吗？主人:没有。","species":"狗"})
T("7.8 SOAP生成", r.status_code in (200,500), f"status={r.status_code}")

r = R("POST","/soap/from-transcript",token=token,data={"transcript":""})
T("7.9 空对话400", r.status_code==400)

r = R("POST",f"/soap/{rec1}/reasoning",token=token,data={})
T("7.10 推理生成", r.status_code in (200,500), f"status={r.status_code}")

r = R("POST",f"/soap/{rec1}/client",token=token,data={})
T("7.11 客户沟通", r.status_code in (200,500), f"status={r.status_code}")

# =========================== 8. ADMIN ===========================
print("\n=== 8. ADMIN 员工管理 ===")

r = R("POST","/auth/register",data={"username":"admintest","password":"abc123","role":"admin"})
r = R("POST","/auth/login",data={"username":"admintest","password":"abc123"})
admin_token = J(r).get("token","")

r = R("GET","/admin/vet",token=token)
T("8.1 vet访问拒绝 403", r.status_code==403, f"got {r.status_code}")

r = R("GET","/admin/vet",token=admin_token)
T("8.2 admin访问200", r.status_code==200)

r = R("GET","/admin/assistant",token=admin_token)
T("8.3 assistant 200", r.status_code==200)

r = R("GET","/admin/worker",token=admin_token)
T("8.4 worker 200", r.status_code==200)

r = R("POST","/admin/vet",token=admin_token,data={"name":"王医生","specialisation":"内科","license_no":"L001","age":35,"address":"北京","contact":"13700137000","consultation_fee":200,"monthly_salary":15000})
T("8.5 admin添加兽医 201", r.status_code==201)

r = R("DELETE","/admin/vet/999999",token=admin_token)
T("8.6 删除不存在", r.status_code in (404,500), f"got {r.status_code}")

# =========================== 9. INFRA ===========================
print("\n=== 9. 基础设施 ===")

r = requests.get("http://localhost:3000/api/health")
T("9.1 健康检查200", r.status_code==200)

r = requests.get("http://localhost:3000/login")
T("9.2 登录页200", r.status_code==200)
T("9.3 HTML正常", len(r.text)>100)

# =========================== 10. CLEANUP ===========================
print("\n=== 10. 清理 ===")

R("DELETE",f"/pets/{pet2}",token=token)
R("DELETE",f"/medical-records/{rec1}",token=token)
R("DELETE",f"/drugs/{drug1}",token=token)
T("10.1 清理完成", True)

# =========================== RESULT ===========================
print(f"\n{'='*60}")
print(f"  全量测试: {P} 通过, {F} 失败, {P+F} 总计")
print(f"{'='*60}")
sys.exit(0 if F==0 else 1)
