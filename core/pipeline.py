from pathlib import Path
import json
import utils.prompts as prompts

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
    
    # Run specified steps sequentially
    for step_num in steps:
        if step_num not in AVAILABLE_STEPS:
            print(f"Warning: Step {step_num} is not available. Skipping.")
            continue
        run_step(pdf_name, fr_id, fr_text, step_num)
    
    print(f"Pipeline completed for {pdf_name} - {fr_id}. Ran steps: {steps}")

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
        except (json.JSONDecodeError, KeyError):
            pass
    
    # Fallback: return FR text for any step if previous data not available
    return {"requirement_text": fr_text}

def run_step(pdf_name, fr_id, fr_text, step_number):
    """Run a specific step of the pipeline."""
    # Get the step prompt from prompts module
    step_prompt = getattr(prompts, f'STEP{step_number}')
    
    # Create output file path
    step_file = Path(f"data/pdf_logbook/{Path(pdf_name).stem}/{fr_id}/step{step_number}.json")
    
    # Prepare the input data for this step
    step_input_data = prepare_step_input(pdf_name, fr_id, fr_text, step_number)
    
    # TODO: Send prompt to LLM with step_input_data and get response
    # For now, save both the prompt and input data
    output_data = {
        "prompt": step_prompt,
        "input_data": step_input_data,
        "fr_id": fr_id,
        "fr_text": fr_text,
        "step_number": step_number
    }
    
    step_file.write_text(json.dumps(output_data, indent=2))
    
    print(f"Completed step {step_number} for {pdf_name} - {fr_id}")

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
    
    for i, fr in enumerate(frs_list, 1):
        fr_id = list(fr.keys())[0]
        print(f"\n--- Processing FR {i}/{len(frs_list)}: {fr_id} ---")
        pipeline(pdf_name, fr)
    
    print(f"\n=== Completed pipeline for {pdf_name} ===")
    
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
    
    # For now, use fake data since LLM isn't set up
    # TODO: Replace this with actual step8 file processing when LLM is ready
    final_output = fakeFinalOutput
    
    # Save the combined output
    final_output_path = outputs_dir / "final_output.json"
    with open(final_output_path, 'w') as f:
        json.dump(final_output, f, indent=2)
    
    print(f"\nFinal output saved to: {final_output_path}")
    print(f"Combined data from {len(step8_files)} step8 files")
    
    return final_output_path

def process_step8_file(file_path):
    """Process a single step8 file and extract test cases.
    
    This will be used when LLM responses are available.
    For now, returns placeholder data.
    """
    try:
        with open(file_path, 'r') as f:
            step8_data = json.load(f)
        
        # TODO: Process actual LLM response from step8_data
        # For now, return empty structure
        return {
            "fr_id": step8_data.get('fr_id', 'Unknown'),
            "test_cases": []
        }
    except (json.JSONDecodeError, FileNotFoundError, KeyError):
        return None

def create_final_output_structure(step8_results, pdf_name):
    """Create the final output JSON structure from processed step8 results."""
    return {
        "document_id": f"{pdf_name}.pdf",
        "test_suite": step8_results
    }