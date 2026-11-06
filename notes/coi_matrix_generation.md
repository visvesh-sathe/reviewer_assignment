<!-- The objective of this md file is to work with a foundation model to identify conflicts of interest in reviewering papers-->

# What is a conflict of interest
* Any reviewer whose affiliation matches with that of at least one of the authors of a paper has a conflict of interest
* Nothing else (like competing institutions/companies) counts
* Remember though, that you're not looking for a pattern match. The same Institution can be named differently enough
to not allow a simple regexp search to suffice. For instance Korea Advanced Institute of Science and Technology and KAIST
are the same entity. Integrated Electronics, Intel and Intel Inc. are all the same. 
* If you think there **may** be a coi, flag it and bring it to the users attention and ask for feedback before proceeding.

# Step 1: Read the paper/author/affiliation file
 * There is a file that contains paper IDs, and affiliations produced by the extract_affiliations script
 * Take that file, along with the reviewer_expertise.csv file and identify conflicts of interest as defined above.
 * Produce a detailed report of these conflicts with justification of why they are conflicts. Either in a report file if using CLI, or just on prompt if using web browser.
 * Produce a coi matrix with rows of papers and columns of reviewers with a "1" for wherever there's a conflict. If on browser print that matrix for copy-paste. If on CLI, produce a file called coi.csv and put it in the output_files. 
 * Remind the user it's his/her job to move that file into input_files for future use by the reviewer_assignment setup.