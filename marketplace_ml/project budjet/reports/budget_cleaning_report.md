# Budget Cleaning Report

## Original vs final shape
- Original rows: 63950
- Original columns: 41
- Final rows: 20042
- Final columns: 45

## Missing values
- Missing before: {'Job Title': 2, 'Job_URL': 1, 'EX_level_demand': 7015, 'Time_Limitation': 40916, 'Search_Keyword': 1, 'Posted_from': 37, 'Description': 2, 'Category1_URL_search': 445, 'Category_1': 445, 'highlight': 13819, 'Category2_URL_search': 4061, 'Category_2': 4061, 'Category3_URL_search': 8953, 'Category_3': 8953, 'Category4_URL_search': 16407, 'Category_4': 16407, 'Category5_URL_search': 24372, 'Category_5': 24372, 'Category6_URL_search': 32643, 'Category_6': 32643, 'Category7_URL_search': 38758, 'Category_7': 38758, 'Category8_URL_search': 43514, 'Category_8': 43514, 'Category9_URL_search': 47469, 'Category_9': 47469, 'Applicants_Num': 1, 'Payment_Situation': 1, 'Enterprise_Client': 63897, 'Freelancers_Num': 0, 'Spent($)': 1646, 'Client_Country': 125, 'Connects_Num': 1, 'New_Connects_Num': 1, 'Rating': 33357, 'Feedback_Num': 1, 'Payment_type': 1, 'Job_Cost': 43837, 'Hourly_Rate': 37380, 'Start_rate': 1, 'End_rate': 37987}
- Missing after: {'Job Title': 0, 'Job_URL': 0, 'EX_level_demand': 0, 'Time_Limitation': 0, 'Search_Keyword': 0, 'Posted_from': 0, 'Description': 0, 'Category1_URL_search': 179, 'Category_1': 0, 'highlight': 5087, 'Category2_URL_search': 1497, 'Category_2': 0, 'Category3_URL_search': 3295, 'Category_3': 0, 'Category4_URL_search': 5981, 'Category_4': 0, 'Category5_URL_search': 8857, 'Category_5': 0, 'Category6_URL_search': 11642, 'Category_6': 0, 'Category7_URL_search': 13684, 'Category_7': 0, 'Category8_URL_search': 15226, 'Category_8': 0, 'Category9_URL_search': 16386, 'Category_9': 0, 'Applicants_Num': 0, 'Payment_Situation': 0, 'Enterprise_Client': 20030, 'Freelancers_Num': 0, 'Spent($)': 449, 'Client_Country': 0, 'Connects_Num': 0, 'New_Connects_Num': 0, 'Rating': 9901, 'Feedback_Num': 0, 'Payment_type': 0, 'Job_Cost': 0, 'Hourly_Rate': 20042, 'Start_rate': 0, 'End_rate': 20042, 'category_text': 0, 'Job_Cost_clean': 0, 'target': 0, 'project_text': 0}

## Duplicate rows
- Before cleaning: 169
- After cleaning: 0

## Transformations applied
- parsed the target currency string into numeric dollars
- removed exact duplicates
- cleaned title/description whitespace and combined them with listed categories
- imputed missing categories and fit one-hot/TF-IDF transformations on training data
- excluded missing/non-positive and greater-than-$1,000,000 target values

## Exclusions
- Rows removed because target budget was missing or invalid: 43739
- Reason: project budget could not be used as a valid supervised label.
- Post-listing outcome fields (realized spending, applicant counts, ratings and feedback) are deliberately excluded from model inputs.

## Decision rationale
`Job_Cost` is the clearest available budget label. The models use listing-time information only; `Spent($)`, applicant/freelancer counts, ratings and feedback are excluded to avoid target leakage.
