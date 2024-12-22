import os
import datetime
import sys
import wave
import argparse
import socket
import logging
from logging.handlers import RotatingFileHandler
import inference

if sys.version_info.major == 3:
    from urllib import parse
    from http.server import HTTPServer
    from http.server import BaseHTTPRequestHandler
else:
    import urlparse
    from BaseHTTPServer import HTTPServer
    from BaseHTTPServer import BaseHTTPRequestHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler('server.log', maxBytes=1024*1024, backupCount=5)
    ]
)
logger = logging.getLogger(__name__)

PORT = 8000

def initialize_semamba(config_path, checkpoint_path):
    """Initialize SEMAMBA model"""
    try:
        inference.initialize_model(config_path, checkpoint_path)
        logger.info("SEMAMBA model initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize SEMAMBA model: {e}")
        sys.exit(1)

class Handler(BaseHTTPRequestHandler):
    def _set_headers(self, length):
        self.send_response(200)
        if length > 0:
            self.send_header('Content-length', str(length))
        self.end_headers()

    def _get_chunk_size(self):
        data = self.rfile.read(2)
        while data[-2:] != b"\r\n":
            data += self.rfile.read(1)
        return int(data[:-2], 16)

    def _get_chunk_data(self, chunk_size):
        data = self.rfile.read(chunk_size)
        self.rfile.read(2)
        return data

    def _write_wav(self, data, rates, bits, ch):
        t = datetime.datetime.utcnow()
        time = t.strftime('%Y%m%dT%H%M%SZ')
        filename = str.format('{}_{}_{}_{}.wav', time, rates, bits, ch)

        wavfile = wave.open(filename, 'wb')
        wavfile.setparams((ch, int(bits/8), rates, 0, 'NONE', 'NONE'))
        wavfile.writeframesraw(bytearray(data))
        wavfile.close()
        return filename

    def do_POST(self):
        try:
            logger.info(f"Received POST request from: {self.client_address}")
            
            if sys.version_info.major == 3:
                urlparts = parse.urlparse(self.path)
            else:
                urlparts = urlparse.urlparse(self.path)
            request_file_path = urlparts.path.strip('/')

            if request_file_path == 'upload':
                content_length = int(self.headers.get('Content-Length', 0))
                sample_rates = self.headers.get('x-audio-sample-rates', '').lower()
                bits = self.headers.get('x-audio-bits', '').lower()
                channel = self.headers.get('x-audio-channel', '').lower()

                try:
                    # Read and save original wav file
                    data = self.rfile.read(content_length)
                    t = datetime.datetime.utcnow()
                    time = t.strftime('%Y%m%dT%H%M%SZ')
                    original_filename = str.format('original_{}_{}_{}_{}.wav', time, sample_rates, bits, channel)
                    
                    with open(original_filename, 'wb') as f:
                        f.write(data)
                    
                    logger.info(f"Original file saved: {original_filename}")
                    
                    # Process with SEMAMBA
                    enhanced_filename = f"enhanced_{time}.wav"
                    try:
                        inference.process_audio(original_filename, enhanced_filename)
                        logger.info(f"Audio enhanced: {enhanced_filename}")
                    except Exception as e:
                        logger.error(f"Failed to enhance audio: {e}")
                        enhanced_filename = original_filename  # 如果增強失敗，使用原始檔案
                    
                    # Response to client
                    self.send_response(200)
                    self.send_header("Content-type", "text/html;charset=utf-8")
                    self.end_headers()
                    response = f'File processed: {enhanced_filename}'
                    self.wfile.write(response.encode('utf-8'))
                    
                except Exception as e:
                    logger.error(f"Error processing file: {e}", exc_info=True)
                    self.send_error(500, str(e))
            else:
                logger.warning(f"Invalid request path: {request_file_path}")
                self.send_error(404, "Invalid request path")

        except Exception as e:
            logger.error(f"Error in POST handler: {e}", exc_info=True)
            self.send_error(500, str(e))

    def do_GET(self):
        try:
            logger.info(f"Received GET request from: {self.client_address}")
            self.send_response(200)
            self.send_header('Content-type', "text/html;charset=utf-8")
            self.end_headers()
            self.wfile.write("Server is running".encode('utf-8'))
            logger.info("GET request handled successfully")
        except Exception as e:
            logger.error(f"Error in GET handler: {e}", exc_info=True)
            self.send_error(500, str(e))

def get_host_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        logger.info(f"Retrieved host IP: {ip}")
        return ip
    except Exception as e:
        logger.error(f"Error getting host IP: {e}")
        return '0.0.0.0'
    finally:
        if 's' in locals():
            s.close()

def main():
    parser = argparse.ArgumentParser(description='HTTP Server for ReSpeaker audio files')
    parser.add_argument('--ip', '-i', nargs='?', type=str)
    parser.add_argument('--port', '-p', nargs='?', type=int)
    parser.add_argument('--config', required=True, help='SEMAMBA config file path')
    parser.add_argument('--checkpoint', required=True, help='SEMAMBA checkpoint file path')
    args = parser.parse_args()

    if not args.ip:
        args.ip = get_host_ip()
    if not args.port:
        args.port = PORT
        
    # Initialize SEMAMBA
    initialize_semamba(args.config, args.checkpoint)

    try:
        logger.info(f"Starting server on {args.ip}:{args.port}")
        httpd = HTTPServer((args.ip, args.port), Handler)
        logger.info(f"Server is running at http://{args.ip}:{args.port}")
        httpd.serve_forever()
    except Exception as e:
        logger.error(f"Server failed to start: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
