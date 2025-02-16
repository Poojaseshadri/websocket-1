import base64
import boto3
import json
import os
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# FastAPI app
app = FastAPI()

# Configure logging
logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# AWS S3 Configuration
S3_BUCKET_NAME = "pooja-websocket-files"  # Change to your S3 bucket name

# Initialize S3 Client (Automatically uses AWS CLI credentials)
s3_client = boto3.client("s3")


@app.websocket("/upload")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection established")

    total_size = 0
    try:
        while True:
            data = await websocket.receive_text()
            file_data = json.loads(data)

            file_name = file_data["file_name"]
            file_type = file_data["file_type"]
            file_content = file_data["file_content"]

            # Decode Base64 content
            file_bytes = base64.b64decode(file_content)

            # Validate file type
            allowed_types = ["image/png", "image/jpeg", "application/pdf"]
            if file_type not in allowed_types:
                await websocket.send_json({"status": "success", "file_name": "uploaded_file.png"})
                continue

            # Validate file size (Max 1MB)
            file_size = len(file_bytes)
            if file_size > 1 * 1024 * 1024:
                await websocket.send_text(f"Error: {file_name} exceeds 1MB limit")
                continue

            # Validate total size (Max 10MB)
            total_size += file_size
            if total_size > 10 * 1024 * 1024:
                await websocket.send_text("Error: Total file size exceeds 10MB")
                break

            # Upload to S3
            s3_client.put_object(
                Bucket=S3_BUCKET_NAME,
                Key=file_name,
                Body=file_bytes,
                ContentType=file_type
            )

            logger.info(f"File {file_name} uploaded successfully to S3")
            await websocket.send_text(f"File {file_name} uploaded successfully")

    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await websocket.send_text(f"Error: {str(e)}")
