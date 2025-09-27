#!/usr/bin/env python3
"""
IZA OS memU Compliance Automation System
Enterprise-grade compliance with comprehensive audit trails
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import yaml
import sqlite3
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Text, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import aiohttp
import docker
from docker.errors import DockerException
import structlog
from prometheus_client import Counter, Histogram, Gauge

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Prometheus metrics
COMPLIANCE_CHECKS = Counter('compliance_checks_total', 'Total compliance checks', ['standard', 'status'])
COMPLIANCE_SCORE = Gauge('compliance_score', 'Overall compliance score', ['standard'])
AUDIT_EVENTS = Counter('audit_events_total', 'Total audit events', ['event_type', 'severity'])

# Database setup
Base = declarative_base()

class ComplianceStandard(Base):
    __tablename__ = 'compliance_standards'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    version = Column(String(20), nullable=False)
    description = Column(Text)
    requirements = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class ComplianceCheck(Base):
    __tablename__ = 'compliance_checks'
    
    id = Column(Integer, primary_key=True)
    standard_id = Column(Integer, nullable=False)
    check_name = Column(String(255), nullable=False)
    description = Column(Text)
    check_type = Column(String(50), nullable=False)  # automated, manual, hybrid
    status = Column(String(20), nullable=False)  # passed, failed, warning, skipped
    score = Column(Float, nullable=False, default=0.0)
    details = Column(JSON)
    executed_at = Column(DateTime, default=datetime.utcnow)
    correlation_id = Column(String(36))

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    event_type = Column(String(100), nullable=False)
    event_description = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    user_id = Column(String(100))
    resource = Column(String(255))
    action = Column(String(100))
    result = Column(String(50))
    details = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
    correlation_id = Column(String(36))

class ComplianceStandardType(Enum):
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    NIST = "nist"
    IZA_OS = "iza_os"

class CheckStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"

class SeverityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ComplianceRequirement:
    """Compliance requirement definition"""
    id: str
    title: str
    description: str
    standard: ComplianceStandardType
    category: str
    priority: int
    automated: bool
    check_script: Optional[str] = None
    manual_steps: List[str] = field(default_factory=list)
    evidence_required: List[str] = field(default_factory=list)

class ComplianceEngine:
    """Main compliance engine for automated compliance checking"""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.db_path = base_path / "compliance.db"
        self.engine = create_engine(f'sqlite:///{self.db_path}')
        Base.metadata.create_all(self.engine)
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
        except DockerException:
            logger.warning("Docker not available")
            self.docker_client = None
        
        # Load compliance standards
        self.standards = self._load_compliance_standards()
        self.requirements = self._load_compliance_requirements()
    
    def _load_compliance_standards(self) -> Dict[str, ComplianceStandard]:
        """Load compliance standards from configuration"""
        standards = {
            "SOC2": ComplianceStandard(
                name="SOC 2 Type II",
                version="2023",
                description="Service Organization Control 2 Type II compliance",
                requirements={
                    "security": ["access_controls", "encryption", "monitoring"],
                    "availability": ["uptime_monitoring", "backup_recovery"],
                    "processing_integrity": ["data_validation", "error_handling"],
                    "confidentiality": ["data_classification", "access_restrictions"],
                    "privacy": ["data_protection", "consent_management"]
                }
            ),
            "ISO27001": ComplianceStandard(
                name="ISO/IEC 27001",
                version="2022",
                description="Information Security Management System",
                requirements={
                    "information_security_policies": ["policy_management", "review_process"],
                    "organization_of_information_security": ["roles_responsibilities", "authorization"],
                    "human_resource_security": ["background_checks", "training"],
                    "asset_management": ["asset_inventory", "classification"],
                    "access_control": ["user_management", "privileged_access"]
                }
            ),
            "GDPR": ComplianceStandard(
                name="General Data Protection Regulation",
                version="2018",
                description="EU data protection and privacy regulation",
                requirements={
                    "lawfulness": ["consent_management", "legal_basis"],
                    "fairness": ["transparency", "data_subject_rights"],
                    "transparency": ["privacy_notices", "data_processing_info"],
                    "purpose_limitation": ["data_minimization", "purpose_specification"],
                    "data_minimization": ["storage_limitation", "accuracy"]
                }
            ),
            "IZA_OS": ComplianceStandard(
                name="IZA OS Enterprise Standards",
                version="2024",
                description="IZA OS specific enterprise development standards",
                requirements={
                    "code_quality": ["type_safety", "error_handling", "testing"],
                    "security": ["input_validation", "encryption", "authentication"],
                    "performance": ["caching", "optimization", "monitoring"],
                    "scalability": ["microservices", "load_balancing", "auto_scaling"],
                    "monitoring": ["observability", "alerting", "logging"]
                }
            )
        }
        
        # Save to database
        Session = sessionmaker(bind=self.engine)
        session = Session()
        
        for standard in standards.values():
            existing = session.query(ComplianceStandard).filter_by(name=standard.name).first()
            if not existing:
                session.add(standard)
        
        session.commit()
        session.close()
        
        return standards
    
    def _load_compliance_requirements(self) -> List[ComplianceRequirement]:
        """Load compliance requirements"""
        return [
            # SOC 2 Requirements
            ComplianceRequirement(
                id="SOC2-CC6.1",
                title="Logical Access Security Software",
                description="Implement logical access security software",
                standard=ComplianceStandardType.SOC2,
                category="security",
                priority=1,
                automated=True,
                check_script="check_access_controls",
                evidence_required=["access_control_policy", "user_management_procedures"]
            ),
            ComplianceRequirement(
                id="SOC2-CC6.2",
                title="Access Restriction",
                description="Restrict access to information and systems",
                standard=ComplianceStandardType.SOC2,
                category="security",
                priority=1,
                automated=True,
                check_script="check_access_restrictions",
                evidence_required=["access_control_matrix", "privilege_management"]
            ),
            
            # ISO 27001 Requirements
            ComplianceRequirement(
                id="ISO27001-A.9.1",
                title="Access Control Policy",
                description="Implement access control policy",
                standard=ComplianceStandardType.ISO27001,
                category="access_control",
                priority=1,
                automated=True,
                check_script="check_access_control_policy",
                evidence_required=["access_control_policy", "implementation_guidelines"]
            ),
            
            # GDPR Requirements
            ComplianceRequirement(
                id="GDPR-Art.32",
                title="Security of Processing",
                description="Implement appropriate technical and organizational measures",
                standard=ComplianceStandardType.GDPR,
                category="data_protection",
                priority=1,
                automated=True,
                check_script="check_data_protection_measures",
                evidence_required=["data_protection_impact_assessment", "security_measures"]
            ),
            
            # IZA OS Requirements
            ComplianceRequirement(
                id="IZA-OS-001",
                title="TypeScript Implementation",
                description="Use TypeScript for all new projects with strict type checking",
                standard=ComplianceStandardType.IZA_OS,
                category="code_quality",
                priority=1,
                automated=True,
                check_script="check_typescript_usage",
                evidence_required=["typescript_config", "type_coverage_report"]
            ),
            ComplianceRequirement(
                id="IZA-OS-002",
                title="Error Handling",
                description="Implement comprehensive error handling with try-catch blocks",
                standard=ComplianceStandardType.IZA_OS,
                category="code_quality",
                priority=1,
                automated=True,
                check_script="check_error_handling",
                evidence_required=["error_handling_documentation", "exception_logs"]
            ),
            ComplianceRequirement(
                id="IZA-OS-003",
                title="Security Headers",
                description="Implement security headers (CSP, XSS protection, etc.)",
                standard=ComplianceStandardType.IZA_OS,
                category="security",
                priority=1,
                automated=True,
                check_script="check_security_headers",
                evidence_required=["security_header_config", "penetration_test_results"]
            ),
            ComplianceRequirement(
                id="IZA-OS-004",
                title="Monitoring Implementation",
                description="Implement comprehensive monitoring and alerting",
                standard=ComplianceStandardType.IZA_OS,
                category="monitoring",
                priority=1,
                automated=True,
                check_script="check_monitoring_implementation",
                evidence_required=["monitoring_dashboard", "alert_configuration"]
            ),
            ComplianceRequirement(
                id="IZA-OS-005",
                title="Testing Coverage",
                description="Maintain 90%+ test coverage",
                standard=ComplianceStandardType.IZA_OS,
                category="testing",
                priority=1,
                automated=True,
                check_script="check_test_coverage",
                evidence_required=["coverage_report", "test_execution_results"]
            )
        ]
    
    async def run_compliance_check(self, standard: ComplianceStandardType, correlation_id: str = None) -> Dict[str, Any]:
        """Run comprehensive compliance check for a standard"""
        logger.info("Starting compliance check", standard=standard.value, correlation_id=correlation_id)
        
        # Get requirements for the standard
        requirements = [req for req in self.requirements if req.standard == standard]
        
        results = {
            "standard": standard.value,
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id,
            "total_requirements": len(requirements),
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "skipped": 0,
            "overall_score": 0.0,
            "requirements": []
        }
        
        # Check each requirement
        for requirement in requirements:
            check_result = await self._check_requirement(requirement, correlation_id)
            results["requirements"].append(check_result)
            
            # Update counters
            if check_result["status"] == CheckStatus.PASSED.value:
                results["passed"] += 1
            elif check_result["status"] == CheckStatus.FAILED.value:
                results["failed"] += 1
            elif check_result["status"] == CheckStatus.WARNING.value:
                results["warnings"] += 1
            else:
                results["skipped"] += 1
            
            # Update Prometheus metrics
            COMPLIANCE_CHECKS.labels(standard=standard.value, status=check_result["status"]).inc()
        
        # Calculate overall score
        if results["total_requirements"] > 0:
            results["overall_score"] = (results["passed"] / results["total_requirements"]) * 100
        
        # Update Prometheus gauge
        COMPLIANCE_SCORE.labels(standard=standard.value).set(results["overall_score"])
        
        # Log audit event
        await self._log_audit_event(
            event_type="compliance_check",
            event_description=f"Compliance check completed for {standard.value}",
            severity=SeverityLevel.HIGH.value if results["overall_score"] < 80 else SeverityLevel.MEDIUM.value,
            correlation_id=correlation_id,
            details=results
        )
        
        logger.info("Compliance check completed", 
                   standard=standard.value, 
                   score=results["overall_score"],
                   passed=results["passed"],
                   failed=results["failed"])
        
        return results
    
    async def _check_requirement(self, requirement: ComplianceRequirement, correlation_id: str) -> Dict[str, Any]:
        """Check a specific compliance requirement"""
        logger.info("Checking requirement", requirement_id=requirement.id, title=requirement.title)
        
        result = {
            "id": requirement.id,
            "title": requirement.title,
            "description": requirement.description,
            "category": requirement.category,
            "priority": requirement.priority,
            "status": CheckStatus.SKIPPED.value,
            "score": 0.0,
            "details": {},
            "evidence": [],
            "recommendations": []
        }
        
        try:
            if requirement.automated and requirement.check_script:
                # Run automated check
                check_method = getattr(self, requirement.check_script, None)
                if check_method:
                    check_result = await check_method(requirement)
                    result.update(check_result)
                else:
                    result["status"] = CheckStatus.FAILED.value
                    result["details"]["error"] = f"Check script {requirement.check_script} not found"
            else:
                # Manual check - mark as requiring manual review
                result["status"] = CheckStatus.WARNING.value
                result["details"]["note"] = "Requires manual review"
                result["recommendations"] = requirement.manual_steps
            
            # Save check result to database
            await self._save_check_result(requirement, result, correlation_id)
            
        except Exception as e:
            logger.error("Error checking requirement", 
                        requirement_id=requirement.id, 
                        error=str(e))
            result["status"] = CheckStatus.FAILED.value
            result["details"]["error"] = str(e)
        
        return result
    
    async def check_access_controls(self, requirement: ComplianceRequirement) -> Dict[str, Any]:
        """Check access control implementation"""
        result = {"status": CheckStatus.PASSED.value, "score": 100.0, "details": {}}
        
        try:
            # Check if authentication is implemented
            auth_endpoints = ["/api/auth/login", "/api/auth/logout", "/api/auth/verify"]
            
            async with aiohttp.ClientSession() as session:
                for endpoint in auth_endpoints:
                    try:
                        async with session.get(f"http://localhost:8000{endpoint}") as response:
                            if response.status in [200, 401, 405]:  # Endpoint exists
                                result["details"][f"endpoint_{endpoint}"] = "exists"
                            else:
                                result["details"][f"endpoint_{endpoint}"] = "not_found"
                    except Exception:
                        result["details"][f"endpoint_{endpoint}"] = "not_accessible"
            
            # Check for security headers
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("http://localhost:8000/api/health") as response:
                        headers = response.headers
                        security_headers = ["X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection"]
                        
                        for header in security_headers:
                            if header in headers:
                                result["details"][f"header_{header}"] = "present"
                            else:
                                result["details"][f"header_{header}"] = "missing"
                                result["score"] -= 20
            except Exception:
                result["details"]["security_headers"] = "not_accessible"
                result["score"] -= 30
            
            # Adjust status based on score
            if result["score"] < 70:
                result["status"] = CheckStatus.FAILED.value
            elif result["score"] < 90:
                result["status"] = CheckStatus.WARNING.value
            
        except Exception as e:
            result["status"] = CheckStatus.FAILED.value
            result["score"] = 0.0
            result["details"]["error"] = str(e)
        
        return result
    
    async def check_typescript_usage(self, requirement: ComplianceRequirement) -> Dict[str, Any]:
        """Check TypeScript usage in the project"""
        result = {"status": CheckStatus.PASSED.value, "score": 100.0, "details": {}}
        
        try:
            # Check for TypeScript configuration files
            tsconfig_files = [
                self.base_path / "super_design_dashboards" / "tsconfig.json",
                self.base_path / "super_design_dashboards" / "tsconfig.node.json"
            ]
            
            tsconfig_found = 0
            for tsconfig in tsconfig_files:
                if tsconfig.exists():
                    tsconfig_found += 1
                    result["details"][f"tsconfig_{tsconfig.name}"] = "found"
                else:
                    result["details"][f"tsconfig_{tsconfig.name}"] = "missing"
                    result["score"] -= 25
            
            # Check for TypeScript files
            ts_files = list(self.base_path.glob("**/*.ts")) + list(self.base_path.glob("**/*.tsx"))
            js_files = list(self.base_path.glob("**/*.js")) + list(self.base_path.glob("**/*.jsx"))
            
            if ts_files:
                result["details"]["typescript_files"] = len(ts_files)
                result["details"]["javascript_files"] = len(js_files)
                
                # Calculate TypeScript usage percentage
                total_files = len(ts_files) + len(js_files)
                if total_files > 0:
                    ts_percentage = (len(ts_files) / total_files) * 100
                    result["details"]["typescript_percentage"] = ts_percentage
                    
                    if ts_percentage < 50:
                        result["score"] -= 30
                        result["status"] = CheckStatus.WARNING.value
                    elif ts_percentage < 80:
                        result["score"] -= 15
            else:
                result["status"] = CheckStatus.FAILED.value
                result["score"] = 0.0
                result["details"]["error"] = "No TypeScript files found"
            
        except Exception as e:
            result["status"] = CheckStatus.FAILED.value
            result["score"] = 0.0
            result["details"]["error"] = str(e)
        
        return result
    
    async def check_monitoring_implementation(self, requirement: ComplianceRequirement) -> Dict[str, Any]:
        """Check monitoring implementation"""
        result = {"status": CheckStatus.PASSED.value, "score": 100.0, "details": {}}
        
        try:
            # Check for monitoring configuration files
            monitoring_files = [
                self.base_path / "monitoring" / "prometheus.yml",
                self.base_path / "monitoring" / "grafana" / "dashboards.yml",
                self.base_path / "monitoring" / "alertmanager.yml"
            ]
            
            for file_path in monitoring_files:
                if file_path.exists():
                    result["details"][f"config_{file_path.name}"] = "found"
                else:
                    result["details"][f"config_{file_path.name}"] = "missing"
                    result["score"] -= 20
            
            # Check for real-time observability service
            observability_service = self.base_path / "realtime_observability_service.py"
            if observability_service.exists():
                result["details"]["observability_service"] = "found"
            else:
                result["details"]["observability_service"] = "missing"
                result["score"] -= 30
            
            # Check for observability dashboard
            dashboard_component = self.base_path / "super_design_dashboards" / "src" / "components" / "RealtimeObservabilityDashboard.tsx"
            if dashboard_component.exists():
                result["details"]["observability_dashboard"] = "found"
            else:
                result["details"]["observability_dashboard"] = "missing"
                result["score"] -= 25
            
            # Adjust status based on score
            if result["score"] < 70:
                result["status"] = CheckStatus.FAILED.value
            elif result["score"] < 90:
                result["status"] = CheckStatus.WARNING.value
            
        except Exception as e:
            result["status"] = CheckStatus.FAILED.value
            result["score"] = 0.0
            result["details"]["error"] = str(e)
        
        return result
    
    async def check_test_coverage(self, requirement: ComplianceRequirement) -> Dict[str, Any]:
        """Check test coverage"""
        result = {"status": CheckStatus.PASSED.value, "score": 100.0, "details": {}}
        
        try:
            # Check for test files
            test_files = list(self.base_path.glob("**/*test*.py")) + list(self.base_path.glob("**/*test*.ts")) + list(self.base_path.glob("**/*test*.tsx"))
            
            if test_files:
                result["details"]["test_files"] = len(test_files)
                
                # Check for test configuration
                test_configs = [
                    self.base_path / "super_design_dashboards" / "vitest.config.ts",
                    self.base_path / "super_design_dashboards" / "src" / "test" / "setup.ts"
                ]
                
                config_found = 0
                for config in test_configs:
                    if config.exists():
                        config_found += 1
                        result["details"][f"test_config_{config.name}"] = "found"
                    else:
                        result["details"][f"test_config_{config.name}"] = "missing"
                        result["score"] -= 15
                
                # Check for test coverage reports (if available)
                coverage_files = list(self.base_path.glob("**/coverage/**/*.html"))
                if coverage_files:
                    result["details"]["coverage_reports"] = len(coverage_files)
                else:
                    result["details"]["coverage_reports"] = "not_found"
                    result["score"] -= 10
                
            else:
                result["status"] = CheckStatus.FAILED.value
                result["score"] = 0.0
                result["details"]["error"] = "No test files found"
            
        except Exception as e:
            result["status"] = CheckStatus.FAILED.value
            result["score"] = 0.0
            result["details"]["error"] = str(e)
        
        return result
    
    async def _save_check_result(self, requirement: ComplianceRequirement, result: Dict[str, Any], correlation_id: str):
        """Save check result to database"""
        Session = sessionmaker(bind=self.engine)
        session = Session()
        
        try:
            # Get standard
            standard = session.query(ComplianceStandard).filter_by(name=requirement.standard.value).first()
            
            if standard:
                check = ComplianceCheck(
                    standard_id=standard.id,
                    check_name=requirement.title,
                    description=requirement.description,
                    check_type="automated" if requirement.automated else "manual",
                    status=result["status"],
                    score=result["score"],
                    details=result["details"],
                    correlation_id=correlation_id
                )
                session.add(check)
                session.commit()
        except Exception as e:
            logger.error("Error saving check result", error=str(e))
            session.rollback()
        finally:
            session.close()
    
    async def _log_audit_event(self, event_type: str, event_description: str, severity: str, 
                              correlation_id: str = None, details: Dict[str, Any] = None):
        """Log audit event"""
        Session = sessionmaker(bind=self.engine)
        session = Session()
        
        try:
            audit_log = AuditLog(
                event_type=event_type,
                event_description=event_description,
                severity=severity,
                correlation_id=correlation_id,
                details=details or {}
            )
            session.add(audit_log)
            session.commit()
            
            # Update Prometheus metrics
            AUDIT_EVENTS.labels(event_type=event_type, severity=severity).inc()
            
        except Exception as e:
            logger.error("Error logging audit event", error=str(e))
            session.rollback()
        finally:
            session.close()
    
    async def generate_compliance_report(self, standard: ComplianceStandardType) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        logger.info("Generating compliance report", standard=standard.value)
        
        # Run compliance check
        check_results = await self.run_compliance_check(standard)
        
        # Get audit logs for the standard
        Session = sessionmaker(bind=self.engine)
        session = Session()
        
        try:
            audit_logs = session.query(AuditLog).filter(
                AuditLog.event_type == "compliance_check",
                AuditLog.details.contains({"standard": standard.value})
            ).order_by(AuditLog.timestamp.desc()).limit(10).all()
            
            report = {
                "standard": standard.value,
                "generated_at": datetime.utcnow().isoformat(),
                "summary": {
                    "overall_score": check_results["overall_score"],
                    "total_requirements": check_results["total_requirements"],
                    "passed": check_results["passed"],
                    "failed": check_results["failed"],
                    "warnings": check_results["warnings"],
                    "skipped": check_results["skipped"]
                },
                "requirements": check_results["requirements"],
                "recent_audit_events": [
                    {
                        "timestamp": log.timestamp.isoformat(),
                        "event_type": log.event_type,
                        "severity": log.severity,
                        "description": log.event_description
                    }
                    for log in audit_logs
                ],
                "recommendations": self._generate_recommendations(check_results)
            }
            
            return report
            
        finally:
            session.close()
    
    def _generate_recommendations(self, check_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on check results"""
        recommendations = []
        
        failed_requirements = [req for req in check_results["requirements"] if req["status"] == CheckStatus.FAILED.value]
        warning_requirements = [req for req in check_results["requirements"] if req["status"] == CheckStatus.WARNING.value]
        
        if failed_requirements:
            recommendations.append(f"Address {len(failed_requirements)} failed requirements immediately")
        
        if warning_requirements:
            recommendations.append(f"Review {len(warning_requirements)} warning requirements")
        
        if check_results["overall_score"] < 80:
            recommendations.append("Overall compliance score is below 80% - immediate action required")
        elif check_results["overall_score"] < 90:
            recommendations.append("Overall compliance score is below 90% - improvement needed")
        
        return recommendations

# Main execution
async def main():
    """Main execution function"""
    base_path = Path("/Users/divinejohns/memU/memu")
    
    # Initialize compliance engine
    compliance_engine = ComplianceEngine(base_path)
    
    # Run compliance checks for all standards
    standards = [ComplianceStandardType.SOC2, ComplianceStandardType.ISO27001, 
                ComplianceStandardType.GDPR, ComplianceStandardType.IZA_OS]
    
    for standard in standards:
        logger.info("Running compliance check", standard=standard.value)
        results = await compliance_engine.run_compliance_check(standard)
        
        logger.info("Compliance check completed", 
                   standard=standard.value,
                   score=results["overall_score"],
                   passed=results["passed"],
                   failed=results["failed"])
        
        # Generate report
        report = await compliance_engine.generate_compliance_report(standard)
        
        # Save report
        report_path = base_path / f"compliance_report_{standard.value}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info("Compliance report saved", 
                   standard=standard.value,
                   report_path=str(report_path))

if __name__ == "__main__":
    asyncio.run(main())
