# HS AI SOLUTIONS — JULY CLI: WINDOWS ISOLATED EXECUTION ENGINE

**Developer & Chief Architect:** Harshan Seliyan  
**Organization:** HS AI Solutions  
**Product:** JULY LLM | Architecture: Windows Isolated Execution Engine  
**Release Target:** Windows 10/11 Enterprise & Professional (64-bit AMD64)

---

## 1. Executive Summary & Zero-Trust Architecture

The **July Windows Isolated Execution Engine** enforces a strict defense-in-depth security boundary for AI-generated code and shell operations. Under zero-trust AI principles, untrusted model outputs must **never execute directly under the primary human user's Windows security context**.

```
[Untrusted AI Model Output / Agent Tool Call]
                       │
                       ▼
    [CommandSecurityValidator (Lexical & AST)]
                       │
       ┌───────────────┴───────────────┐
       ▼                               ▼
[Dangerous Vector Blocked]    [Clean / Approved Command]
(Exit 126 / Audit Logged)              │
                                       ▼
                       [SandboxNetworkPolicy]
                       (OFFLINE by default / Firewall)
                                       │
                                       ▼
                       [SandboxFilesystem Boundary]
                       (Confined strictly to Workspace/)
                                       │
                                       ▼
                       [Windows Job Object + Restricted Token]
                       ├─ Process Max: 512 MB
                       ├─ Total Job Max: 1024 MB
                       ├─ CPU Hard Cap: 50%
                       ├─ Active Processes: Max 16
                       └─ KILL_ON_JOB_CLOSE (Kernel Enforced)
                                       │
                                       ▼
                       [july-sbx-r1 / july-sbx-u1 Accounts]
```

---

## 2. Windows Sandbox Account Management

### 2.1 Dedicated Security Group
- **Group Name:** `JulySandboxUsers`
- **Scope:** Dedicated local Windows security group.
- **Privileges:** Standard unprivileged group with administrative privileges stripped.

### 2.2 Standard Sandboxed Accounts
- **Worker Account:** `july-sbx-r1` (Worker/Replica 1)
- **Untrusted Account:** `july-sbx-u1` (Untrusted Execution 1)
- **Properties:**
  - `UserMayNotChangePassword = True`
  - `PasswordNeverExpires = True`
  - Removed from `Administrators` and `Power Users`.
  - Non-interactive login policy (DenyLocalLogon / SeDenyInteractiveLogonRight) preventing physical console login.

### 2.3 Cryptographic Credential Vault (Windows DPAPI)
- Account passwords are generated with 32 cryptographically random characters adhering to Windows complex password policy (at least 2 uppercase, 2 lowercase, 2 digits, 2 symbols).
- Stored using the **Windows Data Protection API (`CryptProtectData`)** with `CRYPTPROTECT_UI_FORBIDDEN = 0x1` at `%LOCALAPPDATA%\JulySandbox\config\credentials.dpapi`.
- Decryption is possible only on the local machine under the authorized user context (`CryptUnprotectData`).

---

## 3. Kernel Execution Primitives & Windows Job Objects

### 3.1 Job Object Limits (`JOBOBJECT_EXTENDED_LIMIT_INFORMATION`)
- **Process Memory Limit:** 512 MB hard ceiling (`JOB_OBJECT_LIMIT_PROCESS_MEMORY`).
- **Total Job Memory Limit:** 1024 MB hard ceiling (`JOB_OBJECT_LIMIT_JOB_MEMORY`).
- **Process Tree Cap:** Max 16 concurrent processes (`JOB_OBJECT_LIMIT_ACTIVE_PROCESS`) preventing fork-bombs.
- **Automatic Cleanup:** `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` ensures that if the Python runtime or process terminates, the Windows kernel automatically and atomically terminates all child processes.

### 3.2 CPU Rate Control (`JOBOBJECT_CPU_RATE_CONTROL_INFORMATION`)
- Flags: `JOB_OBJECT_CPU_RATE_CONTROL_ENABLE | JOB_OBJECT_CPU_RATE_CONTROL_HARD_CAP`
- Hard cap at 50% CPU cycles to prevent CPU exhaustion or thread starvation.

### 3.3 Atomic Process Termination (`TerminateJobObject`)
- When timeouts occur (default 30s), the executor invokes `TerminateJobObject(hJob, 124)` to atomically terminate the entire process tree within milliseconds.

---

## 4. Win32 Restricted Process Tokens & Safer API

- **Restricted Token Creation:** Derived from `OpenProcessToken` using `CreateRestrictedToken`.
- **Flags:** `DISABLE_MAX_PRIVILEGE | LUA_TOKEN`
- **Stripped SIDs:** Administrative groups (Administrators, Power Users) are stripped.
- **Revoked Privileges:** Dangerous privileges (e.g. `SeDebugPrivilege`, `SeBackupPrivilege`, `SeRestorePrivilege`, `SeTakeOwnershipPrivilege`, `SeTcbPrivilege`, `SeAssignPrimaryTokenPrivilege`) are completely disabled.
- **Safer API:** Integration with `SAFER_LEVELID_CONSTRAINED` to enforce user-level confinement.

---

## 5. Filesystem Security & Reparse-Point Jail

