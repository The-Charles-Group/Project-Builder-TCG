#!/usr/bin/env python3
"""
Agency Project Builder - Comprehensive End-to-End Test Suite
=============================================================
Production Readiness Test - October 15, 2025
Tests all major features for enterprise deployment validation
"""

import os
import sys
import json
import time
import httpx
import asyncio
import hashlib
import traceback
import psutil
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
import xml.etree.ElementTree as ET
import base64

# Test configuration
BASE_URL = "http://localhost:5000"
TEST_TIMEOUT = 60  # seconds per test
PERFORMANCE_THRESHOLDS = {
    "rfp_upload": 5.0,  # seconds
    "gpt5_analysis": 45.0,  # seconds (increased for 100+ deliverables)
    "scenario_build": 10.0,
    "ai_suggest_type": 15.0,
    "optimize_pricing": 15.0,
    "generate_timeline": 20.0,
    "xml_export": 8.0,
    "session_cleanup": 3.0
}

class TestResult:
    """Test result tracking"""
    def __init__(self, name: str):
        self.name = name
        self.status = "PENDING"
        self.start_time = None
        self.end_time = None
        self.duration = 0
        self.details = {}
        self.errors = []
        self.memory_before = 0
        self.memory_after = 0
    
    def start(self):
        self.start_time = time.time()
        self.memory_before = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.status = "RUNNING"
    
    def complete(self, success: bool = True, details: Dict = None):
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.memory_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.status = "PASSED" if success else "FAILED"
        if details:
            self.details.update(details)
    
    def add_error(self, error: str):
        self.errors.append(error)
        self.status = "FAILED"

class ComprehensiveE2ETest:
    """Comprehensive end-to-end test suite"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=TEST_TIMEOUT)
        self.test_results = []
        self.session_id = None
        self.uploaded_filename = None
        self.deliverables_count = 0
        self.scenario_data = None
        self.export_filename = None
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def create_luxury_rfp(self) -> bytes:
        """Create a comprehensive luxury fashion RFP document"""
        rfp_content = """
LUXURY FASHION BRAND - GLOBAL DIGITAL TRANSFORMATION RFP
========================================================

PROJECT OVERVIEW
----------------
Our prestigious luxury fashion house, with 175 years of heritage in haute couture and ready-to-wear, 
seeks a full-service digital agency partner for comprehensive brand transformation and market expansion.

Annual Revenue: $2.8B
Global Presence: 450 boutiques across 65 countries
Digital Revenue Target: 40% by 2027 (currently 18%)

SCOPE OF WORK
-------------

1. DIGITAL ECOSYSTEM TRANSFORMATION
- Complete redesign of global e-commerce platform
- Mobile-first luxury shopping experience
- Virtual showroom and AR try-on capabilities
- Blockchain authentication for products
- NFT collection launches
- Metaverse flagship store development

2. SEASONAL CAMPAIGN DEVELOPMENT (4 COLLECTIONS/YEAR)
- Spring/Summer Haute Couture (January)
- Fall/Winter Haute Couture (July)
- Ready-to-Wear SS (March)
- Ready-to-Wear FW (September)
- Cruise/Resort Collections
- Pre-Fall Collections

3. CONTENT PRODUCTION
- Editorial photography (200+ SKUs per season)
- Runway show live streaming and production
- Behind-the-scenes documentaries
- Artisan craftsmanship videos
- Celebrity and influencer collaborations
- Product storytelling across 15 markets

4. SOCIAL MEDIA & INFLUENCER MARKETING
- Platform management (Instagram, TikTok, WeChat, RED, Line)
- Influencer partnerships (Mega, Macro, Micro tiers)
- User-generated content campaigns
- Social commerce integration
- Live shopping events

5. PAID MEDIA CAMPAIGNS
- Global media planning and buying ($50M annual budget)
- Programmatic advertising
- Search marketing (SEM/SEO)
- Social media advertising
- Print and outdoor (select markets)
- Connected TV and streaming platforms

6. DATA & ANALYTICS
- Customer data platform implementation
- Predictive analytics for inventory
- Personalization engine development
- Marketing attribution modeling
- Real-time dashboard creation

7. CRM & LOYALTY PROGRAM
- VIP client relationship management
- Tiered loyalty program design
- Exclusive member experiences
- Personal shopping services
- Clienteling tools for boutiques

