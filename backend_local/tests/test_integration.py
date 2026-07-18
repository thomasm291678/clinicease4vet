"""
PetCare 集成测试：6 个场景化端到端测试，使用 unittest.mock.patch 模拟 MySQL。

设计思路：
- 每个测试类在 setUp 中创建独立的 mock 环境和 Flask test_client
- 每次 API 调用前设置 fetchone/fetchall/description 期望值
- 使用 side_effect 函数从队列中消费预置的返回值
"""

import pytest
from unittest.mock import MagicMock, patch
from app import create_app
from auth.auth import hash_password


# ============================================================
# Mock 环境工厂
# ============================================================
def _make_mock_state():
    """返回 (get_connection_factory, state_dict)

    state 是可变字典，测试可以随时修改以下键来控制下一个 mock cursor 的行为：
        state['fo']  - fetchone 返回值队列
        state['fa']  - fetchall 返回值队列
        state['cols'] - cursor.description 列名列表
        state['lastrowid'] - cursor.lastrowid 值
    """
    state = {"fo": [], "fa": [], "cols": [], "lastrowid": 1}

    def _get_conn():
        # 快照当前 state，使本次 API 调用的 cursor 不受后续 state 变更影响
        fo_snap = list(state["fo"])
        fa_snap = list(state["fa"])
        cols_snap = list(state["cols"])
        lr = state["lastrowid"]

        def _fetchone():
            return fo_snap.pop(0) if fo_snap else None

        def _fetchall():
            return fa_snap.pop(0) if fa_snap else []

        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        conn.commit = MagicMock()
        conn.rollback = MagicMock()
        cur.lastrowid = lr
        cur.description = [(c,) for c in cols_snap]
        cur.fetchone.side_effect = _fetchone
        cur.fetchall.side_effect = _fetchall
        cur.close = MagicMock()
        return conn

    return _get_conn, state


# ============================================================
# 常用列定义
# ============================================================
PET_COLS = [
    "id", "name", "species", "breed", "gender", "age_months",
    "weight_kg", "color", "owner_name", "owner_contact", "owner_address", "registered_at",
]

MEDICAL_COLS = [
    "id", "pet_id", "vet_name", "visit_date", "diagnosis", "treatment",
    "notes", "follow_up_date", "fee_charged", "created_at",
]

MEDICAL_JOIN_COLS = MEDICAL_COLS + ["pet_name", "species"]

VACCINE_COLS = [
    "id", "pet_id", "vaccine_name", "dose_number", "administered_date",
    "next_due_date", "vet_name", "batch_number", "notes", "created_at",
]

VACCINE_JOIN_COLS = VACCINE_COLS + ["pet_name", "species"]

DRUG_COLS = [
    "id", "drug_name", "category", "manufacturer", "batch_number",
    "quantity", "unit", "unit_price", "expiry_date", "storage_condition",
    "min_stock_level", "notes", "updated_at",
]

VET_COLS = [
    "id", "name", "specialisation", "license_no", "age",
    "address", "contact", "consultation_fee", "monthly_salary",
]

ASSISTANT_COLS = [
    "id", "name", "role", "age", "address", "contact", "monthly_salary",
]

WORKER_COLS = [
    "id", "name", "role", "age", "address", "contact", "monthly_salary",
]


# ============================================================
# 辅助函数
# ============================================================
def _pet_row(pet_id, name, species, breed, gender, age_m, weight, color,
             owner, contact, address, registered="2026-07-01"):
    return (
        pet_id, name, species, breed, gender, age_m, weight, color,
        owner, contact, address, registered,
    )


def _medical_row(rec_id, pet_id, vet, visit, diagnosis, treatment="",
                 notes="", follow_up=None, fee=0, created="2026-07-01"):
    return (
        rec_id, pet_id, vet, visit, diagnosis, treatment,
        notes, follow_up, fee, created,
    )


def _medical_join_row(rec_id, pet_id, vet, visit, diagnosis, treatment="",
                      notes="", follow_up=None, fee=0, created="2026-07-01",
                      pet_name="旺财", species="狗"):
    return (
        rec_id, pet_id, vet, visit, diagnosis, treatment,
        notes, follow_up, fee, created, pet_name, species,
    )


