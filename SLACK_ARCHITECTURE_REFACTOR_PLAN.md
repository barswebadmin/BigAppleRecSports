# Slack Architecture Refactor - Comprehensive Plan

**Goal:** Establish clean architectural boundaries between business logic, orchestration, and transport layers following Domain-Driven Design principles.

**Status:** Planning Phase  
**Estimated Time:** 40-60 hours over 2-3 weeks  
**Last Updated:** January 2, 2026

---

## 🎯 **Target Architecture**

### **Three-Layer Separation**

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: Business Domain (Pure Logic)                      │
│  backend/modules/{refunds|orders|products|leadership}/       │
│  - Zero knowledge of Slack/Shopify/AWS                       │
│  - Pure Python domain models and services                    │
│  - 100% unit testable without mocks                          │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ Data Transfer Objects (DTOs)
                            │
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: Integration Orchestrators (Thin Adapters)         │
│  backend/modules/integrations/slack/{service}/               │
│  - Bolt apps with handlers (one per domain)                  │
│  - Extract Slack data → Call domain → Format response        │
│  - NO business logic, NO decisions                           │
│  - Handlers: <100 lines each                                 │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ Slack SDK Calls
                            │
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: Transport & Formatting (Business-Agnostic)        │
│  backend/modules/integrations/slack/client/                  │
│  backend/modules/integrations/slack/builders/                │
│  - Slack API client wrappers                                 │
│  - Generic message builders                                  │
│  - Security, parsing, formatting utilities                   │
│  - Reusable across all domains                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 **Current State Analysis**

### **Code Volume by Layer (Lines of Code)**

```
Current State (Mixed Architecture):
├── slack_service.py                    500   ❌ Mixed business + transport
├── slack_refunds_utils.py              103   ❌ Business logic in Slack layer
├── leadership/handlers.py            2,189   ❌ 90% business logic, 10% Slack
├── message_builder_legacy.py         1,292   ❌ Refund-specific (should be generic)
├── message_builder.py                  488   ✅ Mostly generic
├── modal_handlers.py                   449   ✅ Generic
├── order_handlers.py                   203   ❌ Business decisions mixed in
├── client/*.py                       1,100   ✅ Transport layer (good)
└── parsers/message_parsers.py          197   ✅ Generic parsing (good)
                                      ─────
                                      6,521   Total Slack-related code

Business Modules (Mostly Good):
├── refunds/                            ~800   ✅ Domain logic
├── orders/services/                  ~1,100   ✅ Domain logic
├── products/services/                ~3,500   ✅ Domain logic
└── leadership/                         ~300   ⚠️  CLI-focused, needs service layer
                                      ─────
                                      5,700   Total business logic

Target State (Clean Separation):
├── Domain (modules/)                 8,000   Pure business logic
├── Orchestrators (integrations/)     2,000   Thin Slack adapters
└── Transport (client/builders/)      1,500   Generic Slack utilities
                                      ─────
                                     11,500   Total (20-30% growth for proper structure)
```

### **Problems in Current Architecture**

#### **1. Business Logic in Slack Layer**
- ❌ `leadership/handlers.py` (2,189 lines): CSV parsing, position matching, hierarchy building
- ❌ `order_handlers.py` (203 lines): Order cancellation decisions, refund calculations
- ❌ `slack_refunds_utils.py` (103 lines): Refund eligibility logic
- ❌ `slack_service.py` (500 lines): Mixed transport and business coordination

#### **2. Domain-Specific Message Builders**
- ❌ `message_builder_legacy.py` (1,292 lines): Refund-specific message formatting
- ❌ Violates "business-agnostic" principle for transport layer

#### **3. Missing Domain Services**
- ⚠️  `modules/leadership/` has no proper service layer (only CLI scripts)
- ⚠️  Refund eligibility logic scattered across Slack and refunds modules
- ⚠️  Order cancellation logic mixed with Slack handlers

#### **4. Tight Coupling**
- ❌ Can't test business logic without Slack SDK
- ❌ Can't reuse CSV parsing for non-Slack interfaces (CLI, API, webhooks)
- ❌ Hard to add new interfaces (Discord, Teams, etc.)

---

## 📋 **Code Quality Standards (Enforced Throughout)**

### **Minimal Comments Policy**
- **Favor readable names** over comments
- When commenting, explain "**why**" not "**what**"
- Docstrings: Brief, focus on business rules or non-obvious behavior
- **No inline imports** unless absolutely necessary (circular dependency only)

### **Import Organization**
```python
# Standard library (native to Python)
import json
import os
from typing import List, Dict

# External libraries
import pytest
from pydantic import BaseModel

# Internal modules
from modules.leadership.domain.models import PersonInfo
from shared import check_dict_equivalence
```

### **Testing Standards**
- **Pytest parameterization**: Single test method per feature with multiple cases
- **Avoid redundant tests**: 10 small tests → 1 parameterized test with 10 cases
- **Brief logs**: Focus on values under test, use colorization
- **Test placement**: Adjacent `tests/` directory to file-under-test

**Example:**
```python
# ❌ BAD: Many small redundant tests
def test_vacant_position_1():
    person = PersonInfo(name="Vacant", bars_email="")
    assert person.is_vacant() == True

def test_vacant_position_2():
    person = PersonInfo(name="  vacant  ", bars_email="")
    assert person.is_vacant() == True

def test_normal_position():
    person = PersonInfo(name="John", bars_email="john@bars.com")
    assert person.is_vacant() == False

# ✅ GOOD: Single test with parameterization
@pytest.mark.parametrize("name,bars_email,expected_vacant", [
    ("Vacant", "", True),
    ("  vacant  ", "", True),
    ("John", "john@bars.com", False),
])
def test_is_vacant(name, bars_email, expected_vacant):
    person = PersonInfo(name=name, bars_email=bars_email)
    assert person.is_vacant() == expected_vacant
```

---

## 🗺️ **Migration Roadmap**

### **🔥 CRITICAL: Legacy Code Elimination Tracker**

**Goal:** ZERO backward compatibility. Complete deletion of old dict-based builders.

