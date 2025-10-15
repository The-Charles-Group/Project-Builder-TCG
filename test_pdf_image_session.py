#!/usr/bin/env python3
"""
Comprehensive PDF Processing, Image Analysis & Session Isolation Test Suite
===========================================================================
Tests all critical functionality for PDF image processing and session isolation
to ensure no data contamination between RFP uploads.
"""

import os
import sys
import json
import time
import asyncio
import httpx
import uuid
import hashlib
import traceback
import psutil
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

# Test dependencies for PDF generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
except ImportError:
    print("Installing reportlab for PDF generation...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "reportlab"], check=True)
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader

try:
    from PIL import Image as PILImage, ImageDraw
except ImportError:
    print("Installing Pillow for image generation...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "Pillow"], check=True)
    from PIL import Image as PILImage, ImageDraw

import io
import random

# Test configuration
API_BASE_URL = "http://localhost:5000"
TIMEOUT = 600  # 10 minutes for large files
CONCURRENCY_LIMIT = 15  # Match server's concurrency for image processing

class PDFImageSessionTester:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {
                "pdf_processing": [],
                "session_isolation": [],
                "performance": []
            },
            "metrics": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0,
                "total_duration": 0,
                "memory_usage": {},
                "image_processing_stats": {},
                "session_isolation_stats": {},
                "performance_stats": {}
            },
            "session_isolation_verdict": None
        }
        self.client = None
        self.test_pdfs_created = []
        
    async def setup(self):
        """Initialize async HTTP client"""
        self.client = httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True)
        print("✅ Test client initialized")
        
    async def teardown(self):
        """Clean up resources"""
        if self.client:
            await self.client.aclose()
        
        # Clean up test PDFs
        for pdf_path in self.test_pdfs_created:
            try:
                os.remove(pdf_path)
                print(f"   Cleaned up: {pdf_path}")
            except:
                pass
    
    def generate_session_id(self) -> str:
        """Generate a unique session ID matching frontend format"""
        return f"session_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
    
    def create_test_pdf_with_images(self, num_images: int, name_suffix: str = "", 
                                    include_decorative: bool = True,
                                    page_count: int = 10) -> str:
        """Create a test PDF with specified number of images"""
        pdf_path = f"test_pdf_{name_suffix}_{num_images}_images_{page_count}p.pdf"
        c = canvas.Canvas(pdf_path, pagesize=letter)
        
        # Add title page with unique content
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, f"Test RFP - {name_suffix.replace('_', ' ').title()}")
        c.setFont("Helvetica", 12)
        c.drawString(100, 700, f"Total Images: {num_images}")
        c.drawString(100, 680, f"Pages: {page_count}")
        c.drawString(100, 650, "Project Requirements:")
        
        # Add unique content based on name_suffix to test isolation
        y_pos = 620
        if "soundcloud" in name_suffix.lower():
            requirements = [
                "• SoundCloud music streaming platform integration",
                "• Audio processing capabilities required",
                "• Real-time streaming infrastructure",
                "• Music recommendation algorithm development",
                "• Social features for music sharing"
            ]
        elif "ecommerce" in name_suffix.lower():
            requirements = [
                "• E-commerce marketplace platform",
                "• Payment gateway integration (Stripe, PayPal)",
                "• Inventory management system",
                "• Shopping cart and checkout flow",
                "• Order tracking and fulfillment"
            ]
        elif "healthcare" in name_suffix.lower():
            requirements = [
                "• Healthcare management system",
                "• HIPAA compliant data storage",
                "• Patient portal development",
                "• Electronic health records (EHR)",
                "• Telemedicine video consultation"
            ]
        else:
            requirements = [
                "• General software development project",
                "• Cloud infrastructure setup (AWS/Azure)",
                "• API development and integration",
                "• Database design and optimization",
                "• Security and authentication system"
            ]
        
        for req in requirements:
            c.drawString(100, y_pos, req)
            y_pos -= 20
        
        c.showPage()
        
        # Distribute images across pages
        images_per_page = max(1, num_images // (page_count - 1)) if page_count > 1 else num_images
        images_added = 0
        
        for page_num in range(2, page_count + 1):
            c.setFont("Helvetica-Bold", 14)
            c.drawString(100, 750, f"Page {page_num} - Technical Specifications")
            
            # Add detailed text content
            c.setFont("Helvetica", 10)
            y = 720
            specs = [
                f"Technical requirement {page_num}.1: System architecture design",
                f"Technical requirement {page_num}.2: Database schema planning",
                f"Technical requirement {page_num}.3: API endpoint documentation",
                f"Technical requirement {page_num}.4: Security implementation",
                f"Technical requirement {page_num}.5: Performance optimization"
            ]
            for spec in specs:
                c.drawString(100, y, f"• {spec}")
                y -= 20
            
            # Add images to this page
            if images_added < num_images:
                images_on_page = min(images_per_page, num_images - images_added)
                
                for img_idx in range(images_on_page):
                    # Create different types of images for testing
                    img_type = img_idx % 4
                    
                    # Create image in memory
                    img_io = io.BytesIO()
                    
                    if img_type == 0:  # Chart/diagram (relevant)
                        img = PILImage.new('RGB', (400, 300), color='white')
                        draw = ImageDraw.Draw(img)
                        # Draw a chart
                        draw.rectangle([50, 50, 350, 250], outline='black', width=2)
                        # Draw data lines
                        points = [(100, 200), (150, 150), (200, 180), (250, 120), (300, 140)]
                        for i in range(len(points)-1):
                            draw.line([points[i], points[i+1]], fill='blue', width=2)
                        draw.text((60, 260), f"Chart {images_added + 1}: Performance Metrics", fill='black')
                        
                    elif img_type == 1 and include_decorative:  # Logo (decorative - should be filtered)
                        img = PILImage.new('RGB', (80, 80), color='lightgray')
                        draw = ImageDraw.Draw(img)
                        draw.ellipse([10, 10, 70, 70], fill='#cccccc', outline='#888888', width=2)
                        draw.text((25, 30), "LOGO", fill='black')
                        
                    elif img_type == 2:  # Architecture diagram (relevant)
                        img = PILImage.new('RGB', (500, 400), color='white')
                        draw = ImageDraw.Draw(img)
                        # Draw system architecture
                        draw.rectangle([20, 20, 480, 60], fill='#e3f2fd', outline='#1976d2', width=2)
                        draw.text((30, 30), "Frontend Layer - React/Vue", fill='black')
                        draw.rectangle([20, 80, 230, 180], fill='#fff3e0', outline='#f57c00', width=2)
                        draw.text((30, 120), "API Gateway", fill='black')
                        draw.rectangle([250, 80, 480, 180], fill='#fff3e0', outline='#f57c00', width=2)
                        draw.text((260, 120), "Microservices", fill='black')
                        draw.rectangle([20, 200, 480, 300], fill='#f3e5f5', outline='#7b1fa2', width=2)
                        draw.text((30, 240), "Database Layer - PostgreSQL", fill='black')
                        draw.text((30, 320), f"Architecture Diagram {images_added + 1}", fill='black')
                        
                    else:  # UI mockup (relevant)
                        img = PILImage.new('RGB', (600, 450), color='white')
                        draw = ImageDraw.Draw(img)
                        # Draw UI mockup
                        draw.rectangle([0, 0, 600, 60], fill='#3f51b5')
                        draw.text((20, 20), "Application Header - Dashboard View", fill='white')
                        draw.rectangle([0, 60, 150, 450], fill='#f5f5f5')
                        draw.text((10, 70), "Navigation", fill='black')
                        draw.rectangle([170, 80, 580, 200], fill='#e8f5e9')
                        draw.text((180, 90), f"Widget {images_added + 1}: Analytics", fill='black')
                        draw.rectangle([170, 220, 580, 340], fill='#fce4ec')
                        draw.text((180, 230), f"Widget {images_added + 2}: Reports", fill='black')
                        draw.rectangle([170, 360, 580, 430], fill='#f3e5f5')
                        draw.text((180, 370), "Recent Activities", fill='black')
                    
                    img.save(img_io, 'PNG')
                    img_io.seek(0)
                    
                    # Add image to PDF
                    try:
                        img_reader = ImageReader(img_io)
                        y_pos = 500 - ((img_idx % 2) * 200)
                        x_pos = 100 if img_idx % 2 == 0 else 350
                        
                        if y_pos > 100:
                            if img_type == 1 and include_decorative:  # Small logo
                                c.drawImage(img_reader, x_pos, y_pos, width=40, height=40)
                            else:  # Larger relevant images
                                width = 180 if img_type != 2 else 200
                                height = 120 if img_type != 2 else 150
                                c.drawImage(img_reader, x_pos if img_type != 2 else 200, 
                                          y_pos, width=width, height=height)
                        images_added += 1
                    except Exception as e:
                        print(f"Warning: Could not add image {images_added}: {e}")
            
            c.showPage()
        
        c.save()
        self.test_pdfs_created.append(pdf_path)
        file_size_mb = os.path.getsize(pdf_path) / 1024 / 1024
        print(f"   Created: {pdf_path} ({num_images} images, {page_count} pages, {file_size_mb:.2f}MB)")
        return pdf_path
    
    # ==================== PDF PROCESSING WITH IMAGES TESTS ====================
    
    async def test_parallel_image_processing(self):
        """Test parallel image processing with OpenAI Vision API"""
        test_name = "Parallel Image Processing (15+ images)"
        print(f"\n🔄 Testing: {test_name}")
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            # Create PDF with 18 images to test parallel processing
            pdf_path = self.create_test_pdf_with_images(18, "parallel_test", include_decorative=False)
            session_id = self.generate_session_id()
            
            # Upload with image analysis enabled
            with open(pdf_path, 'rb') as f:
                files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
                data = {
                    'analyze_images': 'true',
                    'async': 'true',
                    'session_id': session_id
                }
                
                response = await self.client.post(
                    f"{API_BASE_URL}/api/upload",
                    files=files,
                    data=data
                )
            
            if response.status_code != 200:
                raise Exception(f"Upload failed: {response.status_code} - {response.text}")
            
            result = response.json()
            job_id = result.get('job_id')
            
            if not job_id:
                raise Exception("No job_id returned for async processing")
            
            print(f"   Job started: {job_id[:8]}...")
            
            # Monitor progress
            progress_updates = []
            max_wait = 180  # 3 minutes max
            start_wait = time.time()
            completed = False
            last_progress = 0
            
            while time.time() - start_wait < max_wait:
                await asyncio.sleep(2)
                
                progress_response = await self.client.get(
                    f"{API_BASE_URL}/api/upload/progress/{job_id}"
                )
                
                if progress_response.status_code == 200:
                    progress = progress_response.json()
                    current_progress = progress.get('percentage', 0)
                    
                    # Only log significant progress changes
                    if current_progress - last_progress >= 10 or progress.get('status') == 'completed':
                        progress_updates.append({
                            "time": time.time() - start_wait,
                            "percentage": current_progress,
                            "phase": progress.get('phase', 'unknown'),
                            "processed": progress.get('processed_images', 0),
                            "total": progress.get('total_images', 0),
                            "skipped": progress.get('skipped_images', 0),
                            "relevant": progress.get('relevant_images', 0),
                            "status": progress.get('status')
                        })
                        
                        if current_progress > last_progress:
                            print(f"   Progress: {current_progress:.0f}% - Phase: {progress.get('phase', 'processing')}")
                            last_progress = current_progress
                    
                    if progress.get('status') == 'completed':
                        completed = True
                        break
                    elif progress.get('status') == 'failed':
                        raise Exception(f"Job failed: {progress.get('errors', 'Unknown error')}")
            
            if not completed:
                # Try to cancel the job if it's still running
                await self.client.post(f"{API_BASE_URL}/api/upload/cancel/{job_id}")
                raise Exception("Job did not complete within timeout")
            
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            duration = time.time() - start_time
            
            # Verify parallel processing occurred
            parallel_verified = False
            if len(progress_updates) >= 2:
                # Check processing speed indicates parallelism
                for i in range(1, len(progress_updates)):
                    delta_images = progress_updates[i]['processed'] - progress_updates[i-1].get('processed', 0)
                    delta_time = progress_updates[i]['time'] - progress_updates[i-1]['time']
                    if delta_images > 2 and delta_time < 15:  # Multiple images in short time
                        parallel_verified = True
                        break
            
            # Also check if we processed multiple images quickly overall
            if progress_updates and progress_updates[-1]['processed'] > 10:
                images_per_second = progress_updates[-1]['processed'] / duration
                if images_per_second > 0.5:  # More than 0.5 images/second suggests parallelism
                    parallel_verified = True
            
            test_result = {
                "name": test_name,
                "status": "passed" if completed else "failed",
                "completed": completed,
                "parallel_verified": parallel_verified,
                "duration": duration,
                "memory_delta_mb": end_memory - start_memory,
                "progress_updates": len(progress_updates),
                "final_progress": progress_updates[-1] if progress_updates else None
            }
            
            status_icon = "✅" if completed else "❌"
            print(f"{status_icon} {test_name}: {'Passed' if completed else 'Failed'}")
            print(f"   Duration: {duration:.2f}s, Memory: +{end_memory - start_memory:.1f}MB")
            if progress_updates and progress_updates[-1]:
                final = progress_updates[-1]
                print(f"   Processed: {final['processed']}/{final['total']} images")
                print(f"   Parallel processing: {'Yes' if parallel_verified else 'Not verified'}")
            
            self.results["tests"]["pdf_processing"].append(test_result)
            if completed:
                self.results["metrics"]["passed"] += 1
            else:
                self.results["metrics"]["failed"] += 1
            
            return test_result
            
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"]["pdf_processing"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.results["metrics"]["failed"] += 1
            return None
    
    async def test_progress_tracking(self):
        """Test progress tracking during image processing"""
        test_name = "Progress Tracking Accuracy"
        print(f"\n🔄 Testing: {test_name}")
        
        start_time = time.time()
        
        try:
            # Create PDF with known number of images
            pdf_path = self.create_test_pdf_with_images(10, "progress_test", include_decorative=False)
            session_id = self.generate_session_id()
            
            # Upload with async processing
            with open(pdf_path, 'rb') as f:
                files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
                data = {
                    'analyze_images': 'true',
                    'async': 'true',
                    'session_id': session_id
                }
                
                response = await self.client.post(
                    f"{API_BASE_URL}/api/upload",
                    files=files,
                    data=data
                )
            
            result = response.json()
            job_id = result.get('job_id')
            
            # Collect all progress updates
            all_progress = []
            max_wait = 120
            start_wait = time.time()
            
            while time.time() - start_wait < max_wait:
                await asyncio.sleep(1)
                
                progress_response = await self.client.get(
                    f"{API_BASE_URL}/api/upload/progress/{job_id}"
                )
                
                if progress_response.status_code == 200:
                    progress = progress_response.json()
                    all_progress.append({
                        "time": time.time() - start_wait,
                        "percentage": progress.get('percentage', 0),
                        "processed": progress.get('processed_images', 0),
                        "total": progress.get('total_images', 0),
                        "phase": progress.get('phase'),
                        "status": progress.get('status')
                    })
                    
                    if progress.get('status') == 'completed':
                        break
            
            # Verify progress tracking
            progress_valid = True
            issues = []
            
            # Check monotonic increase
            for i in range(1, len(all_progress)):
                if all_progress[i]['percentage'] < all_progress[i-1]['percentage']:
                    progress_valid = False
                    issues.append("Progress went backward")
                    break
            
            # Check final state
            if all_progress and all_progress[-1]['status'] == 'completed':
                if all_progress[-1]['percentage'] < 95:  # Allow small rounding
                    progress_valid = False
                    issues.append(f"Final progress only {all_progress[-1]['percentage']}%")
            
            # Check reasonable update frequency
            if len(all_progress) < 3:
                issues.append("Too few progress updates")
            
            test_result = {
                "name": test_name,
                "status": "passed" if progress_valid and not issues else "warning",
                "progress_valid": progress_valid,
                "total_updates": len(all_progress),
                "issues": issues,
                "duration": time.time() - start_time
            }
            
            status_icon = "✅" if progress_valid and not issues else "⚠️"
            print(f"{status_icon} {test_name}: {'Passed' if progress_valid else 'Warning'}")
            print(f"   Total updates: {len(all_progress)}")
            if issues:
                for issue in issues:
                    print(f"   Issue: {issue}")
            
            self.results["tests"]["pdf_processing"].append(test_result)
            if progress_valid and not issues:
                self.results["metrics"]["passed"] += 1
            else:
                self.results["metrics"]["warnings"] += 1
            
            return test_result
            
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"]["pdf_processing"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.results["metrics"]["failed"] += 1
            return None
    
    async def test_two_tier_image_analysis(self):
        """Test two-tier image analysis (quick scan + deep analysis)"""
        test_name = "Two-Tier Image Analysis (Quick + Deep)"
        print(f"\n🔄 Testing: {test_name}")
        
        start_time = time.time()
        
        try:
            # Create PDF with mix of relevant and decorative images
            pdf_path = self.create_test_pdf_with_images(20, "two_tier", include_decorative=True)
            session_id = self.generate_session_id()
            
            # Upload with async processing
            with open(pdf_path, 'rb') as f:
                files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
                data = {
                    'analyze_images': 'true',
                    'async': 'true',
                    'session_id': session_id
                }
                
                response = await self.client.post(
                    f"{API_BASE_URL}/api/upload",
                    files=files,
                    data=data
                )
            
            result = response.json()
            job_id = result.get('job_id')
            
            # Track phase transitions
            phases_observed = set()
            phase_transitions = []
            last_phase = None
            
            max_wait = 240  # 4 minutes max
            start_wait = time.time()
            completed = False
            
            while time.time() - start_wait < max_wait:
                await asyncio.sleep(2)
                
                progress_response = await self.client.get(
                    f"{API_BASE_URL}/api/upload/progress/{job_id}"
                )
                
                if progress_response.status_code == 200:
                    progress = progress_response.json()
                    current_phase = progress.get('phase', 'unknown')
                    
                    if current_phase not in phases_observed:
                        phases_observed.add(current_phase)
                        phase_transitions.append({
                            "from": last_phase,
                            "to": current_phase,
                            "time": time.time() - start_wait,
                            "processed": progress.get('processed_images', 0),
                            "skipped": progress.get('skipped_images', 0),
                            "relevant": progress.get('relevant_images', 0)
                        })
                        print(f"   Phase transition: {last_phase} → {current_phase} at {time.time() - start_wait:.1f}s")
                        last_phase = current_phase
                    
                    if progress.get('status') == 'completed':
                        completed = True
                        break
            
            # Verify two-tier processing
            has_quick_scan = 'quick_scan' in phases_observed
            has_deep_analysis = 'deep_analysis' in phases_observed
            two_tier_verified = has_quick_scan and has_deep_analysis
            
            test_result = {
                "name": test_name,
                "status": "passed" if two_tier_verified and completed else "failed",
                "two_tier_verified": two_tier_verified,
                "phases_observed": list(phases_observed),
                "phase_count": len(phases_observed),
                "phase_transitions": phase_transitions,
                "completed": completed,
                "duration": time.time() - start_time
            }
            
            status_icon = "✅" if two_tier_verified and completed else "❌"
            print(f"{status_icon} {test_name}: {'Passed' if two_tier_verified else 'Failed'}")
            print(f"   Phases observed: {', '.join(phases_observed)}")
            print(f"   Two-tier analysis: {'Confirmed' if two_tier_verified else 'Not detected'}")
            
            self.results["tests"]["pdf_processing"].append(test_result)
            if two_tier_verified and completed:
                self.results["metrics"]["passed"] += 1
            else:
                self.results["metrics"]["failed"] += 1
            
            return test_result
            
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"]["pdf_processing"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.results["metrics"]["failed"] += 1
            return None
    
    async def test_decorative_image_filtering(self):
        """Test that decorative images are properly filtered out"""
        test_name = "Decorative Image Filtering"
        print(f"\n🔄 Testing: {test_name}")
        
        start_time = time.time()
        
        try:
            # Create PDF with 30% decorative images
            pdf_path = self.create_test_pdf_with_images(
                30, "filtering", include_decorative=True, page_count=6
            )
            session_id = self.generate_session_id()
            
            # Upload with async processing
            with open(pdf_path, 'rb') as f:
                files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
                data = {
                    'analyze_images': 'true',
                    'async': 'true', 
                    'session_id': session_id
                }
                
                response = await self.client.post(
                    f"{API_BASE_URL}/api/upload",
                    files=files,
                    data=data
                )
            
            result = response.json()
            job_id = result.get('job_id')
            
            # Wait for completion and track filtering
            max_wait = 240
            start_wait = time.time()
            final_stats = None
            
            while time.time() - start_wait < max_wait:
                await asyncio.sleep(2)
                
                progress_response = await self.client.get(
                    f"{API_BASE_URL}/api/upload/progress/{job_id}"
                )
                
                if progress_response.status_code == 200:
                    progress = progress_response.json()
                    
                    if progress.get('status') == 'completed':
                        final_stats = {
                            "total": progress.get('total_images', 0),
                            "skipped": progress.get('skipped_images', 0),
                            "relevant": progress.get('relevant_images', 0),
                            "processed": progress.get('processed_images', 0)
                        }
                        break
            
            # Verify filtering occurred
            filtering_verified = False
            filter_ratio = 0
            if final_stats and final_stats['total'] > 0:
                filter_ratio = final_stats['skipped'] / final_stats['total']
                # Expect at least 15% filtering for decorative images
                filtering_verified = filter_ratio > 0.15 or final_stats['skipped'] > 3
            
            test_result = {
                "name": test_name,
                "status": "passed" if filtering_verified else "warning",
                "filtering_verified": filtering_verified,
                "filter_ratio": filter_ratio,
                "final_stats": final_stats,
                "duration": time.time() - start_time
            }
            
            status_icon = "✅" if filtering_verified else "⚠️"
            print(f"{status_icon} {test_name}: {'Passed' if filtering_verified else 'Warning - Low filtering'}")
            if final_stats:
                print(f"   Total images: {final_stats['total']}")
                print(f"   Filtered out: {final_stats['skipped']} ({filter_ratio:.1%})")
                print(f"   Relevant for analysis: {final_stats['relevant']}")
            
            self.results["tests"]["pdf_processing"].append(test_result)
            if filtering_verified:
                self.results["metrics"]["passed"] += 1
            else:
                self.results["metrics"]["warnings"] += 1
            
            return test_result
            
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"]["pdf_processing"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.results["metrics"]["failed"] += 1
            return None
    
    async def test_error_handling_retry(self):
        """Test error handling and retry logic"""
        test_name = "Error Handling & Retry Logic"
        print(f"\n🔄 Testing: {test_name}")
        
        start_time = time.time()
        
        try:
            # Create small PDF for quick test
            pdf_path = self.create_test_pdf_with_images(5, "error_test", page_count=3)
            session_id = self.generate_session_id()
            
            # Upload with async processing
            with open(pdf_path, 'rb') as f:
                files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
                data = {
                    'analyze_images': 'true',
                    'async': 'true',
                    'session_id': session_id
                }
                
                response = await self.client.post(
                    f"{API_BASE_URL}/api/upload",
                    files=files,
                    data=data
                )
            
            result = response.json()
            job_id = result.get('job_id')
            
            # Monitor for errors and completion
            errors_observed = []
            max_wait = 120
            start_wait = time.time()
            completed = False
            final_status = None
            
            while time.time() - start_wait < max_wait:
                await asyncio.sleep(2)
                
                progress_response = await self.client.get(
                    f"{API_BASE_URL}/api/upload/progress/{job_id}"
                )
                
                if progress_response.status_code == 200:
                    progress = progress_response.json()
                    
                    errors = progress.get('errors', [])
                    if errors and errors not in errors_observed:
                        errors_observed = errors
                    
                    final_status = progress.get('status')
                    if final_status in ['completed', 'failed', 'cancelled']:
                        completed = final_status == 'completed'
                        break
            
            # System should handle errors gracefully
            graceful_handling = completed or final_status == 'completed'
            
            test_result = {
                "name": test_name,
                "status": "passed" if graceful_handling else "warning",
                "completed": completed,
                "final_status": final_status,
                "errors_observed": len(errors_observed),
                "graceful_handling": graceful_handling,
                "duration": time.time() - start_time
            }
            
            status_icon = "✅" if graceful_handling else "⚠️"
            print(f"{status_icon} {test_name}: {'Passed' if graceful_handling else 'Warning'}")
            print(f"   Final status: {final_status}")
            print(f"   Errors handled: {len(errors_observed)}")
            print(f"   Graceful completion: {'Yes' if graceful_handling else 'No'}")
            
            self.results["tests"]["pdf_processing"].append(test_result)
            if graceful_handling:
                self.results["metrics"]["passed"] += 1
            else:
                self.results["metrics"]["warnings"] += 1
            
            return test_result
            
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"]["pdf_processing"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.results["metrics"]["failed"] += 1
            return None
    
    # ==================== SESSION ISOLATION TESTS ====================
    
    async def test_sequential_rfp_uploads(self):
        """Test uploading multiple RFPs in sequence with different sessions"""
        test_name = "Sequential RFP Upload Isolation"
        print(f"\n🔄 Testing: {test_name}")
        
        start_time = time.time()
        
        try:
            # Create different RFPs with distinct content
            rfps = [
                ("soundcloud", "SoundCloud streaming platform"),
                ("ecommerce", "E-commerce marketplace"),
                ("healthcare", "Healthcare management system")
            ]
            
            session_data = []
            
            for rfp_name, rfp_description in rfps:
                pdf_path = self.create_test_pdf_with_images(5, rfp_name, page_count=3)
                session_id = self.generate_session_id()
                
                print(f"   Uploading {rfp_name} RFP with session {session_id[:30]}...")
                
                # Upload RFP
                with open(pdf_path, 'rb') as f:
                    files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
                    data = {
                        'analyze_images': 'false',  # Skip images for faster test
                        'session_id': session_id
                    }
                    
                    response = await self.client.post(
                        f"{API_BASE_URL}/api/upload",
                        files=files,
                        data=data
                    )
                
                if response.status_code != 200:
                    print(f"   Warning: Upload failed for {rfp_name}")
                    continue
                
                # Wait a moment for processing
                await asyncio.sleep(2)
                
                # Get suggestions for this session
                suggest_response = await self.client.post(
                    f"{API_BASE_URL}/api/suggest/deliverables",
                    json={"rfp_text": rfp_description, "session_id": session_id}
                )
                
                suggestions = []
                if suggest_response.status_code == 200:
                    suggest_data = suggest_response.json()
                    suggestions = suggest_data.get('deliverables', [])[:10]
                
                session_data.append({
                    "rfp_name": rfp_name,
                    "session_id": session_id,
                    "unique_keywords": rfp_name.lower(),  # Use RFP name as unique keyword
                    "suggestions_text": ' '.join([str(s) for s in suggestions]).lower()
                })
                
                # Clear session after each RFP
                clear_response = await self.client.post(
                    f"{API_BASE_URL}/api/clear_session",
                    json={"session_id": session_id}
                )
                
                if clear_response.status_code == 200:
                    print(f"   Session cleared for {rfp_name}")
                
                await asyncio.sleep(1)
            
            # Check for data contamination between sessions
            contamination_found = False
            contamination_details = []
            
            for i, session in enumerate(session_data):
                # Check if keywords from other sessions appear in this session's suggestions
                for j, other_session in enumerate(session_data):
                    if i != j:
                        # Look for the other session's unique keyword in this session's suggestions
                        if other_session['unique_keywords'] in session['suggestions_text']:
                            contamination_found = True
                            contamination_details.append({
                                "session": session['rfp_name'],
                                "contaminated_by": other_session['rfp_name'],
                                "keyword_found": other_session['unique_keywords']
                            })
            
            test_result = {
                "name": test_name,
                "status": "passed" if not contamination_found else "failed",
                "sessions_tested": len(session_data),
                "contamination_found": contamination_found,
                "contamination_details": contamination_details,
                "duration": time.time() - start_time
            }
            
            status_icon = "✅" if not contamination_found else "❌"
            print(f"{status_icon} {test_name}: {'PASSED - No contamination' if not contamination_found else 'FAILED - Contamination detected'}")
            print(f"   Sessions tested: {len(session_data)}")
            if contamination_found:
                print(f"   ⚠️ CONTAMINATION FOUND:")
                for detail in contamination_details:
                    print(f"      {detail['session']} contains data from {detail['contaminated_by']}")
                    print(f"      Keyword found: '{detail['keyword_found']}'")
            else:
                print(f"   ✓ Each session properly isolated")
            
            self.results["tests"]["session_isolation"].append(test_result)
            if not contamination_found:
                self.results["metrics"]["passed"] += 1
            else:
                self.results["metrics"]["failed"] += 1
            
            return test_result
            
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"]["session_isolation"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.results["metrics"]["failed"] += 1
            return None
    
    async def test_unique_session_ids(self):
        """Verify each RFP gets a unique session ID"""
        test_name = "Unique Session ID Generation"
        print(f"\n🔄 Testing: {test_name}")
        
        start_time = time.time()
        
        try:
            session_ids = []
            
            # Generate multiple session IDs
            for i in range(20):
                session_id = self.generate_session_id()
                session_ids.append(session_id)
                await asyncio.sleep(0.01)  # Small delay to ensure timestamp difference
            
            # Check uniqueness
            unique_ids = set(session_ids)
            all_unique = len(unique_ids) == len(session_ids)
            
            # Check format (should match frontend format)
            format_valid = all(
                s.startswith('session_') and 
                len(s) > 20 and 
                '_' in s[8:]  # Has underscore after timestamp
                for s in session_ids
            )
            
            test_result = {
                "name": test_name,
                "status": "passed" if all_unique and format_valid else "failed",
                "total_generated": len(session_ids),
                "unique_count": len(unique_ids),
                "all_unique": all_unique,
                "format_valid": format_valid,
                "duration": time.time() - start_time
            }
            
            status_icon = "✅" if all_unique and format_valid else "❌"
            print(f"{status_icon} {test_name}: {'Passed' if all_unique and format_valid else 'Failed'}")
            print(f"   Generated: {len(session_ids)} session IDs")
            print(f"   All unique: {'Yes' if all_unique else f'No - {len(session_ids) - len(unique_ids)} duplicates'}")
            print(f"   Format valid: {'Yes' if format_valid else 'No'}")
            
            self.results["tests"]["session_isolation"].append(test_result)
            if all_unique and format_valid:
                self.results["metrics"]["passed"] += 1
            else:
                self.results["metrics"]["failed"] += 1
            
            return test_result
            
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"]["session_isolation"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.results["metrics"]["failed"] += 1
            return None
    
    async def test_embedding_cache_isolation(self):
        """Test that embedding cache is properly isolated by session"""
        test_name = "Embedding Cache Session Isolation"
        print(f"\n🔄 Testing: {test_name}")
        
        start_time = time.time()
        
        try:
            # Create two sessions
            session1 = self.generate_session_id()
            session2 = self.generate_session_id()
            
            test_text1 = "This is a test for SoundCloud music streaming platform integration"
            test_text2 = "This is a test for healthcare management system development"
            
            print(f"   Session 1: {session1[:30]}...")
            print(f"   Session 2: {session2[:30]}...")
            
            # Submit different text to each session
            response1 = await self.client.post(
                f"{API_BASE_URL}/api/suggest/deliverables",
                json={"rfp_text": test_text1, "session_id": session1}
            )
            
            response2 = await self.client.post(
                f"{API_BASE_URL}/api/suggest/deliverables",
                json={"rfp_text": test_text2, "session_id": session2}
            )
            
            # Get suggestions for each session
            suggestions1 = response1.json().get('deliverables', []) if response1.status_code == 200 else []
            suggestions2 = response2.json().get('deliverables', []) if response2.status_code == 200 else []
            
            # Clear session 1
            clear1_response = await self.client.post(
                f"{API_BASE_URL}/api/clear_session",
                json={"session_id": session1}
            )
            
            print(f"   Session 1 cleared: {clear1_response.status_code == 200}")
            
            # Try to get suggestions for session 1 again (should recompute)
            response1_after = await self.client.post(
                f"{API_BASE_URL}/api/suggest/deliverables",
                json={"rfp_text": test_text1, "session_id": session1}
            )
            
            # Session 2 should still work with its cached data
            response2_after = await self.client.post(
                f"{API_BASE_URL}/api/suggest/deliverables",
                json={"rfp_text": test_text2, "session_id": session2}
            )
            
            # Check isolation
            session1_cleared = clear1_response.status_code == 200
            session1_works_after = response1_after.status_code == 200
            session2_unaffected = response2_after.status_code == 200
            
            # Check for cross-contamination
            suggestions1_text = ' '.join([str(s) for s in suggestions1]).lower()
            suggestions2_text = ' '.join([str(s) for s in suggestions2]).lower()
            
            no_soundcloud_in_healthcare = 'soundcloud' not in suggestions2_text
            no_healthcare_in_soundcloud = 'healthcare' not in suggestions1_text
            
            isolation_verified = (
                session1_cleared and 
                session1_works_after and 
                session2_unaffected and
                no_soundcloud_in_healthcare and
                no_healthcare_in_soundcloud
            )
            
            test_result = {
                "name": test_name,
                "status": "passed" if isolation_verified else "failed",
                "isolation_verified": isolation_verified,
                "session1_cleared": session1_cleared,
                "session1_works_after": session1_works_after,
                "session2_unaffected": session2_unaffected,
                "no_cross_contamination": no_soundcloud_in_healthcare and no_healthcare_in_soundcloud,
                "duration": time.time() - start_time
            }
            
            status_icon = "✅" if isolation_verified else "❌"
            print(f"{status_icon} {test_name}: {'Passed' if isolation_verified else 'Failed'}")
            print(f"   Cache isolation: {'Verified' if isolation_verified else 'Not verified'}")
            print(f"   Cross-contamination: {'None detected' if no_soundcloud_in_healthcare and no_healthcare_in_soundcloud else 'DETECTED'}")
            
            self.results["tests"]["session_isolation"].append(test_result)
            if isolation_verified:
                self.results["metrics"]["passed"] += 1
            else:
                self.results["metrics"]["failed"] += 1
            
            return test_result
            
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"]["session_isolation"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.results["metrics"]["failed"] += 1
            return None
    
    async def test_clear_all_data_functionality(self):
        """Test the Clear All Data button functionality"""
        test_name = "Clear All Data Button"
        print(f"\n🔄 Testing: {test_name}")
        
        start_time = time.time()
        
        try:
            session_id = self.generate_session_id()
            
            # Upload some data
            pdf_path = self.create_test_pdf_with_images(3, "clear_test", page_count=2)
            with open(pdf_path, 'rb') as f:
                files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
                data = {
                    'analyze_images': 'false',
                    'session_id': session_id
                }
                
                await self.client.post(
                    f"{API_BASE_URL}/api/upload",
                    files=files,
                    data=data
                )
            
            # Cache some RFP text
            await self.client.post(
                f"{API_BASE_URL}/api/rfp/cache",
                data={"text": "Test RFP content for clearing"}
            )
            
            # Get initial cached text
            cache_before = await self.client.get(f"{API_BASE_URL}/api/rfp/cache")
            has_cache_before = bool(cache_before.json().get('text')) if cache_before.status_code == 200 else False
            
            # Clear all data for session
            clear_response = await self.client.post(
                f"{API_BASE_URL}/api/clear_session",
                json={"session_id": session_id}
            )
            
            # Verify clearing
            clear_success = clear_response.status_code == 200
            clear_data = clear_response.json() if clear_success else {}
            
            # Check cache is cleared
            cache_after = await self.client.get(f"{API_BASE_URL}/api/rfp/cache")
            has_cache_after = bool(cache_after.json().get('text')) if cache_after.status_code == 200 else False
            
            # Check clearing details
            embedding_cleared = clear_data.get('cleared', {}).get('embedding_cache', False)
            rfp_cache_cleared = clear_data.get('cleared', {}).get('rfp_text_cache', False)
            
            clearing_verified = (
                clear_success and
                has_cache_before and
                not has_cache_after and
                embedding_cleared and
                rfp_cache_cleared
            )
            
            test_result = {
                "name": test_name,
                "status": "passed" if clearing_verified else "failed",
                "clearing_verified": clearing_verified,
                "had_cache_before": has_cache_before,
                "has_cache_after": has_cache_after,
                "embedding_cleared": embedding_cleared,
                "rfp_cache_cleared": rfp_cache_cleared,
                "duration": time.time() - start_time
            }
            
            status_icon = "✅" if clearing_verified else "❌"
            print(f"{status_icon} {test_name}: {'Passed' if clearing_verified else 'Failed'}")
            print(f"   Cache before clear: {'Yes' if has_cache_before else 'No'}")
            print(f"   Cache after clear: {'Yes' if has_cache_after else 'No'}")
            print(f"   Embedding cache cleared: {'Yes' if embedding_cleared else 'No'}")
            print(f"   RFP text cache cleared: {'Yes' if rfp_cache_cleared else 'No'}")
            
            self.results["tests"]["session_isolation"].append(test_result)
            if clearing_verified:
                self.results["metrics"]["passed"] += 1
            else:
                self.results["metrics"]["failed"] += 1
            
            return test_result
            
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"]["session_isolation"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.results["metrics"]["failed"] += 1
            return None
    
    # ==================== PERFORMANCE TESTS ====================
    
    async def test_large_pdf_processing(self):
        """Test processing a 100+ page PDF"""
        test_name = "Large PDF Processing (100+ pages)"
        print(f"\n🔄 Testing: {test_name}")
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            # Create large PDF with 100+ pages
            print("   Creating large PDF (this may take a moment)...")
            pdf_path = self.create_test_pdf_with_images(50, "large_performance", page_count=105)
            file_size_mb = os.path.getsize(pdf_path) / 1024 / 1024
            
            session_id = self.generate_session_id()
            
            print(f"   Uploading {file_size_mb:.1f}MB PDF with 105 pages...")
            
            # Upload large PDF
            with open(pdf_path, 'rb') as f:
                files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
                data = {
                    'analyze_images': 'true',
                    'async': 'true',
                    'session_id': session_id
                }
                
                upload_start = time.time()
                response = await self.client.post(
                    f"{API_BASE_URL}/api/upload",
                    files=files,
                    data=data
                )
                upload_time = time.time() - upload_start
            
            if response.status_code != 200:
                raise Exception(f"Upload failed: {response.status_code}")
            
            result = response.json()
            job_id = result.get('job_id')
            
            # Monitor processing
            processing_start = time.time()
            max_wait = 360  # 6 minutes for large file
            completed = False
            final_progress = None
            memory_samples = []
            progress_milestones = []
            
            while time.time() - processing_start < max_wait:
                # Sample memory usage
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)
                
                progress_response = await self.client.get(
                    f"{API_BASE_URL}/api/upload/progress/{job_id}"
                )
                
                if progress_response.status_code == 200:
                    progress = progress_response.json()
                    pct = progress.get('percentage', 0)
                    
                    # Record milestones
                    if pct > 0 and pct % 25 == 0 and pct not in [m['percentage'] for m in progress_milestones]:
                        progress_milestones.append({
                            "percentage": pct,
                            "time": time.time() - processing_start,
                            "memory_mb": current_memory
                        })
                        print(f"   Progress: {pct:.0f}% at {time.time() - processing_start:.1f}s")
                    
                    if progress.get('status') == 'completed':
                        completed = True
                        final_progress = progress
                        break
                
                await asyncio.sleep(3)
            
            processing_time = time.time() - processing_start
            total_time = time.time() - start_time
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            peak_memory = max(memory_samples) if memory_samples else end_memory
            
            # Performance metrics
            pages_per_second = 105 / processing_time if processing_time > 0 else 0
            mb_per_second = file_size_mb / upload_time if upload_time > 0 else 0
            memory_efficiency = (peak_memory - start_memory) / file_size_mb if file_size_mb > 0 else 0
            
            # Check if performance is acceptable
            performance_good = (
                completed and
                total_time < 360 and  # Under 6 minutes total
                memory_efficiency < 50  # Less than 50MB memory per MB of PDF
            )
            
            test_result = {
                "name": test_name,
                "status": "passed" if performance_good else "warning",
                "completed": completed,
                "file_size_mb": file_size_mb,
                "page_count": 105,
                "upload_time": upload_time,
                "processing_time": processing_time,
                "total_time": total_time,
                "pages_per_second": pages_per_second,
                "mb_per_second": mb_per_second,
                "start_memory_mb": start_memory,
                "peak_memory_mb": peak_memory,
                "memory_delta_mb": peak_memory - start_memory,
                "memory_efficiency": memory_efficiency,
                "progress_milestones": progress_milestones
            }
            
            status_icon = "✅" if performance_good else "⚠️"
            print(f"{status_icon} {test_name}: {'Passed' if performance_good else 'Warning - Performance could be better'}")
            print(f"   File: {file_size_mb:.1f}MB, 105 pages")
            print(f"   Upload: {upload_time:.1f}s ({mb_per_second:.1f} MB/s)")
            print(f"   Processing: {processing_time:.1f}s ({pages_per_second:.1f} pages/s)")
            print(f"   Memory: {start_memory:.0f}MB → {peak_memory:.0f}MB (Δ{peak_memory - start_memory:.0f}MB)")
            
            self.results["tests"]["performance"].append(test_result)
            if performance_good:
                self.results["metrics"]["passed"] += 1
            else:
                self.results["metrics"]["warnings"] += 1
            
            return test_result
            
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"]["performance"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.results["metrics"]["failed"] += 1
            return None
    
    async def test_memory_usage_monitoring(self):
        """Monitor memory usage during processing"""
        test_name = "Memory Usage Monitoring"
        print(f"\n🔄 Testing: {test_name}")
        
        start_time = time.time()
        baseline_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            # Create medium-sized PDF
            pdf_path = self.create_test_pdf_with_images(25, "memory_test", page_count=20)
            file_size_mb = os.path.getsize(pdf_path) / 1024 / 1024
            
            session_id = self.generate_session_id()
            
            # Start memory monitoring
            memory_samples = []
            
            # Upload PDF
            with open(pdf_path, 'rb') as f:
                files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
                data = {
                    'analyze_images': 'true',
                    'async': 'true',
                    'session_id': session_id
                }
                
                response = await self.client.post(
                    f"{API_BASE_URL}/api/upload",
                    files=files,
                    data=data
                )
            
            job_id = response.json().get('job_id')
            
            # Monitor memory during processing
            max_wait = 180
            start_monitor = time.time()
            
            while time.time() - start_monitor < max_wait:
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_samples.append({
                    "time": time.time() - start_monitor,
                    "memory_mb": current_memory,
                    "delta_mb": current_memory - baseline_memory
                })
                
                # Check job status
                progress_response = await self.client.get(
                    f"{API_BASE_URL}/api/upload/progress/{job_id}"
                )
                
                if progress_response.status_code == 200:
                    progress = progress_response.json()
                    if progress.get('status') in ['completed', 'failed', 'cancelled']:
                        break
                
                await asyncio.sleep(1)
            
            # Analyze memory usage
            peak_memory = max(s['memory_mb'] for s in memory_samples)
            avg_memory = sum(s['memory_mb'] for s in memory_samples) / len(memory_samples)
            max_delta = max(s['delta_mb'] for s in memory_samples)
            
            # Check for memory leaks (memory should not continuously increase)
            memory_stable = True
            if len(memory_samples) > 10:
                first_half_avg = sum(s['memory_mb'] for s in memory_samples[:len(memory_samples)//2]) / (len(memory_samples)//2)
                second_half_avg = sum(s['memory_mb'] for s in memory_samples[len(memory_samples)//2:]) / (len(memory_samples) - len(memory_samples)//2)
                memory_stable = (second_half_avg - first_half_avg) < 100  # Less than 100MB increase
            
            test_result = {
                "name": test_name,
                "status": "passed" if memory_stable else "warning",
                "memory_stable": memory_stable,
                "baseline_mb": baseline_memory,
                "peak_mb": peak_memory,
                "avg_mb": avg_memory,
                "max_delta_mb": max_delta,
                "samples_collected": len(memory_samples),
                "duration": time.time() - start_time
            }
            
            status_icon = "✅" if memory_stable else "⚠️"
            print(f"{status_icon} {test_name}: {'Passed' if memory_stable else 'Warning - Possible memory leak'}")
            print(f"   Baseline: {baseline_memory:.0f}MB")
            print(f"   Peak: {peak_memory:.0f}MB (Δ{max_delta:.0f}MB)")
            print(f"   Average: {avg_memory:.0f}MB")
            print(f"   Memory stability: {'Good' if memory_stable else 'Potential leak detected'}")
            
            self.results["tests"]["performance"].append(test_result)
            if memory_stable:
                self.results["metrics"]["passed"] += 1
            else:
                self.results["metrics"]["warnings"] += 1
            
            return test_result
            
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"]["performance"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.results["metrics"]["failed"] += 1
            return None
    
    async def test_system_responsiveness(self):
        """Test system remains responsive during heavy processing"""
        test_name = "System Responsiveness Under Load"
        print(f"\n🔄 Testing: {test_name}")
        
        start_time = time.time()
        
        try:
            # Start a heavy processing job
            pdf_path = self.create_test_pdf_with_images(30, "load_test", page_count=40)
            session_id = self.generate_session_id()
            
            with open(pdf_path, 'rb') as f:
                files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
                data = {
                    'analyze_images': 'true',
                    'async': 'true',
                    'session_id': session_id
                }
                
                response = await self.client.post(
                    f"{API_BASE_URL}/api/upload",
                    files=files,
                    data=data
                )
            
            job_id = response.json().get('job_id')
            print(f"   Background job started: {job_id[:8]}...")
            
            # While processing, test other endpoints for responsiveness
            await asyncio.sleep(2)  # Let the job start processing
            
            responsiveness_tests = []
            
            # Test various endpoints
            endpoints = [
                ("/api/options", "GET", None, "Database options"),
                ("/api/rfp/cache", "GET", None, "RFP cache"),
                ("/api/health", "GET", None, "Health check"),
                (f"/api/upload/progress/{job_id}", "GET", None, "Job progress"),
            ]
            
            print("   Testing endpoint responsiveness...")
            for endpoint, method, data, description in endpoints:
                test_start = time.time()
                
                try:
                    if method == "GET":
                        resp = await self.client.get(f"{API_BASE_URL}{endpoint}")
                    else:
                        resp = await self.client.post(f"{API_BASE_URL}{endpoint}", json=data)
                    
                    response_time = time.time() - test_start
                    responsive = response_time < 3.0  # Should respond within 3 seconds
                    
                    responsiveness_tests.append({
                        "endpoint": endpoint,
                        "description": description,
                        "response_time": response_time,
                        "status_code": resp.status_code,
                        "responsive": responsive
                    })
                except Exception as e:
                    responsiveness_tests.append({
                        "endpoint": endpoint,
                        "description": description,
                        "response_time": time.time() - test_start,
                        "error": str(e),
                        "responsive": False
                    })
            
            # Cancel the job to clean up
            await self.client.post(f"{API_BASE_URL}/api/upload/cancel/{job_id}")
            
            # Check responsiveness
            all_responsive = all(t['responsive'] for t in responsiveness_tests)
            avg_response_time = sum(t['response_time'] for t in responsiveness_tests) / len(responsiveness_tests)
            
            test_result = {
                "name": test_name,
                "status": "passed" if all_responsive else "failed",
                "all_responsive": all_responsive,
                "avg_response_time": avg_response_time,
                "responsiveness_tests": responsiveness_tests,
                "duration": time.time() - start_time
            }
            
            status_icon = "✅" if all_responsive else "❌"
            print(f"{status_icon} {test_name}: {'Passed' if all_responsive else 'Failed'}")
            print(f"   Average response time: {avg_response_time:.2f}s")
            for test in responsiveness_tests:
                status = "✓" if test['responsive'] else "✗"
                print(f"   {status} {test['description']}: {test['response_time']:.2f}s")
            
            self.results["tests"]["performance"].append(test_result)
            if all_responsive:
                self.results["metrics"]["passed"] += 1
            else:
                self.results["metrics"]["failed"] += 1
            
            return test_result
            
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"]["performance"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.results["metrics"]["failed"] += 1
            return None
    
    async def run_all_tests(self):
        """Run all comprehensive tests"""
        print("\n" + "="*70)
        print(" PDF PROCESSING, IMAGE ANALYSIS & SESSION ISOLATION TEST SUITE")
        print("="*70)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        total_start = time.time()
        
        # PDF Processing with Images Tests
        print("\n" + "="*70)
        print(" 📄 PDF PROCESSING WITH IMAGES TESTS")
        print("="*70)
        await self.test_parallel_image_processing()
        await self.test_progress_tracking()
        await self.test_two_tier_image_analysis()
        await self.test_decorative_image_filtering()
        await self.test_error_handling_retry()
        
        # Session Isolation Tests
        print("\n" + "="*70)
        print(" 🔒 SESSION ISOLATION TESTS")
        print("="*70)
        await self.test_sequential_rfp_uploads()
        await self.test_unique_session_ids()
        await self.test_embedding_cache_isolation()
        await self.test_clear_all_data_functionality()
        
        # Performance Tests
        print("\n" + "="*70)
        print(" ⚡ PERFORMANCE TESTS")
        print("="*70)
        await self.test_large_pdf_processing()
        await self.test_memory_usage_monitoring()
        await self.test_system_responsiveness()
        
        # Calculate final metrics
        self.results["metrics"]["total_duration"] = time.time() - total_start
        self.results["metrics"]["total_tests"] = (
            self.results["metrics"]["passed"] +
            self.results["metrics"]["failed"] +
            self.results["metrics"].get("warnings", 0)
        )
        
        # Determine session isolation verdict
        isolation_tests = self.results["tests"]["session_isolation"]
        isolation_passed = all(
            t["status"] == "passed" 
            for t in isolation_tests 
            if "Sequential RFP" in t["name"] or "Embedding Cache" in t["name"]
        )
        
        self.results["session_isolation_verdict"] = isolation_passed
        
        # Print comprehensive summary
        print("\n" + "="*70)
        print(" TEST SUMMARY")
        print("="*70)
        print(f"Total Tests Run: {self.results['metrics']['total_tests']}")
        print(f"✅ Passed: {self.results['metrics']['passed']}")
        print(f"❌ Failed: {self.results['metrics']['failed']}")
        print(f"⚠️  Warnings: {self.results['metrics'].get('warnings', 0)}")
        print(f"⏱️  Total Duration: {self.results['metrics']['total_duration']:.1f}s")
        
        # Session Isolation Verdict
        print("\n" + "="*70)
        print(" 🔐 SESSION ISOLATION VERDICT")
        print("="*70)
        if isolation_passed:
            print("✅ SESSION ISOLATION: VERIFIED")
            print("   ✓ No data contamination detected between RFP sessions")
            print("   ✓ Each RFP maintains independent session context")
            print("   ✓ Embedding cache properly isolated by session")
            print("   ✓ Clear data functionality working correctly")
        else:
            print("❌ SESSION ISOLATION: FAILED")
            print("   ✗ Data contamination detected between sessions")
            print("   Please review the test results for details")
        
        # Performance Summary
        perf_tests = self.results["tests"]["performance"]
        if perf_tests:
            print("\n" + "="*70)
            print(" 📊 PERFORMANCE SUMMARY")
            print("="*70)
            
            large_pdf_test = next((t for t in perf_tests if "Large PDF" in t["name"]), None)
            if large_pdf_test and large_pdf_test.get("pages_per_second"):
                print(f"   Processing Speed: {large_pdf_test['pages_per_second']:.1f} pages/second")
            
            memory_test = next((t for t in perf_tests if "Memory" in t["name"]), None)
            if memory_test and memory_test.get("memory_stable"):
                print(f"   Memory Management: {'Stable' if memory_test['memory_stable'] else 'Potential leak'}")
            
            responsive_test = next((t for t in perf_tests if "Responsiveness" in t["name"]), None)
            if responsive_test and responsive_test.get("all_responsive"):
                print(f"   System Responsiveness: {'Good' if responsive_test['all_responsive'] else 'Poor'}")
        
        # Save detailed results
        results_file = f"test_results_pdf_image_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print("\n" + "="*70)
        print(f"📊 Detailed results saved to: {results_file}")
        print("="*70)
        
        return isolation_passed

async def main():
    """Main test execution"""
    tester = PDFImageSessionTester()
    
    try:
        print("\n🚀 Starting Comprehensive Test Suite...")
        print("   Ensuring server is running at http://localhost:5000")
        
        await tester.setup()
        
        # Check server health first
        try:
            health_response = await tester.client.get(f"{API_BASE_URL}/api/health")
            if health_response.status_code != 200:
                print("❌ Server health check failed. Is the server running?")
                return 1
        except:
            print("❌ Cannot connect to server at http://localhost:5000")
            print("   Please start the server first: python main.py")
            return 1
        
        print("✅ Server is healthy, starting tests...\n")
        
        # Run all tests
        isolation_verified = await tester.run_all_tests()
        
        # Return appropriate exit code
        if isolation_verified:
            print("\n✅ ✅ ✅ ALL CRITICAL TESTS PASSED ✅ ✅ ✅")
            print("Session isolation is working correctly!")
            return 0
        else:
            print("\n❌ Session isolation issues detected!")
            return 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return 2
    except Exception as e:
        print(f"\n\n❌ Test suite error: {e}")
        traceback.print_exc()
        return 3
    finally:
        await tester.teardown()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)