def _vaccine_row(rec_id, pet_id, name, dose, administered, next_due=None,
                 vet="", batch="", notes="", created="2026-07-01"):
    return (
        rec_id, pet_id, name, dose, administered, next_due, vet, batch, notes, created,
    )


def _vaccine_join_row(rec_id, pet_id, name, dose, administered, next_due=None,
                      vet="", batch="", notes="", created="2026-07-01",
                      pet_name="旺财", species="狗"):
    return (
        rec_id, pet_id, name, dose, administered, next_due, vet, batch, notes, created,
        pet_name, species,
    )


def _drug_row(drug_id, name, category, quantity, unit="盒", unit_price=0.0,
              manufacturer="", batch="", expiry=None, storage="", min_stock=5,
              notes="", updated="2026-07-01"):
    return (
        drug_id, name, category, manufacturer, batch, quantity, unit,
        unit_price, expiry, storage, min_stock, notes, updated,
    )


def _vet_row(vet_id, name, spec="", license_no="", age=0, address="",
             contact="", fee=0, salary=0):
    return (vet_id, name, spec, license_no, age, address, contact, fee, salary)


# ============================================================
# 场景 1：宠物管理全流程
# ============================================================
class TestScenarioPet:

    @pytest.fixture(autouse=True)
    def _setup(self):
        self._get_conn, self.s = _make_mock_state()
        with patch("routes.auth_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.admin_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.pet_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.medical_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.vaccination_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.drug_routes.get_connection", side_effect=self._get_conn), \
             patch("app.init_database"):
            app = create_app()
            app.config["TESTING"] = True
            self.client = app.test_client()
            yield

    # ---------- helpers ----------
    def _register(self, username, password, role="admin"):
        self.s["fo"] = [None]
        self.s["fa"] = []
        self.s["cols"] = []
        return self.client.post("/api/auth/register", json={
            "username": username, "password": password, "role": role,
        })

    def _login(self, username, password, role):
        pwd_hash = hash_password(password)
        self.s["fo"] = [(pwd_hash, role)]
        self.s["fa"] = []
        self.s["cols"] = []
        return self.client.post("/api/auth/login", json={
            "username": username, "password": password,
        })

    # ---------- test ----------
    def test_full_pet_lifecycle(self):
        c = self.client
        s = self.s

        # --- 注册 admin ---
        resp = self._register("admin", "admin123", "admin")
        assert resp.status_code == 201

        # --- 登录 admin ---
        resp = self._login("admin", "admin123", "admin")
        assert resp.status_code == 200
        token = resp.get_json()["token"]
        h = {"Authorization": f"Bearer {token}"}

        # --- 登记 3 只宠物 ---
        pets = [
            {"name": "旺财", "species": "狗", "breed": "金毛", "gender": "公",
             "age_months": 24, "weight_kg": 30.5, "color": "金色",
             "owner_name": "张三", "owner_contact": "13800001111", "owner_address": "北京"},
            {"name": "咪咪", "species": "猫", "breed": "英短", "gender": "母",
             "age_months": 12, "weight_kg": 4.2, "color": "蓝灰",
             "owner_name": "李四", "owner_contact": "13900002222", "owner_address": "上海"},
            {"name": "小白", "species": "兔", "breed": "垂耳兔", "gender": "公",
             "age_months": 6, "weight_kg": 1.8, "color": "白",
             "owner_name": "王五", "owner_contact": "13700003333", "owner_address": "广州"},
        ]
        for i, data in enumerate(pets):
            s["fo"] = []
            s["fa"] = []
            s["cols"] = []
            s["lastrowid"] = i + 1
            resp = c.post("/api/pets", json=data, headers=h)
            assert resp.status_code == 201, f"pet {data['name']}: {resp.get_json()}"

        # --- 必填字段验证：缺少 name ---
        # 在 pet_routes 中 mising name 直接返回 400，不访问数据库
        resp = c.post("/api/pets", json={"species": "狗", "owner_name": "测试"}, headers=h)
        assert resp.status_code == 400

        # --- 获取 pet/1 ---
        s["fo"] = [_pet_row(1, "旺财", "狗", "金毛", "公", 24, 30.5, "金色",
                            "张三", "13800001111", "北京")]
        s["fa"] = []
        s["cols"] = PET_COLS
        resp = c.get("/api/pets/1", headers=h)
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "旺财"

        # --- 获取不存在的 pet/999 ---
        s["fo"] = [None]
        s["fa"] = []
        s["cols"] = PET_COLS
        resp = c.get("/api/pets/999", headers=h)
        assert resp.status_code == 404

        # --- 更新 pet/1 ---
        # 先 SELECT id 检查存在，再 UPDATE
        s["fo"] = [(1,)]
        s["fa"] = []
        s["cols"] = []
        resp = c.put("/api/pets/1", json={"weight_kg": 32.0}, headers=h)
        assert resp.status_code == 200

        # --- 统计 ---
        # 两次查询：一次 GROUP BY，一次 COUNT
        s["fo"] = [(3,)]   # COUNT(*)
        s["fa"] = [[("狗", 2), ("猫", 1)]]  # GROUP BY
        s["cols"] = ["species", "cnt"]
        resp = c.get("/api/pets/stats", headers=h)
        assert resp.status_code == 200
        assert resp.get_json()["total"] == 3

        # --- 删除 pet/3 ---
        s["fo"] = [_pet_row(3, "小白", "兔", "垂耳兔", "公", 6, 1.8, "白",
                            "王五", "13700003333", "广州")]
        s["fa"] = []
        s["cols"] = PET_COLS
        resp = c.delete("/api/pets/3", headers=h)
        assert resp.status_code == 200

        # --- 无认证 401 ---
        resp = c.get("/api/pets")
        assert resp.status_code == 401