| Phase | Action | Files to DELETE | Status |
|-------|--------|-----------------|--------|
| **Phase 1** | Create typed builders | - | ✅ Done |
| **Phase 2** | Leadership uses typed builders | - | ⬜ Pending |
| **Phase 3** | Refunds uses typed builders | `message_builder_legacy.py` (partial) | ⬜ Pending |
| **Phase 4** | Orders uses typed builders | - | ⬜ Pending |
| **Phase 5** | Products uses typed builders | - | ⬜ Pending |
| **Phase 6** | **DELETE ALL LEGACY** | `message_builder.py`<br>`message_builder_legacy.py` | ⬜ Pending |

**Legacy Code to ELIMINATE:**
```
❌ backend/modules/integrations/slack/builders/message_builder.py (489 lines)
   - SlackMessageBuilder class (dict-based)
   - build_header_block() → Replaced by GenericMessageBuilder.header()
   - build_section_block() → Replaced by GenericMessageBuilder.section()
   - build_hyperlink() → Replaced by GenericMessageBuilder.hyperlink()
   - get_group_mention() → Move to config/slack.py helper
   
❌ backend/modules/integrations/slack/builders/message_builder_legacy.py (1,292 lines)
   - SlackMessageBuilderLegacy class (refund-specific)
   - All 18 refund formatting methods → Migrate to refunds/formatters.py
   
❌ backend/modules/integrations/slack/slack_service.py (500 lines)
   - Monolithic service → Replace with domain-specific Bolt apps
   
❌ backend/modules/integrations/slack/slack_refunds_utils.py (103 lines)
   - Business logic in Slack layer → Move to refunds/services/
```

**Call Sites to Migrate (Found 10 files):**
- [ ] `slack_service.py` → Delete
- [ ] `slack_refunds_utils.py` → Delete
- [ ] `order_handlers.py` → Migrate to orders/formatters.py
- [ ] `order_create_handler.py` → Update to use typed builders
- [ ] `slack_notifier.py` → Update to use typed builders
- [ ] `test_message_building_consolidated.py` → Update tests
- [ ] `test_custom_refund_modal.py` → Update tests

---

### **Phase 1: Foundation** (Week 1, 8-12 hours)
- [x] ✅ Baseline audit complete
- [x] ✅ Create domain service interfaces
- [x] ✅ Extract generic message builder utilities (TYPED)
- [x] ✅ Establish testing patterns
- [x] ✅ Apply code quality standards (minimal comments, pytest parameterization)

### **Phase 2: Leadership Domain** (Week 1, 12-20 hours)
- [x] ✅ Stage 0: Baseline tests exist
- [ ] Stage 1: Extract domain models
- [ ] Stage 2: Extract CSV parser service
- [ ] Stage 3: Extract user enrichment service
- [ ] Stage 4: Refactor Slack handlers (thin)
- [ ] Stage 5: Cleanup & documentation

### **Phase 3: Refunds Domain** (Week 2, 12-16 hours)
- [ ] Stage 1: Extract refund eligibility service
- [ ] Stage 2: Extract refund calculation service
- [ ] Stage 3: Create refunds Bolt app
- [ ] Stage 4: Refactor message builders (generic)
- [ ] Stage 5: Remove slack_refunds_utils.py

### **Phase 4: Orders Domain** (Week 2-3, 10-14 hours)
- [ ] Stage 1: Extract order cancellation service
- [ ] Stage 2: Extract restock decision service
- [ ] Stage 3: Create orders Bolt app
- [ ] Stage 4: Refactor order_handlers.py (thin)
- [ ] Stage 5: Cleanup & documentation

### **Phase 5: Products/Inventory** (Week 3, 6-10 hours)
- [ ] Stage 1: Review existing product services
- [ ] Stage 2: Create inventory notification Bolt app
- [ ] Stage 3: Extract any Slack-specific logic
- [ ] Stage 4: Cleanup & documentation

### **Phase 6: Deprecate Legacy** (Week 3, 4-6 hours)
- [ ] Remove slack_service.py monolith
- [ ] Archive message_builder_legacy.py
- [ ] Update all routers to use Bolt apps
- [ ] Final integration testing

---

## 📋 **Detailed Migration Stages**

---

## **PHASE 1: FOUNDATION** (8-12 hours)

### **Stage 1.1: Create Domain Service Interfaces** (2 hours)

**Goal:** Define clear contracts between domains and Slack orchestrators.

**Create:**
```
backend/modules/shared/
├── interfaces/
│   ├── __init__.py
│   ├── domain_service.py      # Base interface for all domain services
│   └── notification_dto.py     # Standard DTOs for cross-layer communication
└── testing/
    ├── __init__.py
    └── test_helpers.py         # Shared test fixtures
```

**Example Interface:**
```python
# backend/modules/shared/interfaces/domain_service.py
from typing import Protocol, Any, Dict
from dataclasses import dataclass

@dataclass
class NotificationRequest:
    """Standard DTO for requesting notifications"""
    recipient_id: str
    message_type: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = None

class DomainService(Protocol):
    """Base protocol for all domain services"""
    def process(self, request: Any) -> Any:
        """Process a domain request and return result"""
        ...
```

### **Stage 1.2: Extract Generic Message Builder** (3 hours)

**Goal:** Make message builders business-agnostic and reusable.

**Refactor:**
```
backend/modules/integrations/slack/builders/
├── __init__.py
├── message_builder.py          # ✅ Keep (mostly generic)
├── message_builder_legacy.py   # ❌ Archive/deprecate
├── generic_builders.py          # 🆕 Extract all generic methods
├── block_builders.py            # 🆕 Slack Block Kit utilities
└── modal_handlers.py           # ✅ Keep (already generic)
```

**Extract to `generic_builders.py`:**
- Header blocks
- Section blocks
- Button actions
- Divider blocks
- Context blocks
- Hyperlink formatting
- User/channel mentions
- Timestamp formatting

