from rich import print
from pathlib import Path
import json
import pandas as pd
import utils.prompts as prompts

def write_pipeline_status(message):
    """Write status message to file for UI monitoring"""
    status_file = Path("pipeline_status.txt")
    try:
        status_file.write_text(message)
    except:
        pass  # Fail silently if can't write status

def generate_csv_from_final_output(final_output, outputs_dir):
    """Generate CSV file from final output data structure"""
    try:
        csv_path = outputs_dir / "final_output.csv"
        
        # Extract test cases into rows for CSV
        rows = []
        document_id = final_output.get('document_id', 'Unknown Document')
        
        for test_suite in final_output.get('test_suite', []):
            fr_id = test_suite.get('fr_id', 'Unknown')
            for i, test_case in enumerate(test_suite.get('test_cases', []), 1):
                rows.append({
                    'Document': document_id,
                    'FR ID': fr_id,
                    'Test #': i,
                    'Test Case': test_case.get('title', ''),
                    'Precondition': test_case.get('precondition', ''),
                    'Steps': test_case.get('steps', ''),
                    'Test Data': test_case.get('test_data', ''),
                    'Expected Result': test_case.get('expected_result', ''),
                    'Environment': test_case.get('environment', ''),
                    'Actual Result': test_case.get('actual_result', ''),
                    'Status': test_case.get('status', ''),
                    'Jira Bug Link': test_case.get('jira_bug_link', '')
                })
        
        if rows:
            df = pd.DataFrame(rows)
            df.to_csv(csv_path, index=False, encoding='utf-8')
            return True, f"CSV saved to: {csv_path}"
        else:
            return False, "No test cases found to export"
            
    except Exception as e:
        return False, f"Error generating CSV: {str(e)}"
from llm_client import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableParallel

# Define all available steps
AVAILABLE_STEPS = [1, 2, 3, 4, 5, 6, 7, 8]

def pipeline(pdf_name, fr, steps=None):
    """Run pipeline steps for the given PDF and FR.
    
    Args:
        pdf_name: Name of the PDF file
        fr: Dictionary containing FR data (e.g., {"FR-1": "The interface shall..."})
        steps: List of step numbers to run (default: all steps 1-8)
    """
    if steps is None:
        steps = AVAILABLE_STEPS
    
    # Extract FR ID and text
    fr_id = list(fr.keys())[0]
    fr_text = fr[fr_id]
    
    # Create data/pdf_logbook/foo_pdf/FR-X/ if not exists
    logbook_dir = Path(f"data/pdf_logbook/{Path(pdf_name).stem}/{fr_id}")
    logbook_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Starting pipeline for {pdf_name} - {fr_id}: {fr_text[:50]}...")
    write_pipeline_status(f"🚀 Starting pipeline for {fr_id}...")
    
    # Run specified steps sequentially
    for i, step_num in enumerate(steps, 1):
        if step_num not in AVAILABLE_STEPS:
            print(f"Warning: Step {step_num} is not available. Skipping.")
            continue
        
        write_pipeline_status(f"🔄 Processing {fr_id} - Step {step_num}/8 ({i}/{len(steps)} steps)")
        run_step(pdf_name, fr_id, fr_text, step_num)
    
    print(f"Pipeline completed for {pdf_name} - {fr_id}. Ran steps: {steps}")
    write_pipeline_status(f"✅ Completed {fr_id} - All {len(steps)} steps finished!")

