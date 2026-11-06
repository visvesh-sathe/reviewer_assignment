"""Scrubber for paper affiliation files."""

import pandas as pd
import re

class AffiliationScrubber:
    """Reads paper affiliations, scrubs names and titles, and writes the results to a CSV."""

    @staticmethod
    def scrub(input_path: str, output_path: str = "output_files/paper_id_and_affiliations.csv") -> pd.DataFrame:
        """Scrubs the affiliations to retain only paper ID and affiliation names.

        Args:
            input_path: Path to the input affiliations CSV file.
            output_path: Path to write the scrubbed affiliations CSV file.

        Returns:
            A pandas DataFrame with columns 'paper_id' and 'affiliations'.
        """
        # Read the raw CSV file with a robust encoding
        try:
            df_full = pd.read_csv(input_path, encoding="utf-8")
        except UnicodeDecodeError:
            df_full = pd.read_csv(input_path, encoding="iso-8859-1")
            
        cols_lower = [str(c).strip().lower() for c in df_full.columns]
        
        # Find paper_id column
        pid_col_orig = None
        for c, cl in zip(df_full.columns, cols_lower):
            if cl in ["paper_id", "paperid", "id", "paper id"]:
                pid_col_orig = c
                break
        if not pid_col_orig:
            pid_col_orig = df_full.columns[0] # Fallback
            
        # Find all affiliation columns
        aff_cols = [c for c, cl in zip(df_full.columns, cols_lower) if "affiliation" in cl]
        
        # Build the scrubbed dataframe
        df = pd.DataFrame()
        df["paper_id"] = df_full[pid_col_orig]
        
        # Combine all affiliations into one semicolon-separated string
        def combine_affs(row):
            affs = []
            for col in aff_cols:
                val = row[col]
                if pd.notna(val) and str(val).strip():
                    affs.append(str(val).strip())
            return "; ".join(affs)
            
        df["affiliations"] = df_full.apply(combine_affs, axis=1)

        # Save to output path
        import os
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        df.to_csv(output_path, index=False)
        return df

    @staticmethod
    def extract_paper_technical_areas(input_path: str, reviewer_exp_path: str, output_path: str, prepopulate: bool = True):
        pass
