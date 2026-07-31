# Rule Engine Module

The Rule Engine module provides rule-based analysis of standardized geospatial data. It orchestrates the execution of multiple independent rules that process standardized datasets and generate structured analysis results.

## Architecture

### Components

1. **RuleEngine**: Central orchestrator
   - Manages rule registration
   - Executes rules sequentially
   - Isolates failures (one rule failure doesn't affect others)
   - Compiles all results

2. **Rule (Abstract Base Class)**: Interface for all rules
   - Defines required categories
   - Implements analysis logic
   - Returns structured results

3. **Concrete Rules**: Specific analysis implementations
   - AdminBoundaryRule (ADM-001)
   - LandCoverRule (LC-001)
   - BuildingPresenceRule (BLD-001)
   - RoadNetworkRule (RD-001)
   - WaterFeaturesRule (WT-001)
   - ElevationRule (ELV-001)

## Usage

### Basic Usage

```python
from backend.rules import RuleEngine, AdminBoundaryRule, LandCoverRule
from backend.models.schemas import StandardizedDataset, DataCategory

# Create engine
engine = RuleEngine()

# Register rules
engine.register_rules([
    AdminBoundaryRule(),
    LandCoverRule(),
])

# Execute on standardized data
results = engine.execute(standardized_datasets)

# Access results
for rule_id, result in results.items():
    print(f"{rule_id}: {result.status}")
    print(f"Result: {result.result}")
```

### Creating Custom Rules

```python
from backend.rules import Rule
from backend.models.schemas import StandardizedDataset, RuleResult, ProcessingStatus, DataCategory

class CustomRule(Rule):
    def __init__(self):
        super().__init__(
            rule_id="CUSTOM-001",
            rule_name="Custom Analysis Rule",
            required_categories=[DataCategory.ADMIN, DataCategory.BUILDINGS]
        )
    
    def execute(self, standardized_datasets):
        # Get required data
        admin_data = standardized_datasets.get(DataCategory.ADMIN)
        
        if not admin_data:
            return RuleResult(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                status=ProcessingStatus.INSUFFICIENT_DATA,
                result={},
                metadata={}
            )
        
        # Perform analysis
        result_data = self._analyze(admin_data)
        
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            status=ProcessingStatus.SUCCESS,
            result=result_data,
            metadata={"data_points_used": len(admin_data.features)}
        )
    
    def _analyze(self, dataset):
        # Custom analysis logic
        return {"analysis": "results"}
```

## Rules Reference

### AdministrativeBoundaryRule (ADM-001)

Identifies administrative regions intersecting the analyzed polygon.

**Required Data**: Administrative boundaries

**Output**:
```json
{
  "administrative_regions": [...],
  "country": "Country Name",
  "state": "State/Province Name",
  "district": "District Name",
  "all_countries": [...],
  "all_states": [...],
  "all_districts": [...]
}
```

### LandCoverRule (LC-001)

Summarizes dominant land cover types and calculates coverage percentages.

**Required Data**: Land cover classification

**Output**:
```json
{
  "primary_land_cover": "forest",
  "land_cover_types": [...],
  "coverage_breakdown": {
    "forest": {"count": 150, "percentage": 45.2},
    "urban": {"count": 80, "percentage": 24.1},
    ...
  },
  "total_features_analyzed": 331,
  "dominant_coverage_percentage": 45.2
}
```

### BuildingPresenceRule (BLD-001)

Detects infrastructure (buildings) presence and estimates coverage.

**Required Data**: Building footprints

**Output**:
```json
{
  "buildings_detected": true,
  "total_building_count": 42,
  "building_types": {
    "residential": {"count": 30, "percentage": 71.4},
    "commercial": {"count": 12, "percentage": 28.6}
  },
  "primary_building_type": "residential",
  "total_building_area_sqm": 12500.0,
  "building_density_estimate": "medium",
  "infrastructure_present": true
}
```

### RoadNetworkRule (RD-001)

Identifies transportation network access and categorizes road types.

**Required Data**: Road network

**Output**:
```json
{
  "road_access": true,
  "total_road_segments": 8,
  "total_road_length_km": 2.5,
  "road_types": {
    "primary": {"count": 2, "percentage": 25.0},
    "secondary": {"count": 4, "percentage": 50.0},
    "tertiary": {"count": 2, "percentage": 25.0}
  },
  "primary_road_type": "secondary",
  "accessibility": "good",
  "connectivity_estimate": "good"
}
```

### WaterFeaturesRule (WT-001)

Identifies hydrological features and estimates coverage.

**Required Data**: Water bodies

**Output**:
```json
{
  "water_features_detected": true,
  "total_water_features": 3,
  "water_types": {
    "river": {"count": 1, "percentage": 33.3},
    "pond": {"count": 2, "percentage": 66.7}
  },
  "primary_water_type": "pond",
  "total_water_area_sqkm": 0.25,
  "water_coverage_category": "moderate",
  "hydrological_features": ["River", "Pond"]
}
```

### ElevationRule (ELV-001)

Characterizes terrain elevation and slope.

**Required Data**: Elevation/DEM data

**Output**:
```json
{
  "elevation_data_available": true,
  "min_elevation_m": 150.5,
  "max_elevation_m": 280.3,
  "mean_elevation_m": 215.2,
  "median_elevation_m": 210.0,
  "elevation_range_m": 129.8,
  "terrain_category": "rolling",
  "slope_average": 8.5,
  "slope_category": "moderate"
}
```

## Result Structure

Each rule returns a `RuleResult` with this structure:

```python
class RuleResult(BaseModel):
    rule_id: str                      # Unique rule identifier
    rule_name: str                    # Human-readable name
    status: ProcessingStatus          # success|failed|insufficient_data|skipped
    result: Dict[str, Any]            # Rule-specific results
    metadata: Dict[str, Any]          # Execution metadata
```

### Status Values

- **SUCCESS**: Rule executed successfully with results
- **FAILED**: Rule encountered an error during execution
- **INSUFFICIENT_DATA**: Required data categories not available
- **SKIPPED**: Rule was intentionally skipped

## Guarantees

### Property 7: Rule Independence and Continuation

- Rules execute independently in sequence
- Failure of one rule does not affect others
- All rules continue executing regardless of individual outcomes
- Results are compiled regardless of individual failures

### Property 8: Rule Result Compilation

- All rule results are compiled into single output
- No results are lost during compilation
- Each rule result includes required fields
- Result count matches registered rule count

## Error Handling

### Rule Failures

When a rule fails:
1. Exception is caught and logged
2. RuleResult created with FAILED status
3. Error details stored in metadata
4. Engine continues with remaining rules

### Insufficient Data

When required data is unavailable:
1. Rule status set to INSUFFICIENT_DATA
2. Result is empty but included in output
3. Engine continues with remaining rules

## Performance Considerations

- Rules execute sequentially (not parallel)
- Each rule processes entire dataset per execution
- Execution time tracked per rule
- Total time available via `get_execution_time_ms()`

## Testing

Property-based tests validate:
- Rule independence and failure isolation
- Complete result compilation
- Correct status determination
- Data integrity through processing pipeline

Run tests:
```bash
pytest tests/test_rule_engine.py -v
```

## Integration Points

### Input
- Receives: `Dict[DataCategory, StandardizedDataset]`
- From: Data Standardizer module
- Contains: Standardized features only (never raw provider data)

### Output
- Returns: `Dict[str, RuleResult]`
- To: Output Generator module
- Used to: Create API response and frontend display

## Future Extensibility

### Adding New Rules

1. Create new Rule subclass
2. Implement `execute()` method
3. Register with engine
4. Results automatically included in output

### Configuration-Driven Rules

Rules can be loaded from configuration:
```python
# Load rules based on configuration
if config.get("enable_admin_rules"):
    engine.register_rule(AdminBoundaryRule())
```

### Rule Dependencies

Current implementation has no inter-rule dependencies. Future versions could:
- Chain rules (output of one feeds input to another)
- Support conditional rule execution
- Implement rule ordering strategies
