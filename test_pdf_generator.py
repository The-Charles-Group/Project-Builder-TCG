#!/usr/bin/env python3
"""
Generate test PDF files with various configurations for testing
Creates PDFs with text and multiple images to test processing capabilities
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib import colors
from PIL import Image as PILImage
import io
import random
import string

def create_test_image(size=(400, 300), color=None, text=None):
    """Create a test image with optional text"""
    if color is None:
        color = (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
    
    img = PILImage.new('RGB', size, color)
    
    if text:
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            font = ImageFont.load_default()
        draw.text((10, 10), text, fill=(0, 0, 0), font=font)
    
    # Save to bytes buffer
    img_buffer = io.BytesIO()
    img.save(img_buffer, 'PNG')
    img_buffer.seek(0)
    
    # Save to file for reportlab
    filename = f"temp_image_{random.randint(1000, 9999)}.png"
    img.save(filename)
    
    return filename

def generate_rfp_content(category="marketing", pages=5):
    """Generate realistic RFP-like content"""
    if category == "marketing":
        title = "Digital Marketing Services RFP"
        sections = [
            ("Executive Summary", 
             "We are seeking a comprehensive digital marketing agency to develop and execute our integrated marketing strategy. "
             "The selected agency will be responsible for brand development, digital campaigns, social media management, "
             "content creation, and performance analytics across all digital channels."),
            
            ("Scope of Work",
             "The agency will deliver the following services:\n\n"
             "• Brand Strategy Development - Complete brand audit and positioning strategy\n"
             "• Digital Advertising - Manage PPC campaigns across Google, Facebook, LinkedIn\n" 
             "• Social Media Management - Daily content creation and community management\n"
             "• Content Marketing - Blog posts, whitepapers, case studies, video content\n"
             "• Email Marketing - Automated campaigns and newsletter management\n"
             "• SEO Optimization - Technical SEO, content optimization, link building\n"
             "• Analytics & Reporting - Weekly dashboards and monthly strategic reviews\n"
             "• Influencer Marketing - Identify and manage influencer partnerships"),
            
            ("Deliverables",
             "Monthly Deliverables:\n"
             "• 20 social media posts per platform\n"
             "• 4 blog articles (1000+ words)\n"
             "• 2 video assets\n"
             "• 1 email campaign\n"
             "• Monthly performance report\n\n"
             "Quarterly Deliverables:\n"
             "• Brand health assessment\n"
             "• Competitive analysis report\n"
             "• Campaign optimization recommendations\n"
             "• ROI analysis and budget reallocation plan"),
            
            ("Timeline",
             "Project Timeline:\n"
             "• Month 1: Discovery and strategy development\n"
             "• Month 2-3: Campaign setup and launch\n"
             "• Month 4-12: Ongoing execution and optimization\n"
             "• Quarterly: Strategic review and planning sessions"),
            
            ("Budget",
             "Estimated Annual Budget: $500,000 - $750,000\n"
             "• Strategy & Planning: $75,000\n"
             "• Creative Development: $150,000\n"
             "• Media Buying: $200,000\n"
             "• Production: $100,000\n"
             "• Analytics & Reporting: $50,000")
        ]
    
    elif category == "technology":
        title = "Enterprise Software Development RFP"
        sections = [
            ("Project Overview",
             "We require a technology partner to design and develop a cloud-based enterprise resource planning (ERP) system. "
             "The solution must integrate with existing infrastructure and support 5000+ concurrent users globally."),
            
            ("Technical Requirements",
             "Core Modules Required:\n"
             "• Financial Management - GL, AP, AR, budgeting\n"
             "• Human Resources - Employee management, payroll, benefits\n"
             "• Supply Chain - Inventory, procurement, logistics\n"
             "• CRM - Customer data, sales pipeline, support tickets\n"
             "• Business Intelligence - Real-time dashboards, predictive analytics\n"
             "• Mobile Applications - iOS and Android native apps\n"
             "• API Integration - REST APIs for third-party systems"),
            
            ("Deliverables",
             "Phase 1 (Months 1-6):\n"
             "• System architecture design\n"
             "• Database schema development\n"
             "• Core module prototypes\n"
             "• Security framework implementation\n\n"
             "Phase 2 (Months 7-12):\n"
             "• Full module development\n"
             "• Integration testing\n"
             "• User acceptance testing\n"
             "• Production deployment"),
            
            ("Performance Requirements",
             "• 99.9% uptime SLA\n"
             "• < 2 second page load times\n"
             "• Support for 10,000 concurrent users\n"
             "• Data encryption at rest and in transit\n"
             "• GDPR and SOC 2 compliance"),
            
            ("Budget and Timeline",
             "Total Project Budget: $2,000,000 - $3,000,000\n"
             "Timeline: 12-18 months\n"
             "Payment Terms: Monthly milestones\n"
             "Support: 24/7 post-launch support required")
        ]
    
    else:  # construction
        title = "Commercial Building Construction RFP"
        sections = [
            ("Project Description",
             "Construction of a 50,000 sq ft mixed-use commercial building including retail space, offices, and parking structure. "
             "The project requires LEED Gold certification and must incorporate sustainable building practices."),
            
            ("Scope of Work",
             "Major Components:\n"
             "• Site preparation and excavation\n"
             "• Foundation and structural work\n"
             "• MEP systems installation\n"
             "• Interior buildout - 20 office suites\n"
             "• Retail space - 10,000 sq ft ground floor\n"
             "• Parking structure - 200 spaces\n"
             "• Landscaping and exterior finishes\n"
             "• LEED certification documentation"),
            
            ("Deliverables",
             "Pre-Construction:\n"
             "• Site surveys and soil analysis\n"
             "• Architectural drawings and 3D models\n"
             "• Permit applications and approvals\n"
             "• Value engineering proposals\n\n"
             "Construction:\n"
             "• Weekly progress reports\n"
             "• Safety compliance documentation\n"
             "• Change order management\n"
             "• Quality assurance reports"),
            
            ("Timeline",
             "Project Schedule:\n"
             "• Months 1-2: Design finalization\n"
             "• Months 3-4: Permitting and approvals\n"
             "• Months 5-8: Foundation and structure\n"
             "• Months 9-14: MEP and interior work\n"
             "• Months 15-18: Finishing and commissioning"),
            
            ("Budget",
             "Construction Budget: $15,000,000 - $18,000,000\n"
             "• Site work: $2,000,000\n"
             "• Structure: $6,000,000\n"
             "• MEP systems: $3,000,000\n"
             "• Interiors: $2,500,000\n"
             "• Contingency: $1,500,000")
        ]
    
    return title, sections

def create_test_pdf(filename, num_images=5, num_pages=10, category="marketing", include_charts=True):
    """
    Create a test PDF with specified number of images and pages
    
    Args:
        filename: Output PDF filename
        num_images: Number of images to include
        num_pages: Number of pages in PDF
        category: Type of RFP content (marketing, technology, construction)
        include_charts: Whether to include chart/diagram images
    """
    print(f"Creating PDF: {filename}")
    print(f"  - Pages: {num_pages}")
    print(f"  - Images: {num_images}")
    print(f"  - Category: {category}")
    
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Get RFP content
    title, sections = generate_rfp_content(category, num_pages)
    
    # Add title
    story.append(Paragraph(f"<b>{title}</b>", styles['Title']))
    story.append(Spacer(1, 0.5*inch))
    
    # Add metadata
    story.append(Paragraph(f"Date: October 15, 2025", styles['Normal']))
    story.append(Paragraph(f"Document ID: RFP-2025-{random.randint(1000, 9999)}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Temporary image files to clean up
    temp_images = []
    
    # Distribute content and images across pages
    images_per_page = max(1, num_images // num_pages)
    images_added = 0
    
    for page_num in range(num_pages):
        if page_num > 0:
            story.append(PageBreak())
        
        # Add section content
        if page_num < len(sections):
            section_title, section_content = sections[page_num]
            story.append(Paragraph(f"<b>{section_title}</b>", styles['Heading1']))
            story.append(Spacer(1, 0.2*inch))
            
            # Split content into paragraphs
            for para in section_content.split('\n\n'):
                story.append(Paragraph(para, styles['Normal']))
                story.append(Spacer(1, 0.1*inch))
        else:
            # Add appendix content
            story.append(Paragraph(f"<b>Appendix {page_num - len(sections) + 1}</b>", styles['Heading1']))
            story.append(Spacer(1, 0.2*inch))
            story.append(Paragraph("Additional supporting documentation and reference materials.", styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
        
        # Add images on this page
        if images_added < num_images:
            for img_idx in range(images_per_page):
                if images_added >= num_images:
                    break
                
                # Determine image type
                if include_charts and images_added % 3 == 0:
                    # Create chart-like image
                    img_file = create_test_image(
                        size=(500, 350),
                        color=(240, 240, 255),
                        text=f"Analytics Dashboard {images_added + 1}"
                    )
                elif images_added % 3 == 1:
                    # Create diagram-like image
                    img_file = create_test_image(
                        size=(450, 400),
                        color=(255, 250, 240),
                        text=f"Process Flow Diagram {images_added + 1}"
                    )
                else:
                    # Create mockup/screenshot image
                    img_file = create_test_image(
                        size=(480, 360),
                        color=(250, 255, 250),
                        text=f"Design Mockup {images_added + 1}"
                    )
                
                temp_images.append(img_file)
                
                # Add image with caption
                story.append(Spacer(1, 0.2*inch))
                img = Image(img_file, width=4*inch, height=3*inch)
                story.append(img)
                story.append(Paragraph(f"<i>Figure {images_added + 1}: {category.title()} Visual Asset</i>", 
                                      styles['Italic']))
                story.append(Spacer(1, 0.2*inch))
                
                images_added += 1
        
        # Add table on some pages
        if page_num % 3 == 2 and page_num < num_pages - 1:
            story.append(Spacer(1, 0.3*inch))
            data = [
                ['Phase', 'Duration', 'Budget', 'Resources'],
                ['Discovery', '2 weeks', '$25,000', '3 FTEs'],
                ['Development', '8 weeks', '$150,000', '8 FTEs'],
                ['Testing', '2 weeks', '$30,000', '4 FTEs'],
                ['Deployment', '1 week', '$15,000', '2 FTEs'],
            ]
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(table)
    
    # Build PDF
    doc.build(story)
    
    # Clean up temporary image files
    for img_file in temp_images:
        if os.path.exists(img_file):
            os.remove(img_file)
    
    print(f"✅ Created {filename} ({os.path.getsize(filename) / 1024:.1f} KB)")
    return filename

def main():
    """Generate multiple test PDFs with different characteristics"""
    
    test_pdfs_dir = "test_pdfs"
    os.makedirs(test_pdfs_dir, exist_ok=True)
    
    test_configs = [
        # Small PDFs for quick testing
        ("small_marketing_rfp.pdf", 3, 5, "marketing", True),
        ("small_tech_rfp.pdf", 2, 4, "technology", False),
        
        # Medium PDFs with moderate images
        ("medium_marketing_rfp.pdf", 10, 15, "marketing", True),
        ("medium_construction_rfp.pdf", 12, 20, "construction", True),
        
        # Large PDF with many images for stress testing
        ("large_marketing_rfp.pdf", 25, 50, "marketing", True),
        
        # PDF with excessive images for performance testing
        ("stress_test_images.pdf", 50, 30, "technology", True),
        
        # Very large PDF for memory testing
        ("stress_test_pages.pdf", 20, 100, "construction", False),
        
        # Edge cases
        ("no_images_rfp.pdf", 0, 10, "marketing", False),
        ("images_only_rfp.pdf", 30, 5, "technology", True),
    ]
    
    created_files = []
    
    print("="*60)
    print("PDF Test File Generator")
    print("="*60)
    
    for config in test_configs:
        filename, num_images, num_pages, category, include_charts = config
        full_path = os.path.join(test_pdfs_dir, filename)
        
        try:
            create_test_pdf(full_path, num_images, num_pages, category, include_charts)
            created_files.append(full_path)
        except Exception as e:
            print(f"❌ Error creating {filename}: {str(e)}")
    
    print("\n" + "="*60)
    print("Summary:")
    print(f"✅ Created {len(created_files)} test PDF files in {test_pdfs_dir}/")
    print("="*60)
    
    return created_files

if __name__ == "__main__":
    main()