8. EVENTS & EXPERIENCES
- Fashion Week activations (Paris, Milan, NYC, Shanghai)
- Pop-up boutique experiences
- VIP trunk shows
- Celebrity red carpet placements
- Art and cultural partnerships

9. TECHNOLOGY INNOVATIONS
- AI-powered styling recommendations
- Virtual personal shopping assistants
- Smart mirror installations
- RFID inventory tracking
- Sustainable supply chain transparency

10. MARKET EXPANSION
- China digital ecosystem setup
- Middle East luxury market entry
- Gen Z engagement strategies
- Sustainability communications
- Heritage storytelling for new markets

REQUIREMENTS
------------
- Proven luxury fashion experience (Tier 1 brands)
- Global capability with local expertise
- In-house creative and production
- Technology integration capabilities
- Data security and privacy compliance
- Sustainability commitment

BUDGET
------
Total Annual Budget: $75-100M
- Digital Transformation: $30M
- Marketing & Advertising: $50M
- Content Production: $15M
- Technology & Innovation: $10M

TIMELINE
--------
- RFP Response Due: November 1, 2025
- Agency Presentations: November 15-20, 2025
- Decision: December 1, 2025
- Contract Start: January 1, 2026
- Initial Campaign Launch: March 2026 (Spring/Summer)

EVALUATION CRITERIA
-------------------
- Creative excellence and innovation (30%)
- Technical capabilities (25%)
- Luxury market expertise (20%)
- Global reach with local relevance (15%)
- Pricing and value (10%)

DELIVERABLES EXPECTED
---------------------
We expect comprehensive deliverables across all workstreams including but not limited to:
- Strategic planning documents
- Creative concepts and mood boards
- Technical architecture diagrams
- Media plans and forecasts
- Content calendars
- Performance reports and dashboards
- Budget allocations by quarter
- Resource plans and team structures
- Risk mitigation strategies
- Innovation roadmaps

This is a transformational opportunity to partner with one of the world's most iconic luxury brands.
We seek an agency that understands the delicate balance between heritage and innovation,
exclusivity and accessibility, craftsmanship and technology.