# ============================================================
# 场景 2：诊疗记录全流程
# ============================================================
class TestScenarioMedical:

    @pytest.fixture(autouse=True)
    def _setup(self):
        self._get_conn, self.s = _make_mock_state()
        with patch("routes.auth_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.admin_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.pet_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.medical_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.vaccination_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.drug_routes.get_connection", side_effect=self._get_conn), \
             patch("app.init_database"):
            app = create_app()
            app.config["TESTING"] = True
            self.client = app.test_client()
            yield

    def test_full_medical_flow(self):
        c = self.client
        s = self.s

        # --- 注册 vet ---
        s["fo"] = [None]; s["fa"] = []; s["cols"] = []
        resp = c.post("/api/auth/register", json={
            "username": "dr", "password": "pass123", "role": "vet",
        })
        assert resp.status_code == 201

        # --- 登录 vet ---
        s["fo"] = [(hash_password("pass123"), "vet")]; s["fa"] = []; s["cols"] = []
        resp = c.post("/api/auth/login", json={"username": "dr", "password": "pass123"})
        assert resp.status_code == 200
        h = {"Authorization": f"Bearer {resp.get_json()['token']}"}

        # --- 添加宠物（为诊疗记录准备）---
        s["fo"] = []; s["fa"] = []; s["cols"] = []
        resp = c.post("/api/pets", json={
            "name": "旺财", "species": "狗", "breed": "金毛", "owner_name": "张三",
        }, headers=h)
        assert resp.status_code == 201

        # --- 创建诊疗记录 1 ---
        s["fo"] = [(1,)]  # 宠物存在检查
        s["fa"] = []; s["cols"] = []
        resp = c.post("/api/medical-records", json={
            "pet_id": 1, "vet_name": "Dr. 李", "visit_date": "2026-07-01",
            "diagnosis": "皮肤真菌感染", "treatment": "酮康唑药膏 每日2次", "fee_charged": 350,
        }, headers=h)
        assert resp.status_code == 201

        # --- 创建诊疗记录 2 ---
        s["fo"] = [(1,)]
        s["fa"] = []; s["cols"] = []
        resp = c.post("/api/medical-records", json={
            "pet_id": 1, "vet_name": "Dr. 李", "visit_date": "2026-07-10",
            "diagnosis": "左耳感染", "treatment": "抗生素滴耳液", "fee_charged": 280,
        }, headers=h)
        assert resp.status_code == 201

        # --- 缺少 diagnosis ---
        resp = c.post("/api/medical-records", json={
            "pet_id": 1, "visit_date": "2026-01-01",
        }, headers=h)
        assert resp.status_code == 400

        # --- 按 pet 查看（count=2）---
        s["fo"] = []
        s["fa"] = [[
            _medical_join_row(1, 1, "Dr. 李", "2026-07-01", "皮肤真菌感染",
                              "酮康唑药膏 每日2次", "", None, 350, "2026-07-01"),
            _medical_join_row(2, 1, "Dr. 李", "2026-07-10", "左耳感染",
                              "抗生素滴耳液", "", None, 280, "2026-07-10"),
        ]]
        s["cols"] = MEDICAL_JOIN_COLS
        resp = c.get("/api/medical-records?pet_id=1", headers=h)
        assert resp.status_code == 200
        assert resp.get_json()["count"] == 2

        # --- 更新记录 1 ---
        s["fo"] = [(1,)]; s["fa"] = []; s["cols"] = []
        resp = c.put("/api/medical-records/1", json={"diagnosis": "已好转"}, headers=h)
        assert resp.status_code == 200

        # --- 删除记录 1 ---
        s["fo"] = [(1,)]; s["fa"] = []; s["cols"] = []
        resp = c.delete("/api/medical-records/1", headers=h)
        assert resp.status_code == 200

        # --- 验证 count=1 ---
        s["fo"] = []
        s["fa"] = [[
            _medical_join_row(2, 1, "Dr. 李", "2026-07-10", "左耳感染",
                              "抗生素滴耳液", "", None, 280, "2026-07-10"),
        ]]
        s["cols"] = MEDICAL_JOIN_COLS
        resp = c.get("/api/medical-records?pet_id=1", headers=h)
        assert resp.status_code == 200
        assert resp.get_json()["count"] == 1


