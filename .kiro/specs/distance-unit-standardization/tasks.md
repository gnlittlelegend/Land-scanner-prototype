# Implementation Plan: Distance Unit Standardization

## Overview

Convert all distance measurements in the Land Scanner backend from mixed units (m² and km²) to **metres only (m²)**. This involves updating the polygon validator, data models, standardizers, rule engines, and all associated tests.

Implementation language: **Python**

## Tasks

- [x] 1. Update PolygonMetadata dataclass - Remove km² field
  - Edit `backend/validators/polygon_validator.py`
  - Remove `area_sqkm: float` field from PolygonMetadata dataclass
  - Remove `MIN_AREA_SQKM` and `MAX_AREA_SQKM` constants
  - Update docstrings to reference m² only
  - _Requirements: 1.4, 1.5, 10.2_

- [x] 1.1 Write unit test for PolygonMetadata structure
  - Verify `area_sqm` field exists
  - Verify `area_sqkm` field does NOT exist
  - _Requirements: 1.4_

- [-] 2. Update PolygonValidator error messages - Use m² only
  - Edit `backend/validators/polygon_validator.py`
  - Update minimum area error: "10 m²" (never show km²)
  - Update maximum area error: "100,000,000 m²" (never show km²)
  - Remove calculations of `area_sqkm` from error messages
  - _Requirements: 2.1, 2.2, 2.3, 9.1, 9.2, 9.3_

- [x] 2.1 Write unit tests for error messages
  - Test minimum area error message format
  - Test maximum area error message format
  - Test no "km²" appears in error messages
  - _Requirements: 2.1, 2.2, 2.3_
  

- [x] 2.2 Write property test for error message consistency
  - **Property 5: Error messages contain only square metres**
  - **Validates: Requirements 2.3, 9.3, 9.5**
  - Generate random polygons at boundaries
  - Verify error messages never contain "km²"

- [x] 3. Update PolygonValidator validation logic - Remove redundant calculations
  - Edit `backend/validators/polygon_validator.py`
  - Remove line: `area_sqkm = area_sqm / 1e6`
  - Keep only: `area_sqm = self._calculate_area_sqm(coordinates, geom_type)`
  - Return PolygonMetadata with area_sqm only
  - _Requirements: 1.3, 1.5_

- [x] 3.1 Write property test for area calculation
  - **Property 2: Area values calculated in square metres**
  - **Validates: Requirements 1.2, 1.3, 6.1, 6.2**
  - Generate test polygons with known areas
  - Verify calculations are correct in m²

- [x] 3.2 Write property test for metadata field consistency
  - **Property 1: All area metadata uses square metres only**
  - **Validates: Requirements 1.3, 1.4, 1.5**
  - Generate random valid polygons
  - Verify each has area_sqm and no area_sqkm

- [x] 4. Update test file - Remove area_sqkm assertions
  - Edit `backend/validators/test_polygon_validator.py`
  - Remove: `assert result.area_sqkm > 0`
  - Remove: `assert result.area_sqkm <= validator.MAX_AREA_SQKM`
  - Update minimum area test to check: `assert result.area_sqm >= 10`
  - Update maximum area test to check: `assert result.area_sqm <= 100_000_000`
  - Update comments from "km²" to "m²"
  - _Requirements: 7.1, 7.3, 7.4, 10.2_

- [x] 4.1 Run polygon validator tests
  - Ensure all tests pass with new assertions
  - _Requirements: 6.5_

- [x] 5. Update test files - Standardize test output messages
  - Edit `backend/quick_data_test.py`
  - Remove: `{metadata.area_sqkm:.6f} km²`
  - Change to: Show area_sqm only
  - Update print statements to use m² only
  - _Requirements: 3.1, 3.2, 10.2_

- [x] 5.1 Verify quick_data_test output
  - Run the updated test
  - Verify output shows m² values only

- [x] 6. Update test files - e2e verification
  - Edit `backend/test_task_12_1_e2e_verification.py`
  - Update print statement: Remove "km²" display
  - Change: `{polygon_metadata.area_sqkm:.2f} km²` → `{polygon_metadata.area_sqm:.0f} m²`
  - Update comment: "within limits 10m² - 100km²" → "within limits 10m² - 100000000m²"
  - _Requirements: 3.1, 3.2, 10.2_

- [x] 7. Update test files - Real data collection
  - Edit `backend/test_real_data_collection.py`
  - Update output: Remove `area_sqkm` references
  - Change property key: `area_sqkm` → `area_sqm`
  - Update any comments showing km² values
  - _Requirements: 4.1, 4.2, 7.5_

- [x] 8. Update test files - End-to-end test
  - Edit `backend/test_end_to_end.py`
  - Update: `polygon_metadata.area_sqkm` → `polygon_metadata.area_sqm`
  - Update property: `'area_square_kilometers'` → `'area_sqm'`
  - Update output display to show m² only
  - _Requirements: 4.2, 7.5_

- [x] 9. Update test files - Elevation real test
  - Edit `backend/test_elevation_real.py`
  - Update print: Remove km² display
  - Update property: `'area_square_kilometers'` → `'area_sqm'`
  - Update comment references from km² to m²
  - _Requirements: 4.2, 7.5_

- [x] 9.1 Checkpoint - Verify all validator tests pass

  - Run: `pytest backend/validators/test_polygon_validator.py -v`
  - All tests should pass with new m²-only assertions

