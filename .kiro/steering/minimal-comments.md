---
inclusion: always
---

# Global Code Style: Minimal Comments

**Version**: 1.1  
**Last Updated**: December 16, 2024

## Comment Policy

### ✅ **INCLUDE Comments For:**
- **Complex business logic** that isn't obvious from the code
- **Performance trade-offs** and optimization decisions  
- **Workarounds** for bugs or limitations
- **Non-obvious algorithms** or mathematical formulas
- **External dependencies** behavior that's surprising
- **Why** certain approaches were chosen over alternatives

### ❌ **EXCLUDE Comments For:**
- **Self-documenting code** where variable/method names are clear
- **Standard operations** (assignments, basic transformations)
- **Obvious patterns** (filtering, mapping, validation)
- **Method calls** that clearly describe their purpose
- **Variable declarations** with descriptive names
- **Any mention of deprecations, legacy structures, or previous naming**

### Examples

```scala
// ❌ DON'T: Obvious from variable name and method
val filteredFinancialInformation = LeadImporterUtil.applyBankInfoFiltering(lead, lead.financialInformation, subAccountCache)

// ✅ DO: Explains non-obvious business requirement  
val filteredFinancialInformation = LeadImporterUtil.applyBankInfoFiltering(lead, lead.financialInformation, subAccountCache)
// MoneyLion accounts are excluded from VAN filtering per PL-1837 due to ACH return requirements

// ❌ DON'T: Method name is self-explanatory
// Map employment status to partner format
val partnerEmploymentStatus = mapEmploymentStatus(leadEmploymentStatus)

// ✅ DO: Explains why this specific mapping approach
val partnerEmploymentStatus = mapEmploymentStatus(leadEmploymentStatus)  
// Partner requires non-standard enum values that don't align with industry standards
```

## Implementation Behavior

### 🚨 **CRITICAL**: Always Implement Changes
When the user asks to implement, modify, or fix code:
- **ACTUALLY MAKE THE CHANGES** to the files using available tools
- **DO NOT** just provide code suggestions or examples
- **DO NOT** ask for confirmation unless there are ambiguous requirements
- **IMPLEMENT FIRST**, explain second

## Implementation Instructions

1. **Apply this rule globally** across all repositories and languages
2. **Override project-specific settings** when they conflict
3. **Focus on code readability** through naming rather than comments
4. **Prioritize "why" over "what"** when comments are necessary
5. **Always implement actual changes when requested**

## Rule Evolution

Update this rule when:
- Code review patterns reveal missing context
- Team feedback indicates confusion in specific areas
- New language patterns emerge requiring clarification

## Prohibited Content in Comments

- Do not reference deprecated modules, previous directory structures, migrations, or legacy names.
- Comments must describe the current state only (intent, constraints, trade-offs) without historical context.