#!/usr/bin/env python3
"""
Activepieces Browser Automation Integration
Works around API key limitations using browser automation
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import json
import requests

class ActivepiecesBrowserIntegration:
    def __init__(self, base_url="https://cloud.activepieces.com"):
        self.base_url = base_url
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """Setup Chrome driver with options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in background
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
    
    def login(self, email, password):
        """Login to Activepieces"""
        try:
            self.driver.get(f"{self.base_url}/sign-in")
            
            # Wait for login form
            email_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "email"))
            )
            password_input = self.driver.find_element(By.NAME, "password")
            
            # Enter credentials
            email_input.send_keys(email)
            password_input.send_keys(password)
            
            # Click login button
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # Wait for dashboard
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "dashboard"))
            )
            
            print("✅ Successfully logged in to Activepieces")
            return True
            
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return False
    
    def create_flow(self, flow_name, flow_config):
        """Create a new flow using browser automation"""
        try:
            # Navigate to flows page
            self.driver.get(f"{self.base_url}/flows")
            
            # Click create flow button
            create_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Create Flow')]"))
            )
            create_button.click()
            
            # Enter flow name
            name_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "displayName"))
            )
            name_input.send_keys(flow_name)
            
            # Configure flow (simplified example)
            # This would be expanded based on your specific flow requirements
            
            # Save flow
            save_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Save')]")
            save_button.click()
            
            print(f"✅ Flow '{flow_name}' created successfully")
            return True
            
        except Exception as e:
            print(f"❌ Flow creation failed: {e}")
            return False
    
    def trigger_flow(self, flow_id):
        """Trigger a flow execution"""
        try:
            # Navigate to flow
            self.driver.get(f"{self.base_url}/flows/{flow_id}")
            
            # Click run button
            run_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Run')]"))
            )
            run_button.click()
            
            print(f"✅ Flow {flow_id} triggered successfully")
            return True
            
        except Exception as e:
            print(f"❌ Flow trigger failed: {e}")
            return False
    
    def get_flow_status(self, flow_id):
        """Get flow execution status"""
        try:
            self.driver.get(f"{self.base_url}/flows/{flow_id}/runs")
            
            # Get latest run status
            status_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "run-status"))
            )
            
            status = status_element.text
            print(f"📊 Flow {flow_id} status: {status}")
            return status
            
        except Exception as e:
            print(f"❌ Status check failed: {e}")
            return None
    
    def close(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()

# Example usage
if __name__ == "__main__":
    integration = ActivepiecesBrowserIntegration()
    
    # Login (you'll need to provide credentials)
    # integration.login("your_email@example.com", "your_password")
    
    # Create a flow
    flow_config = {
        "name": "IZA OS Integration Flow",
        "trigger": "webhook",
        "actions": [
            {
                "type": "http_request",
                "url": "http://localhost:8000/api/agents",
                "method": "GET"
            }
        ]
    }
    
    # integration.create_flow("IZA OS Flow", flow_config)
    
    integration.close()
