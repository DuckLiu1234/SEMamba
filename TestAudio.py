import subprocess
import time
import sys
import requests
from datetime import datetime
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def record_and_upload(duration=5, server_ip='192.168.100.180', server_port=8000):
    """
    Record audio using ReSpeaker and upload to server
    Args:
        duration: Recording duration in seconds
        server_ip: Server IP address
        server_port: Server port number
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'recording_{timestamp}.wav'

    cmd = f'arecord -Dac108 -f S32_LE -r 16000 -c 1 -d {duration} {filename}'

    logger.info(f"Starting recording for {duration} seconds...")
    logger.info(f"Temp file: {filename}")

    try:
        # Start recording
        process = subprocess.Popen(cmd, shell=True)

        start_time = time.time()
        while process.poll() is None:
            elapsed = time.time() - start_time
            if elapsed > duration:
                break
            progress = (elapsed / duration) * 100
            sys.stdout.write(f"\rRecording progress: {progress:.1f}% ({elapsed:.1f}/{duration}s)")
            sys.stdout.flush()
            time.sleep(0.1)

        logger.info("Recording completed")

        # Upload file
        logger.info(f"Uploading file to {server_ip}:{server_port}")
        url = f'http://{server_ip}:{server_port}/upload'

        with open(filename, 'rb') as f:
            data = f.read()

        headers = {
            'Content-Type': 'audio/wav',
            'x-audio-sample-rates': '16000',
            'x-audio-bits': '32',
            'x-audio-channel': '1',
        }

        response = requests.post(url, data=data, headers=headers)

        if response.status_code == 200:
            logger.info("File upload successful")
            logger.info(f"Server response: {response.text}")
            os.remove(filename)
            logger.info(f"Removed temp file: {filename}")
        else:
            logger.error(f"Upload failed, HTTP status code: {response.status_code}")
            logger.info(f"File retained at: {filename}")

    except KeyboardInterrupt:
        logger.warning("Recording interrupted by user")
        if 'process' in locals():
            process.terminate()
    except Exception as e:
        logger.error(f"Error occurred: {e}")
    finally:
        if 'process' in locals() and process.poll() is None:
            process.terminate()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Record audio and upload to server')
    parser.add_argument('-d', '--duration', type=int, default=5,
                       help='Recording duration in seconds (default: 5)')
    parser.add_argument('-i', '--ip', type=str, default='192.168.100.180',
                       help='Server IP address')
    parser.add_argument('-p', '--port', type=int, default=8000,
                       help='Server port (default: 8000)')

    args = parser.parse_args()

    record_and_upload(
        duration=args.duration,
        server_ip=args.ip,
        server_port=args.port
    )