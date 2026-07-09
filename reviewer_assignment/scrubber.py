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
        # Read the raw CSV file
        df = pd.read_csv(input_path, usecols=lambda x: re.search("affiliation|paper_id", x))

        # Clean up whitespace and format consistently
        df["affiliations"] = df["affiliations"].apply(
            lambda x: "; ".join(
                [aff.strip() for aff in str(x).split(";") if aff.strip()]
            )
        )

        # Save to output path
        df.to_csv(output_path, index=False)
        return df