### 5.1 Directory Hierarchy
```
JulySandbox/
├── Runtime/      (Read & Execute: Tooling, Python binaries, Manifest)
├── Workspace/    (Read, Write, Delete: Code execution & working state)
├── Temporary/    (Read, Write, Delete: Ephemeral temp, wiped on reset)
├── Logs/         (Append & Read: execution.log, violations.log, network.log)
└── Artifacts/    (Write & Read: Deliverables and generated files)
```

### 5.2 Boundary Confinement & Reparse Defense
- **Path Canonicalization:** All file paths are strictly canonicalized via `os.path.realpath`.
- **Reparse-Point & Symlink Attacks:** Any symbolic link or junction pointing outside `Workspace/` or `Temporary/` is blocked with a `SecurityViolation`.
- **Alternate Data Streams:** Blocked (`:stream`).
- **Host System Protection:** Explicitly blocks access to `C:\Windows`, `C:\Program Files`, `%USERPROFILE%\Documents`, `%USERPROFILE%\Desktop`, `%USERPROFILE%\.ssh`, `%USERPROFILE%\.aws`, browser profiles, and configuration files.

---

## 6. Network Security & Windows Firewall

- **Policies:**
  - `OFFLINE` (Default): All network calls blocked before execution.
  - `ALLOWLIST`: Outbound connections restricted to explicitly whitelisted domains.
  - `ONLINE`: Network calls allowed with mandatory connection logging.
- **Windows Advanced Firewall:**
  - Rule `JulySandbox-Block-Outbound`: Blocks outbound traffic from sandbox processes.
  - Rule `JulySandbox-Block-Inbound`: Blocks all unsolicited inbound connections.
- **Connection Audit Log:** Recorded in `JulySandbox/Logs/network.log`.

---

## 7. Command Security & AST Validation

The `CommandSecurityValidator` inspects commands before launch:
- **System Destruction Blocked:** `format`, `diskpart`, `mountvol`, `vssadmin delete shadows`, `del /f /s C:\`, `rd /s /q C:\`.
- **Privilege Escalation Blocked:** `net user`, `net localgroup`, `runas`, `takeown`, `icacls`, `whoami /priv`, `secedit`.
- **Policy Bypasses Blocked:** `Set-ExecutionPolicy Bypass`, `-ep bypass`.
- **Registry Tampering Blocked:** `reg add`, `reg delete`, `Set-ItemProperty HKLM:`.
- **LOLBins Blocked:** `certutil -urlcache`, `bitsadmin`, `powershell -enc`, `mshta`, `rundll32`.
- **Destructive Operation Approval:** File deletions and overwrites flag `requires_user_approval=True`.

---

## 8. CLI Command Specification

```powershell
# 1. Install sandbox accounts, group, directory layout, and firewall rules
july sandbox install

# 2. Display security dashboard and real-time telemetry
july sandbox status

# 3. Prime sandbox runtime
july sandbox start

# 4. Stop running sandbox jobs
july sandbox stop

# 5. Clean ephemeral Workspace and Temporary state
july sandbox reset

# 6. Safe removal of sandbox accounts and data (with confirmation)
july sandbox remove [--confirm]

# 7. Execute command directly in sandbox
july sandbox run "<command>" [--timeout SEC] [--network]
```

### Interactive Chat Mode
- Inside `july chat`, use the `/sandbox` slash command:
  - `/sandbox status`: Display live dashboard
  - `/sandbox reset`: Wipe workspace
  - `/sandbox run <cmd>`: Run isolated command

---

## 9. Fail-Closed Security Boundary

If any sandbox component (Job Object, restricted token, directory validation) fails to initialize:
- **No Unrestricted Fallback:** The engine refuses execution immediately.
- **Exit Code 127:** Returns a `SANDBOX FAILURE` error.
- **Audit Log:** Logs security event to `violations.log`.

---

## 10. Automated Security Verification Matrix

Tested and verified via `tests/test_sandbox_execution_engine.py`:

| # | Test Area | Verification Target | Status |
|---|-----------|---------------------|--------|
| 1 | Unauthorized File Access | Blocks `C:\Windows\System32`, `%USERPROFILE%\Documents`, `.ssh`, `.aws` | **PASS** |
| 2 | Privilege Escalation | Blocks `net user`, `whoami /priv`, `runas`, `takeown`, `certutil` | **PASS** |
| 3 | Network Policies | Enforces `OFFLINE` by default; verifies `ALLOWLIST` and `ONLINE` | **PASS** |
| 4 | Infinite Loops | TerminateJobObject hard-kills hung process in 1.03s | **PASS** |
| 5 | Resource Quotas | Win32 Job Object memory (512MB/1GB) & CPU rate (50%) limits | **PASS** |
| 6 | Process Tree Termination | Atomic kill of entire child tree with exit code 99 | **PASS** |
| 7 | Directory Traversal | Blocks `../../../../Windows` path escape attempts | **PASS** |
| 8 | Symlink Attacks | Detects and blocks symlink/junction redirection attacks | **PASS** |
| 9 | Child Process Escape | Multi-process tree inherited into Job Object and terminated | **PASS** |
| 10 | DPAPI Vault | CryptProtectData encryption, password entropy (32 chars) | **PASS** |
| 11 | Fail-Closed Guarantee | Prevents unisolated fallback if sandbox initialization fails | **PASS** |
| 12 | Ephemeral Reset | Purges Workspace & Temporary while preserving Logs & Artifacts | **PASS** |

---
*HS AI Solutions — Developed by Harshan Seliyan (November 2026)*
