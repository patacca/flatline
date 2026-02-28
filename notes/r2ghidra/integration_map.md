# r2ghidra Integration Map

Source root:
- `third_party/r2ghidra`

## Objective
Map how `r2ghidra` drives Ghidra decompilation and classify integration pieces for reuse in `ghidralib`.

## Required Sections

### 1. Decompiler State Initialization
- Relevant files/functions:
- Notes:
- Classification: `Reusable as-is` | `Reimplement in ghidralib` | `Not needed for MVP`

### 2. Binary Bytes and Memory Model
- Relevant files/functions:
- Notes:
- Classification: `Reusable as-is` | `Reimplement in ghidralib` | `Not needed for MVP`

### 3. Architecture and Context Metadata
- Relevant files/functions:
- Notes:
- Classification: `Reusable as-is` | `Reimplement in ghidralib` | `Not needed for MVP`

### 4. Decompilation Invocation Path
- Relevant files/functions:
- Notes:
- Classification: `Reusable as-is` | `Reimplement in ghidralib` | `Not needed for MVP`

### 5. Output and Error Handling
- Relevant files/functions:
- Notes:
- Classification: `Reusable as-is` | `Reimplement in ghidralib` | `Not needed for MVP`

### 6. Radare2 Adapter Boundaries
- Adapter-only code:
- Generic decompiler glue:
- Notes:
