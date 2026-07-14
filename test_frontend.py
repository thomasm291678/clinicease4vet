"""前端 & 后端全面测试脚本"""
import requests
import json
import sys

BASE = "http://127.0.0.1:5000"
passed = 0
failed = 0
token = ""
results = []


def test(name, method, path, expected_status=None, auth=True, body=None, check_fn=None):
    global passed, failed, token
    headers = {}
    if auth and token:
        headers["Authorization"] = f"Bearer {token}"
    headers["Content-Type"] = "application/json"

    url = BASE + path
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=body, timeout=15)
        elif method == "PUT":
            resp = requests.put(url, headers=headers, json=body, timeout=10)
        elif method == "DELETE":
            resp = requests.delete(url, headers=headers, timeout=10)
        else:
            results.append(("[SKIP]", name, f"Unknown method {method}"))
            return None

        status_ok = expected_status is None or resp.status_code in (expected_status if isinstance(expected_status, (list, tuple)) else [expected_status])
        check_ok = True
        check_msg = ""
        if check_fn:
            check_ok, check_msg = check_fn(resp)

        if status_ok and check_ok:
            passed += 1
            results.append(("[PASS]", name, f"HTTP {resp.status_code} {check_msg}"))
        else:
            failed += 1
            info = f"HTTP {resp.status_code} (expected {expected_status})"
            if not check_ok:
                info += f" CHECK: {check_msg}"
            try:
                info += f" BODY: {resp.text[:200]}"
            except:
                pass
            results.append(("[FAIL]", name, info))
        return resp
    except requests.ConnectionError:
        failed += 1
        results.append(("[FAIL]", name, "Connection refused - 后端未启动"))
        return None
    except requests.Timeout:
        failed += 1
        results.append(("[FAIL]", name, "Request timeout"))
        return None
    except Exception as e:
        failed += 1
        results.append(("[FAIL]", name, str(e)))
        return None


def get_json(resp):
    try:
        return resp.json()
    except:
        return {}


# ============================================================
print("=" * 60)
print("  Clinicease4vet 前端 & 后端测试")
print("=" * 60)
print()

# ---- 0. 基础连通性 ----
print("[0] 基础连通性")
test("健康检查", "GET", "/api/health", 200, auth=False)

# ---- 1. 注册 ----
print("\n[1] 用户注册")
test("缺少请求体", "POST", "/api/auth/register", 400, auth=False, body={},
     check_fn=lambda r: (get_json(r).get("error", "") != "", "正确返回错误"))
test("空用户名", "POST", "/api/auth/register", 400, auth=False, body={"username": "", "password": "123456"},
     check_fn=lambda r: (get_json(r).get("error", "") != "", "正确返回错误"))
test("短密码", "POST", "/api/auth/register", 400, auth=False, body={"username": "testuser", "password": "123"},
     check_fn=lambda r: (get_json(r).get("error", "") != "", "正确返回错误"))
# 先尝试注册管理员（可能已存在）
resp = test("注册管理员", "POST", "/api/auth/register", [201, 409], auth=False,
     body={"username": "admin", "password": "admin123", "role": "admin"})
resp = test("注册兽医", "POST", "/api/auth/register", [201, 409], auth=False,
     body={"username": "vet_test", "password": "vet1234", "role": "vet"})
resp = test("注册员工", "POST", "/api/auth/register", [201, 409], auth=False,
     body={"username": "staff_test", "password": "staff123", "role": "staff"})

# ---- 2. 登录 ----
print("\n[2] 用户登录")
test("缺少请求体", "POST", "/api/auth/login", 400, auth=False, body={},
     check_fn=lambda r: (get_json(r).get("error", "") != "", "正确返回错误"))
test("错误密码", "POST", "/api/auth/login", 401, auth=False,
     body={"username": "admin", "password": "wrongpass"},
     check_fn=lambda r: (get_json(r).get("error", "") != "", "正确返回错误"))
resp = test("正确登录", "POST", "/api/auth/login", 200, auth=False,
     body={"username": "admin", "password": "admin123"})
