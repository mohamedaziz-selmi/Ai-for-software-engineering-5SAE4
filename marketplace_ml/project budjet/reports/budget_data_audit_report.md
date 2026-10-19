# Project Budget Data Audit Report

## Source
- File: `C:\Users\ihebb\Downloads\ai\project budjet\dataset\Final_Upwork_Dataset.csv`
- Rows: 63950
- Columns: 41

## Duplicate and missing values
- Exact duplicate rows: 169
- Target missing values before cleaning: 43837
- Rows excluded for invalid or missing `Job_Cost`: 43739

## Final dataset
- Final rows: 20042
- Final columns: 45
- Missing values in final set: {'Job Title': 0, 'Job_URL': 0, 'EX_level_demand': 0, 'Time_Limitation': 0, 'Search_Keyword': 0, 'Posted_from': 0, 'Description': 0, 'Category1_URL_search': 179, 'Category_1': 0, 'highlight': 5087, 'Category2_URL_search': 1497, 'Category_2': 0, 'Category3_URL_search': 3295, 'Category_3': 0, 'Category4_URL_search': 5981, 'Category_4': 0, 'Category5_URL_search': 8857, 'Category_5': 0, 'Category6_URL_search': 11642, 'Category_6': 0, 'Category7_URL_search': 13684, 'Category_7': 0, 'Category8_URL_search': 15226, 'Category_8': 0, 'Category9_URL_search': 16386, 'Category_9': 0, 'Applicants_Num': 0, 'Payment_Situation': 0, 'Enterprise_Client': 20030, 'Freelancers_Num': 0, 'Spent($)': 449, 'Client_Country': 0, 'Connects_Num': 0, 'New_Connects_Num': 0, 'Rating': 9901, 'Feedback_Num': 0, 'Payment_type': 0, 'Job_Cost': 0, 'Hourly_Rate': 20042, 'Start_rate': 0, 'End_rate': 20042, 'category_text': 0, 'Job_Cost_clean': 0, 'target': 0, 'project_text': 0}

## Cleaning decisions
1. Drop exact duplicate records.
2. Parse `Job_Cost` as currency values and remove invalid/missing/non-positive values or values above $1,000,000.
3. Keep only budget labels that represent actual job budgets; exclude rows with missing or impossible values.
4. Impute missing categorical inputs and fit a TF-IDF transform on training text only.
5. Exclude post-listing outcomes (spend, applicant/freelancer counts, ratings, and feedback) to reduce leakage.
6. Train against `log1p(Job_Cost)` and convert predictions back to dollars.

## Model metrics
- RandomForest: MAE=2711.77, RMSE=37534.05, R2=0.0041
- XGBoost: MAE=2666.17, RMSE=37487.02, R2=0.0066