def process_step_with_llm(step_number, step_prompt, step_input_data, fr_text):
    """Process a step using LLM and return the parsed response."""
    import time
    
    print(f"  📝 Preparing prompt for step {step_number}...")
    start_time = time.time()
    
    # Initialize LLM
    print(f"  🤖 Initializing LLM...")
    llm = get_llm()
    
    if step_number == 1:
        # Step 1: Use FR text directly
        print(f"  📋 Step 1: Processing FR text directly (length: {len(fr_text)} chars)")
        prompt = ChatPromptTemplate.from_messages([
            {"role": "system", "content": step_prompt["system_prompt"]},
            {"role": "user", "content": step_prompt["user_prompt"]},
            {"role": "user", "content": fr_text}
        ])
        
        print(f"  🔗 Creating LLM chain for step 1...")
        chain = RunnableParallel(
            response = prompt | llm | JsonOutputParser(),
        )
        
        print(f"  🚀 Invoking LLM for step 1...")
        result = chain.invoke({})
        
        elapsed = time.time() - start_time
        print(f"  ✅ Step 1 LLM call completed in {elapsed:.1f}s")
        return result["response"]
    
    elif step_number == 2:
        # Step 2: Use atomic blocks from step 1
        atomic_blocks = step_input_data.get("atomic_blocks", [])
        print(f"  📋 Step 2: Processing {len(atomic_blocks)} atomic blocks")
        
        # Create the full user message by combining the base prompt with atomic blocks data
        base_user_prompt = """Using the atomic blocks from Step 1, identify valid and invalid partitions.
Return only JSON following the schema and example.

Atomic Blocks:"""
        atomic_blocks_text = json.dumps(atomic_blocks, indent=2)
        # Escape braces in JSON to prevent ChatPromptTemplate from treating them as variables
        escaped_atomic_blocks = atomic_blocks_text.replace("{", "{{").replace("}", "}}")
        full_user_prompt = f"{base_user_prompt}\n{escaped_atomic_blocks}"
        
        print(f"  📏 User prompt length: {len(full_user_prompt)} chars")
        prompt = ChatPromptTemplate.from_messages([
            {"role": "system", "content": step_prompt["system_prompt"]},
            {"role": "user", "content": full_user_prompt}
        ])
        
        print(f"  🔗 Creating LLM chain for step 2...")
        chain = RunnableParallel(
            response = prompt | llm | JsonOutputParser(),
        )
        
        print(f"  🚀 Invoking LLM for step 2...")
        result = chain.invoke({})
        
        elapsed = time.time() - start_time
        print(f"  ✅ Step 2 LLM call completed in {elapsed:.1f}s")
        return result["response"]
    
    elif step_number == 3:
        # Step 3: Use partitions from step 2
        partitions = step_input_data.get("partitions", [])
        print(f"  📋 Step 3: Processing {len(partitions)} partitions")
        
        base_user_prompt = """Using the partitions from Step 2, define boundary cases for each applicable atomic block.
Return only JSON following the schema and example.

Partitions:"""
        partitions_text = json.dumps(partitions, indent=2)
        escaped_partitions = partitions_text.replace("{", "{{").replace("}", "}}")
        full_user_prompt = f"{base_user_prompt}\n{escaped_partitions}"
        
        print(f"  📏 User prompt length: {len(full_user_prompt)} chars")
        prompt = ChatPromptTemplate.from_messages([
            {"role": "system", "content": step_prompt["system_prompt"]},
            {"role": "user", "content": full_user_prompt}
        ])
        
        print(f"  🔗 Creating LLM chain for step 3...")
        chain = RunnableParallel(
            response = prompt | llm | JsonOutputParser(),
        )
        
        print(f"  🚀 Invoking LLM for step 3... (this may take a while)")
        result = chain.invoke({})
        
        elapsed = time.time() - start_time
        print(f"  ✅ Step 3 LLM call completed in {elapsed:.1f}s")
        return result["response"]
    
    elif step_number == 4:
        # Step 4: Use partitions and boundaries
        partitions = step_input_data.get("partitions", [])
        boundaries = step_input_data.get("boundaries", [])
        print(f"  📋 Step 4: Processing {len(partitions)} partitions and {len(boundaries)} boundaries")
        
        base_user_prompt = """Using partitions and boundary cases, produce test values for each atomic block.
Return only JSON following the schema and example.

Partitions:"""
        partitions_text = json.dumps(partitions, indent=2)
        boundaries_text = json.dumps(boundaries, indent=2)
        escaped_partitions = partitions_text.replace("{", "{{").replace("}", "}}")
        escaped_boundaries = boundaries_text.replace("{", "{{").replace("}", "}}")
        full_user_prompt = f"{base_user_prompt}\n{escaped_partitions}\nBoundaries:\n{escaped_boundaries}"
        
        print(f"  📏 User prompt length: {len(full_user_prompt)} chars")
        prompt = ChatPromptTemplate.from_messages([
            {"role": "system", "content": step_prompt["system_prompt"]},
            {"role": "user", "content": full_user_prompt}
        ])
        
        print(f"  🔗 Creating LLM chain for step 4...")
        chain = RunnableParallel(
            response = prompt | llm | JsonOutputParser(),
        )
        
        print(f"  🚀 Invoking LLM for step 4...")
        result = chain.invoke({})
        
        elapsed = time.time() - start_time
        print(f"  ✅ Step 4 LLM call completed in {elapsed:.1f}s")
        return result["response"]
    
    elif step_number == 5:
        # Step 5: Use test values from step 4
        test_values = step_input_data.get("test_values", [])
        print(f"  📋 Step 5: Processing {len(test_values)} test values")
        
        base_user_prompt = """Combine all test values from previous steps into a unified list.
Return only JSON following the schema and example.

Test Values:"""
        test_values_text = json.dumps(test_values, indent=2)
        escaped_test_values = test_values_text.replace("{", "{{").replace("}", "}}")
        full_user_prompt = f"{base_user_prompt}\n{escaped_test_values}"
        
        print(f"  📏 User prompt length: {len(full_user_prompt)} chars")
        print(f"  🚀 Invoking LLM for step 5...")
        
        prompt = ChatPromptTemplate.from_messages([
            {"role": "system", "content": step_prompt["system_prompt"]},
            {"role": "user", "content": full_user_prompt}
        ])
        
        chain = RunnableParallel(
            response = prompt | llm | JsonOutputParser(),
        )
        
        result = chain.invoke({})
        elapsed = time.time() - start_time
        print(f"  ✅ Step 5 LLM call completed in {elapsed:.1f}s")
        return result["response"]
    
    elif step_number == 6:
        # Step 6: Use unified values from step 5
        unified_values = step_input_data.get("values", [])
        print(f"  📋 Step 6: Processing {len(unified_values)} unified values")
        
        base_user_prompt = """Remove duplicate test values and output a cleaned list.
Return only JSON following the schema and example.

Unified Test Values:"""
        unified_values_text = json.dumps(unified_values, indent=2)
        escaped_unified_values = unified_values_text.replace("{", "{{").replace("}", "}}")
        full_user_prompt = f"{base_user_prompt}\n{escaped_unified_values}"
        
        print(f"  🚀 Invoking LLM for step 6...")
        prompt = ChatPromptTemplate.from_messages([
            {"role": "system", "content": step_prompt["system_prompt"]},
            {"role": "user", "content": full_user_prompt}
        ])
        
        chain = RunnableParallel(
            response = prompt | llm | JsonOutputParser(),
        )
        
        result = chain.invoke({})
        elapsed = time.time() - start_time
        print(f"  ✅ Step 6 LLM call completed in {elapsed:.1f}s")
        return result["response"]
    
    elif step_number == 7:
        # Step 7: Use deduped values from step 6
        deduped_values = step_input_data.get("deduped_values", [])
        print(f"  📋 Step 7: Processing {len(deduped_values)} deduped values")
        
        base_user_prompt = """Organize the deduped test values into equivalence classes and boundary groupings.
Return only JSON following the schema and example.

Deduped Test Values:"""
        deduped_values_text = json.dumps(deduped_values, indent=2)
        escaped_deduped_values = deduped_values_text.replace("{", "{{").replace("}", "}}")
        full_user_prompt = f"{base_user_prompt}\n{escaped_deduped_values}"
        
        print(f"  🚀 Invoking LLM for step 7...")
        prompt = ChatPromptTemplate.from_messages([
            {"role": "system", "content": step_prompt["system_prompt"]},
            {"role": "user", "content": full_user_prompt}
        ])
        
        chain = RunnableParallel(
            response = prompt | llm | JsonOutputParser(),
        )
        
        result = chain.invoke({})
        elapsed = time.time() - start_time
        print(f"  ✅ Step 7 LLM call completed in {elapsed:.1f}s")
        return result["response"]
    
    elif step_number == 8:
        # Step 8: Use organized data from step 7
        organized_data = step_input_data.get("organized_data", [])
        print(f"  📋 Step 8: Processing {len(organized_data)} organized data groups")
        
        base_user_prompt = """Generate detailed test cases using the organized test data.
Return only JSON following the schema and example.

Organized Test Data:"""
        organized_data_text = json.dumps(organized_data, indent=2)
        escaped_organized_data = organized_data_text.replace("{", "{{").replace("}", "}}")
        full_user_prompt = f"{base_user_prompt}\n{escaped_organized_data}"
        
        print(f"  🚀 Invoking LLM for step 8 (final step)...")
        prompt = ChatPromptTemplate.from_messages([
            {"role": "system", "content": step_prompt["system_prompt"]},
            {"role": "user", "content": full_user_prompt}
        ])
        
        chain = RunnableParallel(
            response = prompt | llm | JsonOutputParser(),
        )
        
        result = chain.invoke({})
        elapsed = time.time() - start_time
        print(f"  ✅ Step 8 LLM call completed in {elapsed:.1f}s")
        return result["response"]
    
    else:
        raise ValueError(f"Unknown step number: {step_number}")

