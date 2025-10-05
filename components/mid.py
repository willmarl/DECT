import gradio as gr
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple

css = "text-align: center; margin-top: 20px;"

def get_available_frs() -> List[str]:
    """Get list of available FR IDs from the pipeline logbook"""
    logbook_base = Path("data/pdf_logbook")
    fr_ids = []
    
    if logbook_base.exists():
        for pdf_dir in logbook_base.iterdir():
            if pdf_dir.is_dir():
                for fr_dir in pdf_dir.iterdir():
                    if fr_dir.is_dir() and fr_dir.name.startswith('FR-'):
                        if fr_dir.name not in fr_ids:
                            fr_ids.append(fr_dir.name)
    
    return sorted(fr_ids) if fr_ids else ["No FRs available"]

def find_fr_step_file(fr_id: str, step: int) -> Optional[Path]:
    """Find the step file for a given FR ID and step number"""
    logbook_base = Path("data/pdf_logbook")
    
    if not logbook_base.exists():
        return None
    
    # Search through all PDF directories
    for pdf_dir in logbook_base.iterdir():
        if pdf_dir.is_dir():
            fr_dir = pdf_dir / fr_id
            if fr_dir.exists():
                step_file = fr_dir / f"step{step}.json"
                if step_file.exists():
                    return step_file
    
    return None

def load_step_data(fr_id: str, step: int) -> Tuple[pd.DataFrame, str]:
    """Load step data for a given FR and step, return DataFrame and status message"""
    if fr_id == "No FRs available" or not fr_id:
        return pd.DataFrame([{"Message": "No FR selected or available"}]), "No data available"
    
    step_file = find_fr_step_file(fr_id, step)
    
    if not step_file:
        return pd.DataFrame([{"Message": f"Step {step} data not found for {fr_id}"}]), f"❌ Step {step} not found"
    
    try:
        with open(step_file, 'r') as f:
            data = json.load(f)
        
        # Check if we have LLM response data
        if 'llm_response' in data and data['llm_response']:
            llm_data = data['llm_response']
            status = f"✅ Step {step} completed"
            
            # Convert step-specific data to DataFrame based on step type
            if step == 1 and 'atomic_blocks' in llm_data:
                blocks = llm_data['atomic_blocks']
                df = pd.DataFrame(blocks)
                
            elif step == 2 and 'partitions' in llm_data:
                partitions = llm_data['partitions']
                # Flatten partition data for better display
                rows = []
                for partition in partitions:
                    valid_str = ", ".join(partition.get('valid', []))
                    invalid_str = ", ".join(partition.get('invalid', []))
                    rows.append({
                        'Atomic Block ID': partition.get('atomic_block_id', ''),
                        'Valid Partitions': valid_str,
                        'Invalid Partitions': invalid_str
                    })
                df = pd.DataFrame(rows)
                
            elif step == 3 and 'boundaries' in llm_data:
                boundaries = llm_data['boundaries']
                # Flatten boundary data
                rows = []
                for boundary in boundaries:
                    for case in boundary.get('cases', []):
                        rows.append({
                            'Atomic Block ID': boundary.get('atomic_block_id', ''),
                            'Boundary Label': case.get('label', ''),
                            'Example': case.get('example', '')
                        })
                df = pd.DataFrame(rows)
                
            elif step == 4 and 'test_values' in llm_data:
                test_values = llm_data['test_values']
                df = pd.DataFrame(test_values)
                
            elif step == 5 and 'values' in llm_data:
                values = llm_data['values']
                df = pd.DataFrame({'Unified Values': values})
                
            elif step == 6 and 'deduped_values' in llm_data:
                values = llm_data['deduped_values']
                df = pd.DataFrame({'Deduped Values': values})
                
            elif step == 7 and 'organized_data' in llm_data:
                organized_data = llm_data['organized_data']
                # Flatten organized data for display
                rows = []
                for org in organized_data:
                    test_values_str = ", ".join(org.get('test_values_for_class', []))
                    boundary_values_str = ", ".join(org.get('test_values_for_boundaries', []))
                    rows.append({
                        'Feature': org.get('feature', ''),
                        'Equivalence Class': org.get('equivalence_class', ''),
                        'Test Values': test_values_str,
                        'Boundary Values': boundary_values_str
                    })
                df = pd.DataFrame(rows)
                
            elif step == 8 and 'test_cases' in llm_data:
                test_cases = llm_data['test_cases']
                # Create a comprehensive test case DataFrame
                rows = []
                for i, tc in enumerate(test_cases, 1):
                    rows.append({
                        'Test #': i,
                        'Title': tc.get('title', ''),
                        'Precondition': tc.get('precondition', ''),
                        'Steps': tc.get('steps', ''),
                        'Test Data': tc.get('test_data', ''),
                        'Expected Result': tc.get('expected_result', ''),
                        'Environment': tc.get('environment', ''),
                        'Status': tc.get('status', '')
                    })
                df = pd.DataFrame(rows)
                
            else:
                # Fallback: show raw JSON data
                df = pd.DataFrame([{"Raw Data": json.dumps(llm_data, indent=2)}])
                
        elif 'error' in data:
            df = pd.DataFrame([{"Error": data['error']}])
            status = f"❌ Step {step} failed"
            
        else:
            # Show basic file info if no LLM response yet
            df = pd.DataFrame([{
                "FR ID": data.get('fr_id', 'Unknown'),
                "Step": data.get('step_number', step),
                "Status": "Processing..."
            }])
            status = f"🔄 Step {step} in progress"
            
        return df, status
        
    except Exception as e:
        error_df = pd.DataFrame([{"Error": f"Failed to load step {step}: {str(e)}"}])
        return error_df, f"❌ Error loading step {step}"

