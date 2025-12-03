# Collaboration Management Process Flow

## Overview

This document outlines the complete process flow for managing AWS Cleanrooms collaboration invitations and automatically associating existing resources (configured tables and ID namespaces).

## High-Level Process Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Collaboration Invitation Received            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
        ┌────────────────────────────────────┐
        │  List Pending Invitations         │
        │  (Check AWS + Config File)        │
        └────────────┬───────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
   Single Invite            Multiple Invites
   (1-5)                    (10+)
        │                         │
        │                         │
        ▼                         ▼
┌──────────────────┐    ┌──────────────────────┐
│ Accept Invitation│    │ Process All Invites  │
│ (Manual/Auto)    │    │ (Bulk Operation)     │
└────────┬─────────┘    └──────────┬───────────┘
         │                         │
         │                         │
         ▼                         ▼
┌──────────────────────────────────────────┐
│      Get Membership ID                   │
└────────────┬─────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────┐
│      Associate Resources                 │
│  ┌────────────────────────────────────┐ │
│  │ 1. Configured Tables               │ │
│  │    - All existing tables           │ │
│  │    - Naming: acx_{table_name}      │ │
│  └────────────────────────────────────┘ │
│  ┌────────────────────────────────────┐ │
│  │ 2. ID Namespace                    │ │
│  │    - ACXIdNamespace                │ │
│  │    - From Entity Resolution        │ │
│  └────────────────────────────────────┘ │
└────────────┬─────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────┐
│      Update Configuration File            │
│      (Track Collaboration Status)         │
└────────────┬─────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────┐
│      Verify Associations                 │
│      (Optional - Manual Check)            │
└──────────────────────────────────────────┘
```

## Detailed Process Flows

### Scenario 1: Single Collaboration Invitation

```
START: New Collaboration Invitation Received
│
├─► Step 1: List Pending Invitations
│   │
│   └─► Command: manage-collaboration-invites.py list
│       │
│       └─► Output: Collaboration details (ID, name, creator)
│
├─► Step 2: Accept Invitation
│   │
│   ├─► Option A: Automatic Acceptance with Auto-Associate
│   │   └─► Command: manage-collaboration-invites.py accept \
│   │       │         --collaboration-id <id> \
│   │       │         --auto-associate
│   │       │
│   │       └─► API Call: Accept invitation → Get membership ID
│   │       └─► Automatically associates tables and namespace
│   │
│   └─► Option B: Manual Acceptance
│       │
│       ├─► 1. Accept in AWS Console
│       │
│       ├─► 2. Get membership ID: aws cleanrooms list-memberships
│       │
│       └─► 3. Associate manually:
│           └─► Command: manage-collaboration-invites.py associate \
│               │         --membership-id <membership-id>
│
├─► Step 3: Associate Configured Tables
│   │
│   ├─► Discover configured tables dynamically
│   │   └─► API: list_configured_tables()
│   │   └─► Filter: Only tables starting with "part_"
│   │   └─► Exclude: part_n_a, part_n_a_a
│   │   └─► Sort alphabetically
│   │   └─► Limit: 25 tables (AWS quota)
│   │
│   ├─► For each discovered table:
│   │   │
│   │   ├─► Check if association exists
│   │   │   └─► API: list_configured_table_associations()
│   │   │
│   │   ├─► If NOT exists:
│   │   │   └─► Create association
│   │   │       └─► API: create_configured_table_association()
│   │   │           │
│   │   │           └─► Name: acx_{table_name}
│   │   │           └─► Role: cleanrooms-glue-s3-access
│   │   │
│   │   └─► If exists: Skip (idempotent)
│   │
│   ├─► Create collaboration analysis rules
│   │   └─► For each successful association
│   │   └─► Result receivers: Other member account (not data provider)
│   │
│   └─► Result: All tables associated with correct names and rules
│
├─► Step 4: Associate ID Namespace
│   │
│   ├─► Check if namespace association exists
│   │   └─► API: list_id_namespace_associations()
│   │
│   ├─► If NOT exists:
│   │   └─► Create namespace association
│   │       └─► API: create_id_namespace_association()
│   │           │
│   │           └─► Name: ACXIdNamespace
│   │           └─► ARN: From config/default
│   │
│   └─► If exists: Skip (idempotent)
│
├─► Step 5: Verify (Optional)
│   │
│   ├─► List table associations
│   │   └─► Command: aws cleanrooms list-configured-table-associations
│   │
│   └─► List namespace associations
│       └─► Command: aws cleanrooms list-id-namespace-associations
│
END: Collaboration Ready
```

### Scenario 2: Multiple Collaborations (10+)

```
START: Multiple Collaboration Invitations Received
│
├─► Step 1: Initialize Configuration (First Time Only)
│   │
│   └─► Command: manage-multiple-collaborations.py init-config
│       │
│       └─► Creates: collaboration-config.json
│           │
│           └─► Structure:
│               - defaults (region, role, namespace, etc.)
│               - collaborations (empty list)
│               - pending_invitations (empty list)
│
├─► Step 2: Process All Pending Invitations
│   │
│   └─► Command: manage-multiple-collaborations.py process-invites
│       │
│       ├─► Sub-step 2.1: List Invitations from AWS
│       │   │
│       │   └─► API: list_collaborations() → Filter INVITED status
│       │
│       ├─► Sub-step 2.2: Update Config File
│       │   │
│       │   └─► Write pending invitations to config
│       │
│       ├─► Sub-step 2.3: For Each Invitation
│       │   │
│       │   ├─► Accept invitation
│       │   │   └─► Get membership ID
│       │   │
│       │   ├─► Add to collaborations list in config
│       │   │
│       │   ├─► Associate configured tables
│       │   │
│       │   └─► Associate ID namespace
│       │
│       └─► Sub-step 2.4: Clear Pending Invitations
│           │
│           └─► Update config: pending_invitations = []
│
├─► Step 3: Verify All Collaborations
│   │
│   └─► Command: manage-multiple-collaborations.py list
│       │
│       └─► Display: All active collaborations and their status
│
END: All Collaborations Processed
```

### Scenario 3: Sync Existing Collaborations

```
START: New Configured Tables Added (or Resources Updated)
│
├─► Step 1: New Resources Available
│   │
│   ├─► New configured tables created (via Terraform)
│   │
│   └─► Or: ID namespace updated
│
├─► Step 2: Sync All Active Collaborations
│   │
│   └─► Command: manage-multiple-collaborations.py sync-all
│       │
│       ├─► Load configuration file
│       │   └─► Get all collaborations with status="active"
│       │
│       ├─► For Each Active Collaboration:
│       │   │
│       │   ├─► Get membership ID
│       │   │
│       │   ├─► If auto_associate_tables = true:
│       │   │   └─► Associate all configured tables
│       │   │       │
│       │   │       └─► For each table:
│       │   │           ├─► Check if association exists
│       │   │           └─► Create if missing
│       │   │
│       │   └─► If auto_associate_namespace = true:
│       │       └─► Associate ID namespace
│       │           │
│       │           └─► Check if exists, create if missing
│       │
│       └─► Summary: Tables associated, skipped, failed
│
END: All Collaborations Synced
```

## Integration with Terraform

### Pre-requisites (Managed by Terraform)

```
┌─────────────────────────────────────────┐
│      Terraform Infrastructure            │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │ Configured Tables                │   │
│  │ - part_ibe_01, part_ibe_02, etc. │   │
│  │ - Created via Terraform          │   │
│  └──────────────────────────────────┘   │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │ IAM Role                         │   │
│  │ - cleanrooms-glue-s3-access      │   │
│  │ - Permissions for Glue/S3        │   │
│  └──────────────────────────────────┘   │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │ Entity Resolution Namespace       │   │
│  │ - ACXIdNamespace                 │   │
│  │ - Created separately             │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### Scripts Manage (Per Membership)

