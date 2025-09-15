#!/usr/bin/env python3
"""
Quick test script to check if order 42309 exists in Shopify
"""
import requests
import json

# Use your production values
SHOPIFY_STORE = "09fe59-3.myshopify.com"
SHOPIFY_TOKEN = "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"

def test_order_search():
    url = f"https://{SHOPIFY_STORE}/admin/api/2025-01/graphql.json"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
    }

    # Test 1: Search for order #42309 (exact format backend uses)
    query1 = {
        "query": """
        {
            orders(first: 1, query: "name:#42309") {
                edges {
                    node {
                        id
                        name
                        createdAt
                        customer {
                            email
                        }
                    }
                }
            }
        }
        """
    }

    print("🔍 Testing Shopify API directly...")
    print(f"📍 Store: {SHOPIFY_STORE}")
    print(f"🔑 Token: {SHOPIFY_TOKEN[:15]}...")
    print()

    print("📤 Test 1: Searching for 'name:#42309'")
    try:
        response = requests.post(url, headers=headers, json=query1, timeout=30)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("   Response:", json.dumps(data, indent=2))

            if data.get("data") and data["data"]["orders"]["edges"]:
                print("   ✅ ORDER FOUND!")
                order = data["data"]["orders"]["edges"][0]["node"]
                print(f"      Name: {order['name']}")
                print(f"      ID: {order['id']}")
                print(f"      Email: {order.get('customer', {}).get('email', 'N/A')}")
            else:
                print("   ❌ No orders found")
        else:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"   ❌ Exception: {e}")

    print()

    # Test 2: Search for order 42309 (without #)
    query2 = {
        "query": """
        {
            orders(first: 1, query: "name:42309") {
                edges {
                    node {
                        id
                        name
                        createdAt
                        customer {
                            email
                        }
                    }
                }
            }
        }
        """
    }

    print("📤 Test 2: Searching for 'name:42309' (without #)")
    try:
        response = requests.post(url, headers=headers, json=query2, timeout=30)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get("data") and data["data"]["orders"]["edges"]:
                print("   ✅ ORDER FOUND!")
                order = data["data"]["orders"]["edges"][0]["node"]
                print(f"      Name: {order['name']}")
                print(f"      ID: {order['id']}")
                print(f"      Email: {order.get('customer', {}).get('email', 'N/A')}")
            else:
                print("   ❌ No orders found")
        else:
            print(f"   ❌ Error: {response.status_code}")

    except Exception as e:
        print(f"   ❌ Exception: {e}")

    print()

    # Test 3: Get recent orders to see what format they use
    query3 = {
        "query": """
        {
            orders(first: 5, sortKey: CREATED_AT, reverse: true) {
                edges {
                    node {
                        id
                        name
                        createdAt
                        customer {
                            email
                        }
                    }
                }
            }
        }
        """
    }

    print("📤 Test 3: Getting recent orders to see name format")
    try:
        response = requests.post(url, headers=headers, json=query3, timeout=30)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get("data") and data["data"]["orders"]["edges"]:
                print("   ✅ Recent orders:")
                for i, edge in enumerate(data["data"]["orders"]["edges"]):
                    order = edge["node"]
                    print(f"      {i+1}. Name: '{order['name']}' | Email: {order.get('customer', {}).get('email', 'N/A')}")
            else:
                print("   ❌ No orders found")
        else:
            print(f"   ❌ Error: {response.status_code}")

    except Exception as e:
        print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    test_order_search()