- [x] 10. Update WaterStandardizer - Output area_sqm
  - Edit `backend/standardizers/water_standardizer.py`
  - Change: Any `area_sqkm` field → `area_sqm`
  - Convert all area values to square metres
  - Remove any km² calculations from standardizer
  - Update docstrings to reference m² only
  - _Requirements: 12.1, 12.2, 12.4_

- [x] 10.1 Write unit test for WaterStandardizer area handling


  - Test conversion of area inputs to area_sqm
  - Verify output key is area_sqm
  - Verify values are in square metres
  - _Requirements: 12.1, 12.2_


- [x]* 10.2 Write property test for water standardizer
  - **Property 7: Water standardizer outputs area in square metres**
  - **Validates: Requirements 12.1, 12.2, 12.4**
  - Generate random water feature inputs
  - Verify standardized output has area_sqm in m²

- [x] 11. Update WaterRule - Output total_water_area_sqm
  - Edit `backend/rules/water_rule.py`
  - Change: `total_water_area_sqkm` → `total_water_area_sqm`
  - Ensure output value is in square metres (not km²)
  - Update coverage categorization function to use m² thresholds:
    - Minimal: < 100,000 m²
    - Moderate: 100,000 - 1,000,000 m²
    - Significant: > 1,000,000 m²
  - _Requirements: 13.1, 13.2, 13.3_

- [x] 11.1 Write unit test for water coverage thresholds

  - Test minimal coverage (< 100,000 m²)
  - Test moderate coverage (100,000 - 1,000,000 m²)
  - Test significant coverage (> 1,000,000 m²)
  - _Requirements: 13.3, 13.6_

- [x] 11.2 Write property test for water rule output

  - **Property 8: Water rule outputs use square metres**
  - **Validates: Requirements 13.1, 13.2**
  - Generate random water datasets
  - Verify output has total_water_area_sqm (no sqkm)

- [x] 11.3 Write property test for coverage categorization

  - **Property 9: Coverage categorization uses square metre thresholds**
  - **Validates: Requirements 13.3, 13.6**
  - Generate areas spanning all categories
  - Verify correct categorization using m² thresholds

- [x] 12. Update water rule tests - Use m² assertions
  - Edit `backend/tests/test_water_rule.py`
  - Update assertions: `total_water_area_sqkm` → `total_water_area_sqm`
  - Update expected values to use m² (multiply km² by 1,000,000)
  - Example: 5.0 km² → 5,000,000 m²
  - _Requirements: 7.6, 14.3, 14.6_

- [x] 12.1 Run water rule tests

  - Run: `pytest backend/tests/test_water_rule.py -v`
  - All tests should pass with m² values

- [x] 13. Update water standardizer tests - Use m² assertions
  - Edit `backend/tests/test_water_standardizer.py`
  - Update output assertions: `area_sqkm` → `area_sqm`
  - Update expected values: convert test data to m²
  - Remove references to km² from comments
  - _Requirements: 7.6, 14.3, 14.6_


- [ ] 13.1 Run water standardizer tests

  - Run: `pytest backend/tests/test_water_standardizer.py -v`
  - All tests should pass with m² values

- [x] 14. Update DataSourceManager - Use area_sqm properties
  - Edit `backend/managers/data_source_manager.py`
  - Update property keys: `area_square_kilometers` → `area_sqm`
  - Ensure all collected data uses m² only
  - _Requirements: 4.1, 4.2, 8.1, 8.2_

- [x] 14.1 Write property test for data manager consistency

  - **Property 12: All data through manager uses metres**
  - **Validates: Requirements 8.1, 8.2**
  - Process test polygons through manager
  - Verify all area properties are in m²

- [x] 15. Update all remaining test files - Comment standardization
  - Edit `backend/test_real_data_collection_v2.py`
  - Update comments: "0.005 km²" → "5,000 m²" etc.
  - Remove km² from comments and output
  - _Requirements: 3.1, 3.2, 10.2_

- [x] 16. Update documentation strings - Reference m² only
  - Update `backend/validators/polygon_validator.py` docstrings
  - Update `backend/rules/water_rule.py` docstrings
  - Update `backend/standardizers/water_standardizer.py` docstrings
  - All examples and descriptions use m² only
  - _Requirements: 5.1, 5.2, 10.1, 10.2_

- [x] 16.1 Checkpoint - Run full test suite

  - Run: `pytest backend/tests/ -v`
  - Run: `pytest backend/validators/ -v`
  - Ensure all tests pass



- [x] 16.2 Write comprehensive property tests


  - **Property 10: No kilometre field names in outputs**
  - **Validates: Requirements 4.3, 11.3**
  - Verify no "sqkm", "km2", "km²" in any output



- [x] 16.3 Write round-trip property test

  - **Property 11: Round-trip conversion consistency**
  - **Validates: Requirements 1.3, 6.6**
  - Convert m² → km² → m², verify consistency

- [x] 17. Code review and cleanup
  - Search for remaining "km²" or "sqkm" references
  - Search for "area_square_kilometers" in code
  - Remove any commented-out km² code
  - Verify no dead code remains

  - _Requirements: 5.1, 5.2, 10.1, 10.2_

- [ ]* 17.1 Final verification - All tests pass
  - Run entire test suite: `pytest backend/ -v`
  - Verify all property tests pass (minimum 100 iterations each)
  - Verify no tests reference km² or area_sqkm

## Notes

- **All tasks are required** - Comprehensive standardization from start
- Each task must be completed in order
- Property tests must run minimum 100 iterations
- All tests must pass before task completion
- Breaking changes: `area_sqkm` field is removed from PolygonMetadata
- All 12 correctness properties must be validated