```
┌─────────────────────────────────────────┐
│      Script-Managed Resources            │
│      (Per Collaboration/Membership)      │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │ Table Associations                │   │
│  │ - acx_part_ibe_01                 │   │
│  │ - acx_part_ibe_02                 │   │
│  │ - One per configured table        │   │
│  └──────────────────────────────────┘   │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │ Namespace Association             │   │
│  │ - ACXIdNamespace → Membership    │   │
│  │ - One per membership             │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

## Complete Workflow Example

### Example: Processing 5 New Invitations

```
Day 1: Invitations Received
│
├─► 5 collaboration invitations arrive
│
└─► Run: manage-multiple-collaborations.py process-invites
    │
    ├─► Invitation 1: AMC Collaboration
    │   ├─► Accept → Membership ID: abc-123
    │   ├─► Associate 28 tables
    │   └─► Associate namespace
    │
    ├─► Invitation 2: Partner A Collaboration
    │   ├─► Accept → Membership ID: def-456
    │   ├─► Associate 28 tables
    │   └─► Associate namespace
    │
    ├─► Invitation 3: Partner B Collaboration
    │   ├─► Accept → Membership ID: ghi-789
    │   ├─► Associate 28 tables
    │   └─► Associate namespace
    │
    ├─► Invitation 4: Partner C Collaboration
    │   ├─► Accept → Membership ID: jkl-012
    │   ├─► Associate 28 tables
    │   └─► Associate namespace
    │
    └─► Invitation 5: Partner D Collaboration
        ├─► Accept → Membership ID: mno-345
        ├─► Associate 28 tables
        └─► Associate namespace