def prepare_step_input(pdf_name, fr_id, fr_text, step_number):
    """Prepare input data for a specific step based on previous step outputs."""
    logbook_dir = Path(f"data/pdf_logbook/{Path(pdf_name).stem}/{fr_id}")
    
    if step_number == 1:
        # Step 1 uses the original FR text
        return {"requirement_text": fr_text}
    
    # For steps 2-8, try to load output from previous step
    previous_step = step_number - 1
    prev_file = logbook_dir / f"step{previous_step}.json"
    
    if prev_file.exists():
        try:
            with open(prev_file, 'r') as f:
                prev_data = json.load(f)
            # Extract the actual LLM response if it exists, otherwise use the saved data
            if 'llm_response' in prev_data:
                return prev_data['llm_response']
            elif 'input_data' in prev_data:
                return prev_data['input_data']
        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠️ Warning: Could not load previous step data from {prev_file}: {e}")
            pass
    
    # Fallback: return FR text for any step if previous data not available
    return {"requirement_text": fr_text}

def run_step(pdf_name, fr_id, fr_text, step_number):
    """Run a specific step of the pipeline."""
    import time
    overall_start = time.time()
    
    print(f"\n🔄 Processing step {step_number} for {pdf_name} - {fr_id}")
    print(f"⏰ Started at: {time.strftime('%H:%M:%S')}")
    
    # Get the step prompt from prompts module
    step_prompt = getattr(prompts, f'STEP{step_number}')
    
    # Create output file path
    step_file = Path(f"data/pdf_logbook/{Path(pdf_name).stem}/{fr_id}/step{step_number}.json")
    
    # Prepare the input data for this step
    step_input_data = prepare_step_input(pdf_name, fr_id, fr_text, step_number)
    
    try:
        # Create the LLM chain based on step number
        llm_response = process_step_with_llm(step_number, step_prompt, step_input_data, fr_text)
        
        # Save the complete output including LLM response
        output_data = {
            "prompt": step_prompt,
            "input_data": step_input_data,
            "llm_response": llm_response,
            "fr_id": fr_id,
            "fr_text": fr_text,
            "step_number": step_number
        }
        
        step_file.write_text(json.dumps(output_data, indent=2))
        
        total_elapsed = time.time() - overall_start
        print(f"✅ Completed step {step_number} for {pdf_name} - {fr_id}")
        print(f"⏱️ Total time: {total_elapsed:.1f}s | Finished at: {time.strftime('%H:%M:%S')}")
        
    except Exception as e:
        total_elapsed = time.time() - overall_start
        print(f"❌ Error in step {step_number} for {pdf_name} - {fr_id}: {e}")
        print(f"⏱️ Failed after: {total_elapsed:.1f}s")
        # Save error information for debugging
        output_data = {
            "prompt": step_prompt,
            "input_data": step_input_data,
            "error": str(e),
            "fr_id": fr_id,
            "fr_text": fr_text,
            "step_number": step_number
        }
        step_file.write_text(json.dumps(output_data, indent=2))

