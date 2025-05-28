from flask import Flask, render_template, request, jsonify
import asyncio
import threading
from mcp_client import MCPClient
import logging
import concurrent.futures

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global MCP client instance and event loop
mcp_client = None
client_lock = threading.Lock()
background_loop = None
executor = None

def start_background_loop():
    """Start a background event loop in a separate thread"""
    global background_loop
    background_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(background_loop)
    background_loop.run_forever()

def run_async(coro):
    """Run an async coroutine using the background event loop"""
    global background_loop
    if background_loop is None or background_loop.is_closed():
        raise RuntimeError("Background event loop is not running")
    
    future = asyncio.run_coroutine_threadsafe(coro, background_loop)
    return future.result(timeout=30)  # 30 second timeout

async def initialize_mcp_client():
    """Initialize the MCP client connection"""
    global mcp_client
    try:
        mcp_client = MCPClient()
        await mcp_client.connect_to_server()
        logger.info("MCP Client initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize MCP client: {e}")
        return False

@app.route('/')
def index():
    """Serve the chat interface"""
    return render_template('chat.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    global mcp_client
    
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'success': False, 'error': 'Empty message'})
        
        with client_lock:
            if mcp_client is None:
                return jsonify({
                    'success': False, 
                    'error': 'MCP client not initialized. Please restart the server.'
                })
            
            # Process the query using MCP client
            try:
                response = run_async(mcp_client.process_query(user_message))
                return jsonify({
                    'success': True,
                    'response': response
                })
            except Exception as e:
                logger.error(f"Error processing query: {e}")
                return jsonify({
                    'success': False,
                    'error': f'Failed to process query: {str(e)}'
                })
                
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        })

@app.route('/reset', methods=['POST'])
def reset_conversation():
    """Reset the conversation history"""
    global mcp_client
    
    try:
        with client_lock:
            if mcp_client:
                mcp_client.reset_conversation()
                return jsonify({'success': True, 'message': 'Conversation reset'})
            else:
                return jsonify({'success': False, 'error': 'MCP client not available'})
    except Exception as e:
        logger.error(f"Error resetting conversation: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/status')
def status():
    """Check the status of the MCP client"""
    global mcp_client
    
    with client_lock:
        is_connected = mcp_client is not None
        return jsonify({
            'mcp_connected': is_connected,
            'status': 'ready' if is_connected else 'disconnected'
        })

def startup_mcp_client():
    """Initialize MCP client on startup"""
    global background_loop, executor
    
    # Start background event loop in a separate thread
    loop_thread = threading.Thread(target=start_background_loop, daemon=True)
    loop_thread.start()
    
    # Wait a moment for the loop to start
    import time
    time.sleep(0.5)
    
    logger.info("Initializing MCP client...")
    try:
        success = run_async(initialize_mcp_client())
        if success:
            logger.info("Flask app ready with MCP client")
        else:
            logger.error("Flask app started but MCP client failed to initialize")
    except Exception as e:
        logger.error(f"Failed to start MCP client: {e}")

@app.teardown_appcontext
def cleanup(error):
    """Clean up resources when app context tears down"""
    global background_loop, mcp_client
    if error:
        logger.error(f"App context error: {error}")

def shutdown_background_loop():
    """Shutdown the background event loop"""
    global background_loop, mcp_client
    
    if mcp_client and background_loop and not background_loop.is_closed():
        try:
            # Clean up MCP client
            future = asyncio.run_coroutine_threadsafe(mcp_client.cleanup(), background_loop)
            future.result(timeout=5)
        except Exception as e:
            logger.error(f"Error during MCP client cleanup: {e}")
    
    if background_loop and not background_loop.is_closed():
        background_loop.call_soon_threadsafe(background_loop.stop)

if __name__ == '__main__':
    import atexit
    
    # Register cleanup function
    atexit.register(shutdown_background_loop)
    
    # Initialize MCP client before starting Flask
    startup_mcp_client()
    
    # Start Flask app
    try:
        app.run(debug=True, host='0.0.0.0', port=5001, threaded=True)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        shutdown_background_loop()