**Example:**
```python
# backend/modules/integrations/slack/builders/generic_builders.py
class GenericMessageBuilder:
    """Business-agnostic Slack message building utilities."""
    
    @staticmethod
    def header(text: str) -> Dict:
        return {"type": "header", "text": {"type": "plain_text", "text": text}}
    
    @staticmethod
    def section(text: str, fields: List[str] = None) -> Dict:
        block = {"type": "section", "text": {"type": "mrkdwn", "text": text}}
        if fields:
            block["fields"] = [{"type": "mrkdwn", "text": f} for f in fields]
        return block
    
    @staticmethod
    def button(text: str, action_id: str, value: str, style: str = None) -> Dict:
        button = {
            "type": "button",
            "text": {"type": "plain_text", "text": text},
            "action_id": action_id,
            "value": value
        }
        if style:
            button["style"] = style
        return button
```

### **Stage 1.3: Establish Testing Patterns** (3 hours)

**Create:**
```
backend/modules/shared/testing/
├── __init__.py
├── slack_fixtures.py       # Mock Slack payloads
├── domain_fixtures.py      # Mock domain data
└── integration_helpers.py  # End-to-end test utilities
```

**Example Fixtures:**
```python
# backend/modules/shared/testing/slack_fixtures.py
import pytest
from typing import Dict, Any

@pytest.fixture
def mock_slack_user() -> Dict[str, Any]:
    return {
        "id": "U12345",
        "name": "test_user",
        "email": "test@example.com"
    }

@pytest.fixture
def mock_slack_message():
    return {
        "channel": "C12345",
        "ts": "1234567890.123456",
        "text": "Test message"
    }

@pytest.fixture
def mock_button_action():
    return {
        "type": "block_actions",
        "user": {"id": "U12345", "username": "test_user"},
        "actions": [{
            "action_id": "test_action",
            "value": "test_value"
        }]
    }
```

**Checklist:**
- [ ] Domain service interface created
- [ ] Generic message builders extracted
- [ ] Shared test fixtures created
- [ ] All existing tests still pass

---

## **PHASE 2: LEADERSHIP DOMAIN** (12-20 hours)

### **Target Structure:**
```
backend/modules/leadership/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── leadership_hierarchy.py    # 🆕 Domain models
│   └── position.py                # 🆕 Position, PersonInfo
├── services/
│   ├── __init__.py
│   ├── csv_parser.py              # 🆕 Extract from handlers
│   ├── user_enrichment.py         # 🆕 Extract Slack lookup
│   └── hierarchy_analyzer.py      # 🆕 Completeness analysis
├── tests/
│   ├── models/
│   │   └── test_leadership_hierarchy.py
│   └── services/
│       ├── test_csv_parser.py
│       └── test_user_enrichment.py
└── README.md

backend/modules/integrations/slack/leadership/
├── __init__.py
├── bolt_app.py                    # ✅ Keep
├── handlers.py                    # ♻️  Refactor (thin, <400 lines)
└── tests/
    ├── test_handlers.py
    └── test_integration.py
```

**See:** Previous `LEADERSHIP_MIGRATION_PLAN.md` for detailed steps (Stages 1-5).

**Summary:**
- **Stage 1:** Domain models (PersonInfo, Position, LeadershipHierarchy)
- **Stage 2:** CSV parsing service (pure business logic)
- **Stage 3:** User enrichment service (Slack client injection)
- **Stage 4:** Thin Slack handlers (<100 lines each)
- **Stage 5:** Documentation and cleanup

**Success Criteria:**
- ✅ handlers.py reduced from 2,189 to <400 lines
- ✅ Domain services have zero Slack imports
- ✅ >90% test coverage for domain services
- ✅ All baseline tests pass throughout

---

## **PHASE 3: REFUNDS DOMAIN** (12-16 hours)

### **Current State:**
```
❌ Business Logic Scattered:
├── modules/integrations/slack/slack_refunds_utils.py   (103 lines)
├── modules/integrations/slack/order_handlers.py        (203 lines)
├── modules/integrations/slack/message_builder_legacy.py (1,292 lines) ← DELETE
├── modules/integrations/slack/message_builder.py       (489 lines)  ← DELETE
└── modules/refunds/app/main.py                         (28 lines)

✅ Domain Logic Exists (Good Foundation):
└── modules/refunds/app/
    ├── calculate_refund_due.py
    └── helpers/process_initial_refund_request.py

❌ Call Sites Using Old SlackMessageBuilder:
├── slack_service.py                 (uses old builder)
├── slack_refunds_utils.py          (uses old builder)
├── order_handlers.py               (uses old builder)
└── order_create_handler.py         (uses old builder)
```

### **Target Structure:**
```
backend/modules/refunds/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── refund_request.py          # ✅ Keep
│   ├── refund_eligibility.py      # 🆕 Eligibility domain model
│   └── refund_calculation.py      # 🆕 Extract from app/
├── services/
│   ├── __init__.py
│   ├── refund_eligibility_service.py    # 🆕 Extract from Slack layer
│   ├── refund_calculation_service.py    # ♻️  Refactor existing
│   └── restock_decision_service.py      # 🆕 Extract from Slack layer
├── app/
│   └── main.py                    # ♻️  Simplify to orchestrate services
└── tests/
    ├── services/
    │   ├── test_eligibility.py
    │   ├── test_calculation.py
    │   └── test_restock.py
    └── integration/
        └── test_refund_flow.py

backend/modules/integrations/slack/refunds/
├── __init__.py
├── bolt_app.py                    # 🆕 New Bolt app
├── handlers.py                    # 🆕 Thin orchestration
├── formatters.py                  # 🆕 Refund-specific Slack formatting
└── tests/
    ├── test_handlers.py
    └── test_integration.py
```

### **Stage 3.1: Extract Refund Eligibility Service** (3 hours)

**Write Tests First:**
```python
# backend/modules/refunds/services/test_eligibility.py
def test_refund_eligible_within_window()
def test_refund_ineligible_outside_window()
def test_refund_eligible_with_credit()
def test_refund_requires_manager_approval()
def test_partial_refund_eligibility()
```

