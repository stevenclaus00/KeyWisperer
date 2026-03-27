#!/usr/bin/env python3
"""
VoiceKey PC Server

This server runs on your PC and receives commands from the VoiceKey mobile app.
It can type text, send keystrokes, and control your mouse.

Requirements:
    pip install websockets pynput

Usage:
    python voicekey_server.py

The server will start on port 8765 by default.
Find your PC's IP address and enter it in the VoiceKey app to connect.
"""

import asyncio
import json
import logging
import socket
from typing import Set

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
except ImportError:
    print("Please install websockets: pip install websockets")
    exit(1)

try:
    from pynput.keyboard import Key, Controller as KeyboardController
    from pynput.mouse import Button, Controller as MouseController
except ImportError:
    print("Please install pynput: pip install pynput")
    exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize controllers
keyboard = KeyboardController()
mouse = MouseController()

# Store connected clients
connected_clients: Set[WebSocketServerProtocol] = set()

# Key mapping
KEY_MAP = {
    'ENTER': Key.enter,
    'TAB': Key.tab,
    'BACKSPACE': Key.backspace,
    'DELETE': Key.delete,
    'SPACE': Key.space,
    'ESCAPE': Key.esc,
    'UP': Key.up,
    'DOWN': Key.down,
    'LEFT': Key.left,
    'RIGHT': Key.right,
    'HOME': Key.home,
    'END': Key.end,
    'PAGE_UP': Key.page_up,
    'PAGE_DOWN': Key.page_down,
    'CTRL': Key.ctrl,
    'ALT': Key.alt,
    'SHIFT': Key.shift,
    'F1': Key.f1,
    'F2': Key.f2,
    'F3': Key.f3,
    'F4': Key.f4,
    'F5': Key.f5,
    'F6': Key.f6,
    'F7': Key.f7,
    'F8': Key.f8,
    'F9': Key.f9,
    'F10': Key.f10,
    'F11': Key.f11,
    'F12': Key.f12,
}


def type_text(text: str):
    """Type the given text character by character."""
    try:
        keyboard.type(text)
        logger.info(f"Typed: {text[:50]}..." if len(text) > 50 else f"Typed: {text}")
    except Exception as e:
        logger.error(f"Error typing text: {e}")


def press_key(key_name: str):
    """Press a special key or key combination."""
    try:
        # Handle key combinations (e.g., CTRL+A)
        if '+' in key_name:
            keys = key_name.split('+')
            # Press all modifier keys
            modifiers = []
            for k in keys[:-1]:
                key = KEY_MAP.get(k.upper())
                if key:
                    keyboard.press(key)
                    modifiers.append(key)
            
            # Press the final key
            final_key = keys[-1]
            if final_key.upper() in KEY_MAP:
                keyboard.press(KEY_MAP[final_key.upper()])
                keyboard.release(KEY_MAP[final_key.upper()])
            else:
                keyboard.press(final_key.lower())
                keyboard.release(final_key.lower())
            
            # Release modifiers
            for key in reversed(modifiers):
                keyboard.release(key)
            
            logger.info(f"Pressed key combination: {key_name}")
        else:
            # Single key
            key = KEY_MAP.get(key_name.upper())
            if key:
                keyboard.press(key)
                keyboard.release(key)
                logger.info(f"Pressed key: {key_name}")
            else:
                # Try as a character
                keyboard.press(key_name)
                keyboard.release(key_name)
                logger.info(f"Pressed character: {key_name}")
    except Exception as e:
        logger.error(f"Error pressing key: {e}")


def handle_mouse(action: str, payload: dict):
    """Handle mouse commands."""
    try:
        if action == 'move':
            x = payload.get('x', 0)
            y = payload.get('y', 0)
            mouse.move(x, y)
            logger.info(f"Mouse moved by: ({x}, {y})")
        
        elif action == 'click':
            button = payload.get('button', 'left')
            btn = Button.left if button == 'left' else Button.right
            mouse.click(btn)
            logger.info(f"Mouse {button} click")
        
        elif action == 'scroll':
            dx = payload.get('dx', 0)
            dy = payload.get('dy', 0)
            mouse.scroll(dx, dy)
            logger.info(f"Mouse scrolled: ({dx}, {dy})")
    
    except Exception as e:
        logger.error(f"Error handling mouse: {e}")


def handle_macro(macro_name: str):
    """Handle macro commands."""
    try:
        if macro_name == 'SELECT_ALL_DELETE':
            keyboard.press(Key.ctrl)
            keyboard.press('a')
            keyboard.release('a')
            keyboard.release(Key.ctrl)
            keyboard.press(Key.delete)
            keyboard.release(Key.delete)
            logger.info("Executed macro: SELECT_ALL_DELETE")
        else:
            logger.warning(f"Unknown macro: {macro_name}")
    except Exception as e:
        logger.error(f"Error executing macro: {e}")


async def handle_message(websocket: WebSocketServerProtocol, message: str):
    """Process incoming messages from the mobile app."""
    try:
        data = json.loads(message)
        msg_type = data.get('type', '')
        payload = data.get('payload', {})
        
        if msg_type == 'text':
            text = payload.get('text', '')
            if text:
                type_text(text)
        
        elif msg_type == 'key':
            key = payload.get('key', '')
            if key:
                press_key(key)
        
        elif msg_type == 'mouse':
            action = payload.get('action', '')
            handle_mouse(action, payload)
        
        elif msg_type == 'macro':
            macro = payload.get('macro', '')
            if macro:
                handle_macro(macro)
        
        else:
            logger.warning(f"Unknown message type: {msg_type}")
        
        # Send acknowledgment
        await websocket.send(json.dumps({
            'type': 'ack',
            'status': 'success'
        }))
    
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON: {message}")
        await websocket.send(json.dumps({
            'type': 'error',
            'message': 'Invalid JSON'
        }))
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await websocket.send(json.dumps({
            'type': 'error',
            'message': str(e)
        }))


async def handler(websocket: WebSocketServerProtocol):
    """Handle WebSocket connections."""
    connected_clients.add(websocket)
    client_address = websocket.remote_address
    logger.info(f"Client connected: {client_address}")
    
    try:
        async for message in websocket:
            await handle_message(websocket, message)
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Client disconnected: {client_address}")
    finally:
        connected_clients.remove(websocket)


def get_local_ip():
    """Get the local IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '127.0.0.1'


async def main():
    """Start the WebSocket server."""
    host = '0.0.0.0'
    port = 8765
    local_ip = get_local_ip()
    
    print("\n" + "="*50)
    print("       VoiceKey PC Server")
    print("="*50)
    print(f"\n  Server started on port {port}")
    print(f"\n  Connect from VoiceKey app using:")
    print(f"  --> {local_ip}:{port}")
    print(f"\n  Or if on same network:")
    print(f"  --> ws://{local_ip}:{port}")
    print("\n" + "="*50)
    print("\nWaiting for connections...\n")
    
    async with websockets.serve(handler, host, port):
        await asyncio.Future()  # Run forever


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped.")
