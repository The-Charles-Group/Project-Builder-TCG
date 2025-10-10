import sys
import json
from AI_Scheduler_Kit_v2.src.orchestrator import run_pipeline

def main():
    if len(sys.argv) < 3:
        print("Usage: python ai_schedule_postprocess.py <input_xml> <output_xml> [gantt_json] [explanations_json] [excel_out]")
        raise SystemExit(2)
    
    xml_in = sys.argv[1]
    xml_out = sys.argv[2]
    gantt = sys.argv[3] if len(sys.argv) > 3 else None
    expl = sys.argv[4] if len(sys.argv) > 4 else None
    excel = sys.argv[5] if len(sys.argv) > 5 else None
    
    res = run_pipeline(
        xml_in, 
        xml_out, 
        gantt_json=gantt, 
        explanations_json=expl, 
        excel_out=excel, 
        changes=None, 
        ai_callable=None, 
        round_policy="ceil"
    )
    
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
