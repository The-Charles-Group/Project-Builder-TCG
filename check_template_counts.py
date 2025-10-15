"""
Check actual deliverable counts in each template module
"""

# Import all templates
from luxury_fashion_template import get_fashion_deliverables
from beauty_template import get_beauty_deliverables  
from real_estate_template import get_real_estate_deliverables
from retail_template import get_retail_deliverables
from lifestyle_template import get_lifestyle_deliverables
from tech_template import HardwareTechTemplate, SoftwareTechTemplate

def check_deliverable_counts():
    """Check actual deliverable counts in each template"""
    
    print("=" * 60)
    print("ACTUAL DELIVERABLE COUNTS IN TEMPLATE MODULES")
    print("=" * 60)
    
    # Check Luxury Fashion
    fashion_deliverables = get_fashion_deliverables()
    print(f"\n1. LUXURY FASHION:")
    print(f"   Total deliverables: {len(fashion_deliverables)}")
    categories = set(d.category for d in fashion_deliverables)
    print(f"   Categories: {len(categories)}")
    print(f"   Sample codes: {[d.code for d in fashion_deliverables[:3]]}")
    
    # Check Beauty
    beauty_deliverables = get_beauty_deliverables()
    print(f"\n2. BEAUTY:")
    print(f"   Total deliverables: {len(beauty_deliverables)}")
    categories = set(d.category for d in beauty_deliverables)
    print(f"   Categories: {len(categories)}")
    print(f"   Sample codes: {[d.code for d in beauty_deliverables[:3]]}")
    
    # Check Real Estate
    real_estate_deliverables = get_real_estate_deliverables()
    print(f"\n3. REAL ESTATE:")
    print(f"   Total deliverables: {len(real_estate_deliverables)}")
    categories = set(d.category for d in real_estate_deliverables)
    print(f"   Categories: {len(categories)}")
    print(f"   Sample codes: {[d.code for d in real_estate_deliverables[:3]]}")
    
    # Check Retail
    retail_deliverables = get_retail_deliverables()
    print(f"\n4. RETAIL:")
    print(f"   Total deliverables: {len(retail_deliverables)}")
    categories = set(d.category for d in retail_deliverables)
    print(f"   Categories: {len(categories)}")
    print(f"   Sample codes: {[d.code for d in retail_deliverables[:3]]}")
    
    # Check Lifestyle
    lifestyle_deliverables = get_lifestyle_deliverables()
    print(f"\n5. LIFESTYLE:")
    print(f"   Total deliverables: {len(lifestyle_deliverables)}")
    categories = set(d.category for d in lifestyle_deliverables)
    print(f"   Categories: {len(categories)}")
    print(f"   Sample codes: {[d.code for d in lifestyle_deliverables[:3]]}")
    
    # Check Technology (Hardware + Software)
    hw_template = HardwareTechTemplate()
    sw_template = SoftwareTechTemplate()
    hardware_deliverables = hw_template._get_hardware_deliverables()
    software_deliverables = sw_template._get_software_deliverables()
    print(f"\n6. TECHNOLOGY:")
    print(f"   Hardware deliverables: {len(hardware_deliverables)}")
    print(f"   Software deliverables: {len(software_deliverables)}")
    print(f"   Total deliverables: {len(hardware_deliverables) + len(software_deliverables)}")
    hw_categories = set(d.category for d in hardware_deliverables)
    sw_categories = set(d.category for d in software_deliverables) 
    print(f"   Categories: {len(hw_categories.union(sw_categories))}")
    print(f"   Sample HW codes: {[d.code for d in hardware_deliverables[:2]]}")
    print(f"   Sample SW codes: {[d.code for d in software_deliverables[:2]]}")
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"  • Luxury Fashion: {len(fashion_deliverables)} deliverables")
    print(f"  • Beauty: {len(beauty_deliverables)} deliverables")
    print(f"  • Real Estate: {len(real_estate_deliverables)} deliverables")
    print(f"  • Retail: {len(retail_deliverables)} deliverables")
    print(f"  • Lifestyle: {len(lifestyle_deliverables)} deliverables")
    print(f"  • Technology: {len(hardware_deliverables) + len(software_deliverables)} deliverables")
    print("=" * 60)

if __name__ == "__main__":
    check_deliverable_counts()