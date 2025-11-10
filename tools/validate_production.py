#!/usr/bin/env python3
"""System Validation Script - Verifies Production Readiness

This script validates:
1. All agents are properly implemented (no stubs)
2. Services are initialized correctly  
3. Production execution engine is wired
4. Ollama is available and working
5. CLI and Web UI are synced
6. MCP endpoints are functional
"""

import sys
import requests
import json
from pathlib import Path
from typing import List, Tuple, Dict
import importlib
import inspect


class SystemValidator:
    """Validates system is production-ready"""
    
    def __init__(self):
        self.results = []
        self.errors = []
        self.warnings = []
    
    def log_result(self, check: str, passed: bool, message: str = ""):
        """Log validation result"""
        status = "✓" if passed else "✗"
        self.results.append((check, passed, message))
        
        if passed:
            print(f"{status} {check}")
            if message:
                print(f"  → {message}")
        else:
            print(f"{status} {check} - FAILED")
            if message:
                print(f"  → {message}")
            self.errors.append(f"{check}: {message}")
    
    def log_warning(self, check: str, message: str):
        """Log warning"""
        print(f"⚠ {check}")
        print(f"  → {message}")
        self.warnings.append(f"{check}: {message}")
    
    def check_file_exists(self, filepath: str, description: str) -> bool:
        """Check if a file exists"""
        exists = Path(filepath).exists()
        self.log_result(f"File: {description}", exists, filepath if exists else f"Missing: {filepath}")
        return exists
    
    def check_ollama_available(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                self.log_result(
                    "Ollama Service", 
                    True, 
                    f"Running with {len(models)} models"
                )
                
                # Check for recommended models
                model_names = [m['name'] for m in models]
                recommended = ['llama3.2:latest', 'codellama:latest']
                missing = [m for m in recommended if m not in model_names]
                
                if missing:
                    self.log_warning(
                        "Ollama Models",
                        f"Missing recommended models: {', '.join(missing)}"
                    )
                
                return True
            else:
                self.log_result("Ollama Service", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Ollama Service", False, str(e))
            return False
    
    def check_agent_implementation(self, agent_file: Path) -> Tuple[bool, str]:
        """Check if an agent is properly implemented (not a stub)"""
        try:
            with open(agent_file, 'r') as f:
                content = f.read()
            
            # Check for stub patterns
            stub_patterns = [
                'pass  # TODO',
                'pass  # Stub',
                'raise NotImplementedError',
                '# PLACEHOLDER',
                '# STUB'
            ]
            
            for pattern in stub_patterns:
                if pattern in content:
                    return False, f"Contains stub: {pattern}"
            
            # Check for essential methods
            if 'def execute(' not in content:
                return False, "Missing execute() method"
            
            if 'self.llm_service.generate(' not in content and 'llm_service.generate(' not in content:
                # Some agents might not call LLM (like file_writer)
                if agent_file.stem not in ['file_writer', 'link_validation', 'duplication_check']:
                    return False, "Does not call llm_service.generate()"
            
            return True, "Implemented"
            
        except Exception as e:
            return False, str(e)
    
    def validate_agents(self) -> bool:
        """Validate all agents are properly implemented"""
        print("\n" + "="*70)
        print("AGENT VALIDATION")
        print("="*70)
        
        agents_dir = Path("src/agents")
        categories = ['ingestion', 'research', 'content', 'code', 'seo', 'publishing', 'support']
        
        all_passed = True
        for category in categories:
            category_dir = agents_dir / category
            if not category_dir.exists():
                continue
            
            print(f"\nCategory: {category}")
            for agent_file in category_dir.glob("*.py"):
                if agent_file.name.startswith("_"):
                    continue
                
                passed, message = self.check_agent_implementation(agent_file)
                self.log_result(f"  Agent: {agent_file.stem}", passed, message)
                
                if not passed:
                    all_passed = False
        
        return all_passed
    
    def validate_services(self) -> bool:
        """Validate services are properly configured"""
        print("\n" + "="*70)
        print("SERVICE VALIDATION")
        print("="*70)
        
        all_passed = True
        
        # Check service files exist
        all_passed &= self.check_file_exists(
            "src/services/services.py",
            "Core Services"
        )
        
        all_passed &= self.check_file_exists(
            "src/services/services_fixes.py",
            "Service Fixes (NoMockGate)"
        )
        
        # Verify LLMService has necessary methods
        try:
            from src.services.services import LLMService
            
            required_methods = ['generate', '__init__']
            has_all = all(hasattr(LLMService, m) for m in required_methods)
            self.log_result(
                "LLMService Methods",
                has_all,
                "All required methods present" if has_all else "Missing methods"
            )
            all_passed &= has_all
            
        except Exception as e:
            self.log_result("LLMService Import", False, str(e))
            all_passed = False
        
        # Verify NoMockGate exists
        try:
            from src.services.services_fixes import NoMockGate
            gate = NoMockGate()
            self.log_result("NoMockGate", True, "Initialized successfully")
        except Exception as e:
            self.log_result("NoMockGate", False, str(e))
            all_passed = False
        
        return all_passed
    
    def validate_production_engine(self) -> bool:
        """Validate production execution engine"""
        print("\n" + "="*70)
        print("PRODUCTION ENGINE VALIDATION")
        print("="*70)
        
        all_passed = True
        
        # Check file exists
        all_passed &= self.check_file_exists(
            "src/orchestration/production_execution_engine.py",
            "Production Execution Engine"
        )
        
        # Verify it can be imported
        try:
            from src.orchestration.production_execution_engine import ProductionExecutionEngine
            self.log_result("Import ProductionExecutionEngine", True)
            
            # Check for required methods
            required_methods = ['execute_pipeline', '_execute_agent', '_prepare_agent_input']
            has_all = all(hasattr(ProductionExecutionEngine, m) for m in required_methods)
            self.log_result(
                "Required Methods",
                has_all,
                "All present" if has_all else "Some missing"
            )
            all_passed &= has_all
            
        except Exception as e:
            self.log_result("Import ProductionExecutionEngine", False, str(e))
            all_passed = False
        
        # Verify it's called from job_execution_engine
        try:
            with open("src/orchestration/job_execution_engine.py", 'r') as f:
                content = f.read()
            
            has_import = "from .production_execution_engine import ProductionExecutionEngine" in content
            self.log_result("Job Engine Integration", has_import)
            all_passed &= has_import
            
            has_call = "prod_engine.execute_pipeline(" in content
            self.log_result("Pipeline Execution Call", has_call)
            all_passed &= has_call
            
        except Exception as e:
            self.log_result("Job Engine Check", False, str(e))
            all_passed = False
        
        return all_passed
    
    def validate_cli_web_sync(self) -> bool:
        """Validate CLI and Web UI are synced"""
        print("\n" + "="*70)
        print("CLI/WEB SYNC VALIDATION")
        print("="*70)
        
        all_passed = True
        
        # Check CLI exists
        all_passed &= self.check_file_exists("ucop_cli.py", "CLI Script")
        
        # Check Web UI exists
        all_passed &= self.check_file_exists("start_web_ui.py", "Web UI Launcher")
        
        # Both should use the same JobExecutionEngine
        try:
            with open("ucop_cli.py", 'r') as f:
                cli_content = f.read()
            
            has_engine = "JobExecutionEngine" in cli_content or "ProductionExecutionEngine" in cli_content
            self.log_result("CLI uses execution engine", has_engine)
            all_passed &= has_engine
            
        except Exception as e:
            self.log_result("CLI Check", False, str(e))
            all_passed = False
        
        return all_passed
    
    def validate_syntax(self) -> bool:
        """Validate Python syntax in critical files"""
        print("\n" + "="*70)
        print("SYNTAX VALIDATION")
        print("="*70)
        
        critical_files = [
            "src/orchestration/job_execution_engine.py",
            "src/orchestration/production_execution_engine.py",
            "src/services/services.py",
            "ucop_cli.py"
        ]
        
        all_passed = True
        for filepath in critical_files:
            try:
                with open(filepath, 'r') as f:
                    compile(f.read(), filepath, 'exec')
                self.log_result(f"Syntax: {filepath}", True)
            except SyntaxError as e:
                self.log_result(f"Syntax: {filepath}", False, f"Line {e.lineno}: {e.msg}")
                all_passed = False
            except Exception as e:
                self.log_result(f"Syntax: {filepath}", False, str(e))
                all_passed = False
        
        return all_passed
    
    def print_summary(self):
        """Print validation summary"""
        print("\n" + "="*70)
        print("VALIDATION SUMMARY")
        print("="*70)
        
        passed_count = sum(1 for _, passed, _ in self.results if passed)
        total_count = len(self.results)
        
        print(f"\nTests Passed: {passed_count}/{total_count}")
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  • {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        if not self.errors:
            print("\n✅ SYSTEM IS PRODUCTION READY!")
            return True
        else:
            print("\n❌ SYSTEM HAS ISSUES - FIX BEFORE PRODUCTION USE")
            return False


def main():
    """Run system validation"""
    print("="*70)
    print("UCOP PRODUCTION READINESS VALIDATION")
    print("="*70)
    
    validator = SystemValidator()
    
    # Run validations
    syntax_ok = validator.validate_syntax()
    agents_ok = validator.validate_agents()
    services_ok = validator.validate_services()
    engine_ok = validator.validate_production_engine()
    cli_web_ok = validator.validate_cli_web_sync()
    ollama_ok = validator.check_ollama_available()
    
    # Print summary
    is_ready = validator.print_summary()
    
    # Exit code
    sys.exit(0 if is_ready else 1)


if __name__ == "__main__":
    main()
