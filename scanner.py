# scanner.py

import requests
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from colorama import init, Fore
import argparse

# Initialize colorama
init(autoreset=True)

# A set to store all the links we've already visited to avoid loops
visited_links = set()

def get_all_links(url):
    """
    Crawls a given URL to find all unique links on the page.
    """
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        links = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag.get("href")
            # Join relative URLs with the base URL
            full_url = urljoin(url, href)
            links.add(full_url)
        return links
    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"[-] Error crawling {url}: {e}")
        return set()

def get_forms(url):
    """
    Extracts all HTML forms from a given URL.
    """
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        return soup.find_all("form")
    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"[-] Could not retrieve forms from {url}: {e}")
        return []

def scan_sql_injection(url):
    """
    Scans a given URL for basic SQL Injection vulnerabilities.
    """
    print(Fore.YELLOW + f"\n[+] Scanning for SQL Injection on {url}...")
    forms = get_forms(url)
    
    # Simple SQLi payload and error patterns to check for
    sqli_payload = "'"
    sqli_error_patterns = [
        "you have an error in your sql syntax",
        "warning: mysql",
        "unclosed quotation mark",
        "syntax error"
    ]

    for form in forms:
        action = form.get("action")
        post_url = urljoin(url, action)
        method = form.get("method", "get").lower()

        inputs = form.find_all("input")
        data = {}
        for input_tag in inputs:
            input_type = input_tag.get("type", "text")
            input_name = input_tag.get("name")
            if input_type == "text" and input_name:
                data[input_name] = sqli_payload

        try:
            if method == "post":
                response = requests.post(post_url, data=data)
            else:
                response = requests.get(post_url, params=data)
            
            for pattern in sqli_error_patterns:
                if re.search(pattern, response.text, re.IGNORECASE):
                    print(Fore.RED + f"[!!!] SQL Injection vulnerability discovered at {post_url}")
                    print(Fore.WHITE + f"    Form details: {form}")
                    break # Found a vulnerability, no need to check other patterns
        except requests.exceptions.RequestException:
            pass # Ignore connection errors during scanning

def scan_xss(url):
    """
    Scans a given URL for basic Reflected XSS vulnerabilities.
    """
    print(Fore.YELLOW + f"\n[+] Scanning for XSS on {url}...")
    forms = get_forms(url)
    
    # Simple XSS payload
    xss_payload = "<script>alert('xss')</script>"
    
    for form in forms:
        action = form.get("action")
        post_url = urljoin(url, action)
        method = form.get("method", "get").lower()

        inputs = form.find_all("input")
        data = {}
        for input_tag in inputs:
            input_type = input_tag.get("type", "text")
            input_name = input_tag.get("name")
            if input_type == "text" and input_name:
                data[input_name] = xss_payload

        try:
            if method == "post":
                response = requests.post(post_url, data=data)
            else:
                response = requests.get(post_url, params=data)
            
            if xss_payload in response.text:
                print(Fore.RED + f"[!!!] XSS vulnerability discovered at {post_url}")
                print(Fore.WHITE + f"    Form details: {form}")
        except requests.exceptions.RequestException:
            pass

def main():
    parser = argparse.ArgumentParser(description="VulnScanPy - A Basic Web Vulnerability Scanner")
    parser.add_argument("-u", "--url", required=True, help="The base URL to scan.")
    args = parser.parse_args()
    
    target_url = args.url
    
    print(Fore.CYAN + f"[*] Starting scan on {target_url}")
    
    # Start crawling from the target URL
    links_to_scan = get_all_links(target_url)
    
    for link in links_to_scan:
        if link not in visited_links:
            visited_links.add(link)
            print(Fore.GREEN + f"\n[~] Analyzing page: {link}")
            
            # Scan each found link for vulnerabilities
            scan_sql_injection(link)
            scan_xss(link)
    
    print(Fore.CYAN + "\n[*] Scan finished.")

if __name__ == "__main__":
    main()