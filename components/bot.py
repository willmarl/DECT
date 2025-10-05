import gradio as gr
import json
from pathlib import Path
import pandas as pd

def load_full_final_output():
    """Load the complete final_output.json and convert to DataFrame"""
    final_output_path = Path("outputs/final_output.json")
    
    if not final_output_path.exists():
        # Return empty DataFrame with proper column structure
        return pd.DataFrame(columns=[
            'Document', 'FR ID', 'Test #', 'Test Case', 'Precondition', 'Steps', 
            'Test Data', 'Expected Result', 'Environment', 'Actual Result', 'Status', 'Jira Bug Link'
        ])
    
    try:
        with open(final_output_path, 'r') as f:
            data = json.load(f)
        
        # Extract all test cases from all FRs
        rows = []
        document_id = data.get('document_id', 'Unknown Document')
        
        for test_suite in data.get('test_suite', []):
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
            return pd.DataFrame(rows)
        else:
            # Return empty DataFrame if no test cases found
            return pd.DataFrame(columns=[
                'Document', 'FR ID', 'Test #', 'Test Case', 'Precondition', 'Steps', 
                'Test Data', 'Expected Result', 'Environment', 'Actual Result', 'Status', 'Jira Bug Link'
            ])
            
    except Exception as e:
        print(f"Error loading final output in bot: {e}")
        # Return empty DataFrame on error instead of dummy data
        return pd.DataFrame(columns=[
            'Document', 'FR ID', 'Test #', 'Test Case', 'Precondition', 'Steps', 
            'Test Data', 'Expected Result', 'Environment', 'Actual Result', 'Status', 'Jira Bug Link'
        ])

def get_summary_stats():
    """Get summary statistics from the final output"""
    final_output_path = Path("outputs/final_output.json")
    
    if not final_output_path.exists():
        return "No results available yet. Please run the analysis first."
    
    try:
        with open(final_output_path, 'r') as f:
            data = json.load(f)
        
        total_frs = len(data.get('test_suite', []))
        total_test_cases = sum(len(suite.get('test_cases', [])) for suite in data.get('test_suite', []))
        document_id = data.get('document_id', 'Unknown Document')
        
        return f"📊 **Analysis Results for {document_id}**\n\n" + \
               f"• **Total Functional Requirements:** {total_frs}\n" + \
               f"• **Total Test Cases Generated:** {total_test_cases}\n" + \
               f"• **Average Test Cases per FR:** {total_test_cases/total_frs if total_frs > 0 else 0:.1f}"
               
    except Exception as e:
        return f"Error loading summary: {e}"

def bot():
    gr.Markdown("## Final Compiled Test Cases")
    
    # Summary statistics
    summary = gr.Markdown(get_summary_stats())
    
    # Refresh button to update the data
    refresh_btn = gr.Button("🔄 Refresh Results", variant="secondary")
    
    # Full results dataframe
    full_results = gr.Dataframe(
        value=load_full_final_output(),
        label="Complete Test Cases", 
        wrap=True,
        interactive=False
    )
    
    # Function to refresh both summary and dataframe
    def refresh_all():
        return get_summary_stats(), load_full_final_output()
    
    refresh_btn.click(
        fn=refresh_all,
        inputs=None,
        outputs=[summary, full_results]
    )
    
    return {"summary": summary, "dataframe": full_results, "refresh": refresh_btn}