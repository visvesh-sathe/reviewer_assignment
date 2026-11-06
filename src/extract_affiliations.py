"""Standalone script to extract paper affiliations and technical areas template dynamically using paths defined in a YAML configuration file."""

import argparse
import os
import sys
from pathlib import Path
import yaml

# Ensure src and project root are in sys.path
src_dir = Path(__file__).resolve().parent
project_root = src_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
if str(project_root) not in sys.path:
    sys.path.insert(1, str(project_root))

from reviewer_assignment.scrubber import AffiliationScrubber


def main():
    parser = argparse.ArgumentParser(
        description="Extract paper affiliations and technical areas template based on paths in a YAML config file."
    )
    parser.add_argument(
        "--config",
        "-c",
        default="input_files/config.yaml",
        help="Path to YAML configuration file (default: input_files/config.yaml)",
    )
    parser.add_argument(
        "--input",
        help="Override path to input paper info CSV (default: resolved from YAML config 'affiliations')",
    )
    parser.add_argument(
        "--output",
        help="Override path to write scrubbed affiliations CSV (default: resolved from YAML config 'paper_id_and_affiliations')",
    )
    parser.add_argument(
        "--output-technical-areas",
        "--output-areas",
        help="Override path to write paper technical areas CSV (default: resolved from YAML config 'paper_technical_areas')",
    )
    parser.add_argument(
        "--reviewer-expertise",
        help="Override path to reviewer expertise CSV (default: resolved from YAML config 'reviewer_expertise')",
    )
    parser.add_argument(
        "--blank",
        action="store_true",
        help="Leave technical area scores blank instead of pre-populating suggested scores based on paper titles",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute() and not config_path.exists() and (project_root / config_path).exists():
        config_path = project_root / config_path

    if not os.path.exists(config_path):
        print(f"Error: YAML configuration file not found at '{config_path}'", file=sys.stderr)
        sys.exit(1)

    print(f"Loading configuration from '{config_path}'...")
    try:
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Error parsing YAML config file '{config_path}': {e}", file=sys.stderr)
        sys.exit(1)

    input_dir_raw = cfg.get("input_files_dir", "input_files")
    output_dir_raw = cfg.get("output_files_dir", "output_files")

    input_dir = Path(input_dir_raw)
    if not input_dir.is_absolute() and not input_dir.exists() and (project_root / input_dir).exists():
        input_dir = project_root / input_dir

    output_dir = Path(output_dir_raw)
    if not output_dir.is_absolute() and not output_dir.exists() and (project_root / output_dir).exists():
        output_dir = project_root / output_dir

    files_cfg = cfg.get("files", {})

    # Derive default paths dynamically from YAML configuration
    aff_filename = files_cfg.get("paper_info", files_cfg.get("affiliations", "paper_info.csv"))
    exp_filename = files_cfg.get("reviewer_expertise", "reviewer_expertise.csv")
    scrub_filename = files_cfg.get("paper_id_and_affiliations", "paper_id_and_affiliations.csv")
    tech_filename = files_cfg.get("paper_technical_areas", "paper_technical_areas.csv")

    input_path = Path(args.input) if args.input else (input_dir / Path(aff_filename))
    reviewer_exp_path = Path(args.reviewer_expertise) if args.reviewer_expertise else (input_dir / Path(exp_filename))

    output_path = Path(args.output) if args.output else (output_dir / Path(scrub_filename))
    if not output_path.is_absolute() and not str(output_path).startswith(str(output_dir)):
        output_path = output_dir / output_path

    output_tech_areas_path = Path(args.output_technical_areas) if args.output_technical_areas else (output_dir / Path(tech_filename))
    if not output_tech_areas_path.is_absolute() and not str(output_tech_areas_path).startswith(str(output_dir)):
        output_tech_areas_path = output_dir / output_tech_areas_path

    if not os.path.exists(input_path):
        print(f"Error: Input paper info file not found at '{input_path}'", file=sys.stderr)
        sys.exit(1)

    os.makedirs(output_path.parent, exist_ok=True)
    os.makedirs(output_tech_areas_path.parent, exist_ok=True)

    print(f"Extracting affiliations from '{input_path}'...")
    try:
        AffiliationScrubber.scrub(str(input_path), str(output_path))
        print(f"Successfully extracted affiliations to '{output_path}'.")
    except Exception as e:
        print(f"Error extracting affiliations: {e}", file=sys.stderr)
        sys.exit(1)

    if os.path.exists(reviewer_exp_path):
        action_desc = "blank" if args.blank else "pre-populated (title-suggested)"
        print(f"Extracting {action_desc} paper technical areas from '{input_path}' and '{reviewer_exp_path}'...")
        try:
            AffiliationScrubber.extract_paper_technical_areas(
                str(input_path),
                str(reviewer_exp_path),
                str(output_tech_areas_path),
                prepopulate=not args.blank,
            )
            if not args.blank:
                print(f"Successfully generated pre-populated paper technical areas with suggested scores based on titles to '{output_tech_areas_path}'.")
                print("Users can review and override any suggested scores in this file before running the optimizer.")
            else:
                print(f"Successfully extracted blank paper technical areas template to '{output_tech_areas_path}'.")
        except Exception as e:
            print(f"Error extracting paper technical areas: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Warning: Reviewer expertise file not found at '{reviewer_exp_path}'. Skipping technical areas extraction.", file=sys.stderr)


if __name__ == "__main__":
    main()



