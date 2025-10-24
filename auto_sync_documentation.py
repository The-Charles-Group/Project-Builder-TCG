
#!/usr/bin/env python3
"""
Auto-sync documentation system - keeps MASTER_CONTROL_ROOM.md and Excel updated
Watches for changes in key source files and regenerates documentation automatically
"""

import os
import time
import hashlib
from pathlib import Path
from typing import Set, Dict
import subprocess

# Files to monitor for changes
MONITORED_FILES = [
    "main.py",
    "ai_planner_agencydb.py",
    "ai_timeline_manager.py",
    "ai_weighted_matcher.py",
    "ai_pricing_optimizer.py",
    "backend/scenario_api.py",
    "static/app.js",
    "static/js/pricing-one-table.js",
    "static/js/scenario-manager.js",
    "convert_excel_to_mspdi.py",
    "gpt5_helpers.py",
    "sitecustomize.py"
]

# Output files
MD_FILE = "MASTER_CONTROL_ROOM.md"
EXCEL_FILE = "MASTER_CONTROL_ROOM.xlsx"

class FileWatcher:
    def __init__(self):
        self.file_hashes: Dict[str, str] = {}
        self.initialize_hashes()
    
    def initialize_hashes(self):
        """Calculate initial hashes for all monitored files"""
        for filepath in MONITORED_FILES:
            if os.path.exists(filepath):
                self.file_hashes[filepath] = self._calculate_hash(filepath)
    
    def _calculate_hash(self, filepath: str) -> str:
        """Calculate MD5 hash of file contents"""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def check_for_changes(self) -> Set[str]:
        """Check which files have changed since last check"""
        changed_files = set()
        
        for filepath in MONITORED_FILES:
            if not os.path.exists(filepath):
                continue
            
            current_hash = self._calculate_hash(filepath)
            old_hash = self.file_hashes.get(filepath, "")
            
            if current_hash != old_hash:
                changed_files.add(filepath)
                self.file_hashes[filepath] = current_hash
        
        return changed_files
    
    def regenerate_documentation(self):
        """Regenerate both markdown and Excel documentation"""
        print("🔄 Regenerating documentation...")
        
        try:
            # Step 1: Update markdown (you would implement this based on your current structure)
            print("📝 Updating MASTER_CONTROL_ROOM.md...")
            self._update_markdown()
            
            # Step 2: Generate Excel from markdown
            print("📊 Generating Excel from markdown...")
            subprocess.run(["python", "convert_md_to_excel.py"], check=True)
            
            print("✅ Documentation updated successfully!")
            print(f"   - {MD_FILE}")
            print(f"   - {EXCEL_FILE}")
            
        except Exception as e:
            print(f"❌ Error regenerating documentation: {e}")
    
    def _update_markdown(self):
        """Update the markdown file with current system state"""
        # This would scan your source files and update the markdown
        # For now, we'll just touch the file to show it's being monitored
        
        # Extract actual metrics from codebase
        metrics = self._extract_metrics()
        
        # Read current markdown
        if os.path.exists(MD_FILE):
            with open(MD_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update metrics section (example - you'd expand this)
            import re
            
            # Update endpoint count
            endpoint_pattern = r'(\*\*Total endpoints:\*\* )\d+'
            if re.search(endpoint_pattern, content):
                content = re.sub(endpoint_pattern, f"\\g<1>{metrics['endpoints']}", content)
            
            # Update function count
            function_pattern = r'(\*\*Total functions:\*\* )\d+'
            if re.search(function_pattern, content):
                content = re.sub(function_pattern, f"\\g<1>{metrics['functions']}", content)
            
            # Write updated content
            with open(MD_FILE, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def _extract_metrics(self) -> Dict[str, int]:
        """Extract metrics from source files"""
        metrics = {
            'endpoints': 0,
            'functions': 0,
            'classes': 0,
            'lines_of_code': 0
        }
        
        # Count API endpoints in main.py
        if os.path.exists('main.py'):
            with open('main.py', 'r') as f:
                content = f.read()
                metrics['endpoints'] = len([line for line in content.split('\n') if '@app.' in line and 'route' in line.lower()])
        
        # Count functions and classes across all Python files
        for filepath in MONITORED_FILES:
            if filepath.endswith('.py') and os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')
                    metrics['functions'] += len([l for l in lines if l.strip().startswith('def ')])
                    metrics['classes'] += len([l for l in lines if l.strip().startswith('class ')])
                    metrics['lines_of_code'] += len([l for l in lines if l.strip() and not l.strip().startswith('#')])
        
        return metrics

def main():
    print("🚀 Starting Auto-Sync Documentation System")
    print("📋 Monitoring files for changes...")
    print()
    
    watcher = FileWatcher()
    last_update = time.time()
    
    # Initial generation
    print("🔧 Performing initial documentation sync...")
    watcher.regenerate_documentation()
    print()
    
    # Watch loop
    try:
        while True:
            changed_files = watcher.check_for_changes()
            
            if changed_files:
                print(f"\n🔔 Detected changes in {len(changed_files)} file(s):")
                for filepath in changed_files:
                    print(f"   - {filepath}")
                
                # Debounce: wait 2 seconds for more changes
                time.sleep(2)
                
                # Regenerate documentation
                watcher.regenerate_documentation()
                last_update = time.time()
                print()
            
            # Check every 3 seconds
            time.sleep(3)
            
    except KeyboardInterrupt:
        print("\n⏹️  Auto-sync stopped")
        print(f"📊 Last update: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_update))}")

if __name__ == "__main__":
    main()
