"""
COI Generation Flow (Colab/Interactive Form Wrapper)
Generates the Conflict of Interest (COI) matrix template based on paper and reviewer affiliations.
Outputs 'cfg_template_coi.csv' which can be downloaded, modified, and re-uploaded as 'cfg_coi.csv'.
"""

import sys
import os
from pathlib import Path

# Setup paths to ensure we can import the src modules
current_dir = Path(__file__).resolve().parent
repo_root = current_dir.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
if str(repo_root / "src") not in sys.path:
    sys.path.insert(0, str(repo_root / "src"))

from reviewer_assignment.scrubber import AffiliationScrubber
from generate_coi_matrix import generate_coi

def main():
    print("=====================================================")
    print("        Step 1: COI Matrix Generation Flow           ")
    print("=====================================================\n")
    
    # Files
    paper_info_path = "cfg_paper_info.csv"
    reviewer_exp_path = "cfg_reviewer_expertise.csv"
    
    os.makedirs("outputs/intermediate_data", exist_ok=True)
    scrubbed_affiliations_path = "outputs/intermediate_data/paper_id_and_affiliations.csv"
    
    coi_template_path = "cfg_template_coi.csv"
    report_path = "outputs/coi_report.txt"
    
    if not os.path.exists(paper_info_path) or not os.path.exists(reviewer_exp_path):
        print("Error: Missing required input files.")
        print(f"Ensure '{paper_info_path}' and '{reviewer_exp_path}' exist in the current directory.")
        sys.exit(1)
        
    print(f"-> Scrubbing affiliations from '{paper_info_path}'...")
    try:
        AffiliationScrubber.scrub(paper_info_path, scrubbed_affiliations_path)
    except Exception as e:
        print(f"Error scrubbing affiliations: {e}")
        sys.exit(1)
        
    print(f"\n-> Generating COI Template from '{scrubbed_affiliations_path}' & '{reviewer_exp_path}'...")
    try:
        generate_coi(
            affiliations_path=scrubbed_affiliations_path,
            reviewer_exp_path=reviewer_exp_path,
            output_coi_path=coi_template_path,
            report_output_path=report_path
        )
    except Exception as e:
        print(f"Error generating COI matrix: {e}")
        sys.exit(1)
        
    print("\n=====================================================")
    print("SUCCESS: COI matrix generation complete.")
    print(f"Action Required: Please download '{coi_template_path}'.")
    print("                 Modify it to confirm or reject conflicts.")
    print("                 Re-upload it to this directory as 'cfg_coi.csv'.")
    print("                 Then, proceed to run the Reviewer Allocation flow.")
    print("=====================================================")

if __name__ == "__main__":
    main()