# ============================================================
# 场景 3：疫苗接种记录全流程
# ============================================================
class TestScenarioVaccination:

    @pytest.fixture(autouse=True)
    def _setup(self):
        self._get_conn, self.s = _make_mock_state()
        with patch("routes.auth_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.admin_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.pet_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.medical_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.vaccination_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.drug_routes.get_connection", side_effect=self._get_conn), \
             patch("app.init_database"):
            app = create_app()
            app.config["TESTING"] = True
            self.client = app.test_client()
            yield

    def test_full_vaccination_flow(self):
        c = self.client
        s = self.s

        # --- 注册 vet ---
        s["fo"] = [None]; s["fa"] = []; s["cols"] = []
        resp = c.post("/api/auth/register", json={
            "username": "vet", "password": "pass123", "role": "vet",
        })
        assert resp.status_code == 201

        # --- 登录 vet ---
        s["fo"] = [(hash_password("pass123"), "vet")]; s["fa"] = []; s["cols"] = []
        resp = c.post("/api/auth/login", json={"username": "vet", "password": "pass123"})
        assert resp.status_code == 200
        h = {"Authorization": f"Bearer {resp.get_json()['token']}"}

        # --- 添加宠物 ---
        s["fo"] = []; s["fa"] = []; s["cols"] = []
        resp = c.post("/api/pets", json={
            "name": "旺财", "species": "狗", "breed": "金毛", "owner_name": "张三",
        }, headers=h)
        assert resp.status_code == 201

        # --- 添加 3 条疫苗记录 ---
        vaccines = [
            {"pet_id": 1, "vaccine_name": "狂犬疫苗", "dose_number": 1,
             "administered_date": "2026-06-15", "next_due_date": "2026-07-20",
             "vet_name": "Dr. 李"},
            {"pet_id": 1, "vaccine_name": "五联疫苗", "dose_number": 2,
             "administered_date": "2026-05-20", "vet_name": "Dr. 李"},
            {"pet_id": 1, "vaccine_name": "体内驱虫", "dose_number": 1,
             "administered_date": "2026-07-01", "next_due_date": "2026-10-01"},
        ]
        for v in vaccines:
            s["fo"] = [(1,)]  # 宠物存在检查
            s["fa"] = []; s["cols"] = []
            resp = c.post("/api/vaccinations", json=v, headers=h)
            assert resp.status_code == 201

        # --- 缺少疫苗名称 ---
        resp = c.post("/api/vaccinations", json={
            "pet_id": 1, "administered_date": "2026-07-01",
        }, headers=h)
        assert resp.status_code == 400

        # --- 按 pet 查看（count=3）---
        s["fo"] = []
        s["fa"] = [[
            _vaccine_join_row(1, 1, "狂犬疫苗", 1, "2026-06-15", "2026-07-20", "Dr. 李"),
            _vaccine_join_row(2, 1, "五联疫苗", 2, "2026-05-20", None, "Dr. 李"),
            _vaccine_join_row(3, 1, "体内驱虫", 1, "2026-07-01", "2026-10-01"),
        ]]
        s["cols"] = VACCINE_JOIN_COLS
        resp = c.get("/api/vaccinations?pet_id=1", headers=h)
        assert resp.status_code == 200
        assert resp.get_json()["count"] == 3

        # --- 删除记录 1 ---
        s["fo"] = [(1,)]; s["fa"] = []; s["cols"] = []
        resp = c.delete("/api/vaccinations/1", headers=h)
        assert resp.status_code == 200

        # --- 验证 count=2 ---
        s["fo"] = []
        s["fa"] = [[
            _vaccine_join_row(2, 1, "五联疫苗", 2, "2026-05-20", None, "Dr. 李"),
            _vaccine_join_row(3, 1, "体内驱虫", 1, "2026-07-01", "2026-10-01"),
        ]]
        s["cols"] = VACCINE_JOIN_COLS
        resp = c.get("/api/vaccinations?pet_id=1", headers=h)
        assert resp.status_code == 200
        assert resp.get_json()["count"] == 2


