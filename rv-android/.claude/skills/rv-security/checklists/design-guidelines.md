# Security Design Guidelines Checklist

10 fundamental security design guidelines based on established security engineering principles.

---

## 1. Base Security Decisions on an Explicit Security Policy

**Principle**: Security requirements must be derived from a clear security policy.

### Checklist

- [ ] Security policy exists and is documented
- [ ] Policy defines what assets need protection
- [ ] Policy specifies acceptable risk levels
- [ ] Policy is reviewed and updated periodically
- [ ] Implementation decisions trace back to policy

### Questions to Ask

- What is the security policy for this system?
- Who defined the policy and when was it last reviewed?
- How do current controls map to policy requirements?

---

## 2. Implement Defense in Depth

**Principle**: Use multiple layers of protection so compromise of one layer doesn't compromise the system.

### Checklist

- [ ] Multiple authentication factors where appropriate
- [ ] Network segmentation between components
- [ ] Application-level and infrastructure-level controls
- [ ] Encryption at rest AND in transit
- [ ] Input validation at multiple layers

### Layered Protection Model

```
┌─────────────────────────────────────┐
│         Network Layer               │  Firewalls, IDS/IPS
├─────────────────────────────────────┤
│         Transport Layer             │  TLS, certificate validation
├─────────────────────────────────────┤
│         Application Layer           │  Authentication, authorization
├─────────────────────────────────────┤
│         Data Layer                  │  Encryption, access controls
└─────────────────────────────────────┘
```

### Questions to Ask

- If this control fails, what prevents compromise?
- How many layers must an attacker bypass?
- Are layers independent (not sharing credentials/trust)?

---

## 3. Fail Securely

**Principle**: When failures occur, the system should default to a secure state.

### Checklist

- [ ] Error handlers don't expose sensitive information
- [ ] Failed authentication denies access (not grants)
- [ ] Exceptions don't leave system in inconsistent state
- [ ] Resource exhaustion doesn't bypass security checks
- [ ] Timeouts default to denial, not approval

### Common Failures

| Failure Type | Insecure Default | Secure Default |
|--------------|------------------|----------------|
| Auth timeout | Grant access | Deny access |
| Config missing | Use defaults | Fail startup |
| Exception | Return partial data | Return error |
| Resource limit | Skip validation | Reject request |

### Questions to Ask

- What happens when X fails?
- Is the failure state secure by default?
- Can an attacker force failures to bypass security?

---

## 4. Apply Principle of Least Privilege

**Principle**: Every component should have only the minimum permissions needed.

### Checklist

- [ ] Service accounts have minimal permissions
- [ ] Users have role-based access (not blanket admin)
- [ ] Temporary credentials where possible
- [ ] Permissions are regularly audited
- [ ] No shared credentials between components

### Permission Review

| Component | Current Permissions | Actually Needed | Gap |
|-----------|---------------------|-----------------|-----|
| | | | |

### Questions to Ask

- Why does this component need X permission?
- What's the blast radius if this credential is compromised?
- Can permissions be scoped more narrowly?

---

## 5. Minimize Attack Surface

**Principle**: Reduce the number of entry points and potential vulnerabilities.

### Checklist

- [ ] Unused features/endpoints are disabled
- [ ] Only necessary ports are exposed
- [ ] Debug endpoints removed in production
- [ ] Dependencies minimized and updated
- [ ] Administrative interfaces restricted

### Attack Surface Inventory

| Entry Point | Purpose | Necessary? | Protection |
|-------------|---------|------------|------------|
| | | | |

### Questions to Ask

- Is this feature/endpoint necessary?
- Can this be internal-only?
- What's the minimum exposure needed?

---

## 6. Secure Defaults

**Principle**: Out-of-the-box configuration should be secure.

### Checklist

- [ ] Default passwords are NOT used
- [ ] Security features enabled by default
- [ ] Verbose logging disabled by default (prod)
- [ ] Debug mode off by default
- [ ] Encryption enabled by default

### Configuration Review

| Setting | Default Value | Secure? | Recommendation |
|---------|---------------|---------|----------------|
| | | | |

### Questions to Ask