def run_single_step(pdf_name, fr, step_number):
    """Run just a single step (useful for debugging or re-running specific steps)."""
    fr_id = list(fr.keys())[0]
    fr_text = fr[fr_id]
    logbook_dir = Path(f"data/pdf_logbook/{Path(pdf_name).stem}/{fr_id}")
    logbook_dir.mkdir(parents=True, exist_ok=True)
    run_step(pdf_name, fr_id, fr_text, step_number)

def run_steps_range(pdf_name, fr, start_step, end_step):
    """Run a range of steps from start_step to end_step (inclusive)."""
    steps = list(range(start_step, end_step + 1))
    pipeline(pdf_name, fr, steps)

def get_step_prompt(step_number):
    """Get the prompt for a specific step."""
    if step_number not in AVAILABLE_STEPS:
        raise ValueError(f"Step {step_number} is not available. Available steps: {AVAILABLE_STEPS}")
    
    return getattr(prompts, f'STEP{step_number}')

def list_output_files(pdf_name, fr_id=None):
    """List all step output files for a given PDF and optionally specific FR."""
    base_dir = Path(f"data/pdf_logbook/{Path(pdf_name).stem}")
    if not base_dir.exists():
        return []
    
    step_files = []
    
    if fr_id:
        # List files for specific FR
        fr_dir = base_dir / fr_id
        if fr_dir.exists():
            for step_num in AVAILABLE_STEPS:
                step_file = fr_dir / f"step{step_num}.json"
                if step_file.exists():
                    step_files.append(step_file)
    else:
        # List files for all FRs
        for fr_dir in base_dir.iterdir():
            if fr_dir.is_dir() and fr_dir.name.startswith('FR-'):
                for step_num in AVAILABLE_STEPS:
                    step_file = fr_dir / f"step{step_num}.json"
                    if step_file.exists():
                        step_files.append(step_file)
    
    return step_files