# ============================================================
# 场景 4：药品库存全流程
# ============================================================
class TestScenarioDrug:

    @pytest.fixture(autouse=True)
    def _setup(self):
        self._get_conn, self.s = _make_mock_state()
        with patch("routes.auth_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.admin_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.pet_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.medical_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.vaccination_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.drug_routes.get_connection", side_effect=self._get_conn), \
             patch("app.init_database"):
            app = create_app()
            app.config["TESTING"] = True
            self.client = app.test_client()
            yield

    def test_full_drug_flow(self):
        c = self.client
        s = self.s

        # --- 注册 admin ---
        s["fo"] = [None]; s["fa"] = []; s["cols"] = []
        resp = c.post("/api/auth/register", json={
            "username": "admin", "password": "admin123", "role": "admin",
        })
        assert resp.status_code == 201

        # --- 登录 admin ---
        s["fo"] = [(hash_password("admin123"), "admin")]; s["fa"] = []; s["cols"] = []
        resp = c.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200
        h = {"Authorization": f"Bearer {resp.get_json()['token']}"}

        # --- 添加 3 种药品 ---
        drugs = [
            {"drug_name": "阿莫西林", "category": "抗生素", "quantity": 100,
             "unit": "盒", "unit_price": 25.0, "min_stock_level": 20},
            {"drug_name": "狂犬疫苗", "category": "生物制品", "quantity": 50,
             "unit": "支", "unit_price": 80.0, "min_stock_level": 10},
            {"drug_name": "退烧针剂", "category": "解热镇痛", "quantity": 5,
             "unit": "支", "unit_price": 15.0, "min_stock_level": 10},
        ]
        for d in drugs:
            s["fo"] = []; s["fa"] = []; s["cols"] = []
            resp = c.post("/api/drugs", json=d, headers=h)
            assert resp.status_code == 201

        # --- stock-in +50 ---
        s["fo"] = [(1, 100)]  # SELECT id, quantity
        s["fa"] = []; s["cols"] = []
        resp = c.post("/api/drugs/1/stock-in", json={"quantity": 50}, headers=h)
        assert resp.status_code == 200
        assert "入库成功" in resp.get_json()["message"]

        # --- stock-in 0 被拒 ---
        resp = c.post("/api/drugs/1/stock-in", json={"quantity": 0}, headers=h)
        assert resp.status_code == 400

        # --- stock-out -30 ---
        s["fo"] = [(1, 150, "阿莫西林")]  # SELECT id, quantity, drug_name
        s["fa"] = []; s["cols"] = []
        resp = c.post("/api/drugs/1/stock-out", json={"quantity": 30}, headers=h)
        assert resp.status_code == 200

        # --- stock-out 超量 ---
        s["fo"] = [(1, 120, "阿莫西林")]  # 120 < 9999
        s["fa"] = []; s["cols"] = []
        resp = c.post("/api/drugs/1/stock-out", json={"quantity": 9999}, headers=h)
        assert resp.status_code == 400
        assert "库存不足" in resp.get_json()["error"]

        # --- 搜索 ---
        s["fo"] = []
        s["fa"] = [[_drug_row(2, "狂犬疫苗", "生物制品", 50, "支", 80.0)]]
        s["cols"] = DRUG_COLS
        resp = c.get("/api/drugs?search=疫苗", headers=h)
        assert resp.status_code == 200
        assert resp.get_json()["count"] >= 1

        # --- 更新药品 1 ---
        s["fo"] = [(1,)]; s["fa"] = []; s["cols"] = []
        resp = c.put("/api/drugs/1", json={"unit_price": 22.0}, headers=h)
        assert resp.status_code == 200

        # --- 删除药品 3 ---
        s["fo"] = [(3,)]; s["fa"] = []; s["cols"] = []
        resp = c.delete("/api/drugs/3", headers=h)
        assert resp.status_code == 200


