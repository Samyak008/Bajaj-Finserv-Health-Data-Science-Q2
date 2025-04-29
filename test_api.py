import requests
import json
import argparse
import os
import sys

def test_api(image_path, api_url="http://localhost:8000/get-lab-tests"):
    """
    Send an image file to the lab report processing API and display the results.
    
    Args:
        image_path: Path to the image file
        api_url: URL of the API endpoint (default: http://localhost:8000/get-lab-tests)
    
    Returns:
        API response
    """
    # Check if file exists
    if not os.path.exists(image_path):
        print(f"Error: File not found - {image_path}")
        return
    
    # Check file extension
    _, ext = os.path.splitext(image_path)
    if ext.lower() not in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']:
        print(f"Error: File must be an image - {image_path}")
        return
    
    # Prepare the file for upload
    files = {
        'file': (os.path.basename(image_path), open(image_path, 'rb'), f'image/{ext[1:]}')
    }
    
    print(f"Sending image to API: {image_path}")
    
    try:
        # Make the POST request
        response = requests.post(api_url, files=files)
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            print(f"API Response (status code {response.status_code}):")
            print(json.dumps(result, indent=2))
            
            # Print summary of lab tests
            if result.get("is_success") and "data" in result:
                tests = result["data"]
                print(f"\nFound {len(tests)} lab tests:")
                print("-" * 80)
                print(f"{'Test Name':<30} {'Value':<10} {'Range':<15} {'Unit':<10} {'Out of Range'}")
                print("-" * 80)
                
                for test in tests:
                    print(f"{test['test_name'][:30]:<30} {test['test_value']:<10} "
                          f"{test['bio_reference_range']:<15} {test['test_unit']:<10} "
                          f"{'YES' if test['lab_test_out_of_range'] else 'NO'}")
            
            return result
        else:
            print(f"Error: API returned status code {response.status_code}")
            print(f"Response: {response.text}")
    
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to API: {str(e)}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
    
    finally:
        # Close the file
        files['file'][1].close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test Lab Report Processor API')
    parser.add_argument('--image', type=str, required=True, help='Path to the image file to process')
    parser.add_argument('--url', type=str, default="http://localhost:8000/get-lab-tests", 
                      help='URL of the API endpoint')
    
    args = parser.parse_args()
    test_api(args.image, args.url)