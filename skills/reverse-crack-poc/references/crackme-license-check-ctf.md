# macOS Crackme / License-Check CTF —— 考点与解题 Know-How

> 适用对象:自研 crackme / license-check PoC,用于逆向工程学习与二进制 patching 面试考核。
> 所有符号、地址、路径、产品名均为脱敏 demo。本文档只讨论技术:Objective-C / Mach-O / IDA Pro / LLDB / arm64 / x86_64 / universal binary / code signing / patch validation。
---

## 0. 第一性原理:这道题真正考的是什么

**离线全功能客户端在商业上必然不可行,根因是信任边界放错了一侧。**

当鉴权逻辑完全在攻击者的机器上运行,攻击者同时握有锁、钥匙和锁芯结构图。任何"是否已授权"的判断,只要输入、计算、输出都在本地完成,就一定可观测、可篡改、可绕过。

| 维度 | 防御方 | 攻击方 |
|---|---|---|
| 成本结构 | 每次发版重新付出保护代价 | 一次破解 |
| 分发成本 | —— | 边际成本为零,破解一份 = 破解所有份 |
| 信任根 | 试图把秘密放在"代码位置" | 代码位置恰恰由攻击方完全掌控 |

> **Kerckhoffs 原则的反面教材**:真正的安全把秘密放进密钥,而 license check 把秘密放进"代码位置"。这是一个**范畴错误**——把不可信的本地计算当成了可信根。
>
> 因此一切防御都只能"提高破解成本",永远做不到"使破解不可能"。CTF 设计的本质,就是沿"信任边界"这条轴**逐级抬高攻击成本**。

---

## 1. 逆向骨架:六环闭环

整个分析沿固定骨架推进。每一环既是解题步骤,也是出题的难度旋钮。

```
状态源 → 状态转换 → 门控判断 → 调用约定 → patch 风险 → 验证闭环
 (源)     (流)        (命门)      (语义)      (代价)      (证实)
```

---

## 2. 逐环:考点 ↔ Know-How

### 环 1 · 状态源 —— 从字符串反推

**Know-How(解题)**
- IDA `Shift+F12` 打开 Strings 窗口,搜:`Trial` / `expired` / `register` / `activated` / `Thank you` / `invalid license`,以及 license 文件路径、`NSUserDefaults` key、Keychain service 名。
- 命中目标串后按 `X` 看交叉引用(xref),顺 xref 爬到读取它的方法。
- **本质**:UI 行为是状态的可见投影,字符串是投影的锚点,xref 是从投影回溯到状态源的绳子。

**考点(出题)**

| 难度 | 设计 | 强制对手做什么 |
|---|---|---|
| L1 | 明文字符串 | 静态搜串即可 |
| L2 | XOR / base64 / 运行时拼接,Strings 窗口看不到完整文案 | 必须动态下断,而非静态搜串 |

---

### 环 2 · 调用约定 —— Objective-C 在 Mach-O 上的特殊形态

**Know-How(解题)**
- ObjC 没有普通函数调用,所有方法分发经 `objc_msgSend`。调用图呈"万流归宗":数百调用点汇入同一个 `objc_msgSend`。
- 真正的信息在寄存器里:

| 角色 | arm64 | x86_64 |
|---|---|---|
| receiver (self) | `x0` | `rdi` |
| selector (_cmd) | `x1` | `rsi` |
| 第一个参数 | `x2` | `rdx` |
| 返回值 | `x0` | `rax` |

- 实操:**在每个 `objc_msgSend` 前,往回找谁给 `x1` 赋的 selector 引用、谁给 `x0` 赋的 receiver**,这就是本次消息发送的语义。
- 若 IDA 正确解析 `__objc_selrefs` / `__objc_methname` / `__objc_classrefs`,selector 会还原成可读方法名(`-[LicenseManager isActivated]`),直接拿到高含金量调用地图。

**考点(出题)**
- 符号是否剥离。
- selector 是否运行时动态构造(`NSSelectorFromString` 拼字符串)→ 决定对手能否靠 ObjC 元数据"白嫖"调用地图。

---

### 环 3 · 门控判断 —— 找命门

**Know-How(解题)**
- 鉴权方法最终收敛成一个布尔,布尔喂给条件分支,分支决定"已授权 / 未授权"两条路。
- 盯关键指令:

| 平台 | 指令 | 含义 |
|---|---|---|
| arm64 | `cbz` / `cbnz` | 寄存器是否为零直接分支 |
| arm64 | `tbz` / `tbnz` | 测某一位再分支 |
| arm64 | `cmp` + `b.eq` / `b.ne` | 比较后条件跳转 |
| x86_64 | `test` / `cmp` + `je` / `jne` | 比较后条件跳转 |

