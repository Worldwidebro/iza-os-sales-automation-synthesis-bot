#!/usr/bin/env python3
"""
CUSTOM AUTOMATION SCRIPT - IZA OS ECOSYSTEM
Automated business process automation for 300+ businesses
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IZAOSAutomation:
    def __init__(self):
        self.iza_os_url = "http://localhost:8000"
        self.session = None
        self.running = False
        
    async def start_session(self):
        """Start HTTP session"""
        self.session = aiohttp.ClientSession()
        
    async def close_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            
    async def health_check(self):
        """Check IZA OS health"""
        try:
            async with self.session.get(f"{self.iza_os_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ IZA OS Health: {data['status']}")
                    return True
                else:
                    logger.error(f"❌ IZA OS Health Check Failed: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Health Check Error: {e}")
            return False
            
    async def get_agents(self):
        """Get all AI agents"""
        try:
            async with self.session.get(f"{self.iza_os_url}/agents") as response:
                if response.status == 200:
                    agents = await response.json()
                    logger.info(f"🤖 Found {len(agents)} AI agents")
                    return agents
                else:
                    logger.error(f"❌ Failed to get agents: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"❌ Get Agents Error: {e}")
            return []
            
    async def get_metrics(self):
        """Get system metrics"""
        try:
            async with self.session.get(f"{self.iza_os_url}/metrics") as response:
                if response.status == 200:
                    metrics = await response.json()
                    logger.info(f"📊 System Metrics: {metrics['metrics']['ecosystem_value']}")
                    return metrics
                else:
                    logger.error(f"❌ Failed to get metrics: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"❌ Get Metrics Error: {e}")
            return {}
            
    async def create_venture(self, venture_data: Dict):
        """Create a new venture"""
        try:
            async with self.session.post(
                f"{self.iza_os_url}/api/ventures",
                json=venture_data
            ) as response:
                if response.status == 200:
                    venture = await response.json()
                    logger.info(f"🚀 Created venture: {venture['name']}")
                    return venture
                else:
                    logger.error(f"❌ Failed to create venture: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"❌ Create Venture Error: {e}")
            return None
            
    async def deploy_agent(self, agent_id: str):
        """Deploy an AI agent"""
        try:
            async with self.session.post(
                f"{self.iza_os_url}/api/agents/{agent_id}/deploy"
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"🚀 Deployed agent: {agent_id}")
                    return result
                else:
                    logger.error(f"❌ Failed to deploy agent: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"❌ Deploy Agent Error: {e}")
            return None
            
    async def start_api_discovery(self):
        """Start API discovery process"""
        try:
            async with self.session.post(
                f"{self.iza_os_url}/api/discovery/start"
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"🔍 Started API discovery: {result['discovery_id']}")
                    return result
                else:
                    logger.error(f"❌ Failed to start API discovery: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"❌ API Discovery Error: {e}")
            return None
            
    async def create_api_key(self, key_data: Dict):
        """Create a new API key"""
        try:
            async with self.session.post(
                f"{self.iza_os_url}/api/keys",
                json=key_data
            ) as response:
                if response.status == 200:
                    key = await response.json()
                    logger.info(f"🔑 Created API key: {key['name']}")
                    return key
                else:
                    logger.error(f"❌ Failed to create API key: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"❌ Create API Key Error: {e}")
            return None
            
    async def automation_cycle(self):
        """Main automation cycle"""
        logger.info("🔄 Starting automation cycle...")
        
        # Health check
        if not await self.health_check():
            logger.error("❌ IZA OS not healthy, skipping cycle")
            return
            
        # Get agents and deploy them
        agents = await self.get_agents()
        for agent in agents:
            if agent['status'] == 'active':
                await self.deploy_agent(agent['id'])
                
        # Get metrics
        metrics = await self.get_metrics()
        
        # Start API discovery
        await self.start_api_discovery()
        
        # Create sample ventures
        sample_ventures = [
            {
                "id": f"venture-{int(time.time())}",
                "name": "AI Boss Holdings",
                "type": "holding_company",
                "status": "active",
                "revenue": 150000000.0,
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "metrics": {
                    "businesses": 300,
                    "employees": 1000,
                    "markets": 50
                }
            },
            {
                "id": f"venture-{int(time.time()) + 1}",
                "name": "GenixBank Lite",
                "type": "fintech",
                "status": "active",
                "revenue": 50000000.0,
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "metrics": {
                    "customers": 100000,
                    "transactions": 1000000,
                    "revenue_growth": 25.0
                }
            }
        ]
        
        for venture_data in sample_ventures:
            await self.create_venture(venture_data)
            
        # Create API keys
        api_keys = [
            {
                "name": "WorldwideBro Integration",
                "provider": "WorldwideBro",
                "key": f"wb_{int(time.time())}",
                "environment": "production",
                "permissions": ["read", "write", "deploy"]
            },
            {
                "name": "Activepieces Automation",
                "provider": "Activepieces",
                "key": f"ap_{int(time.time())}",
                "environment": "production",
                "permissions": ["workflow", "trigger", "monitor"]
            }
        ]
        
        for key_data in api_keys:
            await self.create_api_key(key_data)
            
        logger.info("✅ Automation cycle completed")
        
    async def run_continuous(self):
        """Run automation continuously"""
        self.running = True
        await self.start_session()
        
        logger.info("🚀 Starting IZA OS Custom Automation")
        logger.info("🔄 Running continuous automation cycles...")
        
        try:
            while self.running:
                await self.automation_cycle()
                await asyncio.sleep(300)  # Run every 5 minutes
        except KeyboardInterrupt:
            logger.info("🛑 Stopping automation...")
            self.running = False
        finally:
            await self.close_session()
            
    def stop(self):
        """Stop automation"""
        self.running = False

async def main():
    """Main function"""
    automation = IZAOSAutomation()
    await automation.run_continuous()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Automation stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
