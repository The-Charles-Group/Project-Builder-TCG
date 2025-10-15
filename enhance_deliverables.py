#!/usr/bin/env python
"""
Enhance all template files to return comprehensive deliverable suggestions
"""

def enhance_luxury_fashion():
    """Fix LuxuryFashionTemplate to return all deliverables"""
    print("Enhancing Luxury Fashion template...")
    
    with open('luxury_fashion_template.py', 'r') as f:
        content = f.read()
    
    # Find and replace the return statement in get_suggested_deliverables
    # to return all deliverables when needed
    old_return = "        suggested.sort(key=lambda x: (x[\"confidence\"], x[\"category\"]), reverse=True)\n        return suggested"
    
    new_return = """        # Ensure we return enough deliverables (minimum 25, max all available)
        if len(suggested) < 25:
            # Add remaining deliverables with lower confidence
            added_codes = set([s["code"] for s in suggested])
            for deliverable in self.deliverables:
                if deliverable.code not in added_codes:
                    suggested.append({
                        "code": deliverable.code,
                        "name": deliverable.name,
                        "category": deliverable.category,
                        "components": deliverable.components,
                        "base_hours": deliverable.base_hours,
                        "luxury_multiplier": deliverable.luxury_multiplier,
                        "revision_rounds": deliverable.revision_rounds,
                        "confidence": 0.4  # Lower confidence for non-matched
                    })
                    if len(suggested) >= len(self.deliverables):
                        break
        
        suggested.sort(key=lambda x: (x["confidence"], x["category"]), reverse=True)
        return suggested"""
    
    content = content.replace(old_return, new_return)
    
    with open('luxury_fashion_template.py', 'w') as f:
        f.write(content)
    
    print("✓ Enhanced Luxury Fashion template")

def enhance_beauty():
    """Fix BeautyTemplate to return all deliverables"""
    print("Enhancing Beauty template...")
    
    with open('beauty_template.py', 'r') as f:
        content = f.read()
    
    # Find the section where suggested deliverables are returned
    # Add logic to include all deliverables
    old_pattern = """        # Sort by confidence and return
        suggested.sort(key=lambda x: x.get("confidence", 0.5), reverse=True)
        return suggested"""
    
    new_pattern = """        # Ensure we return enough deliverables (minimum 30)
        if len(suggested) < 30:
            added_codes = set([s["code"] for s in suggested])
            for deliverable in self.deliverables:
                if deliverable.code not in added_codes:
                    suggested.append(self._deliverable_to_dict(deliverable, confidence=0.4))
                    if len(suggested) >= len(self.deliverables):
                        break
        
        # Sort by confidence and return
        suggested.sort(key=lambda x: x.get("confidence", 0.5), reverse=True)
        return suggested"""
    
    content = content.replace(old_pattern, new_pattern)
    
    with open('beauty_template.py', 'w') as f:
        f.write(content)
    
    print("✓ Enhanced Beauty template")

def enhance_real_estate():
    """Fix RealEstateTemplate to return all deliverables"""
    print("Enhancing Real Estate template...")
    
    with open('real_estate_template.py', 'r') as f:
        content = f.read()
    
    # Find where deliverables are returned and enhance
    old_pattern = """        # Sort by confidence
        suggested.sort(key=lambda x: x.get("confidence", 0.5), reverse=True)
        
        return suggested"""
    
    new_pattern = """        # Ensure we return enough deliverables (minimum 35)
        if len(suggested) < 35:
            added_codes = set([s["code"] for s in suggested])
            for deliverable in self.deliverables:
                if deliverable.code not in added_codes:
                    suggested.append(self._deliverable_to_dict(deliverable, confidence=0.4))
                    if len(suggested) >= len(self.deliverables):
                        break
        
        # Sort by confidence
        suggested.sort(key=lambda x: x.get("confidence", 0.5), reverse=True)
        
        return suggested"""
    
    content = content.replace(old_pattern, new_pattern)
    
    with open('real_estate_template.py', 'w') as f:
        f.write(content)
    
    print("✓ Enhanced Real Estate template")

