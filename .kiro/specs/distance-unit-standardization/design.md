# Design Document: Distance Unit Standardization

## Overview

This design document outlines the standardization of all distance measurements in the Land Scanner system to use only **square metres (m²)** as the area unit. The current system uses mixed units (m² and km²), which creates inconsistency and potential for calculation errors. This standardization will remove all kilometre-based measurements and ensure all area data is expressed exclusively in square metres.

**Key changes:**
- Remove `area_sqkm` field from PolygonMetadata dataclass
- Update all error messages to display areas in m²
- Standardize all data properties to use m² only
- Update water standardizer and rule engine to output m²
- Convert all test assertions and comments to use m²

## Architecture

### Current System (With Conflicts)

The current system has unit conflicts at multiple layers:
- **Validator layer:** Calculates and returns both `area_sqm` and `area_sqkm` (CONFLICT)
- **Properties layer:** Stores as `area_square_kilometers` mixed with `area_sqm` (CONFLICT)
- **Standardizer layer:** WaterStandardizer outputs `area_sqkm` (CONFLICT)
- **Rule layer:** WaterRule outputs `total_water_area_sqkm` (CONFLICT)
- **Error messages:** Display both m² and km² values (CONFLICT)

### Target System (After Standardization)

All layers will use m² exclusively:
- **Validator layer:** Returns `area_sqm` only
- **Properties layer:** All stored as `area_sqm`
- **Standardizer layer:** Outputs `area_sqm`
- **Rule layer:** Outputs `total_water_area_sqm` with m²-based thresholds
- **Error messages:** Display m² values only

## Components and Interfaces

### 1. PolygonMetadata Dataclass Changes

**Remove:**
```python
area_sqkm: float  # REMOVE THIS FIELD
```

**Keep:**
```python
area_sqm: float  # KEEP - this is the only area field needed
```

### 2. PolygonValidator Constants Changes

**Remove these km² derived constants:**
```python
MIN_AREA_SQKM = MIN_AREA_SQM / 1e6  # REMOVE
MAX_AREA_SQKM = MAX_AREA_SQM / 1e6  # REMOVE
```

**Clean error messages to use m² only:**
```python
# OLD: f"Polygon area {area_sqkm:.2f} km² exceeds maximum of {self.MAX_AREA_SQKM:.2f} km²"
# NEW: f"Polygon area {area_sqm:.0f} m² exceeds maximum of {self.MAX_AREA_SQM:.0f} m²"
```

### 3. Properties Dictionary Standardization

**Change all properties to use `area_sqm`:**
```python
# OLD: properties = {'area_square_kilometers': polygon_metadata.area_sqkm, ...}
# NEW: properties = {'area_sqm': polygon_metadata.area_sqm, ...}
```

### 4. Water Standardizer Changes

**Output area_sqm instead of area_sqkm:**
```python
# OLD: "area_sqkm": convert_to_km2(properties.get("area"))
# NEW: "area_sqm": convert_to_m2(properties.get("area"))
```

### 5. Water Rule Engine Changes

**Change output field names:**
```python
# OLD: "total_water_area_sqkm": calculate_water_area_sqkm(features)
# NEW: "total_water_area_sqm": calculate_water_area_sqm(features)
```

**Update coverage thresholds to m²:**
```python
# Minimal: < 100,000 m² (0.1 km²)
# Moderate: 100,000 - 1,000,000 m² (0.1-1 km²)
# Significant: > 1,000,000 m² (>1 km²)
```

## Data Models

### Area Field Standardization

| Location | Current | New |
|----------|---------|-----|
| PolygonMetadata | area_sqkm, area_sqm | area_sqm only |
| Properties dict | area_square_kilometers | area_sqm |
| Water features | area_sqkm | area_sqm |
| Water rule output | total_water_area_sqkm | total_water_area_sqm |

## Correctness Properties

A property is a formal statement about what the system should do. Properties serve as the bridge between specifications and machine-verifiable correctness.

### Property 1: All area metadata uses square metres only

*For any* validated polygon, the returned PolygonMetadata should have `area_sqm` field and NOT have `area_sqkm` field.

**Validates: Requirements 1.3, 1.4, 1.5**

---

### Property 2: Area values are correctly calculated in square metres

*For any* polygon with known dimensions, the calculated area_sqm should equal the expected area in square metres (within 1% tolerance).

**Validates: Requirements 1.2, 1.3, 6.1, 6.2**

---

### Property 3: Minimum area validation uses square metres

*For any* polygon with area < 10 m², validation should fail with error message containing "10 m²" (never "km²").

**Validates: Requirements 1.1, 2.1, 9.1**

---

### Property 4: Maximum area validation uses square metres

*For any* polygon with area > 100,000,000 m², validation should fail with error message containing "100,000,000 m²" (never in km²).

**Validates: Requirements 1.2, 2.2, 9.2**

---

### Property 5: Error messages contain only square metres

*For any* error message related to polygon area, the message should contain "m²" and should NOT contain "km²".

**Validates: Requirements 2.3, 9.3, 9.5**

---

### Property 6: Data properties use consistent naming

*For any* data property dictionary containing area, the key should be `area_sqm` and value should be in square metres.

**Validates: Requirements 4.1, 4.2, 11.1**

---

### Property 7: Water standardizer outputs area in square metres

*For any* water feature with area data, the standardized output should have `area_sqm` key with value in square metres.

**Validates: Requirements 12.1, 12.2, 12.4**

---

### Property 8: Water rule outputs use square metres

*For any* water feature dataset, the rule output should contain `total_water_area_sqm` (not `total_water_area_sqkm`).

**Validates: Requirements 13.1, 13.2**

---

### Property 9: Coverage categorization uses square metre thresholds

*For any* total water area in square metres, the category should match the m² threshold:
- If area < 100,000 m² → "minimal"
- If 100,000 ≤ area < 1,000,000 m² → "moderate"
- If area ≥ 1,000,000 m² → "significant"

**Validates: Requirements 13.3, 13.6**

---

### Property 10: No kilometre-based field names in outputs

*For any* system output (validator, standardizer, rule), no field name should contain "sqkm", "km2", "km²", or "square_kilometers".

**Validates: Requirements 4.3, 11.3**

---

### Property 11: Round-trip area conversion consistency

*For any* area value, converting m² → km² → m² should produce the same value (within floating-point tolerance).

**Validates: Requirements 1.3, 6.6**

---

### Property 12: All data flowing through manager uses metres

*For any* polygon processed by DataSourceManager, all area values in properties should be in square metres.

**Validates: Requirements 8.1, 8.2**

## Error Handling

### Validation Errors - m² Only

```
Below minimum: "Polygon area 5 m² is below minimum of 10 m²"
Exceeds maximum: "Polygon area 150,000,000 m² exceeds maximum of 100,000,000 m²"
```

All errors display m², never km²

## Testing Strategy

### Unit Tests
- Verify PolygonMetadata has area_sqm (not area_sqkm)
- Test error messages at boundaries (10 m², 100,000,000 m²)
- Test no "km²" appears in error messages
- Test WaterStandardizer outputs area_sqm
- Test WaterRule outputs total_water_area_sqm
- Test coverage thresholds use m² values

### Property-Based Tests
- Run each property with minimum 100 iterations
- Tag each test with property reference
- Verify properties hold for random inputs
- Test boundary conditions systematically

