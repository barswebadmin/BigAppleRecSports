"""
Create group command for Google Directory API.
"""

import json
from typing import Optional

import click_extra as click
import requests

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types.bars_email_identifier import BARS_EMAIL_IDENTIFIER
from bars_cli._core.utils.json_output import output_json_item, output_json_error

from bars_cli.commands.google._shared.google_formatters import _format_group


@click.command('create-group', aliases=['create'])
@handle_display_options(display=True, exit_on_error=True)
@click.argument('group_identifier', type=BARS_EMAIL_IDENTIFIER, required=False)
@click.option('--name', 'group_name', help='Display name for the group (will prompt if not provided)')
@click.option('--description', 'group_description', help='Description for the group (optional)')
@click.option('--url', 'base_url', default='https://bars-backend.loca.lt', show_default=True, help='Backend API URL')
@click.option('--timeout', 'timeout_seconds', default=30.0, show_default=True, type=float, help='Request timeout in seconds')
@click.pass_context
def create_group_cmd(
    ctx: click.Context,
    group_identifier: Optional[str] = None,
    group_name: Optional[str] = None,
    group_description: Optional[str] = None,
    base_url: str = 'https://bars-backend.loca.lt',
    timeout_seconds: float = 30.0
) -> Optional[dict]:
    """
    Create a new Google Workspace group.
    
    GROUP_IDENTIFIER: Group email address (will append @bigapplerecsports.com if not present)
    
    Examples:
      bars google groups create-group team-leads
      bars google groups create team-leads --name "Team Leaders" --description "Leadership team coordination"
      bars --json google groups create team-leads --name "Team Leaders"
    """
    json_output = ctx.obj.get('json_output', False)
    should_display = ctx.obj.get('should_display', True)
    
    # Prompt for group identifier if not provided
    if not group_identifier:
        group_identifier = BARS_EMAIL_IDENTIFIER.convert(None, None, ctx)
    
    # Prompt for group name if not provided
    if not group_name:
        group_name = click.prompt("Enter group display name", type=str)
    
    # Normalize base URL
    base_url = base_url.rstrip('/')
    if not base_url.startswith(('http://', 'https://')):
        base_url = f'https://{base_url}'
    
    # Prepare the API request payload
    payload = {
        'email': group_identifier,
        'name': group_name
    }
    
    if group_description:
        payload['description'] = group_description
    
    # Display creation message
    if should_display and not json_output:
        click.echo(f"🚀 Creating group: {group_identifier}", err=True)
        click.echo(f"   Name: {group_name}", err=True)
        if group_description:
            click.echo(f"   Description: {group_description}", err=True)
        click.echo(f"   API URL: {base_url}/google/groups", err=True)
    
    try:
        # Make the API request
        url = f"{base_url}/google/groups"
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=timeout_seconds
        )
        
        # Handle response
        if response.status_code == 200 or response.status_code == 201:
            # Success
            try:
                response_data = response.json()
                
                if should_display:
                    if json_output:
                        output_json_item(response_data)
                    else:
                        click.echo(f"\n✅ Group Created Successfully!", err=True)
                        click.echo("=" * 60, err=True)
                        click.echo(f"{'Email':<15} {group_identifier}", err=True)
                        click.echo(f"{'Name':<15} {group_name}", err=True)
                        if group_description:
                            click.echo(f"{'Description':<15} {group_description}", err=True)
                        
                        # Display additional info from response if available
                        if 'data' in response_data and isinstance(response_data['data'], dict):
                            data = response_data['data']
                            if 'id' in data:
                                click.echo(f"{'Group ID':<15} {data['id']}", err=True)
                            if 'admin_created' in data:
                                admin_created = "Yes" if data['admin_created'] else "No"
                                click.echo(f"{'Admin Created':<15} {admin_created}", err=True)
                        
                        click.echo("=" * 60, err=True)
                        click.echo(f"\n🎉 Group {group_identifier} is ready to use!", err=True)
                
                return response_data
                
            except json.JSONDecodeError as e:
                error_msg = f"Invalid JSON response from API: {e}"
                if json_output:
                    output_json_error(error_msg, error_type="JSONDecodeError")
                else:
                    click.echo(f"❌ {error_msg}", err=True)
                    click.echo(f"Raw response: {response.text}", err=True)
                raise click.ClickException(error_msg) from e
        
        else:
            # Error response
            error_msg = f"API request failed with status {response.status_code}"
            error_details = {
                'status_code': response.status_code,
                'reason': response.reason,
                'url': url,
                'payload': payload
            }
            
            try:
                error_response = response.json()
                error_details['response'] = error_response
                
                # Extract error message from response if available
                if isinstance(error_response, dict):
                    if 'message' in error_response:
                        error_msg = f"API Error: {error_response['message']}"
                    elif 'error' in error_response:
                        error_msg = f"API Error: {error_response['error']}"
                    elif 'detail' in error_response:
                        if isinstance(error_response['detail'], str):
                            error_msg = f"API Error: {error_response['detail']}"
                        elif isinstance(error_response['detail'], dict) and 'message' in error_response['detail']:
                            error_msg = f"API Error: {error_response['detail']['message']}"
                
            except json.JSONDecodeError:
                error_details['raw_response'] = response.text
            
            if json_output:
                output_json_error(error_msg, error_type="APIError", error_data=error_details)
            else:
                click.echo(f"❌ {error_msg}", err=True)
                click.echo(f"Status Code: {response.status_code} {response.reason}", err=True)
                click.echo(f"URL: {url}", err=True)
                click.echo(f"Payload: {json.dumps(payload, indent=2)}", err=True)
                
                # Show response details
                if 'response' in error_details:
                    click.echo(f"Response: {json.dumps(error_details['response'], indent=2)}", err=True)
                elif 'raw_response' in error_details:
                    click.echo(f"Raw Response: {error_details['raw_response']}", err=True)
            
            raise click.ClickException(error_msg)
    
    except requests.exceptions.Timeout as e:
        error_msg = f"Request timed out after {timeout_seconds} seconds"
        error_details = {
            'timeout_seconds': timeout_seconds,
            'url': url,
            'payload': payload
        }
        
        if json_output:
            output_json_error(error_msg, error_type="TimeoutError", error_data=error_details)
        else:
            click.echo(f"❌ {error_msg}", err=True)
            click.echo(f"URL: {url}", err=True)
            click.echo(f"Try increasing timeout with --timeout option", err=True)
        
        raise click.ClickException(error_msg) from e
    
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Connection error: Unable to connect to {base_url}"
        error_details = {
            'base_url': base_url,
            'url': url,
            'payload': payload,
            'connection_error': str(e)
        }
        
        if json_output:
            output_json_error(error_msg, error_type="ConnectionError", error_data=error_details)
        else:
            click.echo(f"❌ {error_msg}", err=True)
            click.echo(f"URL: {url}", err=True)
            click.echo(f"Check that the backend is running and accessible", err=True)
            click.echo(f"Connection details: {str(e)}", err=True)
        
        raise click.ClickException(error_msg) from e
    
    except requests.exceptions.RequestException as e:
        error_msg = f"Request error: {str(e)}"
        error_details = {
            'url': url,
            'payload': payload,
            'request_error': str(e),
            'error_type': type(e).__name__
        }
        
        if json_output:
            output_json_error(error_msg, error_type="RequestError", error_data=error_details)
        else:
            click.echo(f"❌ {error_msg}", err=True)
            click.echo(f"URL: {url}", err=True)
            click.echo(f"Error Type: {type(e).__name__}", err=True)
            click.echo(f"Error Details: {str(e)}", err=True)
        
        raise click.ClickException(error_msg) from e
    
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        error_type = type(e).__name__
        error_details = {
            'url': url,
            'payload': payload,
            'error_type': error_type,
            'error_message': str(e)
        }
        
        if json_output:
            output_json_error(error_msg, error_type=error_type, error_data=error_details)
        else:
            click.echo(f"❌ {error_msg}", err=True)
            click.echo(f"Error Type: {error_type}", err=True)
            click.echo(f"URL: {url}", err=True)
            click.echo(f"Payload: {json.dumps(payload, indent=2)}", err=True)
            
            # Print full traceback for debugging
            import traceback
            click.echo(f"Full traceback:", err=True)
            click.echo(traceback.format_exc(), err=True)
        
        raise click.ClickException(error_msg) from e