- 典型编译形态:`if (isValid)` → `isValid` 返回值落 `w0` → `cbz w0, <未授权分支>`。
- 找到这条分支 = 找到整个程序的命门。

**考点(出题)**
- 命门数量与位置。
- L1:单点门控。
- 进阶:**TOCTOU 双重门控**——启动时检查一次,点击高级功能时再检查一次。只 NOP 掉启动检查的人,在后续隐藏分支触发时翻车。

---

### 环 4 · 架构差异 —— Universal Binary 陷阱

**Know-How(解题)**
- Fat binary 同时含 arm64 与 x86_64 切片。`lipo -info <binary>` 查看,`lipo -thin arm64 <binary> -output <out>` 拆单片。
- IDA 一次只加载一个切片,需自行选择。
- **关键认知**:同一鉴权逻辑在两切片里是两套独立指令编码。**patch 了 arm64 切片 ≠ patch 了 x86_64 切片**。
- 运行环境:Apple Silicon 默认跑 arm64 片;Intel 或 Rosetta 跑 x86_64 片。

**考点(出题)**
- 让真正的 flag 校验只存在于某一个切片。
- 让两切片校验逻辑故意不一致 → 只 patch 了 arm64 片的人,换到 Intel / Rosetta 环境立刻露馅。
- 这是真实商业软件里 universal binary 让破解工作量翻倍的根因。

---

### 环 5 · Patch 风险 —— 从"读懂"到"改动"

**Know-How(解题):三种基本打法**

| 打法 | arm64 | x86_64 | 特点 |
|---|---|---|---|
| NOP 掉检查调用 | 替换为 `nop` | 替换为 `90` | 让校验形同未发生 |
| 反转 / 短路分支 | `b.eq` → `b.ne`,或改无条件 `b` | `je` → `jne` | 翻转判断方向 |
| 强制返回值 | `mov w0, #1` + `ret` | `mov eax, 1` + `ret`(`B8 01 00 00 00 C3`) | 最干净,从源头让所有调用点拿到"已授权" |

> 强制返回往往最干净:它在源头解决问题,所有调用点统一受益。

**考点(出题):每招都有对应风险,这些风险就是高级考点**

| 风险机制 | 原理 | 破法 |
|---|---|---|
| **Code Signing** | Apple Silicon 上代码须有效签名;改 `__TEXT` → CDHash 变 → 签名失效 → AMFI 毙进程 | patch 后 `codesign -f -s - <binary>` 重做 ad-hoc 签名;留意 hardened runtime / library validation |
| **自校验 / Anti-Tamper** | 程序自算 `__TEXT` 哈希与内置值比对,发现被改即触发陷阱 | 连校验例程一起 patch;或在内存里、自校验跑完之后再改 |
| **PAC(指针认证,arm64e)** | 给指针签名,直接改指针触发认证失败 | 现成的"反 naive patch"机制;避免篡改签名指针,改布尔/比较指令通常不受影响 |
| **服务端依赖** | 真正的功能数据由服务端下发 | patch 布尔为 true 只得空壳——**核心结论的具体显形** |

---

### 环 6 · 验证闭环 —— 用 LLDB 证实

**Know-How(解题):静态给假设,动态给确证**

```bash
lldb <binary>
br set -n "-[LicenseManager isValid]"   # 在怀疑的方法下断
run
register read x0                         # 看 self
# 单步到返回处,看 x0 里的布尔到底是什么
register write x0 1                       # 内存里强行改返回值
continue                                  # 看 UI 是否真的解锁
```

**标准闭环(= patch validation 的全部):**

```
静态定位 → 动态确认 → 内存试改 → 落盘固化 → 重签验证
```

你不是在猜,而是用最小代价证伪/证实每一步假设。先在内存里试错确认命门,再回 IDA 把改动固化进文件并重签名。

**考点(出题)**
- `ptrace(PT_DENY_ATTACH)` 或 `sysctl` 查 `P_TRACED` 阻断 LLDB attach。
- 逼对手先 patch 掉反调试,或改用提前注入方式 → 把"验证闭环"本身变成考点。

---

## 3. 难度阶梯:沿信任边界逐级抬高成本

