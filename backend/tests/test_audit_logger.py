"""
Test data audit logging system.

Tracks all test data access, cache performance, and data consistency.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class AuditEvent:
    """Single audit event."""
    timestamp: str
    event_type: str  # "cache_hit", "cache_miss", "api_call", "validation", etc.
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TestAuditEntry:
    """Audit entry for a single test."""
    test_name: str
    test_file: str
    start_time: str
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    polygon_fixtures_used: List[str] = field(default_factory=list)
    provider_data_accessed: List[dict] = field(default_factory=list)
    cache_hits: int = 0
    cache_misses: int = 0
    api_calls: int = 0
    validation_errors: List[str] = field(default_factory=list)
    events: List[AuditEvent] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "test_file": self.test_file,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "polygon_fixtures_used": self.polygon_fixtures_used,
            "provider_data_accessed": self.provider_data_accessed,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "api_calls": self.api_calls,
            "validation_errors_count": len(self.validation_errors),
            "validation_errors": self.validation_errors,
            "event_count": len(self.events)
        }


class TestAuditLogger:
    """Comprehensive audit logger for test data management."""
    
    def __init__(self, audit_dir: str = "backend/tests/audit"):
        """Initialize audit logger."""
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        
        self.test_entries: Dict[str, TestAuditEntry] = {}
        self.session_start_time = datetime.now().isoformat()
        self.global_events: List[AuditEvent] = []
        self.cache_statistics = {
            "total_hits": 0,
            "total_misses": 0,
            "total_api_calls": 0,
            "by_provider": {}
        }
        
        logger.info(f"TestAuditLogger initialized - audit dir: {self.audit_dir}")
    
    def start_test(self, test_name: str, test_file: str) -> TestAuditEntry:
        """Record test start."""
        entry = TestAuditEntry(
            test_name=test_name,
            test_file=test_file,
            start_time=datetime.now().isoformat()
        )
        self.test_entries[test_name] = entry
        
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            event_type="test_start",
            details={"test_name": test_name, "test_file": test_file}
        )
        self.global_events.append(event)
        
        logger.debug(f"Test started: {test_name}")
        return entry
    
    def end_test(self, test_name: str) -> None:
        """Record test end."""
        if test_name not in self.test_entries:
            logger.warning(f"End test called for unknown test: {test_name}")
            return
        
        entry = self.test_entries[test_name]
        entry.end_time = datetime.now().isoformat()
        
        # Calculate duration
        start = datetime.fromisoformat(entry.start_time)
        end = datetime.fromisoformat(entry.end_time)
        entry.duration_ms = (end - start).total_seconds() * 1000
        
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            event_type="test_end",
            details={
                "test_name": test_name,
                "duration_ms": entry.duration_ms,
                "cache_hits": entry.cache_hits,
                "cache_misses": entry.cache_misses,
                "api_calls": entry.api_calls
            }
        )
        self.global_events.append(event)
        
        logger.debug(f"Test ended: {test_name} ({entry.duration_ms:.1f}ms)")
    
    def record_cache_hit(self, test_name: str, provider: str, polygon_id: str) -> None:
        """Record cache hit."""
        if test_name in self.test_entries:
            self.test_entries[test_name].cache_hits += 1
        
        self.cache_statistics["total_hits"] += 1
        if provider not in self.cache_statistics["by_provider"]:
            self.cache_statistics["by_provider"][provider] = {"hits": 0, "misses": 0, "api_calls": 0}
        self.cache_statistics["by_provider"][provider]["hits"] += 1
        
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            event_type="cache_hit",
            details={"test": test_name, "provider": provider, "polygon": polygon_id}
        )
        if test_name in self.test_entries:
            self.test_entries[test_name].events.append(event)
        self.global_events.append(event)
    
    def record_cache_miss(self, test_name: str, provider: str, polygon_id: str) -> None:
        """Record cache miss."""
        if test_name in self.test_entries:
            self.test_entries[test_name].cache_misses += 1
        
        self.cache_statistics["total_misses"] += 1
        if provider not in self.cache_statistics["by_provider"]:
            self.cache_statistics["by_provider"][provider] = {"hits": 0, "misses": 0, "api_calls": 0}
        self.cache_statistics["by_provider"][provider]["misses"] += 1
        
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            event_type="cache_miss",
            details={"test": test_name, "provider": provider, "polygon": polygon_id}
        )
        if test_name in self.test_entries:
            self.test_entries[test_name].events.append(event)
        self.global_events.append(event)
    
    def record_api_call(self, test_name: str, provider: str, polygon_id: str) -> None:
        """Record real API call."""
        if test_name in self.test_entries:
            self.test_entries[test_name].api_calls += 1
        
        self.cache_statistics["total_api_calls"] += 1
        if provider not in self.cache_statistics["by_provider"]:
            self.cache_statistics["by_provider"][provider] = {"hits": 0, "misses": 0, "api_calls": 0}
        self.cache_statistics["by_provider"][provider]["api_calls"] += 1
        
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            event_type="api_call",
            details={"test": test_name, "provider": provider, "polygon": polygon_id}
        )
        if test_name in self.test_entries:
            self.test_entries[test_name].events.append(event)
        self.global_events.append(event)
    
    def record_polygon_usage(self, test_name: str, polygon_id: str) -> None:
        """Record polygon fixture usage."""
        if test_name in self.test_entries:
            if polygon_id not in self.test_entries[test_name].polygon_fixtures_used:
                self.test_entries[test_name].polygon_fixtures_used.append(polygon_id)
    
    def record_provider_data_access(self, test_name: str, provider: str, polygon_id: str) -> None:
        """Record provider data access."""
        if test_name in self.test_entries:
            self.test_entries[test_name].provider_data_accessed.append({
                "provider": provider,
                "polygon_id": polygon_id
            })
    
    def record_validation_error(self, test_name: str, error_message: str) -> None:
        """Record data validation error."""
        if test_name in self.test_entries:
            self.test_entries[test_name].validation_errors.append(error_message)
        
        logger.warning(f"Validation error in {test_name}: {error_message}")
    
    def get_session_report(self) -> Dict[str, Any]:
        """Get overall session report."""
        total_hits = self.cache_statistics["total_hits"]
        total_misses = self.cache_statistics["total_misses"]
        total_requests = total_hits + total_misses
        hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0
        
        # Calculate efficiency
        total_api_calls = self.cache_statistics["total_api_calls"]
        if total_api_calls > 0:
            efficiency = total_hits / total_api_calls
        else:
            efficiency = 0
        
        return {
            "session_start": self.session_start_time,
            "session_end": datetime.now().isoformat(),
            "total_tests": len(self.test_entries),
            "cache_statistics": {
                "total_hits": total_hits,
                "total_misses": total_misses,
                "total_requests": total_requests,
                "cache_hit_rate_percent": hit_rate,
                "by_provider": self.cache_statistics["by_provider"]
            },
            "api_statistics": {
                "total_api_calls": total_api_calls,
                "cache_efficiency_multiplier": efficiency
            },
            "total_events": len(self.global_events)
        }
    
    def export_session_report(self, filepath: Optional[str] = None) -> str:
        """Export session report to file."""
        if filepath is None:
            filepath = self.audit_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = Path(filepath)
        report = self.get_session_report()
        
        # Include individual test reports
        report["tests"] = {
            name: entry.to_dict() 
            for name, entry in self.test_entries.items()
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Session report exported to {filepath}")
        return str(filepath)
    
    def export_detailed_audit(self, filepath: Optional[str] = None) -> str:
        """Export detailed audit with all events."""
        if filepath is None:
            filepath = self.audit_dir / f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = Path(filepath)
        
        detailed = {
            "session_report": self.get_session_report(),
            "tests": {
                name: entry.to_dict()
                for name, entry in self.test_entries.items()
            },
            "all_events": [event.to_dict() for event in self.global_events]
        }
        
        with open(filepath, 'w') as f:
            json.dump(detailed, f, indent=2)
        
        logger.info(f"Detailed audit exported to {filepath}")
        return str(filepath)
    
    def print_summary(self) -> None:
        """Print human-readable summary."""
        report = self.get_session_report()
        
        print("\n" + "=" * 60)
        print("TEST DATA AUDIT SUMMARY")
        print("=" * 60)
        print(f"Tests run: {report['total_tests']}")
        print(f"Total events: {report['total_events']}")
        print()
        print("CACHE PERFORMANCE:")
        cache = report["cache_statistics"]
        print(f"  Cache hits: {cache['total_hits']}")
        print(f"  Cache misses: {cache['total_misses']}")
        print(f"  Hit rate: {cache['cache_hit_rate_percent']:.1f}%")
        print()
        print("API CALLS:")
        api = report["api_statistics"]
        print(f"  Real API calls made: {api['total_api_calls']}")
        print(f"  Cache efficiency: {api['cache_efficiency_multiplier']:.1f}x")
        print()
        print("PROVIDER BREAKDOWN:")
        for provider, stats in cache["by_provider"].items():
            print(f"  {provider}:")
            print(f"    - Hits: {stats['hits']}")
            print(f"    - Misses: {stats['misses']}")
            print(f"    - API calls: {stats['api_calls']}")
        print("=" * 60 + "\n")


# Global audit logger instance
_global_audit_logger: Optional[TestAuditLogger] = None


def get_audit_logger() -> TestAuditLogger:
    """Get global audit logger instance (lazy initialization)."""
    global _global_audit_logger
    if _global_audit_logger is None:
        _global_audit_logger = TestAuditLogger()
    return _global_audit_logger
