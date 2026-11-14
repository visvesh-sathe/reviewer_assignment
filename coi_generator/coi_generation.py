"""
Standalone COI Generator & Affiliation Scrubber
Part of the coi_generator Colab standalone package.

Features:
1. Affiliation Scrubber: Extracts double-blind paper_id and institutions from submitted paper_info.csv.
2. Local Ollama (qwen2.5:7b) Evaluator: Runs locally against http://localhost:11434/v1 with zero API keys or logins.
3. Gemini-Powered COI Evaluator: Optional cloud evaluation if GEMINI_API_KEY is provided.
4. Heuristic Fallback: String matching fallback if offline without Ollama or API key.
5. COI Matrix & Audit Report Builder: Generates cfg_coi.csv and coi_report.txt.
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path
import pandas as pd


# =====================================================================
# 1. Double-Blind Affiliation Scrubber (Python Pre-Processing)
# =====================================================================

def scrub_affiliations(
    paper_info_path: str,
    output_path: str = "intermediate_files/paper_id_and_affiliations.csv"
) -> pd.DataFrame:
    """
    Scrubs submitted paper_info.csv to extract only paper_id and unique institutional affiliations.
    Removes author names and paper titles to preserve double-blind reviewing integrity.
    """
    if not os.path.exists(paper_info_path):
        raise FileNotFoundError(f"Input file not found: {paper_info_path}")

    # Read with robust encoding fallback
    try:
        df_full = pd.read_csv(paper_info_path, encoding="utf-8")
    except UnicodeDecodeError:
        df_full = pd.read_csv(paper_info_path, encoding="iso-8859-1")

    cols_lower = [str(c).strip().lower() for c in df_full.columns]

    # Resolve Paper ID column
    pid_col = None
    for c, cl in zip(df_full.columns, cols_lower):
        if cl in ["paper_id", "paperid", "id", "paper id"]:
            pid_col = c
            break
    if not pid_col:
        pid_col = df_full.columns[0]

    # Find all affiliation columns
    aff_cols = [c for c, cl in zip(df_full.columns, cols_lower) if "affiliation" in cl]

    # Filter out generic role placeholders
    GENERIC_WORDS = {"student", "professor", "postdoc", "phd", "engineer", "unknown", "n/a", "none", "na", ""}

    def combine_and_dedup_affs(row):
        unique_affs = []
        seen = set()
        for col in aff_cols:
            val = row[col]
            if pd.notna(val):
                aff_clean = str(val).strip()
                aff_norm = aff_clean.lower()
                if aff_clean and aff_norm not in GENERIC_WORDS and aff_norm not in seen:
                    unique_affs.append(aff_clean)
                    seen.add(aff_norm)
        return "; ".join(unique_affs)

    df_scrubbed = pd.DataFrame()
    df_scrubbed["paper_id"] = df_full[pid_col].astype(int)
    df_scrubbed["affiliations"] = df_full.apply(combine_and_dedup_affs, axis=1)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    df_scrubbed.to_csv(output_path, index=False)
    print(f"✅ Scrubbed {len(df_scrubbed)} papers from '{paper_info_path}' -> '{output_path}'")
    return df_scrubbed


# =====================================================================
# 2. Local Ollama (qwen2.5:7b) Evaluator (Zero API Keys / Logins)
# =====================================================================

def evaluate_coi_with_ollama(
    paper_affiliations_path: str,
    reviewer_exp_path: str,
    base_url: str = "http://localhost:11434/v1",
    model: str = "qwen2.5:7b"
) -> list:
    """
    Evaluates institutional Conflicts of Interest using a local Ollama server running qwen2.5:7b.
    Uses the OpenAI-compatible /chat/completions endpoint with zero API keys or logins required.
    Understands institutional acronyms (UIUC, MIT, PKU, THU, GT, UCB, UCSD, etc.),
    corporate subsidiaries, research centers (IMEC, SAIT, Intel Labs), and university branches.
    """
    df_aff = pd.read_csv(paper_affiliations_path, encoding="utf-8", encoding_errors="replace")
    df_exp = pd.read_csv(reviewer_exp_path, encoding="utf-8", encoding_errors="replace")

    pid_col = "paper_id" if "paper_id" in df_aff.columns else df_aff.columns[0]
    aff_col = "affiliations" if "affiliations" in df_aff.columns else df_aff.columns[1]

    cols_exp_lower = [str(c).strip().lower() for c in df_exp.columns]
    fname_col = next((c for c, cl in zip(df_exp.columns, cols_exp_lower) if cl in ["firstname", "first_name", "first name"]), df_exp.columns[0])
    lname_col = next((c for c, cl in zip(df_exp.columns, cols_exp_lower) if cl in ["lastname", "last_name", "last name"]), df_exp.columns[1])
    rev_aff_col = next((c for c, cl in zip(df_exp.columns, cols_exp_lower) if "affiliation" in cl), None)

    df_exp["reviewer_name"] = (
        df_exp[fname_col].astype(str).str.strip() + " " + df_exp[lname_col].astype(str).str.strip()
    ).str.strip()

    reviewers_data = []
    for _, r in df_exp.iterrows():
        r_name = r["reviewer_name"]
        r_aff = str(r[rev_aff_col]).strip() if rev_aff_col and pd.notna(r[rev_aff_col]) else ""
        reviewers_data.append({"reviewer": r_name, "affiliation": r_aff})

    papers_data = []
    for _, p in df_aff.iterrows():
        p_id = int(p[pid_col])
        p_affs_raw = str(p[aff_col]) if pd.notna(p[aff_col]) else ""
        raw_paper_affs = [a.strip() for a in p_affs_raw.split(";") if a.strip()]
        papers_data.append({"paper_id": p_id, "affiliations": raw_paper_affs})

    system_instruction = (
        "You are an expert academic peer-review Conflict of Interest (COI) evaluator. "
        "Analyze the list of reviewers and the list of papers. "
        "Determine every case where a reviewer has an institutional Conflict of Interest with ANY author affiliation of a paper.\n\n"
        "CRITICAL RULES:\n"
        "1. Intelligently match institutional abbreviations, acronyms, and common aliases. For example:\n"
        "   - MIT = Massachusetts Institute of Technology\n"
        "   - GT / Georgia Tech = Georgia Institute of Technology\n"
        "   - UIUC = University of Illinois Urbana-Champaign\n"
        "   - PKU = Peking University\n"
        "   - THU = Tsinghua University\n"
        "   - SNU = Seoul National University\n"
        "   - KAIST = Korea Advanced Institute of Science and Technology\n"
        "   - UCB / UC Berkeley = University of California, Berkeley\n"
        "   - UCSD = University of California, San Diego\n"
        "   - UCLA = University of California, Los Angeles\n"
        "   - Intel = Intel Corporation = Intel Labs\n"
        "   - NVIDIA = Nvidia Corporation\n"
        "   - Samsung = Samsung Electronics = Samsung Advanced Institute of Technology (SAIT)\n"
        "   - Qualcomm = Qualcomm Incorporated = Qualcomm AI Research\n"
        "   - IBM = IBM Research\n"
        "   - IMEC = Interuniversity Microelectronics Centre\n"
        "   - Broadcom = Broadcom Inc. = Avago\n"
        "   - Notre Dame = University of Notre Dame\n"
        "   - SJTU = Shanghai Jiao Tong University\n"
        "   - SKKU = Sungkyunkwan University\n"
        "2. Disregard non-institutional placeholder strings like 'Student', 'Professor', 'Engineer', 'Unknown', 'N/A'.\n"
        "3. Output MUST be a valid JSON array of objects with the exact schema:\n"
        "[\n"
        "  {\n"
        "    \"paper_id\": 27,\n"
        "    \"reviewer\": \"Ashwin Lele\",\n"
        "    \"reviewer_affiliation\": \"Georgia Institute Of Technology\",\n"
        "    \"matched_paper_affiliation\": \"Georgia Tech\",\n"
        "    \"reason\": \"Institutional match between Georgia Institute Of Technology and Georgia Tech\"\n"
        "  }\n"
        "]\n"
        "Return ONLY the raw JSON array (no markdown code blocks, no other text). If there are no conflicts, return []."
    )

    # Process in manageable batches of 25 papers to fit context and maintain high quality
    BATCH_SIZE = 25
    all_conflicts = []

    clean_base = base_url.rstrip("/")
    api_endpoint = f"{clean_base}/chat/completions"

    print(f"🦙 Querying local Ollama server at {api_endpoint} (model: {model})...")

    for i in range(0, len(papers_data), BATCH_SIZE):
        batch_papers = papers_data[i:i + BATCH_SIZE]
        batch_prompt = {
            "reviewers": reviewers_data,
            "papers": batch_papers
        }

        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Analyze these papers and reviewers for institutional conflicts:\n{json.dumps(batch_prompt)}"}
            ],
            "temperature": 0.0
        }

        req = urllib.request.Request(
            api_endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": "Bearer ollama"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                content = res_data["choices"][0]["message"]["content"].strip()
                # Strip markdown code blocks if model wrapped output in ```json ... ```
                if content.startswith("```"):
                    content = content.strip("`")
                    if content.startswith("json"):
                        content = content[4:].strip()
                batch_conflicts = json.loads(content)
                all_conflicts.extend(batch_conflicts)
                print(f"   • Batch {i // BATCH_SIZE + 1}/{(len(papers_data) - 1) // BATCH_SIZE + 1}: detected {len(batch_conflicts)} conflicts")
        except Exception as e:
            print(f"⚠️ Ollama request failed for batch {i // BATCH_SIZE + 1}: {e}")
            print("🔄 Falling back to heuristic rule-based matcher for this batch...")
            # Run fallback for this batch
            temp_df = df_aff.iloc[i:i + BATCH_SIZE]
            temp_path = "intermediate_files/_temp_aff.csv"
            temp_df.to_csv(temp_path, index=False)
            fb_conflicts = evaluate_coi_heuristic(temp_path, reviewer_exp_path)
            all_conflicts.extend(fb_conflicts)
            if os.path.exists(temp_path):
                os.remove(temp_path)

    print(f"🦙 Ollama ({model}) evaluation complete: {len(all_conflicts)} total conflicts detected.")
    return all_conflicts


# =====================================================================
# 3. Heuristic (Fuzzy / Substring) Matcher (Fallback)
# =====================================================================

def evaluate_coi_heuristic(
    paper_affiliations_path: str,
    reviewer_exp_path: str
) -> list:
    """
    Rule-based COI matcher using string normalization and partial substring matching.
    """
    df_aff = pd.read_csv(paper_affiliations_path, encoding="utf-8", encoding_errors="replace")
    df_exp = pd.read_csv(reviewer_exp_path, encoding="utf-8", encoding_errors="replace")

    pid_col = "paper_id" if "paper_id" in df_aff.columns else df_aff.columns[0]
    aff_col = "affiliations" if "affiliations" in df_aff.columns else df_aff.columns[1]

    cols_exp_lower = [str(c).strip().lower() for c in df_exp.columns]
    fname_col = next((c for c, cl in zip(df_exp.columns, cols_exp_lower) if cl in ["firstname", "first_name", "first name"]), df_exp.columns[0])
    lname_col = next((c for c, cl in zip(df_exp.columns, cols_exp_lower) if cl in ["lastname", "last_name", "last name"]), df_exp.columns[1])
    rev_aff_col = next((c for c, cl in zip(df_exp.columns, cols_exp_lower) if "affiliation" in cl), None)

    df_exp["reviewer_name"] = (
        df_exp[fname_col].astype(str).str.strip() + " " + df_exp[lname_col].astype(str).str.strip()
    ).str.strip()

    conflicts = []
    for _, p_row in df_aff.iterrows():
        p_id = int(p_row[pid_col])
        p_affs_raw = str(p_row[aff_col]) if pd.notna(p_row[aff_col]) else ""
        raw_paper_affs = [a.strip() for a in p_affs_raw.split(";") if a.strip()]

        for _, r_row in df_exp.iterrows():
            r_name = r_row["reviewer_name"]
            r_aff = str(r_row[rev_aff_col]).strip() if rev_aff_col and pd.notna(r_row[rev_aff_col]) else ""
            if not r_aff:
                continue

            r_aff_norm = r_aff.lower()
            for p_aff in raw_paper_affs:
                p_aff_norm = p_aff.lower()
                if (r_aff_norm == p_aff_norm) or \
                   (len(r_aff_norm) > 3 and r_aff_norm in p_aff_norm) or \
                   (len(p_aff_norm) > 3 and p_aff_norm in r_aff_norm):
                    conflicts.append({
                        "paper_id": p_id,
                        "reviewer": r_name,
                        "reviewer_affiliation": r_aff,
                        "matched_paper_affiliation": p_aff,
                        "reason": f"Substring / heuristic match: '{r_aff}' matches '{p_aff}'"
                    })
                    break

    return conflicts


# =====================================================================
# 4. Gemini-Powered COI Evaluator (Optional Cloud Alternative)
# =====================================================================

def evaluate_coi_with_gemini(
    paper_affiliations_path: str,
    reviewer_exp_path: str,
    api_key: str,
    model: str = "gemini-2.5-flash"
) -> list:
    """Optional cloud evaluation using Google Gemini if an API key is provided."""
    df_aff = pd.read_csv(paper_affiliations_path, encoding="utf-8", encoding_errors="replace")
    df_exp = pd.read_csv(reviewer_exp_path, encoding="utf-8", encoding_errors="replace")

    pid_col = "paper_id" if "paper_id" in df_aff.columns else df_aff.columns[0]
    aff_col = "affiliations" if "affiliations" in df_aff.columns else df_aff.columns[1]

    cols_exp_lower = [str(c).strip().lower() for c in df_exp.columns]
    fname_col = next((c for c, cl in zip(df_exp.columns, cols_exp_lower) if cl in ["firstname", "first_name", "first name"]), df_exp.columns[0])
    lname_col = next((c for c, cl in zip(df_exp.columns, cols_exp_lower) if cl in ["lastname", "last_name", "last name"]), df_exp.columns[1])
    rev_aff_col = next((c for c, cl in zip(df_exp.columns, cols_exp_lower) if "affiliation" in cl), None)

    df_exp["reviewer_name"] = (
        df_exp[fname_col].astype(str).str.strip() + " " + df_exp[lname_col].astype(str).str.strip()
    ).str.strip()

    reviewers_data = []
    for _, r in df_exp.iterrows():
        r_name = r["reviewer_name"]
        r_aff = str(r[rev_aff_col]).strip() if rev_aff_col and pd.notna(r[rev_aff_col]) else ""
        reviewers_data.append({"reviewer": r_name, "affiliation": r_aff})

    papers_data = []
    for _, p in df_aff.iterrows():
        p_id = int(p[pid_col])
        p_affs_raw = str(p[aff_col]) if pd.notna(p[aff_col]) else ""
        raw_paper_affs = [a.strip() for a in p_affs_raw.split(";") if a.strip()]
        papers_data.append({"paper_id": p_id, "affiliations": raw_paper_affs})

    prompt_payload = {"reviewers": reviewers_data, "papers": papers_data}

    system_instruction = (
        "You are an expert academic peer-review Conflict of Interest (COI) evaluator. "
        "Analyze reviewers and papers. Output a valid JSON array of conflicts matching institutional abbreviations."
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = {
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"parts": [{"text": json.dumps(prompt_payload)}]}],
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0.0}
    }

    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            candidate = res_data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(candidate)
    except Exception as e:
        print(f"⚠️ Gemini request error: {e}. Falling back to heuristic matching...")
        return evaluate_coi_heuristic(paper_affiliations_path, reviewer_exp_path)


# =====================================================================
# 5. COI Matrix and Audit Report Generation
# =====================================================================

def build_coi_matrix_and_report(
    conflicts: list,
    paper_affiliations_path: str,
    reviewer_exp_path: str,
    output_coi_path: str = "output_files/cfg_coi.csv",
    report_path: str = "output_files/coi_report.txt",
    editable_coi_path: str = None
) -> pd.DataFrame:
    """
    Constructs the binary COI matrix (rows = papers, cols = reviewers, 1 = conflict, 0 = none)
    and formats a detailed audit report.
    """
    df_aff = pd.read_csv(paper_affiliations_path, encoding="utf-8", encoding_errors="replace")
    df_exp = pd.read_csv(reviewer_exp_path, encoding="utf-8", encoding_errors="replace")

    pid_col = "paper_id" if "paper_id" in df_aff.columns else df_aff.columns[0]
    cols_exp_lower = [str(c).strip().lower() for c in df_exp.columns]
    fname_col = next((c for c, cl in zip(df_exp.columns, cols_exp_lower) if cl in ["firstname", "first_name", "first name"]), df_exp.columns[0])
    lname_col = next((c for c, cl in zip(df_exp.columns, cols_exp_lower) if cl in ["lastname", "last_name", "last name"]), df_exp.columns[1])
    rev_aff_col = next((c for c, cl in zip(df_exp.columns, cols_exp_lower) if "affiliation" in cl), None)

    df_exp["reviewer_name"] = (
        df_exp[fname_col].astype(str).str.strip() + " " + df_exp[lname_col].astype(str).str.strip()
    ).str.strip()

    paper_ids = [int(p) for p in df_aff[pid_col].tolist()]
    reviewer_names = df_exp["reviewer_name"].tolist()

    # Build empty matrix (0s)
    coi_df = pd.DataFrame(0, index=paper_ids, columns=reviewer_names)
    coi_df.index.name = "paper_id"

    # Populate 1s for conflicts
    conflict_map = {}
    for c in conflicts:
        p_id = int(c.get("paper_id"))
        r_name = str(c.get("reviewer")).strip()
        if p_id in coi_df.index and r_name in coi_df.columns:
            coi_df.loc[p_id, r_name] = 1
            if p_id not in conflict_map:
                conflict_map[p_id] = []
            conflict_map[p_id].append(c)

    total_conflicts = (coi_df == 1).sum().sum()

    # Save CSVs
    os.makedirs(os.path.dirname(os.path.abspath(output_coi_path)), exist_ok=True)
    coi_df.to_csv(output_coi_path)
    print(f"💾 Saved binary COI matrix ({len(paper_ids)} papers x {len(reviewer_names)} reviewers) -> '{output_coi_path}'")

    if editable_coi_path:
        os.makedirs(os.path.dirname(os.path.abspath(editable_coi_path)), exist_ok=True)
        coi_df.to_csv(editable_coi_path)
        print(f"💾 Saved editable copy -> '{editable_coi_path}'")

    # Generate Audit Report
    os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=====================================================\n")
        f.write("   CONFLICT OF INTEREST (COI) AUDIT REPORT           \n")
        f.write("=====================================================\n\n")
        f.write(f"Total Papers: {len(paper_ids)}\n")
        f.write(f"Total Reviewers: {len(reviewer_names)}\n")
        f.write(f"Total Institutional Conflicts Detected: {total_conflicts}\n\n")

        f.write("--- Reviewer Conflict Summary ---\n")
        for r_name in reviewer_names:
            c_count = int(coi_df[r_name].sum())
            r_aff = ""
            for _, r in df_exp.iterrows():
                if r["reviewer_name"] == r_name and rev_aff_col:
                    r_aff = str(r[rev_aff_col])
                    break
            f.write(f"  • {r_name} ({r_aff}): {c_count} conflicts\n")

        f.write("\n--- Itemized Conflict Details ---\n")
        if not conflict_map:
            f.write("No institutional conflicts detected.\n")
        else:
            for p_id in sorted(conflict_map.keys()):
                f.write(f"\nPaper {p_id}:\n")
                for c in conflict_map[p_id]:
                    f.write(f"  - Reviewer: {c.get('reviewer')} [{c.get('reviewer_affiliation', '')}]\n")
                    f.write(f"    Matched:  {c.get('matched_paper_affiliation', '')}\n")
                    if c.get("reason"):
                        f.write(f"    Reason:   {c.get('reason')}\n")

    print(f"📄 Saved COI audit report -> '{report_path}'")
    return coi_df


# =====================================================================
# 6. CLI Flow
# =====================================================================

def main():
    parser = argparse.ArgumentParser(description="Standalone COI Generation and Affiliation Scrubber Tool.")
    parser.add_argument("--paper-info", default="input_files/cfg_paper_info.csv", help="Path to input paper info CSV")
    parser.add_argument("--reviewer-exp", default="input_files/cfg_reviewer_expertise.csv", help="Path to reviewer expertise CSV")
    parser.add_argument("--scrub-output", default="intermediate_files/paper_id_and_affiliations.csv", help="Path to save scrubbed affiliations")
    parser.add_argument("--output-coi", default="output_files/cfg_coi.csv", help="Path to save generated COI matrix")
    parser.add_argument("--editable-coi", default="input_files/cfg_coi.csv", help="Path to save editable copy of COI matrix")
    parser.add_argument("--report-output", default="output_files/coi_report.txt", help="Path to save audit report")
    parser.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1"), help="Ollama / OpenAI base URL")
    parser.add_argument("--model", default="qwen2.5:7b", help="Model name (default: qwen2.5:7b)")
    parser.add_argument("--api-key", default=os.environ.get("GEMINI_API_KEY"), help="Optional Gemini API key")
    parser.add_argument("--use-ollama", action="store_true", default=True, help="Use local Ollama server (default: True)")
    parser.add_argument("--scrub-only", action="store_true", help="Only run affiliation scrubbing")
    parser.add_argument("--coi-only", action="store_true", help="Only run COI matrix generation")

    args = parser.parse_args()

    # Step 1: Pre-processing / Scrubbing
    if not args.coi_only:
        print("\n--- Running Affiliation Scrubber (Python Pre-Processing) ---")
        scrub_affiliations(args.paper_info, args.scrub_output)
        if args.scrub_only:
            return

    # Step 2: COI Generation
    print("\n--- Running Conflict of Interest (COI) Evaluator ---")
    conflicts = []
    # Check if Ollama is accessible
    ollama_ready = False
    try:
        urllib.request.urlopen("http://localhost:11434/api/version", timeout=2)
        ollama_ready = True
    except Exception:
        ollama_ready = False

    if ollama_ready and args.use_ollama:
        print(f"🦙 Connecting to local Ollama server at {args.base_url} (model: {args.model})...")
        conflicts = evaluate_coi_with_ollama(
            args.scrub_output,
            args.reviewer_exp,
            base_url=args.base_url,
            model=args.model
        )
    elif args.api_key:
        print(f"Using Cloud Gemini Model: gemini-2.5-flash")
        conflicts = evaluate_coi_with_gemini(
            args.scrub_output,
            args.reviewer_exp,
            api_key=args.api_key,
            model="gemini-2.5-flash"
        )
    else:
        print("ℹ️ Local Ollama not detected and no API key provided. Using rule-based heuristic matcher...")
        conflicts = evaluate_coi_heuristic(args.scrub_output, args.reviewer_exp)

    build_coi_matrix_and_report(
        conflicts,
        args.scrub_output,
        args.reviewer_exp,
        output_coi_path=args.output_coi,
        report_path=args.report_output,
        editable_coi_path=args.editable_coi
    )
    print("\n✅ COI Generation flow completed successfully!")


if __name__ == "__main__":
    main()
