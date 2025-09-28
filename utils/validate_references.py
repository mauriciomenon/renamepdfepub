#!/usr/bin/env python3
"""
Cross-Reference Validation Script
================================

Validates all file references and entry points in the repository.
Tests for broken imports, missing files, and cross-reference integrity.
"""

import sys
import subprocess
from pathlib import Path
import importlib.util
import json

def test_entry_points():
    """Test all entry point scripts"""
    print("Testing Entry Points")
    print("=" * 40)
    
    entry_points = [
        'start_cli.py',
        'start_web.py', 
        'start_gui.py',
        'start_html.py'
    ]
    
    results = {}
    
    for script in entry_points:
        script_path = Path(script)
        if not script_path.exists():
            results[script] = f"FILE NOT FOUND"
            continue
            
        # Test --help argument
        try:
            result = subprocess.run([
                sys.executable, script, '--help'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                results[script] = "OK - Help works"
            else:
                results[script] = f"ERROR - Help failed: {result.stderr[:100]}"
                
        except subprocess.TimeoutExpired:
            results[script] = "TIMEOUT - Help command"
        except Exception as e:
            results[script] = f"EXCEPTION: {e}"
    
    for script, status in results.items():
        print(f"  {script:<20} {status}")
    
    return results

def test_file_references():
    """Test file references in key modules"""
    print("\nTesting File References")
    print("=" * 40)
    
    # Key files that reference others
    test_files = {
        'src/gui/web_launcher.py': [
            'src/gui/streamlit_interface.py',
            'reports/simple_report_generator.py', 
            'src/core/advanced_algorithm_comparison.py'
        ],
        'start_cli.py': [
            'src/core/advanced_algorithm_comparison.py',
            'src/cli/launch_system.py'
        ],
        'start_html.py': [
            'reports/simple_report_generator.py',
            'reports/advanced_report_generator.py'
        ]
    }
    
    results = {}
    
    for test_file, referenced_files in test_files.items():
        test_path = Path(test_file)
        if not test_path.exists():
            results[test_file] = f"Test file not found"
            continue
            
        file_results = []
        for ref_file in referenced_files:
            ref_path = Path(ref_file)
            if ref_path.exists():
                file_results.append(f"OK - {ref_file}")
            else:
                file_results.append(f"MISSING - {ref_file}")
        
        results[test_file] = file_results
    
    for test_file, file_results in results.items():
        print(f"\n  {test_file}:")
        for result in file_results:
            print(f"    {result}")
    
    return results

def test_import_paths():
    """Test Python import paths"""
    print("\nTesting Import Paths")
    print("=" * 40)
    
    # Test imports that are known to be problematic
    import_tests = [
        ('tkinter', 'Built-in GUI module'),
        ('sqlite3', 'Built-in database module'),
        ('asyncio', 'Built-in async module'),
        ('json', 'Built-in JSON module'),
        ('pathlib', 'Built-in path module')
    ]
    
    results = {}
    
    for module_name, description in import_tests:
        try:
            importlib.import_module(module_name)
            results[module_name] = f"OK - {description}"
        except ImportError as e:
            results[module_name] = f"FAILED - {e}"
    
    for module, status in results.items():
        print(f"  {module:<15} {status}")
    
    return results

def test_directory_structure():
    """Test expected directory structure"""
    print("\nTesting Directory Structure")
    print("=" * 40)
    
    expected_dirs = [
        'src/core',
        'src/gui',  
        'src/cli',
        'utils',
        'reports',
        'data',
        'tests',
        'docs'
    ]
    
    results = {}
    
    for directory in expected_dirs:
        dir_path = Path(directory)
        if dir_path.exists() and dir_path.is_dir():
            file_count = len(list(dir_path.glob('*.py')))
            results[directory] = f"OK - {file_count} Python files"
        else:
            results[directory] = "MISSING"
    
    for directory, status in results.items():
        print(f"  {directory:<15} {status}")
    
    return results

def test_json_files():
    """Test JSON result files"""
    print("\nTesting JSON Files")
    print("=" * 40)
    
    json_files = [
        'advanced_algorithm_comparison.json',
        'multi_algorithm_comparison.json'
    ]
    
    results = {}
    
    for json_file in json_files:
        json_path = Path(json_file)
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Basic structure validation
                if isinstance(data, dict):
                    keys = list(data.keys())
                    results[json_file] = f"OK - {len(keys)} top-level keys"
                else:
                    results[json_file] = "INVALID - Not a dictionary"
                    
            except json.JSONDecodeError as e:
                results[json_file] = f"INVALID JSON - {e}"
            except Exception as e:
                results[json_file] = f"ERROR - {e}"
        else:
            results[json_file] = "NOT FOUND"
    
    for json_file, status in results.items():
        print(f"  {json_file:<30} {status}")
    
    return results

def generate_validation_report(all_results):
    """Generate comprehensive validation report"""
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY REPORT")
    print("=" * 60)
    
    total_tests = 0
    passed_tests = 0
    
    for category, results in all_results.items():
        print(f"\n{category}:")
        
        if isinstance(results, dict):
            for item, status in results.items():
                total_tests += 1
                if isinstance(status, str) and ('OK' in status or 'works' in status):
                    passed_tests += 1
                    print(f"  PASS: {item}")
                else:
                    print(f"  FAIL: {item} - {status}")
        elif isinstance(results, list):
            for result in results:
                total_tests += 1
                if 'OK' in str(result):
                    passed_tests += 1
    
    print(f"\nOVERALL RESULTS:")
    print(f"  Tests Run: {total_tests}")
    print(f"  Passed: {passed_tests}")
    print(f"  Failed: {total_tests - passed_tests}")
    print(f"  Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    # Critical issues
    print(f"\nCRITICAL ISSUES TO FIX:")
    issues = []
    
    for category, results in all_results.items():
        if isinstance(results, dict):
            for item, status in results.items():
                if isinstance(status, str) and any(word in status.upper() for word in ['MISSING', 'FAILED', 'ERROR', 'NOT FOUND']):
                    issues.append(f"  - {category}: {item} -> {status}")
    
    if issues:
        for issue in issues[:10]:  # Show first 10 critical issues
            print(issue)
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more issues")
    else:
        print("  No critical issues found!")
    
    return passed_tests / total_tests if total_tests > 0 else 0

def main():
    """Main validation function"""
    print("Repository Cross-Reference Validation")
    print("====================================")
    print("Checking file references, imports, and entry points...\n")
    
    all_results = {}
    
    # Run all tests
    all_results['Entry Points'] = test_entry_points()
    all_results['File References'] = test_file_references()  
    all_results['Import Paths'] = test_import_paths()
    all_results['Directory Structure'] = test_directory_structure()
    all_results['JSON Files'] = test_json_files()
    
    # Generate report
    success_rate = generate_validation_report(all_results)
    
    # Save detailed report
    report_path = Path('validation_report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed report saved to: {report_path}")
    
    # Exit code based on success rate
    if success_rate >= 0.8:
        print("VALIDATION PASSED - Repository is in good shape")
        return 0
    else:
        print("VALIDATION FAILED - Critical issues need attention") 
        return 1

if __name__ == '__main__':
    exit(main())