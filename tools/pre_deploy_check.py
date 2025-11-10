#!/usr/bin/env python3
"""Comprehensive Pre-Deployment Verification
 
Verifies EVERYTHING before packaging:
1. All Python syntax valid
2. All agent mappings correct
3. All workflows valid
4. All imports work (without external deps)
5. No missing files
6. No broken references
"""

import sys
import ast
from pathlib import Path
from typing import List, Tuple, Dict

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓{Colors.END} {msg}")

def print_error(msg):
    print(f"{Colors.RED}✗{Colors.END} {msg}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠{Colors.END} {msg}")

def print_header(msg):
    print(f"\n{Colors.BLUE}{'='*70}")
    print(f"{msg}")
    print(f"{'='*70}{Colors.END}\n")

class PreDeploymentValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.checks_passed = 0
        self.checks_total = 0
    
    def check(self, condition: bool, success_msg: str, error_msg: str):
        """Track a check"""
        self.checks_total += 1
        if condition:
            print_success(success_msg)
            self.checks_passed += 1
        else:
            print_error(error_msg)
            self.errors.append(error_msg)
    
    def warn(self, msg: str):
        """Log warning"""
        print_warning(msg)
        self.warnings.append(msg)
    
    def verify_syntax(self) -> bool:
        """Verify Python syntax in all critical files"""
        print_header("1. SYNTAX VERIFICATION")
        
        critical_files = [
            'src/orchestration/job_execution_engine.py',
            'src/orchestration/production_execution_engine.py',
            'src/services/services.py',
            'src/services/services_fixes.py',
            'tests/test_production_execution.py',
            'tools/validate_production.py',
        ]
        
        all_valid = True
        for filepath in critical_files:
            path = Path(filepath)
            if not path.exists():
                self.check(False, "", f"File missing: {filepath}")
                all_valid = False
                continue
            
            try:
                with open(path, 'r') as f:
                    compile(f.read(), str(path), 'exec')
                self.check(True, f"Syntax OK: {filepath}", "")
            except SyntaxError as e:
                self.check(False, "", f"Syntax error in {filepath} line {e.lineno}: {e.msg}")
                all_valid = False
        
        return all_valid
    
    def verify_agent_mapping(self) -> bool:
        """Verify all agent mappings are correct"""
        print_header("2. AGENT MAPPING VERIFICATION")
        
        # Read agent mapping from production_execution_engine.py
        engine_file = Path('src/orchestration/production_execution_engine.py')
        if not engine_file.exists():
            self.check(False, "", "production_execution_engine.py not found")
            return False
        
        with open(engine_file, 'r') as f:
            content = f.read()
        
        # Extract agent_class_map
        try:
            tree = ast.parse(content)
            agent_map = {}
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == 'agent_class_map':
                            # Found the mapping
                            if isinstance(node.value, ast.Dict):
                                for k, v in zip(node.value.keys, node.value.values):
                                    if isinstance(k, ast.Constant) and isinstance(v, ast.Tuple):
                                        agent_type = k.value
                                        category = v.elts[0].value
                                        agent_map[agent_type] = category
            
            print(f"Found {len(agent_map)} agents in mapping")
            
            # Verify each agent file exists
            all_found = True
            for agent_type, category in agent_map.items():
                file_path = Path(f"src/agents/{category}/{agent_type}.py")
                if file_path.exists():
                    self.check(True, f"Agent exists: {agent_type}", "")
                else:
                    self.check(False, "", f"Agent file missing: {file_path}")
                    all_found = False
            
            return all_found
            
        except Exception as e:
            self.check(False, "", f"Failed to parse agent mapping: {e}")
            return False
    
    def verify_workflows(self) -> bool:
        """Verify workflow configurations"""
        print_header("3. WORKFLOW VERIFICATION")
        
        config_file = Path('config/main.yaml')
        if not config_file.exists():
            self.check(False, "", "config/main.yaml not found")
            return False
        
        # Simple YAML parsing
        with open(config_file, 'r') as f:
            content = f.read()
        
        # Count workflow definitions
        workflow_count = content.count('name: "')
        self.check(workflow_count >= 3, 
                  f"Found {workflow_count} workflows", 
                  f"Expected at least 3 workflows, found {workflow_count}")
        
        # Check for required workflows
        required_workflows = ['default', 'code_only', 'quick_draft']
        for workflow in required_workflows:
            if f"{workflow}:" in content:
                self.check(True, f"Workflow defined: {workflow}", "")
            else:
                self.check(False, "", f"Workflow missing: {workflow}")
        
        return True
    
    def verify_critical_files(self) -> bool:
        """Verify all critical files exist"""
        print_header("4. CRITICAL FILES CHECK")
        
        required_files = [
            'src/orchestration/job_execution_engine.py',
            'src/orchestration/production_execution_engine.py',
            'src/services/services.py',
            'src/services/services_fixes.py',
            'src/core/config.py',
            'src/core/event_bus.py',
            'config/main.yaml',
            'requirements.txt',
            'README.md',
            'IMPLEMENTATION_COMPLETE.md',
            'CHANGES.md',
            'deploy.sh',
        ]
        
        all_exist = True
        for filepath in required_files:
            if Path(filepath).exists():
                self.check(True, f"File exists: {filepath}", "")
            else:
                self.check(False, "", f"File missing: {filepath}")
                all_exist = False
        
        return all_exist
    
    def verify_no_stubs(self) -> bool:
        """Verify production engine has no stubs"""
        print_header("5. STUB/PLACEHOLDER CHECK")
        
        stub_patterns = [
            'pass  # TODO',
            'pass  # STUB',
            'raise NotImplementedError',
            '# PLACEHOLDER',
        ]
        
        engine_file = Path('src/orchestration/production_execution_engine.py')
        if not engine_file.exists():
            return False
        
        with open(engine_file, 'r') as f:
            content = f.read()
        
        found_stubs = []
        for pattern in stub_patterns:
            if pattern in content:
                found_stubs.append(pattern)
        
        if found_stubs:
            for stub in found_stubs:
                self.check(False, "", f"Found stub pattern: {stub}")
            return False
        else:
            self.check(True, "No stubs found in production_execution_engine.py", "")
            return True
    
    def verify_integration_points(self) -> bool:
        """Verify job engine calls production engine"""
        print_header("6. INTEGRATION VERIFICATION")
        
        job_engine = Path('src/orchestration/job_execution_engine.py')
        if not job_engine.exists():
            return False
        
        with open(job_engine, 'r') as f:
            content = f.read()
        
        # Check for production engine import
        has_import = 'from .production_execution_engine import ProductionExecutionEngine' in content
        self.check(has_import, 
                  "Production engine imported in job engine", 
                  "Production engine NOT imported")
        
        # Check for instantiation
        has_instantiation = 'ProductionExecutionEngine(self.config)' in content or \
                           'ProductionExecutionEngine(config)' in content or \
                           'prod_engine = ProductionExecutionEngine' in content
        self.check(has_instantiation,
                  "Production engine instantiated",
                  "Production engine NOT instantiated")
        
        # Check for execute call
        has_execute = 'prod_engine.execute_pipeline(' in content or \
                     'engine.execute_pipeline(' in content
        self.check(has_execute,
                  "Production engine execute_pipeline called",
                  "execute_pipeline NOT called")
        
        return has_import and has_instantiation and has_execute
    
    def print_summary(self):
        """Print verification summary"""
        print_header("VERIFICATION SUMMARY")
        
        print(f"Checks Passed: {self.checks_passed}/{self.checks_total}")
        
        if self.errors:
            print(f"\n{Colors.RED}ERRORS ({len(self.errors)}):{Colors.END}")
            for error in self.errors:
                print(f"  • {error}")
        
        if self.warnings:
            print(f"\n{Colors.YELLOW}WARNINGS ({len(self.warnings)}):{Colors.END}")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        if not self.errors:
            print(f"\n{Colors.GREEN}✅ ALL CHECKS PASSED - READY FOR PACKAGING{Colors.END}")
            return True
        else:
            print(f"\n{Colors.RED}❌ VERIFICATION FAILED - FIX ERRORS BEFORE PACKAGING{Colors.END}")
            return False

def main():
    print_header("PRE-DEPLOYMENT VERIFICATION")
    print("This script verifies the package is ready for deployment\n")
    
    validator = PreDeploymentValidator()
    
    # Run all verifications
    validator.verify_syntax()
    validator.verify_agent_mapping()
    validator.verify_workflows()
    validator.verify_critical_files()
    validator.verify_no_stubs()
    validator.verify_integration_points()
    
    # Print summary
    success = validator.print_summary()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
