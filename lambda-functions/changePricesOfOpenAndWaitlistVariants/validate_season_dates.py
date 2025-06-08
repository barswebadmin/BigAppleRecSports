import json
from fetch_shopify import fetch_shopify
from date_utils import format_date_only, extract_season_dates

def validate_season_dates(product_gid, season_start_date, off_dates_comma_separated):
    query = '''
    query getProduct($id: ID!) {
      product(id: $id) {
        id
        title
        descriptionHtml
      }
    }
    '''
    data = fetch_shopify(query, variables={"id": product_gid})
    product = data.get("product")
    if not product:
        raise Exception(f"Product not found for ID: {product_gid}")

    extracted_start_date, extracted_off_dates = extract_season_dates(product["descriptionHtml"])

    formatted_input_start = format_date_only(season_start_date)

    input_off_dates = [
        format_date_only(d.strip()) for d in off_dates_comma_separated.split(",") if d.strip()
    ]
    extracted_off_list = [
        d.strip() for d in extracted_off_dates.split(",")] if extracted_off_dates else []
    
    print("🔍 Validation result:")
    print(json.dumps({
        "productId": product_gid,
        "extracted_start_date": extracted_start_date,
        "formatted_input_start": formatted_input_start,
        "extracted_off_dates": extracted_off_list,
        "input_off_dates": input_off_dates
    }, indent=2))

    match_start = extracted_start_date == formatted_input_start
    match_off_dates = sorted(input_off_dates) == sorted(extracted_off_list)

    return {
        "match": match_start and match_off_dates,
        "productTitle": product["title"],
        "expected": {
            "seasonStartDate": extracted_start_date,
            "offDates": extracted_off_list
        },
        "received": {
            "seasonStartDate": formatted_input_start,
            "offDates": input_off_dates
        }
    }