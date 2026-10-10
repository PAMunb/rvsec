# Threat Types Checklist

Classification of security threats with examples and countermeasures.

---

## Threat Classification

Four fundamental threat types based on how they affect system assets:

```
                    ASSETS
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
    ▼                 ▼                 ▼
┌─────────┐     ┌─────────┐     ┌─────────┐
│  DATA   │     │ SERVICE │     │ SYSTEM  │
└────┬────┘     └────┬────┘     └────┬────┘
     │               │               │
     ▼               ▼               ▼
┌────────────────────────────────────────┐
│           THREAT TYPES                 │
├────────────┬────────────┬──────────────┤
│INTERCEPTION│INTERRUPTION│ MODIFICATION │
│            │            │              │
│FABRICATION │            │              │
└────────────┴────────────┴──────────────┘
```

---

## 1. Interception

**Definition**: Unauthorized party gains access to data or services.

### Characteristics

- **Goal**: Access information
- **Effect**: Confidentiality breach
- **Detection**: Often hard to detect (passive)

### Attack Examples

| Attack | Target | Technique |
|--------|--------|-----------|
| Eavesdropping | Network traffic | Packet sniffing |
| Man-in-the-middle | TLS connections | Certificate spoofing |
| Session hijacking | User sessions | Token theft |
| Log exposure | Application logs | Log file access |
| Memory dump | Runtime memory | Core dump analysis |
| Side-channel | Cryptographic keys | Timing attacks |

### Vulnerable Code Patterns (DO NOT USE)

```
# BAD: Logging sensitive data
logger.info(f"User {user} logged in with password {password}")

# BAD: Sensitive data in error message
raise Exception(f"Auth failed for {api_key}")

# BAD: Unencrypted transmission (HTTP instead of HTTPS)

# BAD: Sensitive data in URL query strings
```

### Checklist

- [ ] Sensitive data encrypted in transit (TLS 1.2+)
- [ ] Sensitive data not logged
- [ ] Sensitive data not in URLs/query strings
- [ ] Sensitive data not in error messages
- [ ] Memory cleared after use (for secrets)
- [ ] Network traffic encrypted end-to-end

### Countermeasures

| Threat | Countermeasure |
|--------|----------------|
| Network sniffing | TLS encryption |
| MITM | Certificate pinning |
| Session hijacking | Secure cookies, token rotation |
| Log exposure | Log sanitization, access control |

---

## 2. Interruption

**Definition**: System asset is destroyed or becomes unavailable.

### Characteristics

- **Goal**: Deny service
- **Effect**: Availability breach
- **Detection**: Usually obvious (system down)

### Attack Examples

| Attack | Target | Technique |
|--------|--------|-----------|
| DoS | Server resources | Request flooding |
| DDoS | Network/server | Distributed flooding |
| Resource exhaustion | Memory/CPU | Algorithmic complexity |
| Account lockout | User accounts | Repeated failed logins |
| Data deletion | Stored data | Unauthorized delete |
| Ransomware | All data | Encryption by attacker |

### Vulnerable Code Patterns (DO NOT USE)

```
# BAD: No rate limiting on expensive operations

# BAD: Unbounded resource allocation (no size limits)

# BAD: ReDoS - regex with exponential backtracking like ^(a+)+$

# BAD: O(n^2) algorithms exposed to user input
```

### Checklist

- [ ] Rate limiting on all endpoints
- [ ] Request size limits enforced
- [ ] Timeout limits on operations
- [ ] Resource quotas per user/tenant
- [ ] Graceful degradation under load
- [ ] Regular expressions reviewed for ReDoS
- [ ] Backup and recovery procedures tested

### Countermeasures

| Threat | Countermeasure |
|--------|----------------|
| DoS/DDoS | Rate limiting, CDN, WAF |
| Resource exhaustion | Quotas, timeouts |
| Account lockout | CAPTCHA, progressive delays |
| Data deletion | Backups, soft delete, audit |

---

## 3. Modification

**Definition**: Unauthorized party changes data or system behavior.

### Characteristics

- **Goal**: Alter data or behavior
- **Effect**: Integrity breach
- **Detection**: Can be hard (subtle changes)

### Attack Examples