**Implement Service:**
```python
# backend/modules/refunds/services/refund_eligibility_service.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class EligibilityResult:
    eligible: bool
    reason: Optional[str] = None
    requires_approval: bool = False
    max_refund_amount: Optional[float] = None

class RefundEligibilityService:
    """
    Determines if a refund request is eligible based on business rules.
    Zero dependencies on Slack, Shopify, or other external systems.
    """
    
    def __init__(self, refund_window_days: int = 30):
        self.refund_window_days = refund_window_days
    
    def check_eligibility(
        self,
        order_date: datetime,
        request_date: datetime,
        order_amount: float,
        already_refunded: float = 0,
        is_manager_request: bool = False
    ) -> EligibilityResult:
        """Check if a refund is eligible based on business rules."""
        
        # Check time window
        days_since_order = (request_date - order_date).days
        if days_since_order > self.refund_window_days and not is_manager_request:
            return EligibilityResult(
                eligible=False,
                reason=f"Order is {days_since_order} days old (limit: {self.refund_window_days})"
            )
        
        # Check remaining refund amount
        remaining = order_amount - already_refunded
        if remaining <= 0:
            return EligibilityResult(
                eligible=False,
                reason="Order has already been fully refunded"
            )
        
        # Check if requires approval
        requires_approval = days_since_order > (self.refund_window_days // 2)
        
        return EligibilityResult(
            eligible=True,
            requires_approval=requires_approval,
            max_refund_amount=remaining
        )
```

**Extract from:**
- `slack_refunds_utils.py`: Eligibility checks
- `order_handlers.py`: Time window logic

### **Stage 3.2: Extract Restock Decision Service** (2 hours)

**Write Tests First:**
```python
# backend/modules/refunds/services/test_restock.py
def test_restock_required_for_active_product()
def test_restock_not_required_for_ended_season()
def test_restock_for_waitlist_items()
```

**Implement Service:**
```python
# backend/modules/refunds/services/restock_decision_service.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class RestockDecision:
    should_restock: bool
    reason: str
    priority: int = 1  # 1=normal, 2=high, 3=urgent

class RestockDecisionService:
    """
    Determines if inventory should be restocked after a refund.
    Business logic only - no Slack or Shopify knowledge.
    """
    
    def decide_restock(
        self,
        product_active: bool,
        season_end_date: Optional[datetime],
        current_date: datetime,
        has_waitlist: bool = False,
        current_inventory: int = 0
    ) -> RestockDecision:
        """Decide if restocking is needed."""
        
        if not product_active:
            return RestockDecision(
                should_restock=False,
                reason="Product is no longer active"
            )
        
        # Check if season has ended
        if season_end_date and current_date > season_end_date:
            return RestockDecision(
                should_restock=False,
                reason="Season has ended"
            )
        
        # High priority if waitlist exists
        if has_waitlist:
            return RestockDecision(
                should_restock=True,
                reason="Waitlist exists for this product",
                priority=3
            )
        
        # Normal restock if inventory is low
        if current_inventory < 5:
            return RestockDecision(
                should_restock=True,
                reason="Inventory is low",
                priority=2
            )
        
        return RestockDecision(
            should_restock=True,
            reason="Standard restock",
            priority=1
        )
```

### **Stage 3.3: Create Refunds Bolt App** (4 hours)

**Create Bolt App:**
```python
# backend/modules/integrations/slack/refunds/bolt_app.py
from slack_bolt import App
from config.slack import SlackConfig

app = App(
    token=SlackConfig.Bots.Refunds.token,
    signing_secret=SlackConfig.Bots.Refunds.signing_secret
)
```

**Create Thin Handlers:**
```python
# backend/modules/integrations/slack/refunds/handlers.py
from slack_bolt import App
from modules.refunds.services.refund_eligibility_service import RefundEligibilityService
from modules.refunds.services.restock_decision_service import RestockDecisionService
from .formatters import format_eligibility_result, format_restock_decision

app = App(...)

eligibility_service = RefundEligibilityService()
restock_service = RestockDecisionService()

@app.command("/check-refund-eligibility")
def handle_check_eligibility(ack, command, client):
    ack()
    
    # 1. Extract data from Slack
    order_number = command["text"]
    user_id = command["user_id"]
    
    # 2. Fetch order details (use Shopify service)
    order = shopify_service.get_order(order_number)
    
    # 3. Call domain service
    result = eligibility_service.check_eligibility(
        order_date=order.created_at,
        request_date=datetime.now(),
        order_amount=order.total,
        already_refunded=order.refunded_amount
    )
    
    # 4. Format for Slack
    message = format_eligibility_result(result, order_number)
    
    # 5. Send via Slack
    client.chat_postEphemeral(
        channel=command["channel_id"],
        user=user_id,
        **message
    )

@app.action("process_refund")
def handle_process_refund(ack, body, client):
    ack()
    
    # 1. Extract data
    order_number = body["actions"][0]["value"]
    
    # 2. Call domain service
    refund_result = refunds_service.process_refund(order_number)
    
    # 3. Call restock service
    restock_decision = restock_service.decide_restock(
        product_active=refund_result.product_active,
        season_end_date=refund_result.season_end,
        current_date=datetime.now(),
        has_waitlist=refund_result.has_waitlist
    )
    
    # 4. Format and send
    message = format_restock_decision(restock_decision)
    client.chat_update(...)
```

**Handler Responsibilities:**
1. ✅ Extract data from Slack payload
2. ✅ Call domain services
3. ✅ Format response for Slack
4. ✅ Send via Slack client
5. ❌ NO business logic
6. ❌ NO refund calculations
7. ❌ NO eligibility checks

### **Stage 3.4: Extract Refund Message Formatters** (2 hours)

**Goal:** Create typed formatters and **migrate away from old `SlackMessageBuilder`**

