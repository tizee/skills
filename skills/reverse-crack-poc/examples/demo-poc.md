# PoC Write-up：macOS Universal Mach-O 授权验证逻辑逆向与门控绕过分析

## 1. 项目背景

本项目是一个用于逆向工程学习和面试考核的 PoC。目标是分析一个 macOS 应用中的授权验证框架，理解它如何把底层 license / receipt 校验结果转换成业务层可消费的授权状态，并在受控实验环境中验证一种最小化 patch 思路。

本项目关注的是逆向分析方法论：如何从 UI 行为定位到授权状态消费点，如何区分静态配置与运行时状态，如何处理 Objective-C / Mach-O / universal binary，如何在 x86_64 与 arm64 上正确理解函数入口、调用约定和代码签名影响。

## 2. 分析目标

目标二进制是一个 Mach-O universal framework，包含 x86_64 与 arm64 两个 slice。主应用通过该 framework 查询授权状态。业务层并不直接解析注册码或 receipt，而是调用授权框架暴露的 API 获取一个 integer bitmask。

核心问题是：

```c
currentBits == goodBits
```

如果当前授权状态 `currentBits` 与合法目标状态 `goodBits` 相等，业务层认为授权有效；如果不相等，则进入试用限制、购买提示、升级提示或功能限制逻辑。

## 3. 初始定位路径

分析从 UI 中的 unlock / license 相关字符串开始，但很快发现 `unlock` 关键词噪声很大。在 macOS Objective-C 程序中，`unlock` 可能来自 mutex、focus、UI 状态、AppKit 方法或业务逻辑，直接用字符串搜索容易走偏。

更有效的路径是搜索 `license` 相关符号，并区分三类对象：

第一类是静态配置。例如：

```objc
- licenseConfiguration
- licenseLimitation
```

这类方法通常只是返回 `NSDictionary`、`NSArray` 或字符串配置，用于描述购买项、升级项、试用提示和产品策略。它们属于 policy / configuration 层，不直接执行授权验证。

第二类是业务消费点。例如：

```objc
isDeviceSafetyEngaged
```

这类方法会读取授权 bitmask，并把它翻译成具体业务行为，例如是否启用功能限制、是否显示购买提示、是否允许设备继续工作。

第三类是授权状态来源。例如：

```c
ApplicationLicenseBits()
ApplicationLicenseBitsGoodly()
```

这类函数最关键。前者返回当前运行时授权状态，后者返回当前进程中“合法授权状态”对应的目标值。

## 4. 授权模型还原

通过 IDA 查看调用链，可以还原出两层结构。

业务层逻辑大致如下：

```c
int bits = ApplicationLicenseBits();
int good = ApplicationLicenseBitsGoodly();

if (bits == good) {
    // 授权完整，关闭限制逻辑
} else {
    // 授权不完整，进入限制逻辑
}
```

进一步进入授权 framework 后，发现 `ApplicationLicenseBits()` 并不直接验证 license，而是转发到一个 Objective-C 单例对象：

```objc
[[LicenseStateCenter sharedCenter] signalWellformedness]
```

而 `ApplicationLicenseBitsGoodly()` 返回一个全局变量：

```c
return KeyWellformed;
```

进一步分析 `signalWellformedness`，可以得到核心逻辑：

```c
int signalWellformedness(LicenseStateCenter *self) {
    if (self->receiptWellformed == KeyWellformed)
        return self->receiptWellformed;

    return self->codeWellformed;
}
```

这说明授权系统有两条通道：

```text
receipt 授权路径  -> receiptWellformed
license key 路径 -> codeWellformed
目标合法状态     -> KeyWellformed
```

最终业务层并不关心 license key 如何生成，也不关心 receipt 如何验签。它只关心 `signalWellformedness` 返回的 bitmask 是否等于 `KeyWellformed`。

## 5. 关键发现：运行时随机 sentinel

进一步查看 class initializer 后发现，`KeyWellformed` 不是固定常量，而是在运行时初始化：

```c
int v = random();

if (v == 0)
    v = 1;

if (v < 0)
    v = -v;

KeyWellformed = v;
```

这意味着不能简单把返回值 patch 成 `1`、`0xFFFFFFFF` 或其他硬编码常量。合法值每次进程启动都可能变化。

因此，更稳的 PoC 思路不是伪造一个固定返回值，而是复用程序自己的合法值读取函数：

```c
ApplicationLicenseBitsGoodly()
```

它已经知道当前进程中的 `KeyWellformed` 值。

## 6. Patch 策略：tail-branch 到 Goodly

最小化 patch 思路是：在 `ApplicationLicenseBits()` 的函数入口处放置一个无条件跳转，让它直接跳到 `ApplicationLicenseBitsGoodly()`。

概念上等价于：

```c
int ApplicationLicenseBits(void) {
    return ApplicationLicenseBitsGoodly();
}
```

这样所有业务层调用 `ApplicationLicenseBits()` 时，都会拿到当前进程内真实的 `KeyWellformed` 值，而不是硬编码值。

这个 patch 点比改 `signalWellformedness` 更稳，原因有三点：

1. `ApplicationLicenseBits()` 是公开 API 入口，覆盖面更清楚。
2. `Goodly()` 原生负责读取合法 sentinel，避免 PC-relative / ADRP / RIP-relative 地址计算问题。
3. patch 面积小，x86_64 与 arm64 都只需要替换入口处一条跳转指令。