| Attack | Target | Technique |
|--------|--------|-----------|
| SQL injection | Database | Malicious SQL |
| Command injection | OS | Shell commands |
| XSS (stored) | Web pages | Script injection |
| Data tampering | Records | Direct modification |
| Configuration change | Settings | Unauthorized access |
| Binary patching | Executables | Code modification |

### Vulnerable Code Patterns (DO NOT USE)

```
# BAD: SQL injection via string interpolation
query = f"SELECT * FROM users WHERE id = {user_id}"

# BAD: Command injection via shell execution with user input

# BAD: Path traversal via unvalidated user paths

# BAD: Insecure deserialization of untrusted data

# BAD: Mass assignment without field allowlist
```

### Checklist

- [ ] Parameterized queries for all SQL
- [ ] Input validation (allowlist, not blocklist)
- [ ] Output encoding for all user data
- [ ] Path traversal prevention
- [ ] Safe serialization formats (JSON, not binary)
- [ ] Mass assignment protection
- [ ] Integrity checks on critical data

### Countermeasures

| Threat | Countermeasure |
|--------|----------------|
| SQL injection | Parameterized queries, ORM |
| Command injection | Avoid shell, use libraries |
| XSS | Output encoding, CSP |
| Data tampering | Integrity checks, signatures |
| Path traversal | Canonicalization, allowlist |

---

## 4. Fabrication

**Definition**: Unauthorized party creates false data or identities.

### Characteristics

- **Goal**: Create fake data/identity
- **Effect**: Authenticity breach
- **Detection**: Requires verification mechanisms

### Attack Examples

| Attack | Target | Technique |
|--------|--------|-----------|
| Spoofing | Identity | Fake credentials |
| Replay attack | Transactions | Captured request reuse |
| CSRF | User actions | Forged requests |
| Cache poisoning | Cached data | Malicious cache entries |
| DNS spoofing | Domain resolution | Fake DNS responses |
| Certificate forgery | TLS | Fake certificates |

### Vulnerable Code Patterns (DO NOT USE)

```
# BAD: No replay protection (same request can be reused)

# BAD: No CSRF token validation on state-changing operations

# BAD: Predictable tokens (time-based UUIDs)

# BAD: No origin validation (CORS misconfigured)
```

### Checklist

- [ ] CSRF protection on state-changing operations
- [ ] Cryptographically random tokens
- [ ] Replay protection (nonces, timestamps)
- [ ] Origin validation (CORS properly configured)
- [ ] Certificate validation (no self-signed in prod)
- [ ] Request signing for sensitive operations

### Countermeasures

| Threat | Countermeasure |
|--------|----------------|
| Spoofing | Strong authentication, MFA |
| Replay | Nonces, timestamps, idempotency |
| CSRF | CSRF tokens, SameSite cookies |
| Cache poisoning | Cache key validation |

---

## Threat Analysis Template

For each identified threat:

```markdown
### Threat: [Name]

**Type**: [Interception/Interruption/Modification/Fabrication]

**Asset at Risk**: [What's affected]

**Attack Vector**:
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Likelihood**: [High/Medium/Low]
- Skill required: [High/Medium/Low]
- Access required: [Public/Authenticated/Privileged]
- Detection probability: [High/Medium/Low]

**Impact**: [Critical/High/Medium/Low]
- Confidentiality: [None/Partial/Complete]
- Integrity: [None/Partial/Complete]
- Availability: [None/Partial/Complete]

**Current Controls**: [Existing mitigations]

**Recommended Controls**: [Proposed mitigations]
```

---

## Quick Reference

```
┌─────────────────────────────────────────────────────────┐
│                   THREAT TYPES                          │
├──────────────┬──────────────────────────────────────────┤
│ INTERCEPTION │ Unauthorized ACCESS to data              │
│              │ → Encryption, access control             │
├──────────────┼──────────────────────────────────────────┤
│ INTERRUPTION │ Denial of SERVICE/availability           │
│              │ → Rate limiting, redundancy              │
├──────────────┼──────────────────────────────────────────┤
│ MODIFICATION │ Unauthorized CHANGE of data              │
│              │ → Input validation, integrity checks     │
├──────────────┼──────────────────────────────────────────┤
│ FABRICATION  │ Creation of FALSE data/identity          │
│              │ → Authentication, anti-replay            │
└──────────────┴──────────────────────────────────────────┘
```