| 级别 | 设计 | 考查点 | 解题核心能力 |
|---|---|---|---|
| **L1** | 明文 `strcmp` 序列号 | string → xref → branch 基本功 | 定位 |
| **L2** | 一层可逆变换(XOR / 自定义编码后再比) | 动态下断看变换前的值 | 动态分析 |
| **L3** | **keygen-me**:`f(serial)==expected` 真算法;若 `expected` 依赖用户名则 name-based | 逆出 `f` 写注册机,必要时反演算法 | **理解算法**(教学价值最高) |
| **L4** | 加反调试 | 识别并绕过 `PT_DENY_ATTACH` | 反反调试 |
| **L5** | 自校验 / anti-tamper | patch 顺序与内存时机 | 时序控制 |
| **L6** | universal binary 切片不一致设陷 | 架构完备性 | 全架构覆盖 |
| **L7** | 混淆 / VM-based 校验 | 把成本推到工程极限 | 工程韧性 |
| **L8** | 校验真正依赖服务端 | 离线条件下**原理上无解** | —— |

> **L8 不是更难,而是质变。** 它是"商业可行设计"的终点,也是你想让学生亲身撞上的那堵墙。

---

## 4. 认知分水岭:patch-me vs keygen-me

| | patch-me | keygen-me |
|---|---|---|
| 训练目标 | 定位能力 | 算法理解 |
| 危险错觉 | "破解 = 改一个字节" | —— |
| 校验逻辑 | 被绕过 | 可以是对的、签名完整、自校验全过 |
| 唯一出路 | 翻转那一位 | 真正理解算法 |

**好的出题人会刻意让 patch 路径布满地雷**(多重门控、自校验、PAC),把学生往"必须理解而非必须篡改"的方向逼。

> 这回到 Kerckhoffs 原则:真正的安全把秘密放在密钥里;license check 试图把秘密放在"代码位置"里,而代码位置恰恰是攻击者完全掌控的东西。

---

## 5. 出题人的目标函数:两个方向相反的旋钮

设计 anti-tamper 强度时,先想清楚你在优化哪一个——**二者方向相反**:

| 目标 | anti-tamper 策略 | 解空间 |
|---|---|---|
| **教学深度** | 做满,封死 patch 路径,逼走 keygen | 单解(此时单解是**特性**而非 bug) |
| **解法多样性 / 区分度** | "硬但可绕":自校验存在,但期望哈希可被找到并改,保留 patch 路径同时抬高成本 | 多解(patch / keygen / 内存补丁 / 运行时 hook 各通一条) |

---

## 6. 现代 Apple Silicon 的真实摩擦(方法论是否过时?)

**大体成立,但有真实摩擦:**

- **PAC**:主要影响篡改签名指针(改返回地址、vtable 指针)。对"改布尔返回值""NOP 一条比较指令"这类**不涉及签名指针的 patch 影响有限** → 强制返回值这招大多仍然干净。
- **hardened runtime / library validation**:真正影响在落盘那一步。开了 library validation,注入 dylib(运行时 hook 路径)会被挡;但静态 patch + ad-hoc 重签通常仍可执行。
- **更值得警惕的不是 PAC,而是 Mac App Store 的 FairPlay 加密**:`LC_ENCRYPTION_INFO` 的 `cryptid` 非零,`__TEXT` 是密文,IDA 直接看到乱码,必须先从内存 dump 出解密镜像才能分析。

> **进阶出题建议**:若想贴近真实商业软件难度,**模拟一层"运行时解密的代码段"比堆砌 PAC 更有教学价值**——它直接演示"代码在磁盘上根本不可读"这种现代保护范式,再次指向核心结论:**最强的保护是让有价值的东西在静态二进制里压根不存在。**

---

## 7. 工具速查

| 任务 | 命令 / 操作 |
|---|---|
| 查看架构切片 | `lipo -info <binary>` |
| 拆单架构 | `lipo -thin arm64 <binary> -output <out>` |
| IDA 字符串窗口 | `Shift+F12` |
| IDA 交叉引用 | 选中后按 `X` |
| 加载 LLDB | `lldb <binary>` |
| 按符号下断 | `br set -n "-[Class method]"` |
| 读寄存器 | `register read x0` |
| 写寄存器 | `register write x0 1` |
| ad-hoc 重签名 | `codesign -f -s - <binary>` |
| 查加密标志 | 看 `LC_ENCRYPTION_INFO` 的 `cryptid` |

---

## 8. 一页纸总结

> **方法论的每一步都对应一个考点,而所有考点最终都在演示同一个结论:价值不在那个布尔里。**
>
> 离线全功能 = 在结构上邀请被破解。把这个"体感"通过 L1→L8 的阶梯让学生亲手撞上,就是这道 CTF 题最高的教学价值。