**Create:**
```python
# backend/modules/integrations/slack/refunds/formatters.py
from typing import Dict, Any, List
from modules.refunds.services.refund_eligibility_service import EligibilityResult
from modules.integrations.slack.builders import GenericMessageBuilder  # ← NEW TYPED
from slack_sdk.models.blocks import Block

class RefundMessageFormatter:
    """
    Format refund domain objects into Slack messages using TYPED builders.
    
    Replaces all functionality from:
    - message_builder.py (old dict-based builder)
    - message_builder_legacy.py (refund-specific legacy code)
    """
    
    def __init__(self):
        self.builder = GenericMessageBuilder()  # ← TYPED, not old SlackMessageBuilder
    
    def format_eligibility_result(
        self, 
        result: EligibilityResult, 
        order_number: str
    ) -> Dict[str, Any]:
        """Format eligibility check result for Slack using TYPED blocks."""
        
        if result.eligible:
            emoji = "✅"
            status = "Eligible"
        else:
            emoji = "❌"
            status = "Ineligible"
        
        # ✅ Build with TYPED Slack SDK models
        blocks: List[Block] = [
            self.builder.header(f"{emoji} Refund {status}"),
            self.builder.section(f"*Order:* #{order_number}"),
        ]
        
        if result.reason:
            blocks.append(self.builder.section(f"*Reason:* {result.reason}"))
        
        if result.requires_approval:
            blocks.append(self.builder.section("⚠️ *Requires manager approval*"))
        
        if result.max_refund_amount:
            blocks.append(
                self.builder.section(
                    f"*Max Refund:* ${result.max_refund_amount:.2f}"
                )
            )
        
        # Convert to dict for Slack API
        return {
            "blocks": self.builder.blocks_to_dict(blocks),
            "text": f"Refund {status}"
        }
    
    def format_refund_decision(
        self,
        order_number: str,
        customer_name: str,
        refund_amount: float,
        refund_type: str
    ) -> Dict[str, Any]:
        """
        Format refund decision message.
        Replaces message_builder_legacy.create_refund_decision_message()
        """
        # ✅ Use TYPED builders, not old dict-based methods
        blocks = [
            self.builder.header(f"💵 Refund Request: #{order_number}"),
            self.builder.section(
                f"*Customer:* {customer_name}\n"
                f"*Amount:* ${refund_amount:.2f}\n"
                f"*Type:* {refund_type.title()}"
            ),
            self.builder.divider(),
        ]
        
        # Action buttons
        approve_btn = self.builder.button(
            text="Approve Refund",
            action_id="approve_refund",
            value=order_number,
            style="primary"
        )
        deny_btn = self.builder.button(
            text="Deny Request",
            action_id="deny_refund",
            value=order_number,
            style="danger"
        )
        
        blocks.append(self.builder.actions([approve_btn, deny_btn]))
        
        return {"blocks": self.builder.blocks_to_dict(blocks)}
```

**Migration Checklist:**
- [ ] All refund messages use `RefundMessageFormatter` (typed)
- [ ] Zero calls to old `SlackMessageBuilder.build_*()` methods
- [ ] Zero calls to `message_builder_legacy` methods
- [ ] All tests updated to use typed builders

### **Stage 3.5: Deprecate slack_refunds_utils.py** (1 hour)

**Steps:**
1. Move all remaining logic to appropriate services
2. Update imports across codebase
3. Delete `slack_refunds_utils.py`
4. Run full test suite

**Checklist:**
- [ ] Eligibility service extracted and tested
- [ ] Restock service extracted and tested
- [ ] Refunds Bolt app created
- [ ] Thin handlers implemented (<100 lines each)
- [ ] Message formatters extracted
- [ ] slack_refunds_utils.py deleted
- [ ] All tests pass
- [ ] Manual Slack testing successful

---

## **PHASE 4: ORDERS DOMAIN** (10-14 hours)

### **Current State:**
```
❌ Business Logic in Slack:
└── modules/integrations/slack/builders/order_handlers.py (203 lines)
    - Order cancellation decisions
    - Restock coordination
    - Message parsing

✅ Domain Logic Exists:
└── modules/orders/services/
    ├── orders_service.py           (good foundation)
    └── order_create_handler.py     (webhook handler)
```

### **Target Structure:**
```
backend/modules/orders/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── order.py                   # ♻️  Enhance existing
│   └── cancellation.py            # 🆕 Cancellation domain model
├── services/
│   ├── __init__.py
│   ├── orders_service.py          # ✅ Keep
│   ├── order_cancellation_service.py    # 🆕 Extract from Slack
│   └── order_create_handler.py    # ✅ Keep
└── tests/
    ├── services/
    │   └── test_cancellation.py
    └── integration/
        └── test_order_flow.py

backend/modules/integrations/slack/orders/
├── __init__.py
├── bolt_app.py                    # 🆕 New Bolt app
├── handlers.py                    # 🆕 Thin orchestration
├── formatters.py                  # 🆕 Order-specific Slack formatting
└── tests/
    ├── test_handlers.py
    └── test_integration.py
```

### **Stage 4.1: Extract Order Cancellation Service** (4 hours)

**Write Tests First:**
```python
# backend/modules/orders/services/test_cancellation.py
def test_cancel_order_within_window()
def test_cancel_order_after_window_requires_approval()
def test_cancel_order_already_fulfilled()
def test_partial_cancellation()
```

**Implement Service:**
```python
# backend/modules/orders/services/order_cancellation_service.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class CancellationReason(Enum):
    CUSTOMER_REQUEST = "customer_request"
    DUPLICATE = "duplicate"
    FRAUD = "fraud"
    OTHER = "other"

@dataclass
class CancellationRequest:
    order_number: str
    reason: CancellationReason
    requested_by: str
    notes: Optional[str] = None

@dataclass
class CancellationResult:
    success: bool
    can_cancel: bool
    requires_approval: bool = False
    reason: Optional[str] = None
    refund_amount: Optional[float] = None

class OrderCancellationService:
    """
    Handles order cancellation business logic.
    Zero dependencies on Slack, Shopify implementation details.
    """
    
    def __init__(self, cancellation_window_hours: int = 24):
        self.cancellation_window_hours = cancellation_window_hours
    
    def can_cancel_order(
        self,
        order_created_at: datetime,
        order_fulfillment_status: str,
        current_time: datetime,
        is_manager: bool = False
    ) -> CancellationResult:
        """Determine if an order can be cancelled."""
        
        hours_since_order = (current_time - order_created_at).total_seconds() / 3600
        
        # Check if already fulfilled
        if order_fulfillment_status in ["fulfilled", "partially_fulfilled"]:
            return CancellationResult(
                success=False,
                can_cancel=False,
                reason="Order has already been fulfilled"
            )
        
        # Within automatic cancellation window
        if hours_since_order <= self.cancellation_window_hours:
            return CancellationResult(
                success=True,
                can_cancel=True,
                requires_approval=False
            )
        
        # Outside window - requires manager approval
        if is_manager:
            return CancellationResult(
                success=True,
                can_cancel=True,
                requires_approval=False,
                reason="Manager override"
            )
        
        return CancellationResult(
            success=False,
            can_cancel=True,
            requires_approval=True,
            reason=f"Order is {hours_since_order:.1f} hours old (limit: {self.cancellation_window_hours})"
        )
```

