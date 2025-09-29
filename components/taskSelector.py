import gradio as gr
import json
import os
from pathlib import Path

class TaskSelector:
    def __init__(self, json_directory="extractedFR"):
        self.json_directory = json_directory
        self.json_files = {}
        self.load_json_files()
        
    def load_json_files(self):
        """Load all JSON files from the extractedFR directory"""
        self.json_files = {}
        json_dir = Path(self.json_directory)
        
        if not json_dir.exists():
            return
            
        for json_file in json_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.json_files[json_file.stem] = data
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
    
    def refresh_json_files(self):
        """Refresh the list of JSON files (called after PDF processing)"""
        self.load_json_files()
        return self.get_file_options()
    
    def get_file_options(self):
        """Get list of available JSON files"""
        return list(self.json_files.keys())
    
    def has_files(self):
        """Check if there are any JSON files available"""
        return len(self.json_files) > 0
    
    def is_directory_empty(self):
        """Check if the extractedFR directory is empty or doesn't exist"""
        json_dir = Path(self.json_directory)
        if not json_dir.exists():
            return True
        return len(list(json_dir.glob("*.json"))) == 0
    
    def get_requirements_for_file(self, selected_file):
        """Get requirements from selected JSON file"""
        if not selected_file or selected_file not in self.json_files:
            return [], "Please select a valid file"
            
        data = self.json_files[selected_file]
        requirements = data.get('requirements', [])
        
        # Format requirements for display
        formatted_reqs = []
        for req in requirements:
            req_id = req.get('id', 'N/A')
            req_text = req.get('text', 'No description')
            formatted_reqs.append(f"{req_id}: {req_text}")
            
        return formatted_reqs, f"Loaded {len(requirements)} requirements from {selected_file}.json"
    
    def handle_requirement_selection(self, selected_file, selected_requirements):
        """Handle when user selects specific requirements"""
        if not selected_requirements:
            return "No requirements selected"
            
        result = f"Selected from {selected_file}:\n\n"
        
        # Get the original data to extract full details
        data = self.json_files.get(selected_file, {})
        requirements = data.get('requirements', [])
        
        for selected in selected_requirements:
            # Extract the ID from the formatted string
            req_id = selected.split(':')[0]
            
            # Find the full requirement data
            for req in requirements:
                if req.get('id') == req_id:
                    result += f"• {req_id}: {req.get('text', '')}\n\n"
                    break
                    
        return result
    
    def format_all_selected_requirements(self, all_files_data):
        """Format all selected requirements from all files for display"""
        if not all_files_data:
            return "No tasks selected"
        
        result = "🎯 Currently Selected Tasks:\n\n"
        total_count = 0
        
        for file_name, selected_requirements in all_files_data.items():
            if selected_requirements:
                result += f"📁 From {file_name}.json:\n"
                data = self.json_files.get(file_name, {})
                requirements = data.get('requirements', [])
                
                for selected in selected_requirements:
                    # Extract the ID from the formatted string
                    req_id = selected.split(':')[0]
                    
                    # Find the full requirement data
                    for req in requirements:
                        if req.get('id') == req_id:
                            result += f"  • {req_id}: {req.get('text', '')}\n"
                            total_count += 1
                            break
                result += "\n"
        
        if total_count == 0:
            return "No tasks selected"
        
        result = f"🎯 Currently Selected Tasks ({total_count} total):\n\n" + result[len("🎯 Currently Selected Tasks:\n\n"):]
        return result
    
    def get_selected_requirements_data(self, selected_file, selected_requirements):
        """Get the actual requirement data for selected items"""
        if not selected_requirements or not selected_file:
            return []
            
        data = self.json_files.get(selected_file, {})
        requirements = data.get('requirements', [])
        selected_data = []
        
        for selected in selected_requirements:
            # Extract the ID from the formatted string
            req_id = selected.split(':')[0]
            
            # Find the full requirement data
            for req in requirements:
                if req.get('id') == req_id:
                    selected_data.append(req)
                    break
                    
        return selected_data
    
    def create_tasks_json(self, all_files_data, output_dir="start", filename="tasks.json"):
        """Create a JSON file with all selected tasks organized by file name"""
        import os
        
        # Create the start directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Build the JSON structure
        tasks_json = {}
        
        for file_name, selected_requirements in all_files_data.items():
            if selected_requirements:
                # Get the original data
                data = self.json_files.get(file_name, {})
                requirements = data.get('requirements', [])
                
                # Create an array for this file's requirements
                file_requirements = []
                
                for selected in selected_requirements:
                    # Extract the ID from the formatted string
                    req_id = selected.split(':')[0]
                    
                    # Find the full requirement data
                    for req in requirements:
                        if req.get('id') == req_id:
                            # Create the requirement object with ID as key
                            file_requirements.append({
                                req_id: req.get('text', 'No description')
                            })
                            break
                
                # Add to the main JSON structure if we have requirements
                if file_requirements:
                    tasks_json[file_name] = file_requirements
        
        # Write to file
        output_path = os.path.join(output_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(tasks_json, f, indent=4, ensure_ascii=False)
        
        return output_path, len(tasks_json), sum(len(reqs) for reqs in tasks_json.values())

def create_task_selector():
    """Create and return the task selector component"""
    selector = TaskSelector()
    
    # Store selections from all files
    all_selections = {}
    
    def update_requirements_list(selected_file):
        """Update the requirements checkboxes based on selected file"""
        requirements, status = selector.get_requirements_for_file(selected_file)
        # Restore previous selections for this file if any
        previous_selection = all_selections.get(selected_file, [])
        return gr.update(choices=requirements, value=previous_selection), status
    
    def select_all_requirements(selected_file):
        """Select all available requirements"""
        requirements, _ = selector.get_requirements_for_file(selected_file)
        return gr.update(value=requirements)
    
    def deselect_all_requirements():
        """Deselect all requirements"""
        return gr.update(value=[])
    
    def refresh_files():
        """Refresh the JSON files and update dropdown"""
        nonlocal all_selections
        all_selections = {}  # Clear all selections when refreshing
        file_options = selector.refresh_json_files()
        initial_file = file_options[0] if file_options else None
        
        # Check if directory is empty
        is_empty = selector.is_directory_empty()
        has_files = selector.has_files()
        
        # Also clear the requirements when refreshing
        initial_requirements = []
        if initial_file:
            initial_requirements, _ = selector.get_requirements_for_file(initial_file)
        
        if is_empty:
            output_message = "📂 No processed PDFs found.\n\nPlease upload and process a PDF first using the '1. Process PDF' button above."
            title_text = "### 📋 Task Selector ⚠️ (Disabled - No PDFs Processed)"
        elif not has_files:
            output_message = "⚠️ No valid task files found.\n\nThe extractedFR folder exists but contains no valid JSON files."
            title_text = "### 📋 Task Selector ⚠️ (Disabled - No Valid Files)"
        else:
            output_message = "No tasks selected"
            title_text = "### 📋 Task Selector"
        
        return [
            gr.update(choices=file_options, value=initial_file, interactive=has_files),  # Update dropdown
            gr.update(choices=initial_requirements, value=[], interactive=has_files),   # Update requirements
            output_message,  # Update output message
            gr.update(interactive=has_files),  # Refresh button
            gr.update(interactive=has_files),  # Select all button  
            gr.update(interactive=has_files),  # Deselect all button
            gr.update(value=title_text),  # Update title
        ]
    
    def update_selections_and_output(selected_file, selected_requirements):
        """Update the stored selections and output display"""
        nonlocal all_selections
        
        if selected_file:
            all_selections[selected_file] = selected_requirements or []
        
        # Check if any requirements are selected across all files
        has_selections = any(selections for selections in all_selections.values())
        
        # Format output display
        output_text = selector.format_all_selected_requirements(all_selections)
        
        return str(has_selections), output_text
    
    def get_all_selections():
        """Get all current selections"""
        return all_selections.copy()
    
    def create_tasks_json_file():
        """Create the tasks.json file with all selected tasks"""
        try:
            if not any(selections for selections in all_selections.values()):
                return "❌ No tasks selected. Please select at least one task before running.", False
            
            output_path, num_files, num_tasks = selector.create_tasks_json(all_selections)
            return f"✅ Tasks JSON created successfully!\n\nFile: {output_path}\nFiles processed: {num_files}\nTotal tasks: {num_tasks}", True
        except Exception as e:
            return f"❌ Error creating tasks JSON: {str(e)}", False
    
    # Check initial state
    is_empty = selector.is_directory_empty()
    has_files = selector.has_files()
    file_options = selector.get_file_options()
    initial_file = file_options[0] if file_options else None
    
    # Get initial requirements
    initial_requirements = []
    if initial_file:
        initial_requirements, _ = selector.get_requirements_for_file(initial_file)
    
    # Determine initial output message
    if is_empty:
        initial_output = "📂 No processed PDFs found.\n\nPlease upload and process a PDF first using the '1. Process PDF' button above."
    elif not has_files:
        initial_output = "⚠️ No valid task files found.\n\nThe extractedFR folder exists but contains no valid JSON files."
    else:
        initial_output = "No tasks selected"
    
    # Dynamic title based on state
    if is_empty:
        title_text = "### 📋 Task Selector ⚠️ (Disabled - No PDFs Processed)"
    elif not has_files:
        title_text = "### 📋 Task Selector ⚠️ (Disabled - No Valid Files)"
    else:
        title_text = "### 📋 Task Selector"
    
    title_markdown = gr.Markdown(title_text)
    
    with gr.Row():
        with gr.Column(scale=3):
            # Refresh button to reload JSON files after PDF processing
            refresh_btn = gr.Button("🔄 Refresh Tasks", size="sm", interactive=has_files)
            
            # File selector dropdown
            file_dropdown = gr.Dropdown(
                choices=file_options,
                value=initial_file,
                label="📁 Select Processed PDF",
                interactive=has_files
            )
            
            # Requirements selector (checkboxes)
            requirements_selector = gr.CheckboxGroup(
                choices=initial_requirements,
                label="📝 Available Requirements",
                interactive=has_files
            )
            
            # Select/Deselect all buttons
            with gr.Row():
                select_all_btn = gr.Button("✅ Select All", size="sm", interactive=has_files)
                deselect_all_btn = gr.Button("❌ Deselect All", size="sm", interactive=has_files)
        
        with gr.Column(scale=2):
            # Output textbox showing all selected tasks
            selected_tasks_output = gr.Textbox(
                label="🎯 Selected Tasks Summary",
                value=initial_output,
                lines=10,
                interactive=False,
                max_lines=15
            )
    
    # Hidden output for storing selection status (used by parent component)
    selection_status = gr.Textbox(value="False", visible=False)
    
    # Event handlers
    refresh_btn.click(
        fn=refresh_files,
        outputs=[file_dropdown, requirements_selector, selected_tasks_output, refresh_btn, select_all_btn, deselect_all_btn, title_markdown]
    )
    
    file_dropdown.change(
        fn=update_requirements_list,
        inputs=[file_dropdown],
        outputs=[requirements_selector, gr.Textbox(visible=False)]  # Status not shown in integrated version
    )
    
    select_all_btn.click(
        fn=select_all_requirements,
        inputs=[file_dropdown],
        outputs=[requirements_selector]
    )
    
    deselect_all_btn.click(
        fn=deselect_all_requirements,
        outputs=[requirements_selector]
    )
    
    # Update selection status and output whenever requirements change
    requirements_selector.change(
        fn=update_selections_and_output,
        inputs=[file_dropdown, requirements_selector],
        outputs=[selection_status, selected_tasks_output]
    )
    
    return {
        'refresh_btn': refresh_btn,
        'file_dropdown': file_dropdown,
        'requirements_selector': requirements_selector,
        'select_all_btn': select_all_btn,
        'deselect_all_btn': deselect_all_btn,
        'selection_status': selection_status,
        'selected_tasks_output': selected_tasks_output,
        'title_markdown': title_markdown,
        'selector_instance': selector,
        'get_all_selections': get_all_selections,
        'create_tasks_json_file': create_tasks_json_file
    }

# For standalone testing
if __name__ == "__main__":
    with gr.Blocks(title="Task Selector") as demo:
        task_selector = create_task_selector()
        
        # Test output area
        output_text = gr.Textbox(
            label="🎯 Selection Status",
            lines=3,
            interactive=False
        )
        
        def show_selection_status(selected_file, selected_requirements):
            selector = TaskSelector()
            return selector.handle_requirement_selection(selected_file, selected_requirements)
        
        task_selector['requirements_selector'].change(
            fn=show_selection_status,
            inputs=[task_selector['file_dropdown'], task_selector['requirements_selector']],
            outputs=[output_text]
        )
    
    demo.launch(share=True, server_port=7862)
