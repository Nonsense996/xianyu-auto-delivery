# 闲鱼自动发货管理系统

自建的闲鱼虚拟商品自动发货平台（对标"易店管理平台"的闲鱼自动发货核心能力），**无年费、无抽成、数据全部在自己手里**。

## 功能总览

| 模块 | 说明 |
|---|---|
| 🛒 鱼店管理 | 多账号接入，网页版 Cookie 一键接入，自动校验有效性；每账号一条 WebSocket 长连接，自动心跳/断线重连 |
| 📦 商品与卡密 | 商品绑定闲鱼商品ID；卡密批量导入、库存/已售统计、发货内容模板（`{card}` 占位符） |
| ⚡ 自动发货 | 监听买家消息/付款事件，命中商品自动扣减卡密并发送给买家；卡密不足自动记录待人工处理 |
| 💬 自动回复 | 关键词规则回复（优先级排序、命中统计）+ 兜底回复 |
| 🧾 订单管理 | 发货记录、失败原因、手动补发、状态标注 |
| 📊 工作台 | 今日/累计发货、库存预警、7 日趋势、最近日志 |
| 📄 运行日志 | 全流程留痕，按级别筛选 |

## 技术栈

- 后端：Python 3.12 + FastAPI + SQLAlchemy（async）+ SQLite（本地）/ MySQL 8（Docker）
- 前端：Vue 3 + Vite + Element Plus
- 对接：闲鱼网页版 mtop 接口签名 + WebSocket 长连接（协议参考开源项目 XianyuAutoAgent 的逆向成果）

## 目录结构

```
xianyu-auto-delivery/
├── backend/            # FastAPI 后端
│   └── app/
│       ├── routers/    # API：账号/商品/卡密/订单/规则/统计
│       └── services/   # 闲鱼协议、WebSocket 客户端、发货/回复逻辑
├── frontend/           # Vue3 管理界面
├── docker-compose.yml  # 一键部署（前端+后端+MySQL）
└── docs/
```

## 云服务器部署（Docker）

```bash
# 1. 上传整个目录到服务器，进入目录
cd xianyu-auto-delivery

# 2. 修改 docker-compose.yml 中的三个安全项：
#    - backend.SECRET_KEY：换成一串随机字符
#    - backend.ADMIN_PASSWORD：管理后台密码
#    - db 两个 MySQL 密码
vi docker-compose.yml

# 3. 构建并启动
docker compose up -d --build

# 4. 浏览器访问 http://服务器IP/ ，默认账号 admin（密码见上一步）
```

> 开发调试（本地）：`cd backend && uvicorn app.main:app --reload`；`cd frontend && npm run dev`（已配置代理到 8000 端口）。

## 使用流程

1. **添加鱼店**：鱼店管理 → 添加账号 → 粘贴 Cookie（系统自动校验并解析用户ID）。
2. **添加商品**：商品与卡密 → 添加商品 → 填闲鱼商品ID（商品详情页地址 `goofish.com/item/` 后的数字串）、发货模板。
3. **导入卡密**：商品列表点「卡密」→ 批量导入（每行一张）。
4. 完成。买家拍下付款后，系统监听到消息即自动发货。

## Cookie 获取方法（重要）

Cookie 一般 **7~30 天** 有效，失效后账号状态会变为 `error`，重新粘贴即可：

1. 电脑 Chrome 打开 https://www.goofish.com/ 并登录（手机扫码）；
2. `F12` 打开开发者工具 → `Network` 标签 → 刷新页面；
3. 点任意一个请求 → `Request Headers` → 复制 `Cookie:` 后面的**完整内容**；
   （也可以用 `Application` → `Cookies` → 导出所有键值拼成 `k1=v1; k2=v2; ...` 格式）
4. 粘贴到系统的账号表单里保存。

## ⚠️ 风险与合规说明

- 闲鱼**没有官方开放 API**，本系统与市面所有同类工具一样，基于网页版接口的逆向实现；闲鱼协议调整时需更新 `backend/app/services/xianyu_api.py`（协议层已独立成单文件，便于维护）。
- Cookie 等同账号凭证，请妥善保管，不要泄露给他人。
- 高频自动回复/发货可能触发平台风控，建议保持正常聊天节奏，设置合理的回复内容。
- 仅供个人店铺经营自动化使用，请遵守平台规则与当地法律法规。

## 常见问题

| 现象 | 处理 |
|---|---|
| 账号状态 error：Cookie 失效 | 重新获取 Cookie 粘贴保存 |
| 收不到消息 | 账号页点「重连」；查看运行日志 |
| 发货失败：卡密库存不足 | 及时补货，失败订单可在订单页补发 |
| 消息解析异常 | 闲鱼协议可能调整，更新 `xianyu_api.py` 中的解析字段 |