- What happens if the user doesn't configure security?
- Are insecure options opt-in (not opt-out)?
- Is the secure configuration the easy path?

---

## 7. Validate All Inputs

**Principle**: Never trust input from external sources.

### Checklist

- [ ] All user input is validated
- [ ] API inputs are validated (even from trusted services)
- [ ] File uploads are validated (type, size, content)
- [ ] Validation uses allowlists (not blocklists)
- [ ] Validation happens server-side (not just client)

### Input Validation Matrix

| Input Source | Type | Validation | Sanitization |
|--------------|------|------------|--------------|
| User form | String | Length, format | HTML escape |
| API param | JSON | Schema | Type coercion |
| File upload | Binary | Type, size | Virus scan |
| URL param | String | Format | URL decode |

### Common Injection Points

- SQL: `' OR 1=1 --`
- Command: `; rm -rf /`
- XSS: `<script>alert(1)</script>`
- Path: `../../../etc/passwd`

### Questions to Ask

- Where does this input come from?
- What could an attacker put here?
- Is validation positive (allowlist) or negative (blocklist)?

---

## 8. Compartmentalize (Separation of Concerns)

**Principle**: Isolate components so compromise of one doesn't affect others.

### Checklist

- [ ] Components run with separate identities
- [ ] Network segmentation between tiers
- [ ] Secrets isolated per component
- [ ] Data access restricted per component
- [ ] Failure domains are isolated

### Compartmentalization Model

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Frontend  │───►│   Backend   │───►│  Database   │
│  (limited)  │    │ (service)   │    │  (isolated) │
└─────────────┘    └─────────────┘    └─────────────┘
      │                  │                   │
   Network A         Network B          Network C
```

### Questions to Ask

- If this component is compromised, what else is affected?
- Can components access each other's secrets?
- Are failure domains independent?

---

## 9. Log Security-Relevant Events

**Principle**: Maintain audit trail for security events.

### Checklist

- [ ] Authentication events logged (success/failure)
- [ ] Authorization failures logged
- [ ] Sensitive data access logged
- [ ] Configuration changes logged
- [ ] Logs are protected from tampering

### Security Events to Log

| Event Type | What to Log | What NOT to Log |
|------------|-------------|-----------------|
| Auth | User, time, IP, result | Password |
| Access | Resource, user, action | Full request body |
| Error | Type, context, stack | Sensitive data in error |
| Config | Change, user, before/after | Secret values |

### Log Security

- [ ] Logs stored separately from application
- [ ] Log integrity protection (signing, append-only)
- [ ] Log retention policy defined
- [ ] Logs don't contain secrets/PII

### Questions to Ask

- Can we detect an attack from logs alone?
- Can an attacker tamper with logs?
- Is log retention sufficient for incident investigation?

---

## 10. Design for Recovery

**Principle**: Plan for security incidents and ensure recovery capability.

### Checklist

- [ ] Backup strategy documented and tested
- [ ] Incident response plan exists
- [ ] Recovery procedures documented
- [ ] Recovery time objectives defined
- [ ] Regular recovery testing

### Recovery Capabilities

| Scenario | Detection | Response | Recovery Time |
|----------|-----------|----------|---------------|
| Credential leak | | | |
| Data breach | | | |
| Ransomware | | | |
| DDoS | | | |

### Questions to Ask

- How would we detect this incident?
- What's our response procedure?
- How long to recover?
- Have we tested recovery?

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│           10 SECURITY DESIGN GUIDELINES                 │
├─────────────────────────────────────────────────────────┤
│  1. BASE ON POLICY        → Clear security policy       │
│  2. DEFENSE IN DEPTH      → Multiple layers             │
│  3. FAIL SECURELY         → Secure default state        │
│  4. LEAST PRIVILEGE       → Minimum permissions         │
│  5. MINIMIZE SURFACE      → Reduce entry points         │
│  6. SECURE DEFAULTS       → Safe out-of-box             │
│  7. VALIDATE INPUTS       → Trust nothing               │
│  8. COMPARTMENTALIZE      → Isolate components          │
│  9. LOG EVENTS            → Audit trail                 │
│ 10. DESIGN FOR RECOVERY   → Plan for incidents          │
└─────────────────────────────────────────────────────────┘
```
