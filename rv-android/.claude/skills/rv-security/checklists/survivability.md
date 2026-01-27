# Survivability Checklist

System survivability analysis based on Resistance, Recognition, and Recovery (3R) framework.

---

## Survivability Framework

```
┌─────────────────────────────────────────────────────────────────┐
│                    SURVIVABILITY (3R)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │  RESISTANCE  │──►│ RECOGNITION  │──►│   RECOVERY   │        │
│  │   (Prevent)  │   │   (Detect)   │   │  (Respond)   │        │
│  └──────────────┘   └──────────────┘   └──────────────┘        │
│                                                                 │
│  Goal: System continues essential operations despite attacks    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

A survivable system maintains essential services even when:
- Under attack
- Partially compromised
- Experiencing failures

---

## 1. Resistance (Prevention)

**Goal**: Prevent attacks from succeeding.

### Strategies

| Strategy | Description | Implementation |
|----------|-------------|----------------|
| Access control | Limit who can access | Authentication, authorization |
| Encryption | Protect data confidentiality | TLS, encryption at rest |
| Validation | Reject malicious input | Input sanitization |
| Hardening | Reduce vulnerabilities | Patch management, config |
| Isolation | Limit blast radius | Network segmentation |

### Checklist

**Authentication & Authorization**
- [ ] Strong authentication required (MFA where appropriate)
- [ ] Role-based access control (RBAC) implemented
- [ ] Session management secure (timeout, invalidation)
- [ ] API authentication enforced

**Data Protection**
- [ ] Data encrypted in transit (TLS 1.2+)
- [ ] Data encrypted at rest
- [ ] Secrets managed securely (not in code)
- [ ] Backups encrypted

**Input Validation**
- [ ] All user input validated server-side
- [ ] Input validation uses allowlists
- [ ] File uploads validated and restricted
- [ ] SQL injection prevented (parameterized queries)

**System Hardening**
- [ ] Unnecessary services disabled
- [ ] Default credentials changed
- [ ] Security patches applied
- [ ] Debug features disabled in production

**Network Security**
- [ ] Firewall rules restrict access
- [ ] Network segmentation in place
- [ ] Egress filtering configured
- [ ] VPN/private network for sensitive operations

### Assessment Questions

1. What prevents unauthorized access?
2. What prevents data interception?
3. What prevents malicious input?
4. What reduces attack surface?

---

## 2. Recognition (Detection)

**Goal**: Detect attacks and anomalies in progress.

### Strategies

| Strategy | Description | Implementation |
|----------|-------------|----------------|
| Logging | Record security events | Centralized logging |
| Monitoring | Observe system behavior | Metrics, alerts |
| Intrusion detection | Identify attacks | IDS/IPS, anomaly detection |
| Audit trails | Track changes | Immutable logs |
| Health checks | Verify system state | Probes, synthetic tests |

### Checklist

**Logging**
- [ ] Security events logged (auth, access, errors)
- [ ] Logs include sufficient context (who, what, when, where)
- [ ] Logs are centralized
- [ ] Logs are tamper-resistant
- [ ] Log retention policy defined

**Monitoring**
- [ ] System metrics collected (CPU, memory, network)
- [ ] Application metrics collected (requests, errors, latency)
- [ ] Alerts configured for anomalies
- [ ] Dashboards for visibility

**Intrusion Detection**
- [ ] Network traffic monitored
- [ ] File integrity monitoring
- [ ] Behavioral analysis for anomalies
- [ ] Threat intelligence feeds integrated

**Audit**
- [ ] Configuration changes tracked
- [ ] Data access audited
- [ ] Administrative actions logged
- [ ] Audit logs protected from modification

### Key Events to Detect

| Category | Events |
|----------|--------|
| Authentication | Failed logins, unusual login patterns, credential changes |
| Authorization | Access denied, privilege escalation attempts |
| Data | Large downloads, unusual queries, bulk operations |
| System | Configuration changes, new processes, resource spikes |
| Network | Unusual traffic, new connections, port scans |

### Assessment Questions

1. How would we know if there's an attack in progress?
2. What anomalies would indicate compromise?
3. Are logs sufficient for forensics?
4. How quickly can we detect an incident?

---

## 3. Recovery (Response)

**Goal**: Restore essential services after attack or failure.

### Strategies

| Strategy | Description | Implementation |
|----------|-------------|----------------|
| Backup | Data recovery capability | Regular backups, tested restores |
| Failover | Service continuity | Redundancy, load balancing |
| Incident response | Coordinated reaction | Playbooks, team training |
| Containment | Limit damage | Isolation, kill switches |
| Forensics | Understand attack | Evidence preservation |

### Checklist

**Backup & Restore**
- [ ] Regular backups configured
- [ ] Backup integrity verified
- [ ] Restore procedures documented
- [ ] Restore procedures tested
- [ ] Recovery time objective (RTO) defined
- [ ] Recovery point objective (RPO) defined

**High Availability**
- [ ] Redundant components for critical services
- [ ] Automatic failover configured
- [ ] Load balancing in place
- [ ] Disaster recovery site (if applicable)

**Incident Response**
- [ ] Incident response plan documented
- [ ] Roles and responsibilities defined
- [ ] Communication channels established
- [ ] Escalation procedures defined
- [ ] Response team trained

**Containment**
- [ ] Ability to isolate compromised systems
- [ ] Ability to revoke credentials quickly
- [ ] Ability to block network access
- [ ] Kill switches for critical functions

**Forensics**
- [ ] Evidence preservation procedures
- [ ] Forensic tools available
- [ ] Chain of custody documented
- [ ] Post-incident review process

### Recovery Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| RTO (Recovery Time Objective) | Max acceptable downtime | e.g., 4 hours |
| RPO (Recovery Point Objective) | Max acceptable data loss | e.g., 1 hour |
| MTTR (Mean Time To Recovery) | Average recovery time | e.g., 2 hours |

### Assessment Questions

1. How do we recover from a data breach?
2. How do we restore service after an attack?
3. What's the maximum acceptable downtime?
4. How do we contain an active attack?

---

## Survivability Assessment Matrix

Use this matrix to assess current state and identify gaps:

| Area | Resistance | Recognition | Recovery |
|------|------------|-------------|----------|
| **Authentication** | [Current controls] | [Detection capability] | [Recovery plan] |
| **Data** | [Current controls] | [Detection capability] | [Recovery plan] |
| **Network** | [Current controls] | [Detection capability] | [Recovery plan] |
| **Application** | [Current controls] | [Detection capability] | [Recovery plan] |
| **Infrastructure** | [Current controls] | [Detection capability] | [Recovery plan] |

### Scoring Guide

| Score | Description |
|-------|-------------|
| 0 | No capability |
| 1 | Basic/ad-hoc capability |
| 2 | Documented procedures |
| 3 | Implemented and tested |
| 4 | Mature and continuously improved |

---

## Incident Response Workflow

```
┌─────────────┐
│   DETECT    │ ◄── Recognition
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   ANALYZE   │     Assess scope and impact
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   CONTAIN   │ ◄── Recovery
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  ERADICATE  │     Remove threat
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   RECOVER   │     Restore operations
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   REVIEW    │     Lessons learned
└─────────────┘
```

---

## Quick Reference

```
┌─────────────────────────────────────────────────────────┐
│               SURVIVABILITY (3R)                        │
├──────────────┬──────────────────────────────────────────┤
│  RESISTANCE  │ PREVENT attacks from succeeding          │
│              │ → Access control, encryption, validation │
│              │ → Hardening, isolation                   │
├──────────────┼──────────────────────────────────────────┤
│  RECOGNITION │ DETECT attacks in progress               │
│              │ → Logging, monitoring, IDS               │
│              │ → Audit trails, health checks            │
├──────────────┼──────────────────────────────────────────┤
│  RECOVERY    │ RESPOND and restore operations           │
│              │ → Backup, failover, incident response    │
│              │ → Containment, forensics                 │
└──────────────┴──────────────────────────────────────────┘
```

---

## Survivability Principles

1. **Essential services first** - Identify and protect critical functions
2. **Assume breach** - Plan for successful attacks, not just prevention
3. **Defense in depth** - Multiple layers at each stage
4. **Graceful degradation** - Partial functionality better than total failure
5. **Rapid recovery** - Minimize time to restore operations
6. **Learn and improve** - Use incidents to strengthen defenses