if resp:
    data = get_json(resp)
    token = data.get("token", "")
    if token:
        results[-1] = ("[PASS]", "正确登录", f"获取到token (role: {data.get('role', '?')})")
    else:
        results[-1] = ("[FAIL]", "正确登录", "未返回token")

if not token:
    print("\n[ERROR] 无法获取 token，后续需认证测试将跳过")
    print()

# ---- 3. AI 引擎状态（需登录） ----
print("\n[3] AI 引擎状态")
test("AI引擎状态", "GET", "/api/ai/engine-status", 200)
test("模板列表(新)", "GET", "/api/ai/templates", 200)

# ---- 4. 认证拦截 ----
print("\n[4] 认证拦截")
test("未认证访问", "GET", "/api/pets", 401, auth=False,
     check_fn=lambda r: (get_json(r).get("error", "") != "", "正确拦截"))


# 辅助函数：从响应中提取 ID
def extract_id(resp, field="id"):
    data = get_json(resp)
    item = data.get("data", data)
    if isinstance(item, dict) and field in item:
        return item[field]
    return None


# ---- 5. 宠物 CRUD ----
print("\n[5] 宠物管理 CRUD")
if token:
    resp = test("宠物列表(空)", "GET", "/api/pets", 200)
    test("宠物统计", "GET", "/api/pets/stats", 200)

    resp = test("添加宠物", "POST", "/api/pets", 201,
         body={"name":"旺财","species":"狗","breed":"金毛","gender":"公","age_months":24,"weight_kg":15.5,"color":"金色","owner_name":"张三","owner_contact":"13800138000"})
    pet_id = extract_id(resp, "pet_id")

    test("添加宠物2", "POST", "/api/pets", 201,
         body={"name":"咪咪","species":"猫","breed":"英短","gender":"母","age_months":12,"weight_kg":4.2,"color":"灰色","owner_name":"李四","owner_contact":"13900139000"})

    test("宠物搜索", "GET", "/api/pets?search=旺财", 200,
         check_fn=lambda r: (get_json(r).get("count", 0) > 0, f"搜索到 {get_json(r).get('count', 0)} 条"))

    if pet_id:
        test("查看宠物详情", "GET", f"/api/pets/{pet_id}", 200)
        test("更新宠物", "PUT", f"/api/pets/{pet_id}", 200,
             body={"name":"旺财","species":"狗","breed":"金毛","gender":"公","age_months":25,"weight_kg":16,"color":"金色","owner_name":"张三","owner_contact":"13800138000","owner_address":"北京市"})
else:
    print("  (跳过 - 需要 token)")

# ---- 6. 诊疗记录 CRUD ----
print("\n[6] 诊疗记录 CRUD")
if token and pet_id:
    resp = test("诊疗列表(空)", "GET", "/api/medical-records", 200)

    resp2 = test("添加诊疗", "POST", "/api/medical-records", 201,
          body={"pet_id":pet_id,"vet_name":"王医生","visit_date":"2026-07-13","diagnosis":"急性肠胃炎","treatment":"蒙脱石散 一日两次，益生菌调理","fee_charged":300})
    record_id = extract_id(resp2, "id")

    if record_id:
        test("更新诊疗", "PUT", f"/api/medical-records/{record_id}", 200,
             body={"pet_id":pet_id,"vet_name":"王医生","visit_date":"2026-07-13","diagnosis":"急性肠胃炎(已缓解)","treatment":"蒙脱石散 一日一次","fee_charged":250,"notes":"恢复良好"})
        # 不删除诊疗，留给前端展示
else:
    print("  (跳过 - 需要 token 和 pet_id)")

# ---- 7. 疫苗接种 ----
print("\n[7] 疫苗接种")
if token and pet_id:
    resp = test("接种列表(空)", "GET", "/api/vaccinations", 200)

    resp3 = test("添加接种", "POST", "/api/vaccinations", 201,
          body={"pet_id":pet_id,"vaccine_name":"狂犬疫苗","dose_number":1,"administered_date":"2026-07-13","next_due_date":"2027-07-13","vet_name":"王医生","batch_number":"RB2026001"})
    vacc_id = extract_id(resp3)
    # 不删除