**Extract from:** `order_handlers.py` cancellation logic

### **Stage 4.2: Create Orders Bolt App** (3 hours)

**Create Handlers:**
```python
# backend/modules/integrations/slack/orders/handlers.py
from slack_bolt import App
from modules.orders.services.order_cancellation_service import OrderCancellationService
from .formatters import format_cancellation_result

app = App(...)
cancellation_service = OrderCancellationService()

@app.action("cancel_order")
def handle_cancel_order(ack, body, client):
    ack()
    
    # 1. Extract data
    order_number = body["actions"][0]["value"]
    user_id = body["user"]["id"]
    
    # 2. Fetch order details
    order = shopify_service.get_order(order_number)
    
    # 3. Call domain service
    result = cancellation_service.can_cancel_order(
        order_created_at=order.created_at,
        order_fulfillment_status=order.fulfillment_status,
        current_time=datetime.now()
    )
    
    # 4. Format for Slack
    message = format_cancellation_result(result, order_number)
    
    # 5. Send via Slack
    client.chat_update(...)
```

### **Stage 4.3: Refactor order_handlers.py** (2 hours)

**Before:** 203 lines with business logic  
**After:** <100 lines, thin orchestration only

**Remove:**
- ❌ Cancellation eligibility logic → Move to domain service
- ❌ Restock decision logic → Already in RefundsService
- ❌ Message parsing → Already in message_parsers.py

**Keep:**
- ✅ Slack payload extraction
- ✅ Service orchestration
- ✅ Response formatting

### **Stage 4.4: Cleanup & Documentation** (1 hour)

**Checklist:**
- [ ] Cancellation service extracted and tested
- [ ] Orders Bolt app created
- [ ] order_handlers.py refactored to <100 lines
- [ ] Message formatters extracted
- [ ] All tests pass
- [ ] Manual Slack testing successful

---

## **PHASE 5: PRODUCTS/INVENTORY** (6-10 hours)

### **Current State:**
```
✅ Business Logic Already Clean:
└── modules/products/services/
    ├── product_update_handler.py     # Webhook handler
    ├── products_service.py           # Product operations
    └── create_product_complete_process/

❌ Minimal Slack Integration Needed:
└── Inventory notifications currently ad-hoc
```

### **Target Structure:**
```
backend/modules/integrations/slack/inventory/
├── __init__.py
├── bolt_app.py                    # 🆕 Inventory notifications
├── handlers.py                    # 🆕 Webhook → Slack bridge
├── formatters.py                  # 🆕 Inventory message formatting
└── tests/
    └── test_handlers.py
```

### **Stage 5.1: Create Inventory Bolt App** (3 hours)

**Purpose:** Bridge product webhooks to Slack notifications

```python
# backend/modules/integrations/slack/inventory/handlers.py
from slack_bolt import App
from modules.products.services.product_update_handler import ProductUpdateHandler
from .formatters import format_inventory_update

app = App(...)

@app.event("inventory_low")
def handle_low_inventory(event, client):
    # 1. Extract product data
    product_id = event["product_id"]
    current_stock = event["current_stock"]
    
    # 2. Format for Slack
    message = format_inventory_update(product_id, current_stock)
    
    # 3. Notify relevant channel
    client.chat_postMessage(
        channel=config.Channels.Inventory.id,
        **message
    )
```

### **Stage 5.2: Extract Notification Logic** (2 hours)

**Review:** Check if any business logic is mixed with notifications  
**Extract:** Move any decision logic to product services  
**Keep:** Formatting and delivery in Slack layer

### **Stage 5.3: Documentation** (1 hour)

**Checklist:**
- [ ] Inventory Bolt app created
- [ ] Notification handlers implemented
- [ ] Message formatters extracted
- [ ] Integration with product webhooks tested
- [ ] Documentation updated

---

## **PHASE 6: DEPRECATE LEGACY** (4-6 hours)

### **Stage 6.1: Remove slack_service.py Monolith** (2 hours)

**Current:** 500-line monolithic service  
**Target:** Delete and replace with domain-specific Bolt apps

**Steps:**
1. Verify all functionality moved to Bolt apps
2. Update all imports to use specific Bolt apps
3. Delete `slack_service.py`
4. Run full test suite

### **Stage 6.2: DELETE Legacy Message Builders** (2 hours)

**Current:** 
- `message_builder.py` (489 lines) - Old dict-based builder with `build_hyperlink()`, etc.
- `message_builder_legacy.py` (1,292 lines) - Refund-specific formatting

**Target:** **COMPLETE DELETION** - Zero backward compatibility

**Steps:**
1. **Verify Migration Complete:**
   - ✅ All refund formatting moved to `refunds/formatters.py` (using typed builders)
   - ✅ All order formatting moved to `orders/formatters.py` (using typed builders)
   - ✅ All leadership formatting moved to `leadership/formatters.py` (using typed builders)
   - ✅ All call sites updated to use `GenericMessageBuilder` + `SlackBlockBuilder`

2. **Find All Call Sites:**
   ```bash
   grep -r "SlackMessageBuilder" backend/ --files-with-matches
   grep -r "build_hyperlink" backend/ --files-with-matches
   grep -r "build_header_block" backend/ --files-with-matches
   ```