def get_fr_directories(pdf_name):
    """Get all FR directories for a given PDF."""
    base_dir = Path(f"data/pdf_logbook/{Path(pdf_name).stem}")
    if not base_dir.exists():
        return []
    
    fr_dirs = []
    for fr_dir in base_dir.iterdir():
        if fr_dir.is_dir() and fr_dir.name.startswith('FR-'):
            fr_dirs.append(fr_dir.name)
    
    return sorted(fr_dirs)

def run_pipeline_for_pdf(pdf_name, frs_list):
    """Run the complete pipeline for a PDF with all its FRs.
    
    Args:
        pdf_name: Name of the PDF file
        frs_list: List of FR dictionaries from selected_tasks.json
    """
    print(f"\n=== Starting pipeline for {pdf_name} ===")
    print(f"Found {len(frs_list)} functional requirements")
    write_pipeline_status(f"🚀 Starting analysis of {pdf_name} with {len(frs_list)} FRs")
    
    for i, fr in enumerate(frs_list, 1):
        fr_id = list(fr.keys())[0]
        print(f"\n--- Processing FR {i}/{len(frs_list)}: {fr_id} ---")
        write_pipeline_status(f"🔄 Processing FR {i}/{len(frs_list)}: {fr_id}")
        pipeline(pdf_name, fr)
    
    print(f"\n=== Completed pipeline for {pdf_name} ===")
    write_pipeline_status(f"✅ Analysis complete! Processed {len(frs_list)} FRs for {pdf_name}")
    
    # Summary
    for fr in frs_list:
        fr_id = list(fr.keys())[0]
        files = list_output_files(pdf_name, fr_id)
        print(f"{fr_id}: {len(files)} step files generated")

