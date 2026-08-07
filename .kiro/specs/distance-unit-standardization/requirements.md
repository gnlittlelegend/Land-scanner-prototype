# Requirements Document: Distance Unit Standardization

## Introduction

The Land Scanner system currently uses both square metres (m²) and square kilometres (km²) as distance units throughout the codebase. This creates confusion and inconsistency. The goal is to standardize all distance measurements to use **metres as the base unit**, with all areas expressed in **square metres (m²)** instead of square kilometres.

This standardization ensures:
- Consistent unit usage across all modules
- Simpler calculations without unit conversion
- Reduced chance of mathematical errors
- Clearer documentation and code readability

## Glossary

- **Square Metres (m²)**: Base unit of area measurement used throughout the system
- **Square Kilometres (km²)**: Deprecated unit; all references will be converted to m²
- **Area Limit**: Upper and lower bounds for valid polygon areas, expressed in m²
- **Metadata**: Information extracted during polygon validation
- **Standardization**: Process of converting all distance measurements to metres

## Requirements

### Requirement 1: Polygon Validator Unit Conversion

**User Story:** As a developer, I want the polygon validator to use metres exclusively, so that all area calculations are in the same unit.

#### Acceptance Criteria

1. THE PolygonValidator SHALL define minimum area as 10 m² (not 10 m² plus a km² calculation)
2. THE PolygonValidator SHALL define maximum area as 100,000,000 m² (100 km² converted to m²)
3. WHEN a polygon area is calculated, THE PolygonValidator SHALL express the result in square metres only
4. THE PolygonValidator SHALL remove the `area_sqkm` field from PolygonMetadata
5. WHEN validation completes, THE PolygonValidator SHALL return area in m² only
6. WHEN error messages are generated, THE PolygonValidator SHALL display areas in m² only

---

### Requirement 2: Error Messages Standardization

**User Story:** As a user, I want error messages to use consistent units, so that I understand validation constraints clearly.

#### Acceptance Criteria

1. WHEN a polygon is below the minimum area, THE System SHALL display "Polygon area X m² is below minimum of 10 m²"
2. WHEN a polygon exceeds the maximum area, THE System SHALL display "Polygon area X m² exceeds maximum of 100,000,000 m²"
3. THE System SHALL NOT display km² values in any error messages
4. WHEN polygon metadata is displayed, THE System SHALL show area in m² only

---

### Requirement 3: Test Data Standardization

**User Story:** As a test developer, I want test comments and output to use metres exclusively, so that tests are clear and maintainable.

#### Acceptance Criteria

1. WHEN test comments reference area, THE test SHALL express area in m² only
2. WHEN test output displays results, THE test SHALL show area in m² only
3. ALL test files SHALL remove references to km² from comments and output
4. WHEN test polygons are created, THE test data SHALL be documented in m² only

---

### Requirement 4: Data Model Standardization

**User Story:** As a system, I need all area data in metadata to be in the same unit, so that downstream processors receive consistent information.

#### Acceptance Criteria

1. WHEN data is collected from providers, THE System SHALL express all area data in m²
2. WHEN area data is stored in properties or dictionaries, THE key SHALL indicate m² (not km²)
3. THE System SHALL remove all `area_sqkm` or `area_km²` references from data models
4. WHEN displaying area information to users or logs, THE System SHALL use m² only

---

### Requirement 5: Documentation Standardization

**User Story:** As a developer, I want documentation to reflect the metres-only unit system, so that new developers understand the unit convention.

#### Acceptance Criteria

1. ALL documentation files SHALL reference m² for area measurements
2. ALL comments in code files SHALL refer to m² (not km²)
3. ALL README and specification files SHALL use metres as the base unit
4. WHEN example data is shown, THE examples SHALL use m² values only

---

### Requirement 6: Backward Compatibility Verification

**User Story:** As a system, I need to ensure that functionality remains correct after unit standardization, so that the system continues to work as designed.

#### Acceptance Criteria

1. WHEN a polygon at the minimum area (10 m²) is validated, THE System SHALL accept it
2. WHEN a polygon at the maximum area (100,000,000 m²) is validated, THE System SHALL accept it
3. WHEN a polygon below 10 m² is validated, THE System SHALL reject it
4. WHEN a polygon above 100,000,000 m² is validated, THE System SHALL reject it
5. ALL existing validation tests SHALL pass with the new unit system
6. WHEN area values are compared, THE System SHALL produce identical results to previous calculations

---

### Requirement 7: Test Files Update

**User Story:** As a test suite, I want all test files to reference areas in metres only, so that test expectations are clear and consistent.

#### Acceptance Criteria

1. THE test file `test_polygon_validator.py` SHALL remove all `area_sqkm` assertions
2. THE test file `test_polygon_validator.py` SHALL update all comments to reference m² instead of km²
3. THE test file `quick_data_test.py` SHALL display results in m² only
4. THE test file `test_task_12_1_e2e_verification.py` SHALL show area in m² instead of km²
5. ALL test data files SHALL be updated to show area measurements in m² only
6. WHEN tests output metadata, THE tests SHALL display area_sqm only (no area_sqkm)

