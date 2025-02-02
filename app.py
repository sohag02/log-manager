# app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import docker
from docker.errors import DockerException
from datetime import datetime
import logging
import os
import platform

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_docker_client():
    """
    Initialize Docker client based on platform and environment
    """
    try:
        # Get Docker host from environment or use default
        docker_host = os.getenv('DOCKER_HOST')
        
        if docker_host:
            # If DOCKER_HOST is set, use it
            client = docker.DockerClient(base_url=docker_host)
        else:
            # Platform specific default connections
            if platform.system() == 'Windows':
                client = docker.DockerClient(base_url='npipe:////./pipe/docker_engine')
            else:
                # Linux/Unix systems
                client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        
        # Test the connection
        client.ping()
        return client
    
    except DockerException as e:
        logger.error(f"Failed to initialize Docker client: {str(e)}")
        raise

try:
    docker_client = get_docker_client()
    logger.info("Successfully connected to Docker daemon")
except Exception as e:
    logger.error(f"Failed to initialize Docker client: {str(e)}")
    docker_client = None

@app.route('/status', methods=['GET'])
def get_docker_status():
    """Check Docker daemon connectivity"""
    if docker_client is None:
        return jsonify({
            'status': 'error',
            'message': 'Docker client not initialized'
        }), 500
    
    try:
        docker_client.ping()
        return jsonify({
            'status': 'ok',
            'message': 'Docker daemon is accessible'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Docker daemon is not accessible: {str(e)}'
        }), 500

@app.route('/logs', methods=['GET'])
def get_container_logs():
    """Get container logs"""
    if docker_client is None:
        return jsonify({
            'error': 'Docker client not initialized'
        }), 500
    
    try:
        container_id = request.args.get('container_id')
        
        if not container_id:
            return jsonify({'error': 'Container ID is required'}), 400
            
        # Get container
        try:
            container = docker_client.containers.get(container_id)
        except docker.errors.NotFound:
            return jsonify({'error': f'Container {container_id} not found'}), 404
            
        # Get logs
        logs = container.logs(
            tail=100,  # Last 100 lines
            timestamps=True,
            stream=False
        ).decode('utf-8')
        
        # Parse logs into structured format
        structured_logs = []
        for log_line in logs.split('\n'):
            if log_line:
                try:
                    # Split timestamp and message
                    timestamp_str, message = log_line.split(' ', 1)
                    # Parse timestamp
                    timestamp = datetime.strptime(
                        timestamp_str.split('.')[0], 
                        '%Y-%m-%dT%H:%M:%S'
                    ).isoformat()
                    
                    # Try to parse the message as JSON
                    try:
                        import json
                        parsed_message = json.loads(message)
                        structured_logs.append({
                            'timestamp': timestamp,
                            'message': parsed_message,
                            'is_json': True
                        })
                    except json.JSONDecodeError:
                        # If not JSON, keep as plain text
                        structured_logs.append({
                            'timestamp': timestamp,
                            'message': message,
                            'is_json': False
                        })
                except Exception as e:
                    logger.error(f'Error parsing log line: {e}')
                    structured_logs.append({
                        'timestamp': None,
                        'message': log_line,
                        'is_json': False
                    })
        
        return jsonify({
            'container_id': container_id,
            'logs': structured_logs
        })
        
    except Exception as e:
        logger.error(f'Error getting logs: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/containers', methods=['GET'])
def list_containers():
    """List all containers"""
    if docker_client is None:
        return jsonify({
            'error': 'Docker client not initialized'
        }), 500
    
    try:
        containers = docker_client.containers.list()
        container_list = [{
            'id': container.id,
            'name': container.name,
            'status': container.status
        } for container in containers]
        
        return jsonify(container_list)
        
    except Exception as e:
        logger.error(f'Error listing containers: {e}')
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Get port from environment or use default
    port = int(os.getenv('FLASK_PORT', 8000))
    
    # Get host from environment or use default
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    
    app.run(host=host, port=port, debug=True)