def combine_all_step8_files():
    """Scan all PDF logbook folders and combine step8 files into final output."""
    from utils.mockData import fakeFinalOutput
    from pathlib import Path
    import json
    
    # Ensure outputs directory exists
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(exist_ok=True)
    
    # Scan for all step8 files
    logbook_base = Path("data/pdf_logbook")
    step8_files = []
    
    if logbook_base.exists():
        # Find all step8.json files in pdf_name/fr_id/ structure
        for pdf_dir in logbook_base.iterdir():
            if pdf_dir.is_dir():
                for fr_dir in pdf_dir.iterdir():
                    if fr_dir.is_dir() and fr_dir.name.startswith('FR-'):
                        step8_file = fr_dir / "step8.json"
                        if step8_file.exists():
                            step8_files.append({
                                'pdf_name': pdf_dir.name,
                                'fr_id': fr_dir.name,
                                'file_path': step8_file
                            })
    
    print(f"Found {len(step8_files)} step8 files to combine:")
    for file_info in step8_files:
        print(f"  {file_info['pdf_name']} - {file_info['fr_id']}")
    
    # Process actual step8 files or use fake data as fallback
    if step8_files:
        # Process real step8 files
        test_suites = []
        for file_info in step8_files:
            processed_data = process_step8_file(file_info['file_path'])
            if processed_data:
                test_suites.append(processed_data)
        
        if test_suites:
            # Use the first PDF name found, or create a generic one
            pdf_name = step8_files[0]['pdf_name'] if step8_files else "unknown"
            final_output = create_final_output_structure(test_suites, pdf_name)
        else:
            print("⚠️ Warning: No valid step8 data found, using fallback fake data")
            final_output = fakeFinalOutput
    else:
        print("⚠️ Warning: No step8 files found, using fallback fake data")
        final_output = fakeFinalOutput
    
    # Save the combined output
    final_output_path = outputs_dir / "final_output.json"
    with open(final_output_path, 'w') as f:
        json.dump(final_output, f, indent=2)
    
    print(f"\nFinal output saved to: {final_output_path}")
    
    # Generate CSV version for easy spreadsheet import
    csv_success, csv_message = generate_csv_from_final_output(final_output, outputs_dir)
    if csv_success:
        print(f"📊 CSV export: {csv_message}")
    else:
        print(f"⚠️ CSV export failed: {csv_message}")
    
    print(f"Combined data from {len(step8_files)} step8 files")
    write_pipeline_status(f"🎉 Final results ready! Generated test cases from {len(step8_files)} FRs")
    
    return final_output_path

def process_step8_file(file_path):
    """Process a single step8 file and extract test cases.
    
    Extracts the LLM response containing test cases from step8 output.
    """
    try:
        with open(file_path, 'r') as f:
            step8_data = json.load(f)
        
        # Extract test cases from LLM response
        if 'llm_response' in step8_data and step8_data['llm_response']:
            llm_response = step8_data['llm_response']
            return {
                "fr_id": llm_response.get('fr_id', step8_data.get('fr_id', 'Unknown')),
                "test_cases": llm_response.get('test_cases', [])
            }
        elif 'fr_id' in step8_data:
            # Fallback if no LLM response but file exists
            print(f"⚠️ Warning: No LLM response found in {file_path}")
            return {
                "fr_id": step8_data.get('fr_id', 'Unknown'),
                "test_cases": []
            }
        else:
            print(f"⚠️ Warning: Invalid step8 file format: {file_path}")
            return None
            
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        print(f"❌ Error processing step8 file {file_path}: {e}")
        return None

def create_final_output_structure(step8_results, pdf_name):
    """Create the final output JSON structure from processed step8 results."""
    return {
        "document_id": f"{pdf_name}.pdf",
        "test_suite": step8_results
    }