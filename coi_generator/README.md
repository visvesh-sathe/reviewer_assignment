# Conflict of Interest (COI) Matrix Generator (`coi_generator`)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/visvesh-sathe/reviewer_assignment/blob/main/coi_generator/coi_generator.ipynb)

A self-contained Colab workflow and tool designed to extract author affiliations from submitted papers and evaluate institutional Conflicts of Interest (COI) against reviewer expertise.

Runs locally with **Ollama (`qwen2.5:7b`)** with **ZERO external API keys, logins, or cloud data transfers**.

---

## ⚠️ Important Colab Setting: T4 GPU Required
Before running the notebook in Google Colab, enable a free GPU:
> **Runtime -> Change runtime type -> T4 GPU** (Hardware accelerator: T4 GPU)

---

## 🦙 Why Use a Local LLM (`qwen2.5:7b`)?
Institutional affiliations in conference submissions often use abbreviations, acronyms, or alternate branch names:
- **Acronyms:** `UIUC` ↔ *University of Illinois Urbana-Champaign*, `MIT` ↔ *Massachusetts Institute of Technology*, `GT` ↔ *Georgia Institute of Technology*, `PKU` ↔ *Peking University*, `THU` ↔ *Tsinghua University*, `SNU` ↔ *Seoul National University*, `KAIST` ↔ *Korea Advanced Institute of Science and Technology*.
- **Campuses & Branches:** `UC Berkeley`, `UCSD`, `UCLA`, `CUHK-Shenzhen`.
- **Industry Labs & Subsidiaries:** `Intel Labs` ↔ *Intel Corporation*, `Samsung SAIT` ↔ *Samsung Electronics*, `Qualcomm AI Research` ↔ *Qualcomm*, `Avago` ↔ *Broadcom*.

Pure Python substring matching frequently misses these matches. By running `qwen2.5:7b` locally in Ollama on a T4 GPU, the workflow achieves high-accuracy institutional reasoning with complete privacy and zero API setup.

---

## 📋 The 5-Step Workflow

1. **Setup:** Installs Ollama, starts the background daemon, and pulls `qwen2.5:7b`.
2. **Step 1: Download Reviewer Expertise Template**
   - Downloads `cfg_reviewer_expertise.csv` so users have the required format for reviewer names, affiliations, and expertise.
3. **Step 2: Upload Edited Reviewer Expertise**
   - Uploads your populated `reviewer_expertise.csv` (or `cfg_reviewer_expertise.csv`) to `input_files/`.
4. **Step 3: Upload Submitted Paper Information**
   - Uploads your conference submission export `cfg_paper_info.csv` containing submitted paper IDs and author affiliations.
5. **Step 4: Extract & Scrub Paper Affiliations (Python Pre-Processing)**
   - Automatically parses `cfg_paper_info.csv` using the Python scrubber to strip author names and titles (preserving double-blind integrity) and generates `intermediate_files/paper_id_and_affiliations.csv`.
6. **Step 5: Run `affiliation-matcher` Skill & Download Deliverables**
   - Runs headlessly against the local Ollama server (`OPENAI_BASE_URL="http://localhost:11434/v1"`, `OPENAI_API_KEY="ollama"`, `--model qwen2.5:7b`) with auto-approved permissions:
     ```bash
     OPENAI_BASE_URL="http://localhost:11434/v1" OPENAI_API_KEY="ollama" agy -p "/affiliation-matcher" --model qwen2.5:7b --dangerously-skip-permissions
     ```
   - Generates the $N_{\text{papers}} \times N_{\text{reviewers}}$ binary matrix (`output_files/cfg_coi.csv`) and itemized audit report (`output_files/coi_report.txt`).
   - Automatically downloads `cfg_coi.csv` and `coi_report.txt` to your computer.

---

## 💻 Local CLI Execution
You can also run the tool standalone from terminal:

```bash
cd coi_generator

# Run full flow with local Ollama:
python3 coi_generation.py --base-url "http://localhost:11434/v1" --model "qwen2.5:7b"

# Pre-processing / scrubbing only:
python3 coi_generation.py --scrub-only --paper-info input_files/cfg_paper_info.csv
```