Result: 5 collaborations active, 140 table associations created, 5 namespace associations
```

### Example: Adding New Tables Later

```
Week 2: New Tables Added via Terraform
│
├─► Terraform creates: part_new_table_01, part_new_table_02
│
└─► Run: manage-multiple-collaborations.py sync-all
    │
    ├─► Collaboration 1 (AMC): Associate 2 new tables
    ├─► Collaboration 2 (Partner A): Associate 2 new tables
    ├─► Collaboration 3 (Partner B): Associate 2 new tables
    ├─► Collaboration 4 (Partner C): Associate 2 new tables
    └─► Collaboration 5 (Partner D): Associate 2 new tables

Result: 10 new table associations created across 5 collaborations
```

## Decision Points

### When to Use Single vs Multi Script

```
┌─────────────────────────────────────┐
│  How many collaborations?           │
└────────────┬────────────────────────┘
             │
    ┌────────┴────────┐
    │                 │
    ▼                 ▼
1-5              10+
│                 │
│                 │
▼                 ▼
Use:              Use:
manage-           manage-multiple-
collaboration-    collaborations.py
invites.py        + config file
```

### When to Accept vs Associate

```
┌─────────────────────────────────────┐
│  Invitation Status?                 │
└────────────┬────────────────────────┘
             │
    ┌────────┴────────┐
    │                 │
    ▼                 ▼
Pending            Already Accepted
│                 │
│                 │
▼                 ▼
Use:              Use:
accept            associate
command           command
```

## Error Handling Flow

```
┌─────────────────────────────────────┐
│  Operation Attempted                 │
└────────────┬────────────────────────┘
             │
             ▼
    ┌────────────────┐
    │  Success?      │
    └────┬───────┬───┘
         │       │
      Yes│       │No
         │       │
         │       ▼
         │  ┌──────────────────────┐
         │  │ Check Error Type     │
         │  └────┬─────────────────┘
         │       │
         │   ┌───┴────┬──────────┬──────────┐
         │   │        │          │          │
         │   ▼        ▼          ▼          ▼
         │ Conflict  Not Found  Permission  Other
         │   │        │          │          │
         │   │        │          │          │
         │   ▼        ▼          ▼          ▼
         │ Skip    Log Error  Check IAM   Log & Continue
         │ (Idemp)            Permissions
         │
         ▼
    ┌──────────────────────┐
    │  Continue Next Item  │
    └──────────────────────┘
```

## State Management

### Configuration File State

```
Initial State:
{
  "collaborations": [],
  "pending_invitations": []
}

After Processing Invitations:
{
  "collaborations": [
    {
      "name": "AMC Collaboration",
      "membership_id": "abc-123",
      "status": "active",
      ...
    },
    ...
  ],
  "pending_invitations": []
}
```

### AWS State

```
Before:
- 5 pending invitations
- 0 memberships (for these collaborations)
- 0 table associations
- 0 namespace associations

After:
- 0 pending invitations
- 5 active memberships
- 140 table associations (28 tables × 5 memberships)
- 5 namespace associations
```

## Automation Opportunities

### Scheduled Sync

```
┌─────────────────────────────────────┐
│  Cron Job / Lambda (Daily)          │
└────────────┬────────────────────────┘
             │
             ▼
    ┌──────────────────────┐
    │  Check for New       │
    │  Invitations         │
    └────┬─────────────────┘
         │
         ▼
    ┌──────────────────────┐
    │  If Found:           │
    │  Process Invites     │
    └────┬─────────────────┘
         │
         ▼
    ┌──────────────────────┐
    │  Sync All Active     │
    │  Collaborations      │
    └──────────────────────┘
```

### CI/CD Integration

```
┌─────────────────────────────────────┐
│  Terraform Apply (New Tables)       │
└────────────┬────────────────────────┘
             │
             ▼
    ┌──────────────────────┐
    │  Post-Apply Hook      │
    └────┬─────────────────┘
         │
         ▼
    ┌──────────────────────┐
    │  Run: sync-all        │
    │  (Associate to all)   │
    └──────────────────────┘
```

## Summary

### Key Process Steps

1. **Discovery**: List pending invitations
2. **Acceptance**: Accept invitations (auto or manual)
3. **Association**: Associate tables and namespace
4. **Tracking**: Update configuration file
5. **Verification**: Verify associations (optional)
6. **Maintenance**: Periodic syncs for new resources

### Key Principles

- ✅ **Idempotent**: Safe to run multiple times
- ✅ **Automatic**: Minimal manual intervention
- ✅ **Scalable**: Handles 10+ collaborations efficiently
- ✅ **Trackable**: Configuration file tracks all state
- ✅ **Integrated**: Works with existing Terraform infrastructure

---

**Last Updated**: November 18, 2025