def get_fr_summary(fr_id: str) -> str:
    """Get summary information about an FR"""
    if fr_id == "No FRs available" or not fr_id:
        return "Select an FR to view details"
    
    # Count completed steps
    completed_steps = 0
    for step in range(1, 9):
        if find_fr_step_file(fr_id, step):
            completed_steps += 1
    
    return f"📋 **{fr_id}** | Completed Steps: {completed_steps}/8 | Progress: {completed_steps/8*100:.0f}%"

def mid():
    # Load available FRs
    available_frs = get_available_frs()
    initial_fr = available_frs[0] if available_frs else "No FRs available"
    
    with gr.Row():
        selectFr = gr.Dropdown(
            choices=available_frs, 
            label="Select FR", 
            value=initial_fr,
            multiselect=False, 
            interactive=True
        )
        
        gr.Markdown(
            f"""
            <h2 style="{css}">
                Pipeline Step Viewer
            </h2>
            """
        )
        
        refreshFrButton = gr.Button("🔄 Refresh FRs", variant="secondary")
    
    # FR Summary
    frSummary = gr.Markdown(get_fr_summary(initial_fr))
    
    # Create all step dataframes with initial data
    with gr.Tabs():
        with gr.Tab("Step 1: Atomic Blocks"):
            step1_df = gr.Dataframe(
                value=load_step_data(initial_fr, 1)[0],
                label="Atomic Blocks - Breaking down requirements into testable units",
                wrap=True
            )
            step1_status = gr.Markdown(load_step_data(initial_fr, 1)[1])
            
        with gr.Tab("Step 2: Partitions"):
            step2_df = gr.Dataframe(
                value=load_step_data(initial_fr, 2)[0],
                label="Equivalence Partitions - Valid and invalid input categories",
                wrap=True
            )
            step2_status = gr.Markdown(load_step_data(initial_fr, 2)[1])
            
        with gr.Tab("Step 3: Boundaries"):
            step3_df = gr.Dataframe(
                value=load_step_data(initial_fr, 3)[0],
                label="Boundary Values - Edge cases and limits",
                wrap=True
            )
            step3_status = gr.Markdown(load_step_data(initial_fr, 3)[1])
            
        with gr.Tab("Step 4: Test Values"):
            step4_df = gr.Dataframe(
                value=load_step_data(initial_fr, 4)[0],
                label="Test Values - Concrete examples for each partition",
                wrap=True
            )
            step4_status = gr.Markdown(load_step_data(initial_fr, 4)[1])
            
        with gr.Tab("Step 5: Unified List"):
            step5_df = gr.Dataframe(
                value=load_step_data(initial_fr, 5)[0],
                label="Unified List - Combined test values",
                wrap=True
            )
            step5_status = gr.Markdown(load_step_data(initial_fr, 5)[1])
            
        with gr.Tab("Step 6: Deduped List"):
            step6_df = gr.Dataframe(
                value=load_step_data(initial_fr, 6)[0],
                label="Deduped List - Cleaned test values",
                wrap=True
            )
            step6_status = gr.Markdown(load_step_data(initial_fr, 6)[1])
            
        with gr.Tab("Step 7: Organized Data"):
            step7_df = gr.Dataframe(
                value=load_step_data(initial_fr, 7)[0],
                label="Organized Data - Structured test groups",
                wrap=True
            )
            step7_status = gr.Markdown(load_step_data(initial_fr, 7)[1])
            
        with gr.Tab("Step 8: Test Cases"):
            step8_df = gr.Dataframe(
                value=load_step_data(initial_fr, 8)[0],
                label="Final Test Cases - Complete test specifications",
                wrap=True
            )
            step8_status = gr.Markdown(load_step_data(initial_fr, 8)[1])
    
    # Function to update all tabs when FR selection changes
    def update_all_steps(selected_fr):
        """Update all step dataframes when FR selection changes"""
        results = []
        
        # Update summary
        summary = get_fr_summary(selected_fr)
        results.append(summary)
        
        # Update all 8 steps
        for step in range(1, 9):
            df, status = load_step_data(selected_fr, step)
            results.extend([df, status])  # Add both dataframe and status
        
        return results
    
    # Function to refresh FR list
    def refresh_fr_list():
        """Refresh the list of available FRs"""
        new_frs = get_available_frs()
        new_initial = new_frs[0] if new_frs else "No FRs available"
        
        # Return updated dropdown and all step data for the new initial FR
        update_results = update_all_steps(new_initial)
        return [gr.update(choices=new_frs, value=new_initial)] + update_results
    
    # Connect FR selection to update all steps
    selectFr.change(
        fn=update_all_steps,
        inputs=[selectFr],
        outputs=[
            frSummary,
            step1_df, step1_status,
            step2_df, step2_status,
            step3_df, step3_status,
            step4_df, step4_status,
            step5_df, step5_status,
            step6_df, step6_status,
            step7_df, step7_status,
            step8_df, step8_status
        ]
    )
    
    # Connect refresh button
    refreshFrButton.click(
        fn=refresh_fr_list,
        inputs=None,
        outputs=[
            selectFr, frSummary,
            step1_df, step1_status,
            step2_df, step2_status,
            step3_df, step3_status,
            step4_df, step4_status,
            step5_df, step5_status,
            step6_df, step6_status,
            step7_df, step7_status,
            step8_df, step8_status
        ]
    )
    
    gr.Markdown("---")