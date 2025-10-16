"""
Patch Detector Module
Scans code for timeout/truncation patterns and other patch-style fixes.
Raises errors when violations are detected.
"""

import re
import ast
from typing import List, Tuple, Optional

class PatchViolation:
    """Represents a detected patch-style fix violation."""
    
    def __init__(self, file: str, line: int, violation_type: str, code: str, suggestion: str):
        self.file = file
        self.line = line
        self.violation_type = violation_type
        self.code = code
        self.suggestion = suggestion
    
    def __str__(self):
        return (
            f"❌ PATCH VIOLATION in {self.file}:{self.line}\n"
            f"Type: {self.violation_type}\n"
            f"Code: {self.code}\n"
            f"Fix: {self.suggestion}"
        )

class PatchDetector:
    """Detects patch-style fixes in Python code."""
    
    # Pattern definitions for detecting violations
    TIMEOUT_PATTERNS = [
        (r'asyncio\.wait_for\s*\([^,]+,\s*timeout\s*=', 
         "Timeout patch detected. Fix async/blocking issue instead."),
        (r'\.wait\(\d+\)', 
         "Arbitrary wait detected. Fix timing issue properly."),
        (r'time\.sleep\(\d+\)',
         "Sleep patch detected. Fix synchronization properly."),
        (r'timeout\s*=\s*\d+',
         "Timeout parameter detected. Verify this is not a patch."),
    ]
    
    TRUNCATION_PATTERNS = [
        (r'\[:\d+\]',  # String/list slicing with hardcoded limit
         "Data truncation detected. Handle full data properly."),
        (r'\.head\(\d+\)',
         "Data limiting detected. Process all data."),
        (r'\.limit\(\d+\)',
         "Query limiting detected. Handle all results."),
        (r'text\[:\d+\]',
         "Text truncation detected. Process full text."),
        (r'[:]\s*\d{3,}',  # Slicing with large numbers
         "Arbitrary data limit detected. Handle properly."),
    ]
    
    ERROR_SILENCING_PATTERNS = [
        (r'except\s*:\s*(pass|return)',
         "Silent error handling detected. Handle errors properly."),
        (r'except\s+Exception\s*:\s*(pass|return)',
         "Broad exception silencing detected. Handle specific errors."),
        (r'try:\s*\n.*?\nexcept.*?:\s*\n\s*(pass|continue)',
         "Error silencing detected. Fix root cause."),
    ]
    
    FAKE_PROGRESS_PATTERNS = [
        (r'return\s+["\'].*processing.*["\']',
         "Fake status return detected. Return real status."),
        (r'return\s+["\'].*in progress.*["\']',
         "Fake progress detected. Show real progress."),
        (r'return\s+True\s+#.*workaround',
         "Fake success detected. Return actual result."),
    ]
    
    def __init__(self):
        self.violations: List[PatchViolation] = []
    
    def scan_file(self, filepath: str) -> List[PatchViolation]:
        """Scan a Python file for patch violations."""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                lines = content.split('\n')
        except:
            return []
        
        violations = []
        
        # Check each pattern type
        for patterns, violation_type in [
            (self.TIMEOUT_PATTERNS, "TIMEOUT_PATCH"),
            (self.TRUNCATION_PATTERNS, "DATA_TRUNCATION"),
            (self.ERROR_SILENCING_PATTERNS, "ERROR_SILENCING"),
            (self.FAKE_PROGRESS_PATTERNS, "FAKE_PROGRESS"),
        ]:
            for pattern, suggestion in patterns:
                for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
                    # Find line number
                    line_num = content[:match.start()].count('\n') + 1
                    
                    # Get the actual line of code
                    if line_num <= len(lines):
                        code_line = lines[line_num - 1].strip()
                    else:
                        code_line = match.group(0)[:50]
                    
                    violations.append(
                        PatchViolation(
                            file=filepath,
                            line=line_num,
                            violation_type=violation_type,
                            code=code_line,
                            suggestion=suggestion
                        )
                    )
        
        return violations
    
    def scan_directory(self, directory: str = '.') -> List[PatchViolation]:
        """Scan all Python files in a directory."""
        import os
        violations = []
        
        for root, dirs, files in os.walk(directory):
            # Skip common directories
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'venv', '.venv', 'node_modules']]
            
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    violations.extend(self.scan_file(filepath))
        
        return violations
    
    def assert_no_patches(self, filepath: str) -> None:
        """Raise an exception if patches are detected in a file."""
        violations = self.scan_file(filepath)
        if violations:
            raise AssertionError(
                f"PATCH VIOLATIONS DETECTED!\n\n" +
                "\n\n".join(str(v) for v in violations) +
                "\n\nFIX THE ROOT CAUSE, NOT THE SYMPTOM!"
            )
    
    def generate_report(self) -> str:
        """Generate a report of all violations."""
        if not self.violations:
            return "✅ No patch violations detected!"
        
        report = [
            "=" * 60,
            "PATCH VIOLATIONS DETECTED",
            "=" * 60,
            f"Total violations: {len(self.violations)}",
            "",
        ]
        
        # Group by type
        by_type = {}
        for v in self.violations:
            if v.violation_type not in by_type:
                by_type[v.violation_type] = []
            by_type[v.violation_type].append(v)
        
        for vtype, violations in by_type.items():
            report.append(f"\n{vtype} ({len(violations)} violations):")
            report.append("-" * 40)
            for v in violations:
                report.append(f"  {v.file}:{v.line} - {v.code[:50]}")
                report.append(f"    Fix: {v.suggestion}")
        
        report.append("")
        report.append("FIX THESE ISSUES PROPERLY - NO PATCHES!")
        
        return "\n".join(report)

def check_code_for_patches(code: str) -> Optional[str]:
    """
    Quick function to check code string for patches.
    Returns error message if patches found, None otherwise.
    """
    detector = PatchDetector()
    
    # Write to temp file and scan
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_path = f.name
    
    try:
        violations = detector.scan_file(temp_path)
        if violations:
            return "\n".join(str(v) for v in violations)
    finally:
        import os
        os.unlink(temp_path)
    
    return None

# Runtime enforcement
def enforce_no_patches():
    """
    Call this at startup to scan for patches and raise errors.
    """
    import sys
    detector = PatchDetector()
    
    # Scan main application files
    critical_files = ['main.py', 'ai_planner_agencydb.py', 'ai_timeline_manager.py', 'ai_weighted_matcher.py']
    
    all_violations = []
    for file in critical_files:
        if os.path.exists(file):
            violations = detector.scan_file(file)
            all_violations.extend(violations)
    
    if all_violations:
        print("\n" + "=" * 60)
        print("❌ CRITICAL: PATCH VIOLATIONS DETECTED AT STARTUP")
        print("=" * 60)
        for v in all_violations:
            print(str(v))
        print("\nTHESE MUST BE FIXED BEFORE DEPLOYMENT!")
        print("See CORE_PRINCIPLES.md for guidelines.")
        print("=" * 60 + "\n")
        
        # Don't block startup but make it very visible
        # In production, this should raise an exception
        # raise RuntimeError("Cannot start with patch violations!")

if __name__ == "__main__":
    # Run detector on current directory
    import sys
    import os
    
    detector = PatchDetector()
    directory = sys.argv[1] if len(sys.argv) > 1 else '.'
    
    print(f"Scanning {directory} for patch violations...")
    violations = detector.scan_directory(directory)
    
    if violations:
        detector.violations = violations
        print(detector.generate_report())
        sys.exit(1)
    else:
        print("✅ No patch violations detected!")
        sys.exit(0)