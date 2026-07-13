"""
PetCare 宠物医院管理客户端
用法: python client.py [--host HOST] [--port PORT]
"""

import argparse
import requests
from prettytable import PrettyTable

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000


class PetCareClient:
    """宠物医院管理系统客户端"""

    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT):
        self.base_url = f"http://{host}:{port}"
        self.token = None
        self.user_role = None
        self.session = requests.Session()

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _get(self, path, params=None):
        return self.session.get(f"{self.base_url}{path}", params=params, headers=self._headers())

    def _post(self, path, data=None):
        return self.session.post(f"{self.base_url}{path}", json=data, headers=self._headers())

    def _put(self, path, data=None):
        return self.session.put(f"{self.base_url}{path}", json=data, headers=self._headers())

    def _delete(self, path, data=None):
        kwargs = {"headers": self._headers()}
        if data is not None:
            kwargs["json"] = data
        return self.session.delete(f"{self.base_url}{path}", **kwargs)

    def _safe_int(self, prompt):
        try:
            return int(input(prompt) or 0)
        except ValueError:
            print("请输入有效数字！")
            return None

    # ======================== 认证 ========================

    def register(self):
        print("\n" + "=" * 50)
        print("********** 用户注册 **********")
        print("=" * 50)
        username = input("用户名: ").strip()
        password = input("密码 (至少6位): ").strip()
        print("角色: 1-admin(管理员)  2-vet(兽医)  3-staff(员工)")
        role_map = {"1": "admin", "2": "vet", "3": "staff"}
        role = role_map.get(input("请选择: ").strip(), "staff")

        resp = self._post("/api/auth/register", {"username": username, "password": password, "role": role})
        data = resp.json()
        if resp.status_code == 201:
            print(f"\n✅ {data['message']} (角色: {data['role']})")
        else:
            print(f"\n❌ {data.get('error', '注册失败')}")
        input("\n按任意键继续...")

    def login(self):
        print("\n" + "=" * 50)
        print("********** 用户登录 **********")
        print("=" * 50)
        username = input("用户名: ").strip()
        password = input("密码: ").strip()

        resp = self._post("/api/auth/login", {"username": username, "password": password})
        data = resp.json()
        if resp.status_code == 200:
            self.token = data["token"]
            self.user_role = data.get("role", "staff")
            print(f"\n✅ {data['message']} (角色: {self.user_role})")
            return True
        else:
            print(f"\n❌ {data.get('error', '登录失败')}")
            input("\n按任意键继续...")
            return False

    # ======================== 宠物管理 ========================

    def pet_menu(self):
        while True:
            print("""
        *-----------------------------------*
        |         🐾 宠物管理                |
        *-----------------------------------*
        | 1. 查看全部宠物                    |
        | 2. 按物种筛选                      |
        | 3. 搜索宠物                        |
        | 4. 登记新宠物                      |
        | 5. 更新宠物信息                    |
        | 6. 删除宠物记录                    |
        | 7. 宠物统计信息                    |
        | 8. 返回上级                        |
        *-----------------------------------*""")
            c = input("请选择: ").strip()

            if c == "1":
                self._list_pets()
            elif c == "2":
                self._list_pets_by_species()
            elif c == "3":
                self._search_pets()
            elif c == "4":
                self._add_pet()
            elif c == "5":
                self._update_pet()
            elif c == "6":
                self._delete_pet()
            elif c == "7":
                self._pet_stats()
            elif c == "8":
                break

    def _list_pets(self):
        resp = self._get("/api/pets")
        data = resp.json()
        if not data["data"]:
            print("暂无宠物记录。"); return

        table = PrettyTable(["ID", "名称", "物种", "品种", "性别", "月龄", "体重kg", "主人", "联系方式"])
        for r in data["data"]:
            table.add_row([r["id"], r["name"], r["species"], r.get("breed", ""),
                           r.get("gender", ""), r.get("age_months", ""),
                           r.get("weight_kg", ""), r.get("owner_name", ""),
                           r.get("owner_contact", "")])
        print(table); print(f"总计: {data['count']} 只宠物")

    def _list_pets_by_species(self):
        species = input("请输入物种 (如: 猫/狗/兔): ").strip()
        resp = self._get("/api/pets", {"species": species})
        data = resp.json()
        print(f"\n物种 '{species}': {data['count']} 条记录")
        self._list_pets()

    def _search_pets(self):
        kw = input("搜索关键词 (名称/品种/主人): ").strip()
        resp = self._get("/api/pets", {"search": kw})
        data = resp.json()
        print(f"\n搜索 '{kw}': {data['count']} 条结果")
        self._list_pets()

    def _add_pet(self):
        print("\n--- 登记新宠物 ---")
        name = input("宠物名称: ").strip()
        if not name: print("名称不能为空！"); return
        species = input("物种 (如: 猫/狗/兔/鸟): ").strip()
        if not species: print("物种不能为空！"); return
        owner = input("主人姓名: ").strip()
        if not owner: print("主人不能为空！"); return

        payload = {
            "name": name, "species": species,
            "breed": input("品种: ").strip(),
            "gender": input("性别 (公/母): ").strip(),
            "age_months": self._safe_int("月龄: "),
            "weight_kg": input("体重(kg): ").strip() or 0,
            "color": input("毛色: ").strip(),
            "owner_name": owner,
            "owner_contact": input("主人联系方式: ").strip(),
            "owner_address": input("主人地址: ").strip(),
        }
        if payload["age_months"] is None: return

        resp = self._post("/api/pets", payload)
        d = resp.json()
        print(f"✅ {d.get('message', d.get('error'))} (ID: {d.get('pet_id', '')})" if resp.status_code == 201 else f"❌ {d.get('error')}")

    def _update_pet(self):
        pet_id = self._select_pet("更新")
        if not pet_id: return
        print("输入新值，留空则不修改:")
        payload = {k: v for k, v in {
            "name": input("宠物名称: ").strip(),
            "species": input("物种: ").strip(),
            "breed": input("品种: ").strip(),
            "gender": input("性别: ").strip(),
            "owner_name": input("主人姓名: ").strip(),
            "owner_contact": input("主人联系方式: ").strip(),
            "owner_address": input("主人地址: ").strip(),
        }.items() if v}
        a = self._safe_int("月龄: ");
        if a is not None: payload["age_months"] = a
        w = input("体重(kg): ").strip()
        if w: payload["weight_kg"] = float(w)

        resp = self._put(f"/api/pets/{pet_id}", payload)
        d = resp.json()
        print(f"{'✅' if resp.status_code == 200 else '❌'} {d.get('message', d.get('error'))}")

    def _delete_pet(self):
        pet_id = self._select_pet("删除")
        if not pet_id: return
        if input("⚠️ 确认删除？(将同时删除关联诊疗和疫苗记录) (y/n): ").strip().lower() != "y":
            print("已取消。"); return
        resp = self._delete(f"/api/pets/{pet_id}")
        d = resp.json()
        print(f"{'✅' if resp.status_code == 200 else '❌'} {d.get('message', d.get('error'))}")

    def _pet_stats(self):
        resp = self._get("/api/pets/stats")
        d = resp.json()
        print(f"\n总宠物数: {d['total']}")
        if d["by_species"]:
            table = PrettyTable(["物种", "数量"])
            for s in d["by_species"]:
                table.add_row([s["species"], s["count"]])
            print(table)

    def _select_pet(self, action):
        resp = self._get("/api/pets")
        data = resp.json()
        if not data["data"]: print("暂无宠物记录。"); return None
        print(f"\n请选择要{action}的宠物:")
        for r in data["data"]:
            print(f"  ID:{r['id']} | {r['name']} ({r['species']}) | 主人: {r.get('owner_name', '')}")
        try:
            return int(input("\n输入ID: "))
        except ValueError:
            print("无效ID。"); return None

    # ======================== 诊疗记录 ========================

    def medical_menu(self):
        while True:
            print("""
        *-----------------------------------*
        |         📋 诊疗记录管理            |
        *-----------------------------------*
        | 1. 查看全部诊疗记录                |
        | 2. 按宠物查看诊疗历史              |
        | 3. 新增诊疗记录                    |
        | 4. 更新诊疗记录                    |
        | 5. 删除诊疗记录                    |
        | 6. 返回上级                        |
        *-----------------------------------*""")
            c = input("请选择: ").strip()

            if c == "1": self._list_medical()
            elif c == "2": self._medical_by_pet()
            elif c == "3": self._add_medical()
            elif c == "4": self._update_medical()
            elif c == "5": self._delete_medical()
            elif c == "6": break

    def _list_medical(self):
        resp = self._get("/api/medical-records")
        data = resp.json()
        if not data["data"]: print("暂无诊疗记录。"); return
        table = PrettyTable(["ID", "宠物", "兽医", "就诊日期", "诊断", "治疗", "费用", "复诊日期"])
        for r in data["data"]:
            table.add_row([r["id"], f"{r.get('pet_name','')}({r.get('species','')})",
                           r.get("vet_name", ""), r["visit_date"], r.get("diagnosis", ""),
                           r.get("treatment", ""), r.get("fee_charged", ""),
                           r.get("follow_up_date", "")])
        print(table); print(f"总计: {data['count']} 条记录")

    def _medical_by_pet(self):
        pet_id = self._select_pet("查看诊疗记录")
        if not pet_id: return
        resp = self._get("/api/medical-records", {"pet_id": pet_id})
        data = resp.json()
        if not data["data"]: print("该宠物暂无诊疗记录。"); return
        print(f"\n诊疗历史 ({data['count']} 条):")
        table = PrettyTable(["ID", "日期", "兽医", "诊断", "治疗", "费用"])
        for r in data["data"]:
            table.add_row([r["id"], r["visit_date"], r.get("vet_name", ""),
                           r.get("diagnosis", ""), r.get("treatment", ""),
                           r.get("fee_charged", "")])
        print(table)

    def _add_medical(self):
        pet_id = self._select_pet("添加诊疗记录")
        if not pet_id: return
        print("\n--- 新增诊疗记录 ---")
        diagnosis = input("诊断结果: ").strip()
        if not diagnosis: print("诊断结果不能为空！"); return
        visit_date = input("就诊日期 (YYYY-MM-DD): ").strip()
        if not visit_date: print("就诊日期不能为空！"); return

        f = self._safe_int("费用: ")
        if f is None: return
        payload = {
            "pet_id": pet_id, "vet_name": input("兽医姓名: ").strip(),
            "visit_date": visit_date, "diagnosis": diagnosis,
            "treatment": input("治疗方案: ").strip(),
            "notes": input("备注: ").strip(),
            "follow_up_date": input("复诊日期 (YYYY-MM-DD, 可空): ").strip() or None,
            "fee_charged": f,
        }
        resp = self._post("/api/medical-records", payload)
        d = resp.json()
        print(f"{'✅' if resp.status_code == 201 else '❌'} {d.get('message', d.get('error'))}")

    def _update_medical(self):
        self._list_medical()
        try: rid = int(input("\n输入要更新的诊疗记录ID: "))
        except ValueError: print("无效ID。"); return
        print("输入新值，留空则不修改:")
        payload = {k: v for k, v in {
            "vet_name": input("兽医姓名: ").strip(),
            "visit_date": input("就诊日期: ").strip(),
            "diagnosis": input("诊断: ").strip(),
            "treatment": input("治疗: ").strip(),
            "notes": input("备注: ").strip(),
            "follow_up_date": input("复诊日期: ").strip() or None,
        }.items() if v}
        f = self._safe_int("费用: ")
        if f is not None: payload["fee_charged"] = f
        resp = self._put(f"/api/medical-records/{rid}", payload)
        print(f"{'✅' if resp.status_code == 200 else '❌'} {resp.json().get('message', resp.json().get('error'))}")

    def _delete_medical(self):
        self._list_medical()
        try: rid = int(input("\n输入要删除的诊疗记录ID: "))
        except ValueError: print("无效ID。"); return
        if input("确认删除? (y/n): ").strip().lower() != "y": print("已取消。"); return
        resp = self._delete(f"/api/medical-records/{rid}")
        print(f"{'✅' if resp.status_code == 200 else '❌'} {resp.json().get('message', resp.json().get('error'))}")

    # ======================== 疫苗接种 ========================

    def vaccine_menu(self):
        while True:
            print("""
        *-----------------------------------*
        |         💉 疫苗接种管理            |
        *-----------------------------------*
        | 1. 查看全部接种记录                |
        | 2. 按宠物查看接种历史              |
        | 3. 到期接种提醒 (30天内)           |
        | 4. 新增接种记录                    |
        | 5. 删除接种记录                    |
        | 6. 返回上级                        |
        *-----------------------------------*""")
            c = input("请选择: ").strip()

            if c == "1": self._list_vaccines()
            elif c == "2": self._vaccine_by_pet()
            elif c == "3": self._vaccine_reminder()
            elif c == "4": self._add_vaccine()
            elif c == "5": self._delete_vaccine()
            elif c == "6": break

    def _list_vaccines(self):
        resp = self._get("/api/vaccinations")
        data = resp.json()
        if not data["data"]: print("暂无接种记录。"); return
        table = PrettyTable(["ID", "宠物", "疫苗名称", "剂次", "接种日期", "下次接种", "兽医"])
        for r in data["data"]:
            table.add_row([r["id"], f"{r.get('pet_name','')}", r["vaccine_name"],
                           r.get("dose_number", ""), r["administered_date"],
                           r.get("next_due_date", ""), r.get("vet_name", "")])
        print(table); print(f"总计: {data['count']} 条")

    def _vaccine_by_pet(self):
        pet_id = self._select_pet("查看接种记录")
        if not pet_id: return
        resp = self._get("/api/vaccinations", {"pet_id": pet_id})
        data = resp.json()
        if not data["data"]: print("该宠物暂无接种记录。"); return
        print(f"\n接种历史 ({data['count']} 条):")
        table = PrettyTable(["ID", "疫苗", "剂次", "接种日期", "下次接种", "批次号"])
        for r in data["data"]:
            table.add_row([r["id"], r["vaccine_name"], r.get("dose_number", ""),
                           r["administered_date"], r.get("next_due_date", ""),
                           r.get("batch_number", "")])
        print(table)

    def _vaccine_reminder(self):
        resp = self._get("/api/vaccinations", {"upcoming": "true"})
        data = resp.json()
        print(f"\n🔔 30天内到期接种提醒: {data['count']} 条")
        if data["data"]:
            table = PrettyTable(["宠物", "主人", "联系方式", "疫苗", "到期日"])
            for r in data["data"]:
                table.add_row([r.get("pet_name", ""), r.get("owner_name", ""),
                               r.get("owner_contact", ""), r["vaccine_name"], r["next_due_date"]])
            print(table)

    def _add_vaccine(self):
        pet_id = self._select_pet("添加接种记录")
        if not pet_id: return
        print("\n--- 新增接种记录 ---")
        name = input("疫苗名称: ").strip()
        if not name: print("疫苗名称不能为空！"); return
        date = input("接种日期 (YYYY-MM-DD): ").strip()
        if not date: print("接种日期不能为空！"); return

        d = self._safe_int("剂次: ")
        if d is None: return
        payload = {
            "pet_id": pet_id, "vaccine_name": name, "dose_number": d,
            "administered_date": date,
            "next_due_date": input("下次接种日期 (YYYY-MM-DD, 可空): ").strip() or None,
            "vet_name": input("兽医姓名: ").strip(),
            "batch_number": input("批次号: ").strip(),
            "notes": input("备注: ").strip(),
        }
        resp = self._post("/api/vaccinations", payload)
        d2 = resp.json()
        print(f"{'✅' if resp.status_code == 201 else '❌'} {d2.get('message', d2.get('error'))}")

    def _delete_vaccine(self):
        self._list_vaccines()
        try: vid = int(input("\n输入要删除的记录ID: "))
        except ValueError: print("无效ID。"); return
        if input("确认删除? (y/n): ").strip().lower() != "y": print("已取消。"); return
        resp = self._delete(f"/api/vaccinations/{vid}")
        print(f"{'✅' if resp.status_code == 200 else '❌'} {resp.json().get('message', resp.json().get('error'))}")

    # ======================== 药品库存 ========================

    def drug_menu(self):
        while True:
            print("""
        *-----------------------------------*
        |         💊 药品库存管理            |
        *-----------------------------------*
        | 1. 查看全部药品                    |
        | 2. 搜索药品                        |
        | 3. 低库存预警                      |
        | 4. 已过期药品                      |
        | 5. 添加新药品                      |
        | 6. 药品入库                        |
        | 7. 药品出库                        |
        | 8. 更新药品信息                    |
        | 9. 删除药品                        |
        | 0. 返回上级                        |
        *-----------------------------------*""")
            c = input("请选择: ").strip()

            if c == "1": self._list_drugs()
            elif c == "2": self._search_drugs()
            elif c == "3": self._low_stock_alert()
            elif c == "4": self._expired_drugs()
            elif c == "5": self._add_drug()
            elif c == "6": self._drug_stock_in()
            elif c == "7": self._drug_stock_out()
            elif c == "8": self._update_drug()
            elif c == "9": self._delete_drug()
            elif c == "0": break

    def _list_drugs(self):
        resp = self._get("/api/drugs")
        data = resp.json()
        if not data["data"]: print("暂无药品记录。"); return
        table = PrettyTable(["ID", "药品名称", "类别", "库存", "单位", "单价", "有效期", "最低库存"])
        for r in data["data"]:
            alert = " ⚠️" if r["quantity"] <= r.get("min_stock_level", 5) else ""
            table.add_row([r["id"], r["drug_name"], r.get("category", ""),
                           f"{r['quantity']}{alert}", r.get("unit", ""),
                           r.get("unit_price", ""), r.get("expiry_date", ""),
                           r.get("min_stock_level", "")])
        print(table); print(f"总计: {data['count']} 种药品")

    def _search_drugs(self):
        kw = input("搜索药品关键词: ").strip()
        resp = self._get("/api/drugs", {"search": kw})
        data = resp.json()
        print(f"\n搜索 '{kw}': {data['count']} 条结果")
        self._list_drugs()

    def _low_stock_alert(self):
        resp = self._get("/api/drugs", {"low_stock": "true"})
        data = resp.json()
        print(f"\n⚠️ 低库存预警: {data['count']} 种药品库存不足")
        if data["data"]:
            table = PrettyTable(["ID", "药品名称", "当前库存", "最低库存", "建议"]
                                )
            for r in data["data"]:
                suggest = max(0, r["min_stock_level"] - r["quantity"])
                table.add_row([r["id"], r["drug_name"], r["quantity"], r.get("min_stock_level", ""), f"需补货 {suggest}"])
            print(table)

    def _expired_drugs(self):
        resp = self._get("/api/drugs", {"expired": "true"})
        data = resp.json()
        print(f"\n❌ 已过期药品: {data['count']} 种")
        if data["data"]:
            table = PrettyTable(["ID", "药品名称", "库存", "有效期", "批号"])
            for r in data["data"]:
                table.add_row([r["id"], r["drug_name"], r["quantity"],
                               r.get("expiry_date", ""), r.get("batch_number", "")])
            print(table)

    def _add_drug(self):
        print("\n--- 添加新药品 ---")
        name = input("药品名称: ").strip()
        if not name: print("药品名称不能为空！"); return
        qty = self._safe_int("初始库存: ")
        if qty is None: return
        price = input("单价: ").strip() or 0

        payload = {
            "drug_name": name, "category": input("类别: ").strip(),
            "manufacturer": input("生产厂家: ").strip(),
            "batch_number": input("批号: ").strip(),
            "quantity": qty, "unit": input("单位 (默认:瓶): ").strip() or "瓶",
            "unit_price": float(price),
            "expiry_date": input("有效期 (YYYY-MM-DD, 可空): ").strip() or None,
            "storage_condition": input("储存条件: ").strip(),
            "min_stock_level": self._safe_int("最低库存预警: ") or 5,
            "notes": input("备注: ").strip(),
        }
        resp = self._post("/api/drugs", payload)
        d = resp.json()
        print(f"{'✅' if resp.status_code == 201 else '❌'} {d.get('message', d.get('error'))}")

    def _select_drug(self, action):
        resp = self._get("/api/drugs")
        data = resp.json()
        if not data["data"]: print("暂无药品。"); return None
        print(f"\n请选择要{action}的药品:")
        for r in data["data"]:
            print(f"  ID:{r['id']} | {r['drug_name']} | 库存:{r['quantity']}{r.get('unit','')}")
        try: return int(input("\n输入ID: "))
        except ValueError: print("无效ID。"); return None

    def _drug_stock_in(self):
        drug_id = self._select_drug("入库")
        if not drug_id: return
        qty = self._safe_int("入库数量: ")
        if qty is None or qty <= 0: print("数量必须大于0！"); return
        resp = self._post(f"/api/drugs/{drug_id}/stock-in", {"quantity": qty})
        print(f"{'✅' if resp.status_code == 200 else '❌'} {resp.json().get('message', resp.json().get('error'))}")

    def _drug_stock_out(self):
        drug_id = self._select_drug("出库")
        if not drug_id: return
        qty = self._safe_int("出库数量: ")
        if qty is None or qty <= 0: print("数量必须大于0！"); return
        resp = self._post(f"/api/drugs/{drug_id}/stock-out", {"quantity": qty})
        print(f"{'✅' if resp.status_code == 200 else '❌'} {resp.json().get('message', resp.json().get('error'))}")

    def _update_drug(self):
        drug_id = self._select_drug("更新")
        if not drug_id: return
        print("输入新值，留空则不修改:")
        payload = {k: v for k, v in {
            "drug_name": input("药品名称: ").strip(),
            "category": input("类别: ").strip(),
            "manufacturer": input("生产厂家: ").strip(),
            "batch_number": input("批号: ").strip(),
            "unit": input("单位: ").strip(),
            "expiry_date": input("有效期: ").strip() or None,
            "storage_condition": input("储存条件: ").strip(),
            "notes": input("备注: ").strip(),
        }.items() if v}
        qty = self._safe_int("库存: ");
        if qty is not None: payload["quantity"] = qty
        p = input("单价: ").strip();
        if p: payload["unit_price"] = float(p)
        m = self._safe_int("最低库存: ");
        if m is not None: payload["min_stock_level"] = m
        resp = self._put(f"/api/drugs/{drug_id}", payload)
        print(f"{'✅' if resp.status_code == 200 else '❌'} {resp.json().get('message', resp.json().get('error'))}")

    def _delete_drug(self):
        drug_id = self._select_drug("删除")
        if not drug_id: return
        if input("确认删除? (y/n): ").strip().lower() != "y": print("已取消。"); return
        resp = self._delete(f"/api/drugs/{drug_id}")
        print(f"{'✅' if resp.status_code == 200 else '❌'} {resp.json().get('message', resp.json().get('error'))}")

    # ======================== 行政管理 ========================

    def admin_menu(self):
        while True:
            print("""
        *-----------------------------------*
        |         👥 行政管理                |
        *-----------------------------------*
        | 1. 查看兽医列表                    |
        | 2. 查看助理列表                    |
        | 3. 查看其他员工                    |
        | 4. 添加人员 (仅管理员)             |
        | 5. 删除人员 (仅管理员)             |
        | 6. 返回上级                        |
        *-----------------------------------*""")
            c = input("请选择: ").strip()

            if c == "1": self._list_staff("vet")
            elif c == "2": self._list_staff("assistant")
            elif c == "3": self._list_staff("worker")
            elif c == "4": self._add_staff()
            elif c == "5": self._delete_staff()
            elif c == "6": break

    def _list_staff(self, role):
        resp = self._get(f"/api/admin/{role}")
        data = resp.json()
        if not data["data"]: print(f"暂无{role}记录。"); return
        if role == "vet":
            table = PrettyTable(["ID", "姓名", "专科", "执照号", "年龄", "联系方式", "诊费", "月薪"])
            for r in data["data"]:
                table.add_row([r["id"], r["name"], r.get("specialisation", ""),
                               r.get("license_no", ""), r.get("age", ""),
                               r.get("contact", ""), r.get("consultation_fee", ""),
                               r.get("monthly_salary", "")])
        else:
            table = PrettyTable(["ID", "姓名", "角色", "年龄", "联系方式", "月薪"])
            for r in data["data"]:
                table.add_row([r["id"], r["name"], r.get("role", ""), r.get("age", ""),
                               r.get("contact", ""), r.get("monthly_salary", "")])
        print(table); print(f"总计: {data['count']} 条")

    def _add_staff(self):
        print("\n选择人员类型: 1-兽医  2-助理  3-其他员工")
        role_map = {"1": "vet", "2": "assistant", "3": "worker"}
        role = role_map.get(input("请选择: ").strip())
        if not role: print("无效选择。"); return

        name = input("姓名: ").strip()
        if not name: print("姓名不能为空！"); return
        payload = {"name": name}
        if role == "vet":
            payload["specialisation"] = input("专科: ").strip()
            payload["license_no"] = input("执照号: ").strip()
            f = self._safe_int("诊费: ")
            if f is not None: payload["consultation_fee"] = f
        else:
            payload["role"] = input("岗位: ").strip()
        a = self._safe_int("年龄: ");
        if a is not None: payload["age"] = a
        s = self._safe_int("月薪: ");
        if s is not None: payload["monthly_salary"] = s
        payload["address"] = input("地址: ").strip()
        payload["contact"] = input("联系方式: ").strip()

        resp = self._post(f"/api/admin/{role}", payload)
        d = resp.json()
        print(f"{'✅' if resp.status_code == 201 else '❌'} {d.get('message', d.get('error'))}")

    def _delete_staff(self):
        print("\n选择: 1-兽医  2-助理  3-其他员工")
        role = {"1": "vet", "2": "assistant", "3": "worker"}.get(input("请选择: ").strip())
        if not role: print("无效选择。"); return
        self._list_staff(role)
        try: sid = int(input("\n输入要删除的ID: "))
        except ValueError: print("无效ID。"); return
        if input("确认删除? (y/n): ").strip().lower() != "y": print("已取消。"); return
        resp = self._delete(f"/api/admin/{role}/{sid}")
        print(f"{'✅' if resp.status_code == 200 else '❌'} {resp.json().get('message', resp.json().get('error'))}")

    # ======================== AI 智能助手 ========================

    def ai_menu(self):
        """AI 智能助手主菜单"""
        import os
        iflytek_ready = bool(os.getenv("IFLYTEK_API_KEY") and os.getenv("IFLYTEK_APP_ID"))
        deepseek_ready = bool(os.getenv("DEEPSEEK_API_KEY") and os.getenv("DEEPSEEK_API_KEY") != "")

        engine_badge = "🧠 DeepSeek" if deepseek_ready else "📋 规则引擎"
        voice_label = "🎤 语音录入 (讯飞引擎)" if iflytek_ready else "🎤 语音录入 (Google引擎)"

        while True:
            print(f"""
        *-----------------------------------*
        |   🤖 AI 智能诊疗助手 [{engine_badge}]  |
        *-----------------------------------*
        | 1. {voice_label:<26} |
        | 2. ✏️ 文字输入病历 (AI 解析)       |
        | 3. 📋 获取病历模板                  |
        | 4. 🔍 根据症状建议疾病              |
        | 5. 🏥 一键自动填表 (文字→提交病历) |
        | 6. 返回上级                        |
        *-----------------------------------*""")
            c = input("请选择: ").strip()

            if c == "1": self._ai_voice_record()
            elif c == "2": self._ai_text_input()
            elif c == "3": self._ai_templates()
            elif c == "4": self._ai_disease_suggest()
            elif c == "5": self._ai_auto_fill_and_submit()
            elif c == "6": break

    def _ai_voice_record(self):
        """🎤 语音录入：录音 → 转文字 → AI 解析 → 预览"""
        print("\n" + "=" * 50)
        print("    🎤 AI 语音录入病历")
        print("=" * 50)
        print()
        print("录音功能需要系统麦克风支持。")
        print("如果录音不可用，可以直接粘贴文字。")
        print()

        # 尝试导入语音识别库
        text = self._record_audio()
        if not text:
            print("录音失败或无音频输入设备，请使用文字输入模式。")
            input("\n按任意键继续...")
            return

        print(f"\n📝 识别文本: {text}")
        self._ai_parse_and_preview(text)

    def _record_audio(self):
        """
        录音并转文字，支持三级降级策略:
          1. 科大讯飞 (IFLYTEK_* 环境变量已配置)
          2. Google STT (speech_recognition库)
          3. 手动文字输入
        """
        import builtins

        # ---- 检查讯飞凭证 ----
        import os
        iflytek_key = os.getenv("IFLYTEK_API_KEY", "")
        iflytek_ready = bool(iflytek_key and os.getenv("IFLYTEK_APP_ID") and os.getenv("IFLYTEK_API_SECRET"))

        # ---- 录音 ----
        pcm_data = None
        google_audio = None

        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                print("🎙️  正在调整麦克风环境噪音...")
                recognizer.adjust_for_ambient_noise(source, duration=0.8)
                print("🔴 开始录音，请描述病历 (说话结束后自动停止)...")
                try:
                    audio = recognizer.listen(source, timeout=10, phrase_time_limit=60)
                except sr.WaitTimeoutError:
                    print("⏰ 录音超时，未检测到语音输入。")
                    return input("\n请直接输入/粘贴病历文本: ").strip()

            # 保存 Google Audio 用于回退
            google_audio = audio

            # 提取 PCM 数据 (16kHz, 16bit) 用于讯飞
            try:
                pcm_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
            except Exception:
                pcm_data = None

        except ImportError:
            print("⚠️ 未安装 speech_recognition 库。")
            print("   安装命令: pip install speech_recognition pyaudio")
            return input("\n请直接输入/粘贴病历文本: ").strip()
        except OSError:
            print("⚠️ 未检测到麦克风设备。")
            return input("\n请直接输入/粘贴病历文本: ").strip()
        except Exception as e:
            print(f"⚠️ 录音初始化失败: {e}")
            return input("\n请直接输入/粘贴病历文本: ").strip()

        # ---- 策略1: 科大讯飞 (通过服务器端 API) ----
        if iflytek_ready and pcm_data:
            print("📡 正在使用科大讯飞引擎进行语音识别...")
            try:
                # 构造 WAV 文件上传
                import io
                import wave
                wav_buffer = io.BytesIO()
                with wave.open(wav_buffer, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(pcm_data)
                wav_buffer.seek(0)

                import requests as req
                resp = self.session.post(
                    f"{self.base_url}/api/ai/transcribe",
                    files={"audio": ("recording.wav", wav_buffer, "audio/wav")},
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=30,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    text = data.get("text", "")
                    engine = data.get("engine", "unknown")
                    print(f"✅ 讯飞识别完成 (引擎: {engine})")
                    if not text.startswith("[回退]") and not text.startswith("[错误]"):
                        return text
                    print(f"⚠️ 讯飞返回异常: {text}")
                else:
                    print(f"⚠️ 讯飞服务不可用 (HTTP {resp.status_code})")
            except Exception as e:
                print(f"⚠️ 讯飞识别失败: {e}")

        # ---- 策略2: Google STT (本地) ----
        if google_audio is not None:
            print("📡 正在使用 Google 引擎进行语音识别...")
            try:
                text = google_audio  # noqa - the audio object
                import speech_recognition as _sr
                r = _sr.Recognizer()
                text = r.recognize_google(google_audio, language="zh-CN")
                print("✅ Google 识别完成")
                return text
            except Exception as e:
                print(f"⚠️ Google 识别失败: {e}")

        # ---- 策略3: 手动输入回退 ----
        return input("\n[回退] 语音识别均不可用，请直接输入病历文本: ").strip()

    def _ai_text_input(self):
        """✏️ 文字输入 → AI 解析 → 预览"""
        print("\n" + "=" * 50)
        print("    ✏️ AI 文字解析病历")
        print("=" * 50)
        print("\n请输入/粘贴兽医病历描述文本：")
        print("(示例: 今天来了一只金毛叫旺财，主人张三说一直抓耳朵，")
        print(" 检查发现耳螨感染，开了耳漂洗耳液，一周后复诊，费用150元)")
        print()
        text = input("> ").strip()
        if not text:
            print("输入为空。")
            return
        self._ai_parse_and_preview(text)

    def _ai_parse_and_preview(self, text):
        """发送文本到 AI 解析服务，显示解析预览"""
        print("\n⏳ AI 正在分析...")
        resp = self._post("/api/ai/parse-record", {"text": text})
        if resp.status_code != 200:
            print(f"❌ 解析失败: {resp.json().get('error')}")
            return

        data = resp.json()
        result = data["result"]

        print("\n" + "=" * 60)
        print("  🤖 AI 解析结果")
        print(f"  置信度: {result['confidence']}%")
        print("=" * 60)

        # 宠物信息
        pi = result.get("pet_info", {})
        if pi:
            fields = []
            if pi.get("pet_name"): fields.append(f"名称: {pi['pet_name']}")
            if pi.get("pet_species"): fields.append(f"物种: {pi['pet_species']}")
            if pi.get("pet_breed"): fields.append(f"品种: {pi['pet_breed']}")
            if pi.get("pet_gender"): fields.append(f"性别: {pi['pet_gender']}")
            if pi.get("owner_name"): fields.append(f"主人: {pi['owner_name']}")
            if fields:
                print(f"  🐾 宠物信息: {' | '.join(fields)}")

        # 诊断
        diag = result.get("diagnosis", {})
        if diag.get("name"):
            print(f"  🏥 诊断: {diag['name']} (置信度: {diag['confidence']}%)")

        # 治疗方案
        treat = result.get("treatment", {})
        if treat.get("plan"):
            print(f"  💊 治疗方案: {treat['plan']}")
        if treat.get("prescription"):
            print(f"  📝 处方: {treat['prescription']}")

        # 日期
        dates = result.get("dates", {})
        if dates.get("visit_date"):
            print(f"  📅 就诊日期: {dates['visit_date']}")
        if dates.get("follow_up_date"):
            print(f"  📆 复诊日期: {dates['follow_up_date']}")

        # 费用
        fee = result.get("fee", {})
        if fee.get("fee_charged"):
            print(f"  💰 费用: {fee['fee_charged']} 元")

        # 备注
        if result.get("notes"):
            print(f"  📌 备注: {result['notes']}")

        # 摘要
        if result.get("summary"):
            print(f"\n  📋 摘要: {result['summary']}")

        print("=" * 60)

        # 询问是否直接创建诊疗记录
        print()
        choice = input("是否自动创建诊疗记录？(y/n): ").strip().lower()
        if choice == "y":
            self._ai_create_medical_record(text, result)

    def _ai_create_medical_record(self, text, result):
        """根据 AI 解析结果自动创建诊疗记录"""
        # 先选择宠物
        pet_id = None
        resp = self._get("/api/pets")
        if resp.status_code == 200:
            data = resp.json()
            if data["data"]:
                print("\n请选择关联的宠物:")
                for r in data["data"]:
                    print(f"  ID:{r['id']} | {r['name']} ({r['species']}) | 主人:{r.get('owner_name','')}")
                try:
                    pet_id = int(input("\n输入宠物 ID (按0跳过): "))
                    if pet_id == 0: pet_id = None
                except ValueError:
                    pet_id = None

        # 构建请求数据
        diag = result.get("diagnosis", {})
        treat = result.get("treatment", {})
        dates = result.get("dates", {})
        fee = result.get("fee", {})

        payload = {
            "pet_id": pet_id,
            "vet_name": "",
            "visit_date": dates.get("visit_date", "") or input("就诊日期 (YYYY-MM-DD): ").strip(),
            "diagnosis": diag.get("name", "") or input("诊断结果: ").strip(),
            "treatment": treat.get("plan", "") or input("治疗方案: ").strip(),
            "notes": result.get("notes", ""),
            "follow_up_date": dates.get("follow_up_date") or input("复诊日期 (YYYY-MM-DD, 可空): ").strip() or None,
            "fee_charged": fee.get("fee_charged", 0) or self._safe_int("费用: ") or 0,
        }

        resp = self._post("/api/medical-records", payload)
        d = resp.json()
        if resp.status_code == 201:
            print(f"\n✅ 诊疗记录创建成功！ID: {d.get('record_id', '')}")
            # 同时检查是否需要创建疫苗记录
            if any(kw in text for kw in ["疫苗", "接种", "免疫", "驱虫"]):
                if input("\n检测到疫苗相关关键词，是否同时创建接种记录？(y/n): ").strip().lower() == "y":
                    vaccine_name = input("疫苗名称: ").strip()
                    if vaccine_name:
                        self._post("/api/vaccinations", {
                            "pet_id": pet_id,
                            "vaccine_name": vaccine_name,
                            "administered_date": dates.get("visit_date", ""),
                            "next_due_date": dates.get("follow_up_date") or None,
                            "dose_number": self._safe_int("剂次: ") or 1,
                        })
                        print("✅ 接种记录已创建。")
        else:
            print(f"❌ 创建失败: {d.get('error')}")

    def _ai_auto_fill_and_submit(self):
        """一键自动填表并提交"""
        print("\n" + "=" * 50)
        print("    🏥 一键自动填表 (文字 → 病历)")
        print("=" * 50)
        print("\n请输入兽医病历描述：")
        text = input("> ").strip()
        if not text:
            return

        pet_id = None
        try:
            pet_id = int(input("关联宠物 ID (按0跳过): ") or 0)
            if pet_id == 0: pet_id = None
        except ValueError:
            pass

        print("\n⏳ AI 正在分析并提交...")
        resp = self._post("/api/ai/auto-fill", {"text": text, "pet_id": pet_id})
        if resp.status_code != 200:
            print(f"❌ 解析失败: {resp.json().get('error')}")
            return

        data = resp.json()
        print(f"\n📋 AI 解析摘要: {data['summary']}")
        print(f"置信度: {data['confidence']}%")
        print(f"预填表单: {data['form_data']}")

        if input("\n确认提交病历？(y/n): ").strip().lower() == "y":
            resp = self._post("/api/medical-records", data["form_data"])
            d = resp.json()
            if resp.status_code == 201:
                print(f"✅ 病历提交成功！ID: {d.get('record_id', '')}")
            else:
                print(f"❌ 提交失败: {d.get('error')}")

            # 检查是否需要创建疫苗记录
            if data.get("vaccine_data") and input("\n是否同时创建接种记录？(y/n): ").strip().lower() == "y":
                resp = self._post("/api/vaccinations", data["vaccine_data"])
                if resp.status_code == 201:
                    print("✅ 接种记录已创建。")

    def _ai_templates(self):
        """获取 AI 病历模板"""
        resp = self._get("/api/ai/templates")
        if resp.status_code != 200:
            print(f"❌ 获取失败: {resp.json().get('error')}")
            return

        data = resp.json()
        print(f"\n📋 可用病历模板 ({data['count']} 个):\n")
        for t in data["templates"]:
            print(f"  [{t['id']}] {t['name']} ({t['category']})")

        choice = input("\n选择模板 ID 查看详情 (直接回车返回): ").strip()
        if not choice:
            return

        for t in data["templates"]:
            if t["id"] == choice:
                print(f"\n{'='*50}")
                print(f"  模板: {t['name']} ({t['category']})")
                print(f"{'='*50}")
                print(t["content"].replace("{", "<").replace("}", ">"))
                print(f"{'='*50}")

                use = input("\n使用此模板输入病历？(y/n): ").strip().lower()
                if use == "y":
                    print("\n请在下方填写模板内容 (按模板格式输入):")
                    print("(" + t["content"][:80].replace("{", "<").replace("}", ">") + "...)")
                    text = input("> ").strip()
                    if text:
                        self._ai_parse_and_preview(text)
                return

        print("未找到该模板。")

    def _ai_disease_suggest(self):
        """根据症状搜索可能的疾病"""
        symptoms = input("\n请输入症状关键词 (逗号分隔，如: 呕吐,腹泻,发烧): ").strip()
        if not symptoms:
            return

        resp = self._get("/api/ai/disease-suggest", {"symptoms": symptoms})
        if resp.status_code != 200:
            print(f"❌ 查询失败: {resp.json().get('error')}")
            return

        data = resp.json()
        print(f"\n🔍 症状: {', '.join(data['symptoms'])}")
        print(f"匹配疾病: {data['total_matches']} 个\n")

        if data["suggestions"]:
            from prettytable import PrettyTable
            table = PrettyTable(["排名", "疾病", "置信度", "匹配关键词"])
            for i, s in enumerate(data["suggestions"], 1):
                table.add_row([i, s["disease"], f"{s['confidence']}%", ", ".join(s["matched_keywords"])])
            print(table)
        else:
            print("未找到匹配的疾病，建议进一步检查。")


    # ======================== 主入口 ========================

    def run(self):
        while True:
            print("""
        ╔══════════════════════════════════════════╗
        ║        🐾 PetCare 宠物医院管理系统 v2.0  ║
        ║      专业兽医诊所 · 一站式管理平台       ║
        ╚══════════════════════════════════════════╝
        *----------------------*
        | 1. 登录 (LOGIN)       |
        | 2. 注册 (REGISTER)    |
        | 3. 退出               |
        *----------------------*""")
            c = input("请选择: ").strip()
            if c == "1":
                if self.login():
                    self._main_menu()
                    self.token = None; self.user_role = None
            elif c == "2": self.register()
            elif c == "3": print("感谢使用 PetCare，再见！"); break

    def _main_menu(self):
        while True:
            print(f"""
        *-------------------------------------------*
        |    PetCare 主菜单 (当前角色: {self.user_role})     |
        *-------------------------------------------*
        | 1. 🐾 宠物信息管理                         |
        | 2. 📋 诊疗记录管理                         |
        | 3. 💉 疫苗接种管理                         |
        | 4. 💊 药品库存管理                         |
        | 5. 👥 行政管理                             |
        | 6. 🤖 AI 智能助手                          |
        | 7. 退出登录                                |
        *-------------------------------------------*""")
            c = input("请选择: ").strip()
            if c == "1": self.pet_menu()
            elif c == "2": self.medical_menu()
            elif c == "3": self.vaccine_menu()
            elif c == "4": self.drug_menu()
            elif c == "5": self.admin_menu()
            elif c == "6": self.ai_menu()
            elif c == "7": print("已退出登录。"); break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PetCare 宠物医院管理客户端")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"服务器地址 (默认: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"端口 (默认: {DEFAULT_PORT})")
    args = parser.parse_args()

    client = PetCareClient(host=args.host, port=args.port)

    try:
        resp = requests.get(f"http://{args.host}:{args.port}/api/health", timeout=3)
        if resp.status_code == 200:
            print(f"✅ 已连接到 {resp.json().get('service', 'PetCare')} 服务器")
        else:
            print("⚠️ 服务器响应异常。")
    except requests.ConnectionError:
        print(f"❌ 无法连接到服务器 http://{args.host}:{args.port}")
        print("请先启动后端: python backend/app.py")
        exit(1)

    client.run()
