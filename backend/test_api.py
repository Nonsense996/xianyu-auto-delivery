"""临时验证脚本：跑完删除"""
import httpx

BASE = "http://127.0.0.1:8000/api"
c = httpx.Client(timeout=15)

# 登录
token = c.post(f"{BASE}/auth/login", json={"username": "admin", "password": "admin123"}).json()["access_token"]
c.headers["Authorization"] = f"Bearer {token}"
print("1 登录 OK")

# 建商品
p = c.post(f"{BASE}/products", json={
    "account_id": 1, "name": "测试卡密商品", "xianyu_item_id": "123456789",
    "price": 9.9, "delivery_template": "感谢购买！您的卡密：{card}",
}).json()
assert "id" in p, p
print(f"2 建商品 OK id={p['id']}")

# 导入卡密
r = c.post(f"{BASE}/cards/import", json={"product_id": p["id"],
           "contents": "CARD-AAA-001\nCARD-BBB-002\nCARD-CCC-003"}).json()
print(f"3 导入卡密 OK: {r['msg']}")
assert r["msg"].startswith("成功导入 3")

# 库存
d = c.get(f"{BASE}/products").json()[0]
assert d["stock"] == 3, d
print(f"4 库存统计 OK stock={d['stock']} sold={d['sold_count']}")

# 卡密查询
cards = c.get(f"{BASE}/cards", params={"product_id": p["id"]}).json()
assert cards["total"] == 3
print("5 卡密列表 OK total=3")

# 回复规则 CRUD
rule = c.post(f"{BASE}/rules", json={"keyword": "多少钱,价格", "reply_text": "拍下自动发货哦~", "priority": 5}).json()
assert "id" in rule, rule
rules = c.get(f"{BASE}/rules").json()
assert len(rules) == 1
dr = c.put(f"{BASE}/rules/default-reply", json={"enabled": True, "reply_text": "亲，在的~"}).json()
print("6 回复规则+兜底 OK")

# 订单列表（空）
o = c.get(f"{BASE}/orders").json()
assert o["total"] == 0
print("7 订单列表 OK total=0")

# 日志
lg = c.get(f"{BASE}/logs").json()
print(f"8 日志接口 OK total={lg['total']}")

# 工作台库存
db = c.get(f"{BASE}/dashboard").json()
assert db["cards"]["stock"] == 3
print("9 工作台 OK stock=3")

# 卡密删除（未售）
ids = [x["id"] for x in c.get(f"{BASE}/cards", params={"product_id": p["id"]}).json()["items"]]
r = c.post(f"{BASE}/cards/delete", json={"ids": ids[:1]}).json()
print(f"10 卡密删除 OK: {r['msg']}")
assert r["msg"].startswith("删除 1")

print("\n=== 全部 10 项业务接口验证通过 ===")