3. **Migrate Each Call Site:**
   ```python
   # ❌ OLD (Dict-based)
   from modules.integrations.slack.builders import SlackMessageBuilder
   builder = SlackMessageBuilder(sport_groups)
   header = builder.build_header_block("Title")  # Returns Dict[str, Any]
   link = builder.build_hyperlink(url, "Click")
   
   # ✅ NEW (Typed)
   from modules.integrations.slack.builders import GenericMessageBuilder
   builder = GenericMessageBuilder()
   header = builder.header("Title")  # Returns HeaderBlock
   link = builder.hyperlink(url, "Click")
   blocks_dict = builder.blocks_to_dict([header])  # Convert for API
   ```

4. **Delete Files:**
   ```bash
   rm backend/modules/integrations/slack/builders/message_builder.py
   rm backend/modules/integrations/slack/builders/message_builder_legacy.py
   ```

5. **Update Exports:**
   ```python
   # backend/modules/integrations/slack/builders/__init__.py (AFTER)
   from .generic_builders import GenericMessageBuilder
   from .block_builders import SlackBlockBuilder
   
   __all__ = [
       "GenericMessageBuilder",
       "SlackBlockBuilder",
       # SlackMessageBuilder REMOVED
       # SlackCacheManager moved to client/
       # SlackMetadataBuilder moved to client/
   ]
   ```

6. **Run Full Test Suite:**
   - All tests must use new typed builders
   - Zero references to old `SlackMessageBuilder`
   - No backward compatibility code

**Critical:**
- ❌ NO archives
- ❌ NO backward compatibility wrappers
- ❌ NO "just in case" code
- ✅ COMPLETE deletion
- ✅ Git history is the only reference

### **Stage 6.3: Update Routers to Use Bolt Apps** (2 hours)

**Refactor:**
```python
# backend/routers/slack.py (BEFORE)
slack_service = SlackService()  # 500-line monolith

@router.post("/interactions")
async def handle_interactions(request: Request):
    return await slack_service.handle_slack_interaction(...)

# backend/routers/slack.py (AFTER)
from modules.integrations.slack.leadership.bolt_app import app as leadership_app
from modules.integrations.slack.refunds.bolt_app import app as refunds_app
from modules.integrations.slack.orders.bolt_app import app as orders_app
from modules.integrations.slack.inventory.bolt_app import app as inventory_app
from slack_bolt.adapter.fastapi import SlackRequestHandler

leadership_handler = SlackRequestHandler(leadership_app)
refunds_handler = SlackRequestHandler(refunds_app)
orders_handler = SlackRequestHandler(orders_app)
inventory_handler = SlackRequestHandler(inventory_app)

@router.post("/leadership/interactions")
async def leadership_interactions(request: Request):
    return await leadership_handler.handle(request)

@router.post("/refunds/interactions")
async def refunds_interactions(request: Request):
    return await refunds_handler.handle(request)

@router.post("/orders/interactions")
async def orders_interactions(request: Request):
    return await orders_handler.handle(request)

@router.post("/inventory/interactions")
async def inventory_interactions(request: Request):
    return await inventory_handler.handle(request)
```

### **Stage 6.4: Final Verification & Zero-Legacy Audit** (2 hours)

**Goal:** Ensure **ZERO** legacy code remains

#### **1. Code Verification**

```bash
# ❌ These searches MUST return ZERO results:
grep -r "SlackMessageBuilder" backend/ --files-with-matches
# Expected: No files (class completely removed)

grep -r "message_builder_legacy" backend/ --files-with-matches
# Expected: No files (module completely removed)

grep -r "build_header_block\|build_section_block" backend/ --files-with-matches
# Expected: No files (old methods removed)

grep -r "slack_service.handle_slack_interaction" backend/ --files-with-matches
# Expected: No files (monolith removed)

# ✅ These searches SHOULD return results (new typed builders):
grep -r "GenericMessageBuilder" backend/ --files-with-matches
# Expected: All new handler files

grep -r "SlackBlockBuilder" backend/ --files-with-matches
# Expected: Modal handlers
```

#### **2. Integration Testing**

**Test All Flows:**
- [ ] Leadership bot: CSV upload, slash commands, user ID lookup
- [ ] Refunds bot: Eligibility checks, refund processing, approval workflow
- [ ] Orders bot: Cancellations, restock notifications, fulfillment updates
- [ ] Inventory bot: Low stock alerts, restock triggers
- [ ] All webhooks still working (Shopify product updates, order creates)
- [ ] Performance same or better (typed models have zero overhead)

#### **3. Final Checklist**

**Files DELETED (not archived):**
- [ ] ✅ `backend/modules/integrations/slack/builders/message_builder.py`
- [ ] ✅ `backend/modules/integrations/slack/builders/message_builder_legacy.py`
- [ ] ✅ `backend/modules/integrations/slack/slack_service.py`
- [ ] ✅ `backend/modules/integrations/slack/slack_refunds_utils.py`
- [ ] ✅ `backend/modules/integrations/slack/builders/order_handlers.py`

**Imports Updated:**
- [ ] ✅ `builders/__init__.py` exports only `GenericMessageBuilder` + `SlackBlockBuilder`
- [ ] ✅ No references to `SlackMessageBuilder` anywhere
- [ ] ✅ No references to `message_builder_legacy` anywhere
- [ ] ✅ No references to `slack_service.handle_slack_interaction`

**Tests:**
- [ ] ✅ All test files use typed builders
- [ ] ✅ All test fixtures use typed builders
- [ ] ✅ Full test suite passes (100% with typed builders)
- [ ] ✅ No tests reference old builders

**Routers:**
- [ ] ✅ All routers use domain-specific Bolt apps
- [ ] ✅ `/slack/leadership/*` routes to `leadership_bolt_app`
- [ ] ✅ `/slack/refunds/*` routes to `refunds_bolt_app`
- [ ] ✅ `/slack/orders/*` routes to `orders_bolt_app`
- [ ] ✅ `/slack/inventory/*` routes to `inventory_bolt_app`

#### **4. Git Verification**

```bash
# Verify files are actually deleted, not just ignored
git status
# Should show deletions, not renames

git log --oneline --grep="DELETE" | head -5
# Should show deletion commits

# Ensure no "backward compatibility" commits
git log --oneline --grep="compat\|archive\|legacy" | head -10
# Should ONLY show deletion commits, not "keep for reference"
```