# ============================================================
# 场景 5：权限矩阵
# ============================================================
class TestScenarioPermissions:

    @pytest.fixture(autouse=True)
    def _setup(self):
        self._get_conn, self.s = _make_mock_state()
        with patch("routes.auth_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.admin_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.pet_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.medical_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.vaccination_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.drug_routes.get_connection", side_effect=self._get_conn), \
             patch("app.init_database"):
            app = create_app()
            app.config["TESTING"] = True
            self.client = app.test_client()
            yield

    def test_permission_matrix(self):
        c = self.client
        s = self.s

        # --- 注册 3 种角色 ---
        for user, pw, role in [
            ("admin", "admin123", "admin"),
            ("vet1", "vetpass1", "vet"),
            ("staff1", "staffpass", "staff"),
        ]:
            s["fo"] = [None]; s["fa"] = []; s["cols"] = []
            resp = c.post("/api/auth/register", json={
                "username": user, "password": pw, "role": role,
            })
            assert resp.status_code == 201

        # --- 登录 3 种角色 ---
        def login_as(u, p, r):
            s["fo"] = [(hash_password(p), r)]; s["fa"] = []; s["cols"] = []
            resp = c.post("/api/auth/login", json={"username": u, "password": p})
            assert resp.status_code == 200
            return {"Authorization": f"Bearer {resp.get_json()['token']}"}

        h = {
            "admin": login_as("admin", "admin123", "admin"),
            "vet": login_as("vet1", "vetpass1", "vet"),
            "staff": login_as("staff1", "staffpass", "staff"),
        }

        # --- 所有人可查看 pets ---
        for role in ["admin", "vet", "staff"]:
            s["fo"] = []; s["fa"] = [[]]; s["cols"] = PET_COLS
            resp = c.get("/api/pets", headers=h[role])
            assert resp.status_code == 200, f"{role} should view pets"

        # --- 所有人可查看 drugs ---
        for role in ["admin", "vet", "staff"]:
            s["fo"] = []; s["fa"] = [[]]; s["cols"] = DRUG_COLS
            resp = c.get("/api/drugs", headers=h[role])
            assert resp.status_code == 200, f"{role} should view drugs"

        # --- 所有人可查看 medical records ---
        for role in ["admin", "vet", "staff"]:
            s["fo"] = []; s["fa"] = [[]]; s["cols"] = MEDICAL_JOIN_COLS
            resp = c.get("/api/medical-records", headers=h[role])
            assert resp.status_code == 200, f"{role} should view records"

        # --- 所有人可查看 staff ---
        for role in ["admin", "vet", "staff"]:
            s["fo"] = []; s["fa"] = [[]]; s["cols"] = VET_COLS
            resp = c.get("/api/admin/vet", headers=h[role])
            assert resp.status_code == 200, f"{role} should view staff"

        # --- admin 添加 vet → 201 ---
        s["fo"] = []; s["fa"] = []; s["cols"] = []
        resp = c.post("/api/admin/vet", json={
            "name": "Dr. 王", "specialisation": "内科", "license_no": "V001",
        }, headers=h["admin"])
        assert resp.status_code == 201

        # --- vet 添加 vet → 403（role_required 拦截）---
        resp = c.post("/api/admin/vet", json={
            "name": "Dr. 赵",
        }, headers=h["vet"])
        assert resp.status_code == 403

        # --- staff 添加 vet → 403 ---
        resp = c.post("/api/admin/vet", json={
            "name": "Dr. 钱",
        }, headers=h["staff"])
        assert resp.status_code == 403

        # --- admin 删除 vet → 200 ---
        s["fo"] = [_vet_row(1, "Dr. 王", "内科", "V001")]; s["fa"] = []; s["cols"] = VET_COLS
        resp = c.delete("/api/admin/vet/1", headers=h["admin"])
        assert resp.status_code == 200

        # --- staff 删除 vet → 403 ---
        resp = c.delete("/api/admin/vet/1", headers=h["staff"])
        assert resp.status_code == 403

        # --- 所有角色可添加宠物 ---
        for role in ["admin", "vet", "staff"]:
            s["fo"] = []; s["fa"] = []; s["cols"] = []
            resp = c.post("/api/pets", json={
                "name": f"测试-{role}", "species": "狗", "owner_name": "测试",
            }, headers=h[role])
            assert resp.status_code == 201, f"{role} should add pets"


