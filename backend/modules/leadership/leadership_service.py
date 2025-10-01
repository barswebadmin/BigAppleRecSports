from typing import List, Dict, Any, Optional
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Handle imports for both direct execution and module import
try:
    from ..shopify import ShopifyService
    from ..csv import CSVService
except ImportError:
    try:
        from modules.integrations.shopify import ShopifyService
        from shared.csv.csv_processor import CSVService
    except ImportError:
        from modules.integrations.shopify import ShopifyService
        from shared.csv.csv_processor import CSVService

class LeadershipService:
    def __init__(self):
        self.shopify_service = ShopifyService()
        self.csv_service = CSVService()
    
    def process_leadership_emails(self, emails: List[str], year: Optional[int] = None) -> Dict[str, Any]:
        """
        Process leadership emails following the same logic as the Google Apps Script
        """
        if year is None:
            year = datetime.now().year
            
        leadership_segment_name = f"Leadership {year}"
        leadership_tag = f"leadership{year}"
        
        valid_customers = []
        invalid_emails = []
        
        # Step 1: Filter emails to only include valid email addresses (must contain "@")
        filtered_emails = [email.strip() for email in emails if email and email.strip() and "@" in email.strip()]
        
        print(f"📧 Original count: {len(emails)}, Filtered count: {len(filtered_emails)}")
        
        if not filtered_emails:
            return {
                "success": False,
                "message": "No valid email addresses found (emails must contain '@')",
                "valid_customers": [],
                "invalid_emails": emails
            }
        
        # Step 2: Batch process customer lookups (10 at a time for efficiency)
        batch_results = self.shopify_service.get_customers_batch(filtered_emails)
        
        for email in filtered_emails:
            customer_data = batch_results.get(email)
            if customer_data:
                valid_customers.append({
                    "id": customer_data["id"], 
                    "email": email,
                    "existing_tags": customer_data["tags"]
                })
            else:
                invalid_emails.append(email)
        
        print(f"✅ Valid customers: {len(valid_customers)}")
        print(f"❌ Invalid emails: {len(invalid_emails)}")
        
        if not valid_customers:
            return {
                "success": False,
                "message": "No valid customers found",
                "valid_customers": [],
                "invalid_emails": invalid_emails
            }
        
        # Step 3: Create Customer Segment
        segment_query = f"customer_tags CONTAINS '{leadership_tag}'"
        segment_id = self.shopify_service.create_segment(leadership_segment_name, segment_query)
        
        if not segment_id:
            return {
                "success": False,
                "message": f"Failed to create segment: {leadership_segment_name}",
                "valid_customers": valid_customers,
                "invalid_emails": invalid_emails
            }
        
        print(f"✅ Created Segment ID: {segment_id}")
        
        # Step 4: Add Leadership Tag to Customers (preserving existing tags)
        tag_results = []
        for customer in valid_customers:
            success = self.shopify_service.add_tag_to_customer(
                customer["id"], 
                leadership_tag, 
                customer.get("existing_tags", [])
            )
            tag_results.append({
                "customer_id": customer["id"],
                "email": customer["email"],
                "existing_tags": customer.get("existing_tags", []),
                "tag_added": success
            })
        
        # Step 5: Create Discounts for the Leadership Segment
        seasons = ["Winter", "Spring", "Summer", "Fall"]
        discount_results = []
        
        for season in seasons:
            # Create discount codes as per original logic
            discounts = [
                {"code": f"Leadership{season}{year}100off1", "usage_limit": 1, "discount_amount": 1.0},
                {"code": f"Leadership{season}{year}100off2", "usage_limit": 1, "discount_amount": 1.0},
                {"code": f"Leadership{season}{year}50off", "usage_limit": 0, "discount_amount": 0.5}
            ]
            
            for discount in discounts:
                success = self.shopify_service.create_discount_code(
                    discount["code"],
                    discount["usage_limit"],
                    season,
                    year,
                    segment_id,
                    discount["discount_amount"]
                )
                discount_results.append({
                    "code": discount["code"],
                    "season": season,
                    "created": success
                })
        
        return {
            "success": True,
            "message": f"Successfully processed {len(valid_customers)} customers for leadership discounts",
            "year": year,
            "segment_id": segment_id,
            "segment_name": leadership_segment_name,
            "valid_customers": valid_customers,
            "invalid_emails": invalid_emails,
            "tag_results": tag_results,
            "discount_results": discount_results
        }
    
    def process_leadership_csv(self, csv_data: List[List[str]], spreadsheet_title: Optional[str] = None, year: Optional[int] = None) -> Dict[str, Any]:
        """
        Process leadership CSV data - converts to objects and extracts emails for processing
        """
        # Convert CSV to objects for reusable processing
        objects = self.csv_service.process_csv_input(csv_data)
        print(f"📊 CSV Processing: Converted {len(objects)} rows to objects")
        print(f"keys: {objects[0].keys()}")
        
        if not objects:
            error_result = {
                "success": False,
                "message": "No valid data rows found in CSV",
                "csv_info": self.csv_service.get_csv_info(csv_data),
                "objects_created": 0,
                "emails_found": 0,
                "valid_customers": [],
                "invalid_emails": []
            }
            error_result["display_text"] = self.generate_display_text(error_result)
            return error_result
        
        # Extract emails from objects specifically looking for 'personal email' column
        emails = self.csv_service.extract_emails_from_objects(objects, "personal email")
        print(f"📧 Extracted {len(emails)} unique emails from 'personal email' column")
        
        # Get CSV info for debugging/logging (keep for backward compatibility)
        csv_info = self.csv_service.get_csv_info(csv_data)
        print(f"📊 CSV Analysis: {csv_info['data_rows_count']} data rows, {csv_info['total_columns']} columns")
        
        if not emails:
            error_result = {
                "success": False,
                "message": "No valid email addresses found in 'personal email' column",
                "csv_info": csv_info,
                "objects_created": len(objects),
                "emails_found": 0,
                "valid_customers": [],
                "invalid_emails": []
            }
            error_result["display_text"] = self.generate_display_text(error_result)
            return error_result
        
        # Determine year - priority: explicit year, title extraction, current year
        determined_year = year
        if not determined_year and spreadsheet_title:
            determined_year = self.csv_service.extract_year_from_title(spreadsheet_title)
        if not determined_year:
            determined_year = datetime.now().year
        
        print(f"📅 Using year: {determined_year} (from: {'explicit' if year else 'title' if spreadsheet_title else 'current'})")
        
        # Process the emails using existing logic
        result = self.process_leadership_emails(emails, determined_year)
        
        # Add CSV processing info to result
        result.update({
            "csv_info": csv_info,
            "objects_created": len(objects),
            "emails_extracted": len(emails),
            "spreadsheet_title": spreadsheet_title,
            "year_source": "explicit" if year else "title" if (spreadsheet_title and self.csv_service.extract_year_from_title(spreadsheet_title)) else "current"
        })
        
        # Generate display text for frontend
        result["display_text"] = self.generate_display_text(result)
        
        return result
    
    def generate_display_text(self, result: Dict[str, Any]) -> str:
        """
        Generate formatted display text for the frontend
        Returns a string with \n for line breaks
        """
        if not result.get('success'):
            return f"❌ Processing Failed\n\n{result.get('message', 'Unknown error occurred')}"
        
        # Build comprehensive summary message
        message = "✅ Leadership Processing Complete!\n\n"
        
        # CSV Analysis Section
        if result.get('csv_info'):
            csv_info = result['csv_info']
            message += "📊 CSV Analysis:\n"
            message += f"• Total rows processed: {csv_info.get('total_rows', 0)}\n"
            message += f"• Data rows: {csv_info.get('data_rows_count', 0)}\n"
            message += f"• Total columns: {csv_info.get('total_columns', 0)}\n"
            
            if csv_info.get('email_columns') and len(csv_info['email_columns']) > 0:
                email_col_names = [col['name'] for col in csv_info['email_columns']]
                message += f"• Email columns detected: {', '.join(email_col_names)}\n"
            else:
                message += "• Email detection: Auto-detected from content\n"
            message += "\n"
        
        # Objects processing info
        if result.get('objects_created'):
            message += f"🔄 Objects Created: {result['objects_created']}\n\n"
        
        # Email Processing Section
        message += "📧 Email Processing:\n"
        message += f"• Emails extracted: {result.get('emails_extracted', 0)}\n"
        message += f"• Valid customers found: {len(result.get('valid_customers', []))}\n"
        message += f"• Invalid emails filtered: {len(result.get('invalid_emails', []))}\n"
        message += "\n"
        
        # Year and Configuration
        message += f"📅 Processing Year: {result.get('year', 'Unknown')} "
        if result.get('year_source'):
            year_source_text = {
                'explicit': 'manually set',
                'title': 'from spreadsheet title',
                'current': 'current year default'
            }.get(result['year_source'], result['year_source'])
            message += f"({year_source_text})\n"
        else:
            message += "\n"
        
        # Customer Segments and Tags
        valid_customers = result.get('valid_customers', [])
        if valid_customers:
            message += "\n🏷️ Customer Tagging:\n"
            customers_with_existing_tags = [c for c in valid_customers if c.get('existing_tags')]
            message += f"• Customers with existing tags: {len(customers_with_existing_tags)}\n"
            message += f"• New leadership tags added: {len(valid_customers)}\n"
        
        # Discount Codes Section
        discount_results = result.get('discount_results', [])
        if discount_results:
            message += "\n🎫 Discount Codes Created:\n"
            successful_discounts = [d for d in discount_results if d.get('success')]
            failed_discounts = [d for d in discount_results if not d.get('success')]
            
            message += f"• Successfully created: {len(successful_discounts)}\n"
            if failed_discounts:
                message += f"• Failed to create: {len(failed_discounts)}\n"
            
            message += "\nDiscount Details:\n"
            for discount in discount_results:
                status = "✅" if discount.get('success') else "❌"
                message += f"{status} {discount.get('title', 'Unknown')}\n"
        
        # Invalid Emails Section (if any)
        invalid_emails = result.get('invalid_emails', [])
        if invalid_emails:
            message += f"\n❌ Invalid Emails ({len(invalid_emails)}):\n"
            show_emails = invalid_emails[:10]  # Show max 10
            for email in show_emails:
                message += f"• {email}\n"
            if len(invalid_emails) > 10:
                message += f"• ... and {len(invalid_emails) - 10} more\n"
        
        # Performance info
        if result.get('processing_time'):
            message += f"\n⏱️ Processing completed in ~{result['processing_time']}s\n"
        
        # Final message
        message += "\n🎉 Leadership discount processing completed successfully!"
        
        return message 