---

### Requirement 8: Data Source Manager and Collectors Update

**User Story:** As a data manager, I need to track and display area data in metres consistently, so that all modules receive standardized information.

#### Acceptance Criteria

1. WHEN data is collected and passed to collectors, THE area SHALL be stored as m² only
2. ANY dictionary or property containing area data SHALL use m² (not km²)
3. WHEN status messages are generated, THE System SHALL display area in m² only
4. THE System SHALL remove any `area_sqkm` or similar km² references from data dictionaries

---

### Requirement 9: Error Messages Throughout System

**User Story:** As a user or developer, I need all error and status messages to use consistent units, so that I understand system behavior clearly.

#### Acceptance Criteria

1. ALL error messages in PolygonValidator SHALL reference m² only (not km²)
2. ALL status messages in DataSourceManager SHALL show m² only
3. ALL test output and debug messages SHALL use m² exclusively
4. ALL log messages SHALL reference m² when displaying area values
5. THE System SHALL NOT mix units in any single message or output

---

### Requirement 10: Documentation and Comments

**User Story:** As a developer reading the codebase, I want all code comments and documentation to use metres consistently, so that I understand the unit system immediately.

#### Acceptance Criteria

1. ALL code comments SHALL reference m² and metres exclusively
2. ALL docstrings SHALL explain areas in m² (not km²)
3. ALL README and specification files SHALL state that the system uses m² exclusively
4. WHEN examples are given (e.g., "100 km² test area"), THE comments SHALL show the m² equivalent (100,000,000 m²)
5. ALL project documentation SHALL state the valid range as "10 m² to 100,000,000 m²" (not "10 m² to 100 km²")

---

### Requirement 11: Property Naming Consistency

**User Story:** As a system, I need all data properties that reference areas to use consistent naming conventions, so that the data model is clear and unambiguous.

#### Acceptance Criteria

1. WHEN area data is stored in properties dictionaries, THE key SHALL be `area_sqm` or consistent variant (not mixed names like `area_square_kilometers`)
2. THE System SHALL NOT use `area_square_kilometers` in any new code or properties
3. THE System SHALL NOT have mixed naming like `area_sqkm`, `area_km2`, `area_km²` in the same codebase
4. ALL standardizers (water, land cover, buildings, etc.) SHALL store area data using m² only
5. WHERE historical data uses `area_sqkm`, THE System SHALL convert it to `area_sqm` during standardization
6. ALL test files SHALL verify that area properties use only m² units

---

### Requirement 12: Water Standardizer Unit Consistency

**User Story:** As a water standardizer, I need to process all water area data in square metres, so that the water rule engine receives consistent input.

#### Acceptance Criteria

1. THE WaterStandardizer SHALL accept `area`, `area_sqkm`, `area_km2` as input field names
2. WHEN standardizing water data, THE WaterStandardizer SHALL convert all area inputs to m² (multiply km² by 1,000,000)
3. THE WaterStandardizer SHALL output area data using `area_sqm` key only
4. WHEN water properties are processed, THE System SHALL remove `area_sqkm` and `total_water_area_sqkm` fields
5. ALL water rule engine outputs SHALL express area in m² exclusively
6. WHEN water coverage is categorized, THE System SHALL use m² thresholds (not km² thresholds)

---

### Requirement 13: Water Rule Engine Output Standardization

**User Story:** As a water rule engine, I need to output area measurements in square metres, so that downstream consumers receive consistent data.

#### Acceptance Criteria

1. THE WaterRule output SHALL NOT include `total_water_area_sqkm` field
2. THE WaterRule output SHALL include `total_water_area_sqm` field instead
3. WHEN calculating water coverage categories, THE Rule SHALL use m² thresholds:
   - Minimal: < 100,000 m² (0.1 km²)
   - Moderate: 100,000 - 1,000,000 m² (0.1-1 km²)
   - Significant: > 1,000,000 m² (>1 km²)
4. ALL water rule test expectations SHALL reference m² values
5. WHEN water results are displayed, THE System SHALL show m² values in output

---

### Requirement 14: Test Property Assertions Update

**User Story:** As a test suite, I want all assertions about area values to use consistent units, so that test failures are clear and understandable.

#### Acceptance Criteria

1. WHEN test files assert area values, THE assertions SHALL check `area_sqm` only (not `area_sqkm`)
2. TEST assertions like `assert result.area_sqkm > 0` SHALL be removed or converted
3. ALL test setup code creating area properties SHALL use m² only
4. WHEN test data is compared, THE comparison SHALL use m² values exclusively
5. ALL property assertions in water tests SHALL check `total_water_area_sqm` (not `total_water_area_sqkm`)
6. WHEN test comments reference expected areas, THE comments SHALL show m² values

</content>