## 7. 函数入口纪律：必须覆盖第一条指令

一个容易出错的点是：无条件跳转必须放在 `ApplicationLicenseBits()` 的第一条指令上，不能放在 prologue 之后。

x86_64 函数入口常见形式：

```asm
push rbp
mov  rbp, rsp
...
```

arm64 函数入口常见形式：

```asm
stp x29, x30, [sp, #-0x10]!
mov x29, sp
...
```

如果 prologue 已经执行，再跳入另一个函数，就可能造成栈不平衡。x86_64 会多压栈，arm64 会多分配栈空间。短时间可能不崩，但多次调用后可能出现栈破坏或不可预测行为。

所以正确原则是：

```text
patch 必须覆盖函数入口第一条指令，让原函数 prologue 完全不执行。
```

这是本 PoC 中最重要的工程细节之一。

## 8. Universal Mach-O 的双架构处理

目标 framework 是 universal binary，包含 x86_64 和 arm64 两个 slice。因此 patch 不是“改一个地址”就结束。

需要分别处理：

```text
x86_64 slice:
    使用 x86_64 指令编码
    关注 x86_64 VM address 与 file offset

arm64 slice:
    使用 ARM64 指令编码
    关注 arm64 VM address 与 file offset
```

IDA 加载 universal Mach-O 时，应明确选择对应 slice。每个 slice 的地址空间、函数地址、文件偏移和指令编码都不同。

在 IDA 中的工作流程是：

```text
1. 分别加载 x86_64 slice 与 arm64 slice
2. 在 Names / Exports 中定位 ApplicationLicenseBits
3. 定位 ApplicationLicenseBitsGoodly
4. 在 ApplicationLicenseBits 第一条指令处 assemble 无条件跳转
5. 应用 patch 到输入文件
6. 对另一个 slice 重复该过程
```

不要把 x86_64 的 patch bytes 用到 arm64，也不要把 arm64 的 branch 编码用到 x86_64。

## 9. 代码签名问题

macOS 对 Mach-O 的 `__TEXT` 段有代码签名页哈希校验。修改 framework 的机器码后，原始签名会失效。尤其在 Apple Silicon 上，运行时执行到被修改的代码页时，可能因为 Code Signature Invalid 被系统终止。

因此 patch 后需要重新签名。

在实验环境中，可以使用 ad-hoc 签名：

```bash
codesign -s - -f --deep /path/to/TestApp.app
```

如果 app bundle 内部有多个 framework、helper、extension 或带 entitlements 的组件，可能需要先单独签内部组件，再签整个 app bundle。

需要区分两个问题：

```text
patch 是否正确：由 IDA / LLDB 验证
程序是否能加载：由 codesign / dyld / macOS runtime 验证
```

这两个问题属于不同层面。

## 10. LLDB 验证

patch 后可以用 LLDB 验证控制流是否符合预期：

```lldb
breakpoint set -n ApplicationLicenseBits
breakpoint set -n ApplicationLicenseBitsGoodly
```

触发业务逻辑后，观察 `ApplicationLicenseBits` 是否直接跳入 `Goodly`。

x86_64 返回值看：

```lldb
register read eax
```

arm64 返回值看：

```lldb
register read w0
```

验证目标是：

```text
ApplicationLicenseBits() 返回值 == ApplicationLicenseBitsGoodly() 返回值
```

同时可以继续断业务层 predicate，例如：

```text
isFeatureRestricted
isLicenseLimited
isDeviceSafetyEngaged
```

确认业务层确实因为 bitmask 相等而进入“授权完整”路径。

## 11. 技术总结

本 PoC 的核心不是生成合法注册码，而是找到授权状态在业务层的门控点，并理解 license framework 如何把复杂校验结果压缩成一个 runtime bitmask。

最终还原出的模型是：

```text
receipt / license key / local state
        ↓
授权 framework 内部校验
        ↓
receiptWellformed / codeWellformed
        ↓
signalWellformedness()
        ↓
ApplicationLicenseBits()
        ↓
业务层比较 currentBits == goodBits
```

由于 `goodBits` 是运行时随机 sentinel，直接硬编码返回值并不稳。更稳的方式是把 `ApplicationLicenseBits()` 的入口 tail-branch 到 `ApplicationLicenseBitsGoodly()`，复用原程序自己的合法 sentinel 读取逻辑。

这个项目体现的逆向能力包括：

```text
Objective-C selector / method list 分析
Mach-O import / export / framework 定位
IDA 静态分析与函数重命名
Hex-Rays 伪代码与汇编交叉验证
x86_64 与 arm64 调用约定差异
universal binary slice 区分
函数 prologue / stack discipline
macOS code signing 与 runtime 验证
LLDB 动态验证
```

## 12. 面试回答版本

如果要用一句话概括这个 PoC：

我从 UI 层的 license 行为出发，定位到业务层消费的 license bitmask，然后进入授权 framework 还原出 `currentBits == goodBits` 的门控模型。进一步发现 `goodBits` 是运行时随机 sentinel，不能硬编码。因此我选择在 `ApplicationLicenseBits()` 入口做 tail-branch，让它直接复用 `ApplicationLicenseBitsGoodly()` 返回当前进程内的合法 sentinel。为了保证稳定性，patch 必须覆盖函数第一条指令，避免 x86_64 / arm64 prologue 造成栈失衡。最后分别处理 universal Mach-O 的两个 slice，并通过重新签名和 LLDB 验证 patch 后的控制流。