# ============================================================
# 场景 6：错误处理
# ============================================================
class TestScenarioErrorHandling:

    @pytest.fixture(autouse=True)
    def _setup(self):
        self._get_conn, self.s = _make_mock_state()
        with patch("routes.auth_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.admin_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.pet_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.medical_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.vaccination_routes.get_connection", side_effect=self._get_conn), \
             patch("routes.drug_routes.get_connection", side_effect=self._get_conn), \
             patch("app.init_database"):
            app = create_app()
            app.config["TESTING"] = True
            self.client = app.test_client()
            yield

    def test_error_scenarios(self):
        c = self.client
        s = self.s

        # --- 注册 admin ---
        s["fo"] = [None]; s["fa"] = []; s["cols"] = []
        resp = c.post("/api/auth/register", json={
            "username": "admin", "password": "admin123", "role": "admin",
        })
        assert resp.status_code == 201

        # --- 登录 admin（获取有效 token）---
        s["fo"] = [(hash_password("admin123"), "admin")]; s["fa"] = []; s["cols"] = []
        resp = c.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200
        token = resp.get_json()["token"]
        h = {"Authorization": f"Bearer {token}"}

        # --- 空请求体 POST（4 个模块）---
        for endpoint in ["/api/pets", "/api/medical-records", "/api/vaccinations", "/api/drugs"]:
            resp = c.post(endpoint, headers=h)
            assert resp.status_code == 400, f"{endpoint} should reject empty body"

        # --- 无效令牌 401 ---
        resp = c.get("/api/pets", headers={"Authorization": "Bearer invalid"})
        assert resp.status_code == 401

        # --- 无认证头 401 ---
        resp = c.get("/api/pets")
        assert resp.status_code == 401

        # --- 错误的 Authorization 格式 401 ---
        resp = c.get("/api/pets", headers={"Authorization": "NoBearer x"})
        assert resp.status_code == 401

        # --- 密码过短 400 ---
        resp = c.post("/api/auth/register", json={"username": "x", "password": "12345"})
        assert resp.status_code == 400
        assert "6" in resp.get_json()["error"]

        # --- 空登录 400 ---
        resp = c.post("/api/auth/login", json={})
        assert resp.status_code == 400

        # --- 不存在的 API 404 ---
        resp = c.get("/api/nonexistent")
        assert resp.status_code == 404

        # --- 健康检查无需认证 200 ---
        resp = c.get("/api/health")
        assert resp.status_code == 200
        assert "PetCare" in resp.get_json()["service"]