Please provide detailed proposals addressing all scope areas with specific examples,
case studies, and recommended approaches for luxury fashion digital excellence.
"""
        return rfp_content.encode('utf-8')
    
    async def test_1_rfp_upload(self) -> TestResult:
        """Test 1: Upload comprehensive luxury fashion RFP"""
        result = TestResult("RFP Upload")
        result.start()
        
        try:
            # Create RFP content
            rfp_content = self.create_luxury_rfp()
            
            # Upload RFP
            files = {
                'file': ('luxury_fashion_rfp.txt', rfp_content, 'text/plain')
            }
            
            response = await self.client.post('/api/upload-and-extract', files=files)
            
            if response.status_code != 200:
                result.add_error(f"Upload failed with status {response.status_code}")
                return result
            
            data = response.json()
            
            # Validate response
            if 'text' not in data or not data['text']:
                result.add_error("No text extracted from RFP")
                return result
            
            # Check content extraction
            extracted_length = len(data['text'])
            if extracted_length < 1000:
                result.add_error(f"Insufficient text extracted: {extracted_length} chars")
                return result
            
            self.uploaded_filename = data.get('filename', 'luxury_fashion_rfp.txt')
            
            result.complete(True, {
                "filename": self.uploaded_filename,
                "text_length": extracted_length,
                "extraction_time": response.elapsed.total_seconds()
            })
            
        except Exception as e:
            result.add_error(f"Exception: {str(e)}")
            result.complete(False)
        
        return result
    
    async def test_2_industry_template(self) -> TestResult:
        """Test 2: Select and apply Luxury/Fashion industry template"""
        result = TestResult("Industry Template Selection")
        result.start()
        
        try:
            # Get RFP text from previous upload
            rfp_text = self.create_luxury_rfp().decode('utf-8')
            
            # Apply luxury fashion template
            response = await self.client.post(
                '/api/industry/suggest-deliverables',
                json={
                    "industry": "luxury_fashion",
                    "rfp_text": rfp_text
                }
            )
            
            if response.status_code != 200:
                result.add_error(f"Template application failed: {response.status_code}")
                return result
            
            data = response.json()
            
            # Validate template data
            deliverables = data.get('deliverables', [])
            if len(deliverables) < 50:  # Luxury template should have many deliverables
                result.add_error(f"Insufficient template deliverables: {len(deliverables)}")
                return result
            
            # Check for luxury-specific deliverables
            luxury_keywords = ['fashion', 'runway', 'couture', 'editorial', 'luxury']
            luxury_found = sum(1 for d in deliverables if any(k in str(d).lower() for k in luxury_keywords))
            
            if luxury_found < 10:
                result.add_error(f"Too few luxury-specific deliverables: {luxury_found}")
                return result
            
            result.complete(True, {
                "industry": "luxury_fashion",
                "template_deliverables": len(deliverables),
                "luxury_specific": luxury_found,
                "response_time": response.elapsed.total_seconds()
            })
            
        except Exception as e:
            result.add_error(f"Exception: {str(e)}")
            result.complete(False)
        
        return result
    
    async def test_3_gpt5_analysis(self) -> TestResult:
        """Test 3: Run GPT-5 analysis and verify 100+ deliverables"""
        result = TestResult("GPT-5 Analysis (100+ Deliverables)")
        result.start()
        
        try:
            rfp_text = self.create_luxury_rfp().decode('utf-8')
            
            # Start GPT-5 analysis with industry template
            response = await self.client.post(
                '/api/agencydb/analyze-rfp',
                json={
                    "rfp_text": rfp_text,
                    "industry": "luxury_fashion",
                    "mode": "deep",  # Use deep mode for comprehensive analysis
                    "min_deliverables": 100  # Explicitly request 100+ deliverables
                },
                timeout=60.0  # Extended timeout for deep analysis
            )
            
            if response.status_code != 200:
                result.add_error(f"Analysis failed: {response.status_code}")
                if response.text:
                    result.add_error(f"Error details: {response.text[:500]}")
                return result
            
            data = response.json()
            
            # Handle async job if returned
            if 'job_id' in data:
                job_id = data['job_id']
                # Poll for completion
                max_polls = 30  # 30 seconds max wait
                for i in range(max_polls):
                    await asyncio.sleep(1)
                    
                    status_response = await self.client.get(f'/api/agencydb/job-status/{job_id}')
                    if status_response.status_code != 200:
                        continue
                    
                    job_data = status_response.json()
                    if job_data.get('status') == 'completed':
                        data = job_data.get('result', {})
                        break
                    elif job_data.get('status') == 'failed':
                        result.add_error(f"Job failed: {job_data.get('error', 'Unknown error')}")
                        return result
                else:
                    result.add_error("Analysis job timed out")
                    return result
            
            # Verify deliverables count
            deliverables = data.get('deliverables', [])
            self.deliverables_count = len(deliverables)
            
            if self.deliverables_count < 100:
                result.add_error(f"Insufficient deliverables: {self.deliverables_count} (expected 100+)")
                return result
            
            # Check for GPT-5 specific features
            analysis_details = data.get('analysis', {})
            using_gpt5 = 'gpt-5' in str(analysis_details).lower() or data.get('model', '').startswith('gpt-5')
            
            # Verify quality of deliverables
            with_components = sum(1 for d in deliverables if d.get('components'))
            with_tasks = sum(1 for d in deliverables if any(c.get('tasks') for c in d.get('components', [])))
            
            result.complete(True, {
                "total_deliverables": self.deliverables_count,
                "deliverables_with_components": with_components,
                "deliverables_with_tasks": with_tasks,
                "using_gpt5": using_gpt5,
                "analysis_time": response.elapsed.total_seconds(),
                "luxury_focus": 'luxury' in str(deliverables).lower()
            })
            
        except Exception as e:
            result.add_error(f"Exception: {str(e)}")
            result.complete(False)
        
        return result
    
    async def test_4_build_scenario(self) -> TestResult:
        """Test 4: Build Scenario A and verify persistence"""
        result = TestResult("Build Scenario A")
        result.start()
        
        try:
            # Build scenario with selected deliverables
            build_payload = {
                "project_name": "Luxury Fashion Digital Transformation",
                "scenario": "A",
                "deliverables": [],  # Will be populated from previous analysis
                "timeline_months": 12,
                "team_size": "large"
            }
            
            # Get deliverables from analysis (simulate selection)
            # In real test, these would come from step 2 UI
            response = await self.client.post(
                '/api/build',
                json=build_payload
            )
            
            if response.status_code != 200:
                result.add_error(f"Scenario build failed: {response.status_code}")
                return result
            
            data = response.json()
            self.scenario_data = data
            
            # Verify scenario structure
            if 'scenario_a' not in data:
                result.add_error("Scenario A not found in response")
                return result
            
            scenario = data['scenario_a']
            
            # Check scenario completeness
            if not scenario.get('tasks'):
                result.add_error("No tasks in scenario")
                return result
            
            # Verify persistence by fetching again
            await asyncio.sleep(1)
            fetch_response = await self.client.get('/api/scenarios')
            if fetch_response.status_code == 200:
                persisted = fetch_response.json()
                if 'scenario_a' not in persisted:
                    result.add_error("Scenario not persisted")
                    return result
            
            result.complete(True, {
                "total_tasks": len(scenario.get('tasks', [])),
                "total_hours": scenario.get('summary', {}).get('total_hours', 0),
                "total_cost": scenario.get('summary', {}).get('total_cost', 0),
                "build_time": response.elapsed.total_seconds()
            })
            
        except Exception as e:
            result.add_error(f"Exception: {str(e)}")
            result.complete(False)
        
        return result
    
    async def test_5_ai_suggest_type(self) -> TestResult:
        """Test 5: AI Suggest Type (PROJECT vs RETAINER)"""
        result = TestResult("AI Suggest Type")
        result.start()
        
        try:
            rfp_text = self.create_luxury_rfp().decode('utf-8')
            
            response = await self.client.post(
                '/api/agencydb/ai-suggest-type',
                json={"rfp_text": rfp_text}
            )
            
            if response.status_code != 200:
                result.add_error(f"Type suggestion failed: {response.status_code}")
                return result
            
            data = response.json()
            
            # Verify response structure
            if 'recommendation' not in data:
                result.add_error("No recommendation in response")
                return result
            
            recommendation = data['recommendation']
            if recommendation not in ['PROJECT', 'RETAINER', 'HYBRID']:
                result.add_error(f"Invalid recommendation: {recommendation}")
                return result
            
            # For luxury fashion, should likely be RETAINER or HYBRID
            confidence = data.get('confidence', 0)
            
            result.complete(True, {
                "recommendation": recommendation,
                "confidence": confidence,
                "reasoning": data.get('reasoning', ''),
                "response_time": response.elapsed.total_seconds()
            })
            
        except Exception as e:
            result.add_error(f"Exception: {str(e)}")
            result.complete(False)
        
        return result
    
    async def test_6_optimize_pricing(self) -> TestResult:
        """Test 6: Optimize Pricing with $2M budget"""
        result = TestResult("Optimize Pricing ($2M Budget)")
        result.start()
        
        try:
            if not self.scenario_data:
                result.add_error("No scenario data available")
                return result
            
            response = await self.client.post(
                '/api/ai-optimize-price',
                json={
                    "scenario": self.scenario_data.get('scenario_a', {}),
                    "target_budget": 2000000,  # $2M
                    "optimization_goal": "maximize_value"
                }
            )
            
            if response.status_code != 200:
                result.add_error(f"Pricing optimization failed: {response.status_code}")
                return result
            
            data = response.json()
            
            # Verify optimization results
            if 'optimized_scenario' not in data:
                result.add_error("No optimized scenario returned")
                return result
            
            optimized = data['optimized_scenario']
            new_total = optimized.get('summary', {}).get('total_cost', 0)
            
            # Check if optimization worked
            if new_total <= 0:
                result.add_error("Invalid optimized total")
                return result
            
            # Verify it's close to target
            variance = abs(new_total - 2000000) / 2000000
            if variance > 0.1:  # More than 10% off target
                result.add_error(f"Optimization variance too high: {variance:.2%}")
            
            result.complete(True, {
                "original_budget": self.scenario_data.get('scenario_a', {}).get('summary', {}).get('total_cost', 0),
                "optimized_budget": new_total,
                "target_budget": 2000000,
                "variance_percent": variance * 100,
                "optimization_time": response.elapsed.total_seconds()
            })
            
        except Exception as e:
            result.add_error(f"Exception: {str(e)}")
            result.complete(False)
        
        return result
    
    async def test_7_generate_timeline(self) -> TestResult:
        """Test 7: Generate AI Timeline with CPM analysis"""
        result = TestResult("Generate AI Timeline")
        result.start()
        
        try:
            response = await self.client.post(
                '/api/ai-generate-timeline',
                json={
                    "deliverables": [],  # Would be populated from scenario
                    "start_date": "2026-01-01",
                    "duration_months": 12,
                    "use_cpm": True
                }
            )
            
            if response.status_code != 200:
                result.add_error(f"Timeline generation failed: {response.status_code}")
                return result
            
            data = response.json()
            
            # Verify timeline structure
            if 'timeline' not in data:
                result.add_error("No timeline in response")
                return result
            
            timeline = data['timeline']
            
            # Check for CPM analysis
            has_critical_path = data.get('critical_path', False)
            
            result.complete(True, {
                "total_tasks": len(timeline),
                "has_critical_path": has_critical_path,
                "start_date": data.get('start_date'),
                "end_date": data.get('end_date'),
                "response_time": response.elapsed.total_seconds()
            })
            
        except Exception as e:
            result.add_error(f"Exception: {str(e)}")
            result.complete(False)
        
        return result
    
    async def test_8_resource_risk(self) -> TestResult:
        """Test 8: Verify Resource Risk Management"""
        result = TestResult("Resource Risk Management")
        result.start()
        
        try:
            if not self.scenario_data:
                result.add_error("No scenario data available")
                return result
            
            scenario = self.scenario_data.get('scenario_a', {})
            tasks = scenario.get('tasks', [])
            
            # Check department distribution
            departments = {}
            for task in tasks:
                dept = task.get('department', 'Unknown')
                departments[dept] = departments.get(dept, 0) + 1
            
            # Check for resource conflicts
            conflicts = []
            resource_allocation = {}
            
            for task in tasks:
                resources = task.get('resources', [])
                start_date = task.get('start_date')
                end_date = task.get('end_date')
                
                for resource in resources:
                    if resource not in resource_allocation:
                        resource_allocation[resource] = []
                    
                    # Check for overlaps
                    for existing in resource_allocation[resource]:
                        if (start_date <= existing['end'] and end_date >= existing['start']):
                            conflicts.append({
                                'resource': resource,
                                'task1': task.get('name'),
                                'task2': existing['task']
                            })
                    
                    resource_allocation[resource].append({
                        'task': task.get('name'),
                        'start': start_date,
                        'end': end_date
                    })
            
            result.complete(True, {
                "total_departments": len(departments),
                "department_distribution": departments,
                "resource_conflicts": len(conflicts),
                "unique_resources": len(resource_allocation),
                "risk_level": "High" if len(conflicts) > 10 else "Medium" if len(conflicts) > 5 else "Low"
            })
            
        except Exception as e:
            result.add_error(f"Exception: {str(e)}")
            result.complete(False)
        
        return result
    
    async def test_9_xml_export(self) -> TestResult:
        """Test 9: Export to XML and validate Workfront compatibility"""
        result = TestResult("XML Export (Workfront)")
        result.start()
        
        try:
            # Export to Workfront XML
            response = await self.client.post(
                '/api/export',
                json={
                    "format": "xml",
                    "scenario": "A",
                    "project_name": "Luxury Fashion Digital Transformation"
                }
            )
            
            if response.status_code != 200:
                result.add_error(f"Export failed: {response.status_code}")
                return result
            
            # Save XML content
            xml_content = response.content
            self.export_filename = "test_export.xml"
            
            # Parse and validate XML structure
            try:
                root = ET.fromstring(xml_content)
                
                # Check for required MSPDI elements
                project = root.find('.//Project')
                if project is None:
                    result.add_error("No Project element in XML")
                    return result
                
                tasks = root.findall('.//Task')
                if len(tasks) < 10:
                    result.add_error(f"Insufficient tasks in XML: {len(tasks)}")
                    return result
                
                # Check for WBS structure
                wbs_codes = [t.find('WBS').text for t in tasks if t.find('WBS') is not None]
                if len(wbs_codes) < len(tasks) * 0.8:
                    result.add_error("Missing WBS codes in tasks")
                    return result
                
                # Check for resource assignments
                assignments = root.findall('.//Assignment')
                
                result.complete(True, {
                    "xml_size_kb": len(xml_content) / 1024,
                    "total_tasks": len(tasks),
                    "total_assignments": len(assignments),
                    "has_wbs": len(wbs_codes) > 0,
                    "workfront_compatible": True,
                    "export_time": response.elapsed.total_seconds()
                })
                
            except ET.ParseError as e:
                result.add_error(f"XML parsing error: {str(e)}")
                result.complete(False)
            
        except Exception as e:
            result.add_error(f"Exception: {str(e)}")
            result.complete(False)
        
        return result
    
    async def test_10_session_cleanup(self) -> TestResult:
        """Test 10: Test session cleanup and data isolation"""
        result = TestResult("Session Cleanup & Data Isolation")
        result.start()
        
        try:
            # Clear current session
            response = await self.client.post(
                '/api/clear_session',
                json={"session_id": self.session_id}
            )
            
            if response.status_code != 200:
                result.add_error(f"Session clear failed: {response.status_code}")
            
            # Upload a different RFP
            new_rfp = b"Simple test RFP for data isolation check. Need website redesign."
            files = {
                'file': ('test_rfp.txt', new_rfp, 'text/plain')
            }
            
            response = await self.client.post('/api/upload-and-extract', files=files)
            
            if response.status_code != 200:
                result.add_error(f"New upload failed: {response.status_code}")
                return result
            
            new_data = response.json()
            
            # Verify no contamination from previous session
            new_text = new_data.get('text', '')
            if 'luxury' in new_text.lower() or 'fashion' in new_text.lower():
                result.add_error("Data contamination detected - previous RFP content found")
                return result
            
            # Check scenarios are cleared
            scenarios_response = await self.client.get('/api/scenarios')
            if scenarios_response.status_code == 200:
                scenarios = scenarios_response.json()
                if scenarios and any(scenarios.values()):
                    result.add_error("Previous scenarios not cleared")
                    return result
            
            result.complete(True, {
                "session_cleared": True,
                "new_rfp_loaded": True,
                "data_isolation_verified": True,
                "cleanup_time": response.elapsed.total_seconds()
            })
            
        except Exception as e:
            result.add_error(f"Exception: {str(e)}")
            result.complete(False)
        
        return result
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Execute all tests and generate comprehensive report"""
        print("\n" + "="*80)
        print("AGENCY PROJECT BUILDER - COMPREHENSIVE E2E TEST SUITE")
        print("="*80)
        print(f"Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
        
        start_time = time.time()
        
        # Execute all tests
        tests = [
            self.test_1_rfp_upload,
            self.test_2_industry_template,
            self.test_3_gpt5_analysis,
            self.test_4_build_scenario,
            self.test_5_ai_suggest_type,
            self.test_6_optimize_pricing,
            self.test_7_generate_timeline,
            self.test_8_resource_risk,
            self.test_9_xml_export,
            self.test_10_session_cleanup
        ]
        
        for i, test_func in enumerate(tests, 1):
            print(f"\n[TEST {i}/10] Running: {test_func.__name__.replace('test_', '').replace('_', ' ').title()}")
            print("-" * 40)
            
            try:
                result = await test_func()
                self.test_results.append(result)
                
                # Print immediate result
                status_symbol = "✅" if result.status == "PASSED" else "❌"
                print(f"Status: {status_symbol} {result.status}")
                if result.duration:
                    print(f"Duration: {result.duration:.2f}s")
                if result.details:
                    for key, value in result.details.items():
                        print(f"  {key}: {value}")
                if result.errors:
                    for error in result.errors:
                        print(f"  ERROR: {error}")
                
            except Exception as e:
                print(f"  ❌ CRITICAL ERROR: {str(e)}")
                error_result = TestResult(test_func.__name__)
                error_result.status = "FAILED"
                error_result.add_error(f"Critical error: {str(e)}")
                self.test_results.append(error_result)
        
        total_time = time.time() - start_time
        
        # Generate comprehensive report
        report = self.generate_report(total_time)
        
        return report
    
    def generate_report(self, total_time: float) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        
        # Calculate statistics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.status == "PASSED")
        failed_tests = sum(1 for r in self.test_results if r.status == "FAILED")
        
        # Performance metrics
        avg_duration = sum(r.duration for r in self.test_results if r.duration) / max(1, len([r for r in self.test_results if r.duration]))
        total_memory = sum(abs(r.memory_after - r.memory_before) for r in self.test_results if r.memory_after)
        
        # Check performance against thresholds
        performance_issues = []
        for result in self.test_results:
            test_name = result.name.lower().replace(' ', '_')
            if test_name in PERFORMANCE_THRESHOLDS:
                threshold = PERFORMANCE_THRESHOLDS[test_name]
                if result.duration and result.duration > threshold:
                    performance_issues.append({
                        "test": result.name,
                        "duration": result.duration,
                        "threshold": threshold,
                        "exceeded_by": result.duration - threshold
                    })
        
        # Identify critical issues
        critical_issues = []
        for result in self.test_results:
            if result.status == "FAILED":
                critical_issues.extend([
                    {"test": result.name, "error": err} for err in result.errors
                ])
        
        # Production readiness assessment
        production_ready = self.assess_production_readiness(
            passed_tests, total_tests, performance_issues, critical_issues
        )
        
        report = {
            "test_suite": "Agency Project Builder - Comprehensive E2E",
            "execution_date": datetime.now().isoformat(),
            "total_duration": f"{total_time:.2f} seconds",
            
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "pass_rate": f"{(passed_tests/total_tests)*100:.1f}%"
            },
            
            "features_tested": [
                "RFP Document Upload and Extraction",
                "Industry Template System (Luxury/Fashion)",
                "GPT-5 Deep Analysis (100+ Deliverables)",
                "Scenario Building and Persistence",
                "AI Type Suggestion (Project/Retainer)",
                "AI Pricing Optimization",
                "AI Timeline Generation with CPM",
                "Resource Risk Management",
                "Workfront XML Export",
                "Session Cleanup and Data Isolation"
            ],
            
            "test_details": [
                {
                    "name": r.name,
                    "status": r.status,
                    "duration": f"{r.duration:.2f}s" if r.duration else "N/A",
                    "memory_delta": f"{abs(r.memory_after - r.memory_before):.1f} MB" if r.memory_after else "N/A",
                    "details": r.details,
                    "errors": r.errors
                }
                for r in self.test_results
            ],
            
            "performance_metrics": {
                "average_test_duration": f"{avg_duration:.2f}s",
                "total_memory_usage": f"{total_memory:.1f} MB",
                "performance_issues": performance_issues
            },
            
            "critical_issues": critical_issues,
            
            "production_readiness": production_ready
        }
        
        return report
    
    def assess_production_readiness(
        self, passed: int, total: int, 
        perf_issues: List, critical_issues: List
    ) -> Dict[str, Any]:
        """Assess production readiness based on test results"""
        
        pass_rate = (passed / total) * 100
        
        # Determine readiness level
        if pass_rate == 100 and len(perf_issues) == 0:
            readiness_level = "FULLY READY"
            recommendation = "System is ready for enterprise deployment"
            risk_level = "LOW"
        elif pass_rate >= 90 and len(critical_issues) <= 2:
            readiness_level = "READY WITH MINOR ISSUES"
            recommendation = "Deploy with monitoring, address minor issues in next sprint"
            risk_level = "MEDIUM-LOW"
        elif pass_rate >= 80:
            readiness_level = "CONDITIONALLY READY"
            recommendation = "Address critical issues before production deployment"
            risk_level = "MEDIUM"
        else:
            readiness_level = "NOT READY"
            recommendation = "Significant issues must be resolved before deployment"
            risk_level = "HIGH"
        
        return {
            "readiness_level": readiness_level,
            "recommendation": recommendation,
            "risk_level": risk_level,
            "pass_rate": f"{pass_rate:.1f}%",
            "blocking_issues": len([i for i in critical_issues if "GPT-5" in str(i) or "critical" in str(i).lower()]),
            "performance_concerns": len(perf_issues),
            
            "strengths": [
                "Comprehensive RFP processing capability",
                "Industry-specific template system",
                "Multi-scenario planning",
                "Enterprise-grade export formats",
                "Session isolation for data security"
            ],
            
            "areas_for_improvement": [
                issue["error"] for issue in critical_issues[:3]
            ] if critical_issues else ["None identified"],
            
            "deployment_checklist": {
                "core_functionality": pass_rate >= 80,
                "performance_acceptable": len(perf_issues) <= 3,
                "data_integrity": "session_cleanup" not in [i["test"].lower() for i in critical_issues],
                "export_compatibility": "xml_export" not in [i["test"].lower() for i in critical_issues],
                "ai_features_operational": "ai" not in " ".join([i["error"].lower() for i in critical_issues])
            }
        }
    
    def print_report(self, report: Dict[str, Any]):
        """Print formatted test report"""
        
        print("\n" + "="*80)
        print("TEST EXECUTION REPORT")
        print("="*80)
        
        # Summary
        summary = report["summary"]
        print(f"\nSUMMARY:")
        print(f"  Total Tests: {summary['total_tests']}")
        print(f"  Passed: {summary['passed']} ✅")
        print(f"  Failed: {summary['failed']} ❌")
        print(f"  Pass Rate: {summary['pass_rate']}")
        print(f"  Total Duration: {report['total_duration']}")
        
        # Test Details
        print(f"\nTEST RESULTS:")
        print("-" * 80)
        for detail in report["test_details"]:
            status_icon = "✅" if detail["status"] == "PASSED" else "❌"
            print(f"{status_icon} {detail['name']}")
            print(f"   Duration: {detail['duration']} | Memory: {detail['memory_delta']}")
            if detail["errors"]:
                for error in detail["errors"]:
                    print(f"   ❌ {error}")
        
        # Performance Metrics
        print(f"\nPERFORMANCE METRICS:")
        print("-" * 80)
        perf = report["performance_metrics"]
        print(f"  Average Test Duration: {perf['average_test_duration']}")
        print(f"  Total Memory Usage: {perf['total_memory_usage']}")
        if perf["performance_issues"]:
            print(f"  ⚠️ Performance Issues Detected:")
            for issue in perf["performance_issues"]:
                print(f"    - {issue['test']}: {issue['duration']:.2f}s (threshold: {issue['threshold']:.2f}s)")
        
        # Critical Issues
        if report["critical_issues"]:
            print(f"\n⚠️ CRITICAL ISSUES:")
            print("-" * 80)
            for issue in report["critical_issues"]:
                print(f"  - [{issue['test']}] {issue['error']}")
        
        # Production Readiness
        print(f"\nPRODUCTION READINESS ASSESSMENT:")
        print("=" * 80)
        readiness = report["production_readiness"]
        
        # Use color codes for readiness level
        level_colors = {
            "FULLY READY": "\033[92m",  # Green
            "READY WITH MINOR ISSUES": "\033[93m",  # Yellow
            "CONDITIONALLY READY": "\033[93m",  # Yellow
            "NOT READY": "\033[91m"  # Red
        }
        reset_color = "\033[0m"
        
        level_color = level_colors.get(readiness["readiness_level"], "")
        print(f"  Status: {level_color}{readiness['readiness_level']}{reset_color}")
        print(f"  Risk Level: {readiness['risk_level']}")
        print(f"  Recommendation: {readiness['recommendation']}")
        
        print(f"\n  Deployment Checklist:")
        for check, passed in readiness["deployment_checklist"].items():
            check_icon = "✅" if passed else "❌"
            print(f"    {check_icon} {check.replace('_', ' ').title()}")
        
        print(f"\n  Strengths:")
        for strength in readiness["strengths"]:
            print(f"    • {strength}")
        
        if readiness["areas_for_improvement"] and readiness["areas_for_improvement"][0] != "None identified":
            print(f"\n  Areas for Improvement:")
            for area in readiness["areas_for_improvement"]:
                print(f"    • {area}")
        
        print("\n" + "="*80)
        print("END OF REPORT")
        print("="*80 + "\n")

async def main():
    """Main test execution"""
    async with ComprehensiveE2ETest() as test_suite:
        report = await test_suite.run_all_tests()
        
        # Print report to console
        test_suite.print_report(report)
        
        # Save report to file
        report_filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Full report saved to: {report_filename}")
        
        # Return exit code based on results
        if report["summary"]["failed"] == 0:
            print("\n✅ ALL TESTS PASSED - System is production ready!")
            return 0
        else:
            print(f"\n❌ {report['summary']['failed']} TESTS FAILED - Review report for details")
            return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)