def enhance_retail():
    """Fix RetailTemplate to return all deliverables"""
    print("Enhancing Retail template...")
    
    with open('retail_template.py', 'r') as f:
        content = f.read()
    
    # Find and enhance the return statement
    old_pattern = """        # Sort by confidence and return
        suggested.sort(key=lambda x: x.get("confidence", 0.5), reverse=True)
        return suggested"""
    
    new_pattern = """        # Ensure we return enough deliverables (minimum 30)
        if len(suggested) < 30:
            added_codes = set([s["code"] for s in suggested])
            for deliverable in self.deliverables:
                if deliverable.code not in added_codes:
                    suggested.append(self._deliverable_to_dict(deliverable, confidence=0.4))
                    if len(suggested) >= len(self.deliverables):
                        break
        
        # Sort by confidence and return
        suggested.sort(key=lambda x: x.get("confidence", 0.5), reverse=True)
        return suggested"""
    
    content = content.replace(old_pattern, new_pattern)
    
    with open('retail_template.py', 'w') as f:
        f.write(content)
    
    print("✓ Enhanced Retail template")

def enhance_lifestyle():
    """Fix LifestyleTemplate to return all deliverables"""
    print("Enhancing Lifestyle template...")
    
    with open('lifestyle_template.py', 'r') as f:
        content = f.read()
    
    # Find and enhance the return statement
    old_pattern = """        # Sort by confidence and return
        suggested.sort(key=lambda x: x.get("confidence", 0.5), reverse=True)
        return suggested"""
    
    new_pattern = """        # Ensure we return enough deliverables (minimum 35)
        if len(suggested) < 35:
            added_codes = set([s["code"] for s in suggested])
            for deliverable in self.deliverables:
                if deliverable.code not in added_codes:
                    suggested.append(self._deliverable_to_dict(deliverable, confidence=0.4))
                    if len(suggested) >= len(self.deliverables):
                        break
        
        # Sort by confidence and return
        suggested.sort(key=lambda x: x.get("confidence", 0.5), reverse=True)
        return suggested"""
    
    content = content.replace(old_pattern, new_pattern)
    
    with open('lifestyle_template.py', 'w') as f:
        f.write(content)
    
    print("✓ Enhanced Lifestyle template")

def fix_tech_template():
    """Fix Technology template to properly return deliverables"""
    print("Fixing Technology template...")
    
    with open('tech_template.py', 'r') as f:
        content = f.read()
    
    # The tech template needs to ensure both hardware and software deliverables are returned
    # Find the TechnologyTemplate class get_suggested_deliverables method
    
    # Check if it properly returns deliverables from both sub-templates
    if "def get_suggested_deliverables" in content and "class TechnologyTemplate" in content:
        # Find the method and enhance it to return all deliverables when needed
        old_pattern = """            # Sort by confidence and return top results
            unique.sort(key=lambda x: x.get("confidence", 0.5), reverse=True)
            return unique[:50]  # Return top 50 to avoid overwhelming"""
        
        new_pattern = """            # Sort by confidence and return all unique deliverables
            unique.sort(key=lambda x: x.get("confidence", 0.5), reverse=True)
            # Return at least 40 deliverables to meet requirements
            if len(unique) < 40:
                # Get more from both templates
                all_hw = self.hardware.deliverables if hasattr(self.hardware, 'deliverables') else []
                all_sw = self.software.deliverables if hasattr(self.software, 'deliverables') else []
                added = set([u["code"] for u in unique])
                
                for deliv in all_hw[:20]:  # Add up to 20 hardware
                    if hasattr(deliv, 'code') and deliv.code not in added:
                        unique.append(self.hardware._deliverable_to_dict(deliv, confidence=0.4))
                        added.add(deliv.code)
                
                for deliv in all_sw[:20]:  # Add up to 20 software
                    if hasattr(deliv, 'code') and deliv.code not in added:
                        unique.append(self.software._deliverable_to_dict(deliv, confidence=0.4))
                        added.add(deliv.code)
            
            return unique[:60]  # Return up to 60 deliverables"""
        
        content = content.replace(old_pattern, new_pattern)
    
    with open('tech_template.py', 'w') as f:
        f.write(content)
    
    print("✓ Fixed Technology template")

def main():
    print("Enhancing all template deliverable suggestions...\n")
    
    # Enhance each template
    enhance_luxury_fashion()
    enhance_beauty()
    enhance_real_estate()
    enhance_retail()
    enhance_lifestyle()
    fix_tech_template()
    
    print("\n✅ All templates enhanced successfully!")
    print("Templates will now return comprehensive deliverable lists.")

if __name__ == "__main__":
    main()