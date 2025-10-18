#!/usr/bin/env python3
"""
Test script to demonstrate the enhanced AI timeline generation with realistic PM dependencies
"""

import asyncio
import json
from datetime import datetime, timedelta
from ai_timeline_manager import (
    generate_ai_timeline,
    TimelineOptimizer,
    generate_phase_based_schedule,
    process_ai_timeline
)

async def test_timeline_generation():
    """Test the enhanced timeline generation with realistic dependencies"""
    
    # Sample deliverables representing a typical agency project
    test_deliverables = [
        {
            'deliverable_code': 'STRAT_001',
            'deliverable_name': 'Brand Strategy Deck',
            'department': 'Strategy',
            'total_hours': 48,
            'components': [
                {'name': 'Market Research', 'hours': 16},
                {'name': 'Competitive Analysis', 'hours': 12},
                {'name': 'Strategy Development', 'hours': 20}
            ]
        },
        {
            'deliverable_code': 'CREAT_001',
            'deliverable_name': 'Creative Campaign Concept',
            'department': 'Creative',
            'total_hours': 64,
            'components': [
                {'name': 'Concept Development', 'hours': 24},
                {'name': 'Visual Design', 'hours': 20},
                {'name': 'Copywriting', 'hours': 20}
            ]
        },
        {
            'deliverable_code': 'GUID_001',
            'deliverable_name': 'Brand Guidelines',
            'department': 'Creative',
            'total_hours': 32,
            'components': [
                {'name': 'Visual Standards', 'hours': 16},
                {'name': 'Voice & Tone Guide', 'hours': 16}
            ]
        },
        {
            'deliverable_code': 'MEDIA_001',
            'deliverable_name': 'Paid Media Plan',
            'department': 'Paid Media',
            'total_hours': 40,
            'components': [
                {'name': 'Channel Strategy', 'hours': 16},
                {'name': 'Budget Allocation', 'hours': 12},
                {'name': 'Campaign Setup', 'hours': 12}
            ]
        },
        {
            'deliverable_code': 'TECH_001',
            'deliverable_name': 'Website Development',
            'department': 'Technology',
            'total_hours': 80,
            'components': [
                {'name': 'Frontend Development', 'hours': 40},
                {'name': 'Backend Development', 'hours': 30},
                {'name': 'Testing & QA', 'hours': 10}
            ]
        },
        {
            'deliverable_code': 'CONTENT_001',
            'deliverable_name': 'Content Calendar',
            'department': 'Content',
            'total_hours': 24,
            'components': [
                {'name': 'Content Planning', 'hours': 12},
                {'name': 'Editorial Calendar', 'hours': 12}
            ]
        }
    ]
    
    # Sample RFP context
    rfp_text = """
    Global brand refresh and digital transformation project.
    Need complete rebrand with new visual identity, website, and integrated marketing campaign.
    Timeline: 3 months. Budget: $500K.
    Key deliverables: Strategy deck, brand guidelines, website, paid media campaign.
    """
    
    print("=" * 80)
    print("TESTING ENHANCED AI TIMELINE GENERATION")
    print("=" * 80)
    print()
    
    # Test 1: Generate timeline with AI (if available) with balanced optimization
    print("Test 1: AI Timeline with Balanced Optimization")
    print("-" * 40)
    
    try:
        timeline_result = await generate_ai_timeline(
            deliverables=test_deliverables,
            rfp_text=rfp_text,
            project_start=datetime.now().strftime('%Y-%m-%d'),
            optimization_mode='balanced',
            use_intelligent_scheduler=False,  # Use our enhanced logic
            include_governance=True,
            project_complexity='medium'
        )
        
        print_timeline_summary(timeline_result)
        
    except Exception as e:
        print(f"Error generating AI timeline: {e}")
        print("Falling back to deterministic timeline generation...")
        
        # Test with fallback
        from ai_timeline_manager import generate_fallback_timeline
        timeline_result = generate_fallback_timeline(
            test_deliverables,
            datetime.now().strftime('%Y-%m-%d')
        )
        print_timeline_summary(timeline_result)
    
    print()
    
    # Test 2: Phase-based scheduling
    print("Test 2: Phase-Based Scheduling")
    print("-" * 40)
    
    optimizer = TimelineOptimizer()
    phases = generate_phase_based_schedule(
        test_deliverables,
        datetime.now(),
        90  # 90-day project
    )
    
    for phase_name, phase_info in phases.items():
        print(f"\n{phase_name} Phase:")
        print(f"  Start: {phase_info['start'].strftime('%Y-%m-%d')}")
        print(f"  End: {phase_info['end'].strftime('%Y-%m-%d')}")
        print(f"  Tasks: {len(phase_info['tasks'])}")
        if phase_info['tasks']:
            print(f"  Deliverables:")
            for task in phase_info['tasks'][:3]:  # Show first 3
                print(f"    - {task.get('deliverable_name', 'Unknown')}")
    
    print()
    
    # Test 3: Dependency identification
    print("Test 3: Intelligent Dependency Mapping")
    print("-" * 40)
    
    # Create task list for dependency analysis
    task_list = []
    for deliv in test_deliverables:
        category = optimizer.get_deliverable_category(deliv.get('deliverable_name', ''))
        task_list.append({
            'id': f"task_{deliv['deliverable_code']}",
            'deliverable_code': deliv['deliverable_code'],
            'deliverable_name': deliv['deliverable_name'],
            'department': deliv.get('department', 'Strategy'),
            'category': category,
            'component_order': 0
        })
    
    dependencies = optimizer.identify_dependencies(task_list)
    
    print("\nDependency Map:")
    for task_id, deps in dependencies.items():
        if deps:
            task = next(t for t in task_list if t['id'] == task_id)
            print(f"\n{task['deliverable_name']}:")
            print(f"  Category: {task['category']}")
            print(f"  Depends on: {', '.join(deps)}")
    
    print()
    
    # Test 4: Duration calculation
    print("Test 4: Intelligent Duration Calculation")
    print("-" * 40)
    
    for deliv in test_deliverables[:3]:
        hours = deliv['total_hours']
        category = optimizer.get_deliverable_category(deliv['deliverable_name'])
        complexity = "complex" if hours > 40 else "moderate" if hours > 20 else "simple"
        
        duration = optimizer.calculate_intelligent_duration(hours, category, complexity)
        
        print(f"\n{deliv['deliverable_name']}:")
        print(f"  Hours: {hours}")
        print(f"  Category: {category}")
        print(f"  Complexity: {complexity}")
        print(f"  Calculated Duration: {duration} days")
        print(f"  Buffer: {optimizer.calculate_buffer_days(duration, category == 'deck_strategy')} days")
    
    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


