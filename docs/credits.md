# LIFEE Credits 计费手册

> 给队友看的：现在每个会烧 LLM 的接口扣多少 credits、怎么扣、新加接口怎么接进来。

## 1. 价目表

| 接口 / 按钮               | 价格 (cr)  | 扣费时机   | 失败退款 | 备注                                              |
| ------------------------- | ---------- | ---------- | -------- | ------------------------------------------------- |
| `/decision` 普通圆桌      | 1 / 人 / 轮 | 每发言一次 | 否       | speakers × rounds 起跳就预检查                    |
| `/decision` 联网搜索      | 2 / 人 / 轮 | 每发言一次 | 否       | `webSearch=true` 切到 `chat-web`                  |
| `/followup`               | 1          | 预扣       | 是       | 单人追问                                          |
| `/summarize`              | 1          | 预扣       | 是       | 对话总结                                          |
| `/path-options`           | 2          | 预扣       | 是       | 生成 3 条 roadmap 分支                            |
| `/simulate-path`          | 3          | 预扣       | 是       | "Walk this path"：返 outcome + 下一层 3 条新路径 |
| `/plan-30-days`           | 3          | 预扣       | 是       | 30 天行动计划                                     |
| `/generate-personas`      | **0**      | —          | —        | 只返推荐预览（id/name/role/voice），不含 soul     |
| `/generate-persona-soul`  | **3 / 个** | 预扣       | 是       | 用户在弹窗勾选 + 确认后才调用，按勾选数量计费     |
| `/extract-memory`         | 0          | —          | —        | 免费（写 USER.md 用，量很小）                     |
| `/recommend-personas`     | 0          | —          | —        | 免费（只是从已有 persona 里挑 id）                |

**特殊**：`/credits/generate/{n}` 受 `ADMIN_TOKEN` 保护，需 `x-admin-token` header，只给我们自己生成兑换码用。

## 2. Persona 生成的两段式（重要）

```
打开弹窗
  ↓
/recommend-personas        免费    从已有 roster 里挑 2 个 id
/generate-personas         免费    LLM 写 2 个新 persona 预览（无 soul）
  ↓
[用户勾选 + 点确认]
  ↓
/generate-persona-soul     3cr/个  只为被勾选的 gen-* persona 生成 200-300 字 system prompt
  ↓
进入对话
```

为什么这么拆：让 user 没勾的预览不烧钱。原本 modal 一打开就扣 3cr 即使用户什么都不选，浪费。

## 3. 扣费/退款机制

三个 helper，全在 `lifee/api.py` 顶部：

```python
# 1) 入口：检查登录 + 预扣，失败直接返回 401/402 给前端
uid, err = await _charge_or_response(request, cost, reason)
if err: return err

# 2) 业务异常时退款（静默失败，不掩盖原始异常）
await _refund(uid, cost, reason)

# 3) 底层：原子扣费，余额不足返回 False
await _deduct(uid, amount, reason)
```

**扣费策略**：
- **预扣**（绝大多数接口）：进入接口先扣，LLM 报错 / 返回空 / 上游 402 都 `_refund` 退回。
- **按消息扣**（仅 `/decision`）：每个 participant 发完话后单独 `_deduct`，余额不足时停止后续轮次（不退款，因为前面的人已经讲过了）。
- **按数量扣 + 部分退款**（`/generate-persona-soul`）：进入按 `3 × len(personas)` 预扣，LLM 返回了 N 条但少于请求数时，缺多少退多少。

`_refund` 调用的是 `lifee.store.credits_credit(uid, amount, reason)`，会写一条 `refund:<reason>` 流水。

## 4. 加新付费接口的模板

```python
@app.post("/your-new-endpoint")
async def your_new_endpoint(request: Request, req: YourReq):
    uid, err = await _charge_or_response(request, 2, "your-reason")
    if err:
        return err
    try:
        result = await call_llm(...)
        if not result:
            await _refund(uid, 2, "your-reason")
            return JSONResponse({"error": "empty"}, status_code=502)
        return {"data": result}
    except Exception:
        await _refund(uid, 2, "your-reason")
        raise
```

**reason 命名**：和接口名一致（kebab-case），方便对账时 `SELECT reason, SUM(amount) FROM credit_transactions GROUP BY reason`。

## 5. 前端怎么处理 402

后端返回 `{"error": "insufficient_credits", "balance": X, "needed": Y, "reason": "..."}` + 402 状态码。

前端两个全局 helper（`web/void/index.html` 顶部定义）：

```js
window.__lifeeMaybe402(data)        // 检测 data.error==='insufficient_credits' 时弹兑换码弹窗
window.__lifeeRefreshBalance()      // 拉 /credits 并广播 'lifee:balance' 事件，刷侧边栏数字
```

**所有付费 fetch 都要遵循**：

```js
const r = await fetch('/your-endpoint', { credentials: 'include', ... });
const data = await r.json();
if (window.__lifeeMaybe402?.(data)) return;   // 余额不足，弹窗已起来
window.__lifeeRefreshBalance?.();             // 成功就刷余额
// ...用 data
```

事件总线：
- `lifee:insufficient-credits` → App.useEffect 监听，自动打开 RedeemModal 并显示 `needed/balance`。
- `lifee:balance` → 侧边栏 credits 数字组件监听，更新显示。

## 6. 兑换码

```bash
# 本地生成（Aliyun 上有 ADMIN_TOKEN 也能生成，但通常本地跑就行）
curl -H "x-admin-token: $ADMIN_TOKEN" https://lifee.world/credits/generate/100

# 改默认面值：
curl -H "x-admin-token: $ADMIN_TOKEN" "https://lifee.world/credits/generate/50?credits=200"
```

- 不会重复（数据库 UNIQUE 约束 + 重试）。
- 没设过期时间（`expires_at IS NULL`），永久有效，除非手动改 DB。
- 兑换走 `/redeem`，每个 uid + code 只能成功一次。

## 7. 排查

**用户说扣了但前端余额没变**：检查那个接口的前端 fetch 有没有调 `__lifeeRefreshBalance()`。

**用户说没用功能也扣 credits**：查 `credit_transactions` 表的 `reason`，正常扣费 reason 是接口名，退款 reason 是 `refund:<接口名>`，正常情况下两者抵消。

**调试单个用户**：

```bash
sqlite3 ~/.lifee/users.db "SELECT * FROM credit_transactions WHERE uid='user:<id>' ORDER BY created_at DESC LIMIT 20;"
```