#### **5. Documentation Final Check**

- [ ] ✅ `TYPED_BUILDERS_USAGE.md` is the ONLY builder documentation
- [ ] ✅ No references to old builders in any README
- [ ] ✅ Migration plan updated to show "COMPLETED"
- [ ] ✅ All docstrings reference typed builders only

**Final Verdict:**
- ✅ **ZERO legacy code remains**
- ✅ **ZERO backward compatibility**
- ✅ **100% typed builders**
- ✅ **All tests pass**
- ✅ **All manual tests pass**

---

**Commit Message:**
```
Phase 6 Complete: Delete all legacy Slack builders

DELETED FILES (no archives, no compatibility):
- message_builder.py (489 lines)
- message_builder_legacy.py (1,292 lines)
- slack_service.py (500 lines)
- slack_refunds_utils.py (103 lines)
- order_handlers.py (203 lines)

REPLACED WITH:
- GenericMessageBuilder (typed, 277 lines)
- SlackBlockBuilder (typed, 283 lines)
- Domain-specific Bolt apps (leadership, refunds, orders, inventory)
- Domain-specific formatters (business-agnostic)

VERIFICATION:
✅ Zero references to SlackMessageBuilder
✅ Zero references to old builder methods
✅ 100% typed Slack SDK models
✅ All tests pass
✅ No backward compatibility code
```

---

## 📊 **Success Metrics**

### **Architecture Quality**

```
✅ Clean Separation:
├── Business logic: Zero Slack/Shopify imports
├── Orchestrators: <100 lines per handler
└── Transport: Business-agnostic builders

✅ Testability:
├── Domain services: 100% unit testable
├── Integration tests: End-to-end coverage
└── Test coverage: >90% for domain logic

✅ Maintainability:
├── Clear responsibilities per layer
├── Easy to add new interfaces (Discord, Teams)
└── Business logic reusable across channels
```

### **Code Metrics**

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **Slack Layer LOC** | 6,521 | 2,000 | -69% |
| **Domain Layer LOC** | 5,700 | 8,000 | +40% |
| **Average Handler Size** | 400+ | <100 | -75% |
| **Test Coverage** | ~60% | >90% | +50% |
| **Bolt Apps** | 1 | 4 | +300% |

### **Business Value**

✅ **Reusability:** CSV parsing usable from CLI, API, Slack  
✅ **Testability:** Can test refund logic without Slack SDK  
✅ **Extensibility:** Easy to add Discord/Teams integrations  
✅ **Maintainability:** Clear boundaries, single responsibility  
✅ **Performance:** Domain services are pure functions (fast)

---

## 🚨 **Rollback Strategy**

### **Feature Flags**

```python
# Use environment variables for gradual rollout
USE_NEW_LEADERSHIP_SERVICE = os.getenv("USE_NEW_LEADERSHIP_SERVICE", "false") == "true"
USE_NEW_REFUNDS_SERVICE = os.getenv("USE_NEW_REFUNDS_SERVICE", "false") == "true"
USE_NEW_ORDERS_SERVICE = os.getenv("USE_NEW_ORDERS_SERVICE", "false") == "true"
```

### **Rollback Process**

1. **Identify stage with issue**
2. **Revert last commit:** `git revert HEAD`
3. **Set feature flag:** `USE_NEW_*_SERVICE=false`
4. **Verify baseline tests:** `pytest backend/modules/{domain}/tests/`
5. **Deploy rollback**
6. **Investigate and fix**
7. **Re-deploy when ready**

---

## 📚 **Testing Strategy**

### **Test Pyramid**

```
                  ▲
                /   \
              /  E2E  \          10%  - End-to-end Slack flows
            /───────────\
          /  Integration \       20%  - Domain ↔ Slack
        /─────────────────\
      /      Unit Tests     \    70%  - Domain services
    /─────────────────────────\
```

### **Test Commands**

```bash
# Domain layer (pure unit tests)
pytest backend/modules/leadership/tests/ -v
pytest backend/modules/refunds/tests/ -v
pytest backend/modules/orders/tests/ -v

# Integration layer (Slack orchestration)
pytest backend/modules/integrations/slack/leadership/tests/ -v
pytest backend/modules/integrations/slack/refunds/tests/ -v
pytest backend/modules/integrations/slack/orders/tests/ -v

# Full suite with coverage
pytest backend/ --cov=backend/modules --cov-report=html --cov-report=term-missing

# Specific domain coverage
pytest backend/modules/leadership/ --cov=backend/modules/leadership --cov-report=term-missing
```

---

## 📝 **Next Actions**

### **Week 1: Foundation + Leadership**
1. ✅ Review this plan with team
2. Create feature branch: `feat/slack-architecture-refactor`
3. **Phase 1:** Foundation (Stages 1.1-1.3)
4. **Phase 2:** Leadership (Stages 1-5)
5. Daily standup: Progress check, blockers

### **Week 2: Refunds + Orders**
6. **Phase 3:** Refunds (Stages 3.1-3.5)
7. **Phase 4:** Orders (Stages 4.1-4.4)
8. Mid-week review: Architecture validation
9. Integration testing with Slack sandbox

### **Week 3: Products + Cleanup**
10. **Phase 5:** Products/Inventory (Stages 5.1-5.3)
11. **Phase 6:** Deprecate Legacy (Stages 6.1-6.4)
12. Final testing and documentation
13. Production deployment plan

---

## 🔗 **References**

- **Domain-Driven Design:** https://martinfowler.com/bliki/DomainDrivenDesign.html
- **Ports and Adapters:** https://alistair.cockburn.us/hexagonal-architecture/
- **Slack Bolt:** https://slack.dev/bolt-python/
- **Test-Driven Development:** https://martinfowler.com/bliki/TestDrivenDevelopment.html
- **Current Slack Code:** `backend/modules/integrations/slack/`
- **Domain Code:** `backend/modules/{refunds|orders|products|leadership}/`

---

**Last Updated:** January 2, 2026  
**Estimated Completion:** January 20-24, 2026  
**Current Phase:** Planning Complete → Ready to Start Phase 1

