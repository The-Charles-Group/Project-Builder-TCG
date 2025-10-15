#!/usr/bin/env python3
"""
Fix for the missing job status endpoint in ai_planner_agencydb.py
This code should be added to the mount_routes_agencydb function
"""

# This code snippet should be added to ai_planner_agencydb.py after line 1669 (in mount_routes_agencydb function)

def add_job_status_endpoint_fix():
    """
    Add this route handler to ai_planner_agencydb.py to fix the 404 error
    """
    code_to_add = '''
    @router.get("/jobs/{job_id}")
    async def get_job_status(job_id: str):
        """Get the status and results of an AI analysis job"""
        
        # Check if job exists
        if job_id not in AI_JOB_STORE:
            # Check if it's an old job that was cleaned up
            cleanup_ai_jobs()
            raise HTTPException(404, f"Job {job_id} not found or expired")
        
        job = AI_JOB_STORE[job_id]
        
        # Prepare response based on job status
        response = {
            "job_id": job_id,
            "status": job.status,
            "created_at": job.created_at.isoformat() if hasattr(job, 'created_at') else None,
            "updated_at": job.updated_at.isoformat() if hasattr(job, 'updated_at') else None,
        }
        
        # Add progress information if available
        if hasattr(job, 'progress'):
            response["progress"] = job.progress
        
        # Add stage information if available
        if hasattr(job, 'current_stage'):
            response["current_stage"] = job.current_stage
            
        # Add results if job is completed
        if job.status == "completed":
            response["result"] = job.result
            if hasattr(job, 'deliverable_count'):
                response["deliverable_count"] = job.deliverable_count
                
        # Add error information if job failed
        elif job.status == "failed":
            response["error"] = job.error if hasattr(job, 'error') else "Unknown error"
            
        # Add timing information
        if hasattr(job, 'duration'):
            response["duration"] = job.duration
            
        return response
    '''
    
    return code_to_add

def increase_gpt5_output_limits():
    """
    Configuration changes needed to increase deliverable output
    """
    config_changes = '''
# Add these environment variables or update the configuration:

# Increase minimum deliverables expected
AI_MIN_DELIVERABLES = 100  # Currently 15
AI_MIN_COMPONENTS_PER_DELIV = 5  # Currently 2
AI_MIN_TASKS_PER_COMPONENT = 5  # Currently 2

# Increase GPT-5 output limits
GPT5_MAX_OUTPUT_TOKENS = 16384  # Increase from current limit
GPT5_MAX_ITEMS_PER_BATCH = 50  # Increase from 15

# Adjust chunking strategy
GPT5_CHUNK_SIZE = 25  # Increase from 15
GPT5_MAX_PARALLEL_CHUNKS = 10  # Increase parallel processing

# Update retry logic
GPT5_MAX_RETRIES = 5  # Increase from 3
GPT5_RETRY_DELAY = 3  # Seconds between retries
    '''
    
    return config_changes

def fix_file_encoding_issue():
    """
    Fix for the Unicode decoding errors in file uploads
    """
    fix_code = '''
def _extract_text_from_upload(content: bytes, filename: str) -> str:
    """Extract text from uploaded file with proper encoding handling"""
    ext = os.path.splitext(filename or "")[1].lower()

    # Plain text-like files
    if ext in (".txt", ".md", ".csv"):
        # Try multiple encodings in order of likelihood
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
        for encoding in encodings:
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        # If all fail, use latin-1 with error handling
        return content.decode("latin-1", errors="ignore")

    # DOCX files
    if ext == ".docx":
        try:
            import io
            from docx import Document
            doc = Document(io.BytesIO(content))
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)
            return "\\n".join(paragraphs)
        except Exception as e:
            print(f"[DOCX ERROR] Failed to parse: {e}")
            return ""

    # PDF files
    if ext == ".pdf":
        try:
            import io
            import PyPDF2
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text_parts = []
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                if text.strip():
                    text_parts.append(text)
            return "\\n".join(text_parts)
        except Exception as e:
            print(f"[PDF ERROR] Failed to parse: {e}")
            return ""

    # Default: try as text
    try:
        return content.decode("utf-8", errors="ignore")
    except:
        return content.decode("latin-1", errors="ignore")
    '''
    
    return fix_code

if __name__ == "__main__":
    print("=" * 60)
    print("CRITICAL FIXES NEEDED FOR GPT-5 RFP ANALYSIS")
    print("=" * 60)
    
    print("\n1. ADD JOB STATUS ENDPOINT")
    print("-" * 40)
    print("Location: ai_planner_agencydb.py, in mount_routes_agencydb function")
    print("Add this code:")
    print(add_job_status_endpoint_fix())
    
    print("\n2. INCREASE GPT-5 OUTPUT LIMITS")
    print("-" * 40)
    print("Location: Configuration/Environment variables")
    print(increase_gpt5_output_limits())
    
    print("\n3. FIX FILE ENCODING ISSUES")
    print("-" * 40)
    print("Location: Replace _extract_text_from_upload function in main.py")
    print(fix_file_encoding_issue())
    
    print("\n" + "=" * 60)
    print("SUMMARY OF ISSUES FOUND:")
    print("=" * 60)
    print("✅ GPT-5 is working and responding")
    print("❌ Job status endpoint returns 404 (needs implementation)")
    print("❌ Only getting 52 deliverables instead of 100+ required")
    print("❌ DOCX/PDF file processing has encoding errors")
    print("⚠️ Response times are slow (30-150+ seconds)")
    print("⚠️ JSON parsing errors occur occasionally")
    print("\nRefer to comprehensive_test_report.md for full details.")