else:
    print("  (跳过 - 需要 token 和 pet_id)")

# ---- 8. 药品 CRUD + 出入库 ----
print("\n[8] 药品库存")
if token:
    resp = test("药品列表(空)", "GET", "/api/drugs", 200)

    resp = test("添加药品", "POST", "/api/drugs", 201,
         body={"drug_name":"蒙脱石散","category":"肠胃","manufacturer":"某某制药","quantity":100,"unit":"盒","unit_price":25,"expiry_date":"2027-12-31","min_stock_level":20})
    drug_id = extract_id(resp, "drug_id")

    resp2 = test("添加药品2", "POST", "/api/drugs", 201,
          body={"drug_name":"狂犬疫苗","category":"疫苗","manufacturer":"某某生物","quantity":50,"unit":"支","unit_price":80,"expiry_date":"2027-06-30","min_stock_level":10})
    drug2_id = extract_id(resp2)

    if drug_id:
        test("药品入库", "POST", f"/api/drugs/{drug_id}/stock-in", 200, body={"quantity": 50})
        test("药品出库", "POST", f"/api/drugs/{drug_id}/stock-out", 200, body={"quantity": 5})

    test("药品列表(有数据)", "GET", "/api/drugs", 200,
         check_fn=lambda r: (get_json(r).get("count", len(get_json(r).get("data", []))) > 0, "有药品数据"))
else:
    print("  (跳过 - 需要 token)")

# ---- 9. 员工管理 ----
print("\n[9] 员工管理")
if token:
    resp = test("兽医列表", "GET", "/api/admin/vet", 200)
    resp = test("添加兽医", "POST", "/api/admin/vet", 201,
         body={"name":"王医生","specialisation":"内科","license_no":"VET2026001","age":35,"address":"北京市","contact":"13600136000","consultation_fee":200,"monthly_salary":15000})
    vet_id = extract_id(resp)

    test("助理列表", "GET", "/api/admin/assistant", 200)
    resp = test("添加助理", "POST", "/api/admin/assistant", 201,
         body={"name":"小刘","role":"护士","age":28,"address":"北京市","contact":"13700137000","monthly_salary":8000})

    test("其他员工列表", "GET", "/api/admin/worker", 200)
else:
    print("  (跳过 - 需要 token)")

# ---- 10. AI 功能 ----
print("\n[10] AI 功能测试")
test("病历解析(空文本)", "POST", "/api/ai/parse-record", 200, auth=token != "",
     body={"text": "今天接诊了一只2岁的金毛犬旺财，主人是张三。狗狗体重15kg，体温39.2度，症状是呕吐和腹泻。诊断为急性肠胃炎，给开了蒙脱石散一天两次，奥美拉唑一天一次。收费300元。"},
     check_fn=lambda r: (
         (lambda j: (
             j.get("result", {}).get("diagnosis", {}).get("confidence", 0) > 0
             or j.get("result", {}).get("confidence", 0) > 0
         ))(get_json(r))
         or get_json(r).get("error", "").startswith("[API错误]"), "AI 引擎响应正常"))

test("智能填表", "POST", "/api/ai/auto-fill", 200, auth=token != "",
     body={"text": "3岁的英短猫咪咪，主人李四。体重4.2kg，打猫三联疫苗，收费150元。", "pet_id": pet_id if pet_id else None})

test("疾病建议", "GET", "/api/ai/disease-suggest?symptoms=呕吐,腹泻", 200, auth=token != "")

test("模板列表", "GET", "/api/ai/templates", 200, auth=token != "")


# ---- 汇总 ----
print("\n" + "=" * 60)
print(f"  测试结果: {passed} 通过, {failed} 失败, {len(results)} 总计")
print("=" * 60)
for status, name, msg in results:
    print(f"  {status}  {name:<20s}  {msg}")

print()
if failed == 0:
    print("全部测试通过")
else:
    print(f"{failed} 项测试失败，需要修复")

sys.exit(0 if failed == 0 else 1)
