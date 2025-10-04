#!/usr/bin/env python3
"""
Script to combine all step8 files into final output.
Run this after the pipeline has completed processing all PDFs and FRs.
"""

from core.pipeline import combine_all_step8_files

if __name__ == "__main__":
    print("Combining all step8 files into final output...")
    final_output_path = combine_all_step8_files()
    print(f"Done! Final output saved to: {final_output_path}")