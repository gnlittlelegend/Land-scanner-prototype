"""
Rule Engine orchestrator for processing standardized data.
Executes rules sequentially and compiles results.
"""

import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod

from backend.models.schemas import (
    StandardizedDataset,
    RuleResult,
    ProcessingStatus,
    DataCategory
)

logger = logging.getLogger(__name__)


class Rule(ABC):
    """Abstract base class for all rules."""
    
    def __init__(self, rule_id: str, rule_name: str, required_categories: List[DataCategory]):
        """
        Initialize a rule.
        
        Args:
            rule_id: Unique identifier for the rule (e.g., "ADM-001")
            rule_name: Human-readable rule name
            required_categories: List of required data categories for this rule
        """
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.required_categories = required_categories
    
    @abstractmethod
    def execute(self, standardized_datasets: Dict[DataCategory, StandardizedDataset]) -> RuleResult:
        """
        Execute the rule on standardized data.
        
        Args:
            standardized_datasets: Dictionary mapping category to standardized dataset
            
        Returns:
            RuleResult with execution status and results
        """
        pass
    
    def has_required_data(self, standardized_datasets: Dict[DataCategory, StandardizedDataset]) -> bool:
        """
        Check if required data categories are available.
        
        Args:
            standardized_datasets: Dictionary of available datasets
            
        Returns:
            True if all required categories are present with data
        """
        for category in self.required_categories:
            if category not in standardized_datasets:
                return False
            dataset = standardized_datasets[category]
            if not dataset.features or len(dataset.features) == 0:
                return False
        return True


class RuleEngine:
    """
    Orchestrator for executing rules on standardized data.
    
    Responsibilities:
    - Load and manage enabled rules
    - Execute rules sequentially on standardized datasets
    - Handle rule failures gracefully (continue with remaining rules)
    - Compile rule results into structured output
    - Track execution status
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Rule Engine.
        
        Args:
            config: Configuration dictionary (for future extensibility)
        """
        self.config = config or {}
        self.rules: List[Rule] = []
        self.execution_start_time: Optional[float] = None
        self.execution_end_time: Optional[float] = None
    
    def register_rule(self, rule: Rule) -> None:
        """
        Register a rule with the engine.
        
        Args:
            rule: Rule instance to register
        """
        self.rules.append(rule)
        logger.debug(f"Registered rule: {rule.rule_id} - {rule.rule_name}")
    
    def register_rules(self, rules: List[Rule]) -> None:
        """
        Register multiple rules at once.
        
        Args:
            rules: List of Rule instances
        """
        for rule in rules:
            self.register_rule(rule)
    
    def execute(self, standardized_datasets: Dict[DataCategory, StandardizedDataset]) -> Dict[str, RuleResult]:
        """
        Execute all registered rules on standardized data.
        
        Guarantees:
        - All rules execute independently
        - Failure of one rule does not affect others
        - Missing data results in "insufficient_data" status, not failure
        - All rule results are collected and returned
        
        Args:
            standardized_datasets: Dictionary mapping category to standardized dataset
            
        Returns:
            Dictionary mapping rule_id to RuleResult
        """
        self.execution_start_time = time.time()
        results: Dict[str, RuleResult] = {}
        
        logger.info(f"Rule Engine starting execution with {len(self.rules)} rules")
        
        for rule in self.rules:
            try:
                rule_start_time = time.time()
                
                # Check if required data is available
                if not rule.has_required_data(standardized_datasets):
                    logger.info(f"Rule {rule.rule_id} skipped - insufficient data")
                    result = RuleResult(
                        rule_id=rule.rule_id,
                        rule_name=rule.rule_name,
                        status=ProcessingStatus.INSUFFICIENT_DATA,
                        result={},
                        metadata={
                            "execution_time_ms": (time.time() - rule_start_time) * 1000,
                            "data_points_used": 0,
                            "reason": "Required data categories not available"
                        }
                    )
                else:
                    # Execute the rule
                    result = rule.execute(standardized_datasets)
                    result.metadata["execution_time_ms"] = (time.time() - rule_start_time) * 1000
                
                results[rule.rule_id] = result
                logger.info(f"Rule {rule.rule_id} completed with status: {result.status}")
                
            except Exception as e:
                # Catch and log individual rule failures
                # Continue with remaining rules (isolation)
                logger.error(f"Rule {rule.rule_id} failed with error: {str(e)}", exc_info=True)
                result = RuleResult(
                    rule_id=rule.rule_id,
                    rule_name=rule.rule_name,
                    status=ProcessingStatus.FAILED,
                    result={},
                    metadata={
                        "execution_time_ms": (time.time() - rule_start_time) * 1000,
                        "error": str(e)
                    }
                )
                results[rule.rule_id] = result
        
        self.execution_end_time = time.time()
        logger.info(f"Rule Engine execution complete. Executed {len(results)} rules")
        
        return results
    
    def get_execution_time_ms(self) -> Optional[float]:
        """
        Get the total execution time in milliseconds.
        
        Returns:
            Execution time in milliseconds, or None if not executed yet
        """
        if self.execution_start_time is None or self.execution_end_time is None:
            return None
        return (self.execution_end_time - self.execution_start_time) * 1000
    
    def get_overall_status(self, results: Dict[str, RuleResult]) -> ProcessingStatus:
        """
        Determine overall Rule Engine status based on rule results.
        
        Args:
            results: Dictionary of rule results
            
        Returns:
            ProcessingStatus (SUCCESS if all rules succeeded, PARTIAL if some failed/insufficient,
            FAILED if all failed)
        """
        if not results:
            return ProcessingStatus.FAILED
        
        statuses = [result.status for result in results.values()]
        
        # If all succeeded
        if all(status == ProcessingStatus.SUCCESS for status in statuses):
            return ProcessingStatus.SUCCESS
        
        # If all failed
        if all(status == ProcessingStatus.FAILED for status in statuses):
            return ProcessingStatus.FAILED
        
        # If mixed (some succeeded, some failed or insufficient)
        return ProcessingStatus.PARTIAL
