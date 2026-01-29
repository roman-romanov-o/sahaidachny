---
name: complexity
description: |
  Use this skill when checking or discussing code complexity. Activated when:
  - Running complexity checks with complexipy
  - Reviewing function complexity
  - Discussing cognitive complexity metrics
version: 0.1.0
---

# Cognitive Complexity with complexipy

complexipy is a tool for measuring cognitive complexity of Python code. It helps identify functions that are difficult to understand and maintain.

## What is Cognitive Complexity?

Cognitive complexity measures how difficult code is to understand (not just how complex it is structurally). It penalizes:

- **Nesting**: Each level of nesting increases complexity
- **Breaks in linear flow**: `if`, `for`, `while`, `try`, etc.
- **Recursion**: Functions calling themselves
- **Boolean operators**: `and`, `or` in conditions

## Running complexipy

```bash
# Check a file
complexipy path/to/file.py

# Check a directory
complexipy src/

# Set maximum allowed complexity (default: 15)
complexipy src/ --max-complexity 10

# Output as JSON
complexipy src/ --output json
```

## Complexity Thresholds

| Score | Assessment | Action |
|-------|------------|--------|
| 1-5 | Simple | No action needed |
| 6-10 | Moderate | Consider simplifying |
| 11-15 | Complex | Should be refactored |
| 16+ | Very complex | Must be refactored |

## Reducing Complexity

### 1. Extract Helper Functions

**Before (complexity: 12):**
```python
def process_order(order):
    if order.status == "pending":
        if order.payment_verified:
            if order.items:
                for item in order.items:
                    if item.in_stock:
                        reserve_item(item)
                    else:
                        notify_out_of_stock(item)
```

**After (complexity: 3 each):**
```python
def process_order(order):
    if not is_ready_to_process(order):
        return
    process_order_items(order.items)

def is_ready_to_process(order):
    return order.status == "pending" and order.payment_verified and order.items

def process_order_items(items):
    for item in items:
        handle_item_stock(item)

def handle_item_stock(item):
    if item.in_stock:
        reserve_item(item)
    else:
        notify_out_of_stock(item)
```

### 2. Use Early Returns

**Before:**
```python
def validate(data):
    if data:
        if data.get("email"):
            if "@" in data["email"]:
                return True
    return False
```

**After:**
```python
def validate(data):
    if not data:
        return False
    if not data.get("email"):
        return False
    return "@" in data["email"]
```

### 3. Replace Conditionals with Polymorphism

**Before:**
```python
def calculate_price(product):
    if product.type == "book":
        return product.price * 0.9
    elif product.type == "electronics":
        return product.price * 1.1
    elif product.type == "food":
        return product.price
```

**After:**
```python
PRICE_MULTIPLIERS = {
    "book": 0.9,
    "electronics": 1.1,
    "food": 1.0,
}

def calculate_price(product):
    multiplier = PRICE_MULTIPLIERS.get(product.type, 1.0)
    return product.price * multiplier
```

### 4. Use Dictionary Dispatch

**Before:**
```python
def handle_event(event):
    if event.type == "click":
        handle_click(event)
    elif event.type == "hover":
        handle_hover(event)
    elif event.type == "scroll":
        handle_scroll(event)
```

**After:**
```python
EVENT_HANDLERS = {
    "click": handle_click,
    "hover": handle_hover,
    "scroll": handle_scroll,
}

def handle_event(event):
    handler = EVENT_HANDLERS.get(event.type)
    if handler:
        handler(event)
```

## Best Practices

1. **Keep functions under 50 lines** - Long functions are usually complex
2. **Limit nesting to 3-4 levels** - Deep nesting hurts readability
3. **One function, one responsibility** - Single-purpose functions are simpler
4. **Prefer flat over nested** - Use early returns and guard clauses
5. **Extract complex conditions** - Name boolean expressions

## Integration with Sahaidachny

The agentic loop runs complexipy during the Code Quality phase. Functions exceeding the threshold (default: 15) will cause the iteration to fail with fix_info pointing to the complex functions.
