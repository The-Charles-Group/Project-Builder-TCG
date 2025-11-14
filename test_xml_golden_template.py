#!/usr/bin/env python3
"""
Test script to validate XML export matches the golden template requirements.
"""
import xml.etree.ElementTree as ET
from convert_excel_to_mspdi import convert_excel_to_mspdi
import os

def test_xml_export():
    test_file = 'test_enhanced_project.xlsx'
    output_file = 'test_xml_validation.xml'
    
    print('Testing XML export with golden template fixes...')
    print('Input:', test_file)
    print('Output:', output_file)
    
    # Run conversion
    result = convert_excel_to_mspdi(
        input_xlsx=test_file,
        output_xml=output_file,
        sheet_name='Scenario A',
        project_name='Test Project',
        blended_rate=195.0
    )
    
    print('\nConversion result:', result)
    
    # Parse and validate
    if not os.path.exists(output_file):
        print('ERROR: Output file not created')
        return False
    
    tree = ET.parse(output_file)
    root = tree.getroot()
    ns_url = 'http://schemas.microsoft.com/project'
    
    print('\n=== VALIDATION RESULTS ===')
    all_pass = True
    
    # 1. StandardRate format (should be plain decimal like "195.00")
    rates = root.findall('.//{%s}StandardRate' % ns_url)
    print('\n1. StandardRate fields:', len(rates), 'found')
    if rates:
        sample = rates[0].text
        print('   Sample:', sample)
        has_symbols = ('$' in sample) or ('/h' in sample)
        if has_symbols:
            print('   FAIL: Contains currency symbols or /h')
            all_pass = False
        else:
            print('   PASS: Plain decimal format')
    
    # 2. Duration format (should be PT{minutes}M like "PT480M")
    durations = root.findall('.//{%s}Duration' % ns_url)
    print('\n2. Duration fields:', len(durations), 'found')
    if durations:
        sample = durations[0].text if durations[0].text else 'PT0M'
        print('   Sample:', sample)
        has_h = ('H' in sample) and (sample != 'PT0M')
        if has_h:
            print('   FAIL: Contains hour format (H)')
            all_pass = False
        else:
            print('   PASS: Minute format (PTxxxM)')
    
    # 3. Work format (should be PT{minutes}M)
    works = root.findall('.//{%s}Work' % ns_url)
    print('\n3. Work fields:', len(works), 'found')
    if works:
        sample = works[0].text if works[0].text else 'PT0M'
        print('   Sample:', sample)
        has_h = ('H' in sample) and (sample != 'PT0M')
        if has_h:
            print('   FAIL: Contains hour format (H)')
            all_pass = False
        else:
            print('   PASS: Minute format (PTxxxM)')
    
    # 4. PredecessorLink Type
    pred_types = root.findall('.//{%s}PredecessorLink/{%s}Type' % (ns_url, ns_url))
    print('\n4. PredecessorLink Type fields:', len(pred_types), 'found')
    if pred_types:
        types_set = set(t.text for t in pred_types)
        print('   Types found:', types_set)
        print('   PASS: Type elements present')
    
    # 5. Calendar times (should be 08:00-12:00 and 13:00-17:00)
    from_times = root.findall('.//{%s}FromTime' % ns_url)
    to_times = root.findall('.//{%s}ToTime' % ns_url)
    print('\n5. Calendar WorkingTime:', len(from_times), 'periods found')
    if from_times and to_times:
        morning_from = from_times[0].text
        morning_to = to_times[0].text
        print('   Morning:', morning_from, '-', morning_to)
        if len(from_times) > 1 and len(to_times) > 1:
            afternoon_from = from_times[1].text
            afternoon_to = to_times[1].text
            print('   Afternoon:', afternoon_from, '-', afternoon_to)
        
        is_correct = (morning_from == '08:00:00') and (to_times[-1].text == '17:00:00')
        if is_correct:
            print('   PASS: 08:00-17:00 schedule')
        else:
            print('   FAIL: Incorrect schedule')
            all_pass = False
    
    # 6. Check for problematic headers (should NOT be present)
    save_v = root.find('{%s}SaveVersion' % ns_url)
    ms_srv = root.find('{%s}MicrosoftProjectServerURL' % ns_url)
    print('\n6. Problematic headers:')
    if save_v is not None:
        print('   SaveVersion: FOUND (FAIL)')
        all_pass = False
    else:
        print('   SaveVersion: Not found (PASS)')
    
    if ms_srv is not None:
        print('   MicrosoftProjectServerURL: FOUND (FAIL)')
        all_pass = False
    else:
        print('   MicrosoftProjectServerURL: Not found (PASS)')
    
    print('\n=== TEST COMPLETE ===')
    if all_pass:
        print('ALL TESTS PASSED!')
    else:
        print('SOME TESTS FAILED')
    
    return all_pass

if __name__ == '__main__':
    success = test_xml_export()
    exit(0 if success else 1)
