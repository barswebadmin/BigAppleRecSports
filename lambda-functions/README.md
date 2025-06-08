# Lambda Functions Directory

This directory contains 5 Python Lambda functions that are automatically deployed to AWS via GitHub Actions.

## Functions

1. **changePricesOfOpenAndWaitlistVariants**
2. **createScheduledPriceChanges**
3. **CreateScheduleLambda**
4. **schedulePriceChanges**
5. **MoveInventoryLambda**

## Directory Structure

Each function has its own directory containing:

-   `lambda_function.py` - Main handler function
-   `requirements.txt` - Python dependencies

## Setup Instructions

### 1. Copy Function Code

For each function directory:

1. Go to AWS Lambda Console
2. Open the function (e.g., `changePricesOfOpenAndWaitlistVariants`)
3. Copy all the code from the Code editor
4. Paste it into the corresponding `lambda_function.py` file
5. Make sure the handler function is named `lambda_handler`

### 2. Add Dependencies

For each function:

1. Check what imports are used in your code
2. Add the required packages to `requirements.txt`
3. Use specific versions (e.g., `boto3==1.26.137`)

### 3. Deploy

Once you commit and push changes to GitHub:

-   The GitHub Action will automatically detect changed functions
-   Install dependencies
-   Package the function
-   Deploy to AWS Lambda

## GitHub Secrets Required

Make sure these secrets are set in your GitHub repository:

-   `AWS_ACCESS_KEY_ID`
-   `AWS_SECRET_ACCESS_KEY`

## Notes

-   Functions are deployed automatically when code changes
-   Python runtime version is set to 3.9 (modify in `.github/workflows/deploy.yml` if needed)
-   AWS region is set to `us-east-1` (modify if your functions are in a different region)
