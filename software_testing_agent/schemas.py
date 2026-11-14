"""Data models and schemas for Software Testing Agent."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TestCaseResult(BaseModel):
    """Result of an individual test case."""
    name: str = Field(description="Name or identifier of the test case")
    status: str = Field(description="'PASSED', 'FAILED', or 'SKIPPED'")
    duration_ms: float = Field(default=0.0, description="Execution duration in milliseconds")
    error_message: Optional[str] = Field(default=None, description="Error message or assertion failure detail")
    stack_trace: Optional[str] = Field(default=None, description="Extracted stack trace for failed tests")


class TestSuiteResult(BaseModel):
    """Aggregate result of a test suite execution."""
    framework: str = Field(default="pytest", description="Testing framework used")
    total_tests: int = Field(default=0)
    passed: int = Field(default=0)
    failed: int = Field(default=0)
    errors: int = Field(default=0)
    skipped: int = Field(default=0)
    duration_seconds: float = Field(default=0.0)
    tests: List[TestCaseResult] = Field(default_factory=list)


class ApiEndpointAssertion(BaseModel):
    """Specification and result of an API endpoint test."""
    url: str
    method: str = "GET"
    expected_status: int = 200
    actual_status: Optional[int] = None
    latency_ms: Optional[float] = None
    passed: bool = False
    details: Optional[str] = None


class CodeSecurityFinding(BaseModel):
    """A vulnerability or code smell detected during static code analysis."""
    severity: str = Field(description="'CRITICAL', 'HIGH', 'MEDIUM', or 'LOW'")
    issue_type: str = Field(description="Category of the finding (e.g., Hardcoded Secret, SQL Injection, eval)")
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    description: str
    remediation: str