def print_timeline_summary(timeline_result):
    """Print a summary of the timeline results"""
    
    if 'tasks' in timeline_result:
        print(f"\nGenerated {len(timeline_result['tasks'])} tasks")
        
        # Show first few tasks
        for task in timeline_result['tasks'][:5]:
            deps = task.get('dependencies', '').split(',') if task.get('dependencies') else []
            print(f"\n  Task: {task.get('name', 'Unknown')}")
            print(f"    ID: {task.get('id')}")
            print(f"    Start: {task.get('start')}")
            print(f"    End: {task.get('end')}")
            if deps:
                print(f"    Dependencies: {', '.join(deps)}")
            if task.get('progress'):
                print(f"    Progress: {task.get('progress')}%")
    
    if 'metadata' in timeline_result:
        print(f"\nProject Metadata:")
        meta = timeline_result['metadata']
        print(f"  Total Duration: {meta.get('total_duration_days', 0)} days")
        print(f"  Project Start: {meta.get('project_start')}")
        print(f"  Project End: {meta.get('project_end')}")
        print(f"  Critical Tasks: {meta.get('critical_tasks', 0)}")
        print(f"  Departments: {', '.join(meta.get('departments_involved', []))}")
    
    if 'cpm_analysis' in timeline_result:
        cpm = timeline_result['cpm_analysis']
        if 'critical_path' in cpm:
            cp = cpm['critical_path']
            print(f"\nCritical Path Analysis:")
            print(f"  Critical Tasks: {cp.get('count', 0)}")
            print(f"  Percentage: {cp.get('percentage', 0)}%")
        
        if 'buffers' in cpm:
            buffers = cpm['buffers']
            print(f"\nBuffer Analysis:")
            print(f"  Project Buffer: {buffers.get('project_buffer_days', 0)} days")
            print(f"  Total Buffer Days: {buffers.get('total_buffer_days', 0)} days")
    
    if 'reasoning' in timeline_result:
        reasoning = timeline_result['reasoning']
        print(f"\nAI Reasoning:")
        print(f"  Strategy: {reasoning.get('overall_strategy', 'Not specified')}")
        print(f"  Confidence Score: {reasoning.get('confidence_score', 0)}")
        
        if reasoning.get('parallel_opportunities'):
            print(f"  Parallel Opportunities: {len(reasoning['parallel_opportunities'])}")
        
        if reasoning.get('risk_factors'):
            print(f"  Identified Risks: {len(reasoning['risk_factors'])}")


if __name__ == '__main__':
    asyncio.run(test_timeline_generation())