"""Check certificate fields in MongoDB"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import json

async def check_cert_structure():
    # Use your MongoDB URL directly
    MONGODB_URL = "mongodb+srv://anuragchess22:Shadowguy123@cluster000.e1zei6x.mongodb.net/"
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client["SatyaSetu"]
    
    # Get one certificate to see its structure
    cert = await db.certificates.find_one()
    
    if cert:
        print("Certificate structure:")
        print(json.dumps(cert, indent=2, default=str))
    else:
        print("No certificates found")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_cert_structure())
