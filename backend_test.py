#!/usr/bin/env python3
"""
VoiceKey AI Backend API Testing Suite
Tests all backend endpoints for functionality and data integrity
"""

import requests
import json
import io
import wave
import struct
import tempfile
import os
from typing import Dict, Any, Optional

# Backend URL from environment
BACKEND_URL = "https://voicekey-ai.preview.emergentagent.com/api"

class VoiceKeyAPITester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "response_data": response_data
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        if response_data and not success:
            print(f"   Response: {response_data}")
    
    def test_health_check(self):
        """Test GET /api/health endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["status", "stt_available", "pc_connections"]
                
                if all(field in data for field in required_fields):
                    self.log_test(
                        "Health Check API", 
                        True, 
                        f"Status: {data['status']}, STT: {data['stt_available']}, PC Connections: {data['pc_connections']}", 
                        data
                    )
                else:
                    self.log_test(
                        "Health Check API", 
                        False, 
                        f"Missing required fields. Got: {list(data.keys())}", 
                        data
                    )
            else:
                self.log_test(
                    "Health Check API", 
                    False, 
                    f"HTTP {response.status_code}", 
                    response.text
                )
                
        except Exception as e:
            self.log_test("Health Check API", False, f"Exception: {str(e)}")
    
    def test_settings_api(self):
        """Test Settings API - GET and PUT"""
        try:
            # Test GET settings
            response = self.session.get(f"{self.base_url}/settings")
            
            if response.status_code == 200:
                settings = response.json()
                required_fields = ["immediate_insertion", "chunk_duration_ms", "language", "auto_punctuation", "pc_connection_enabled"]
                
                if all(field in settings for field in required_fields):
                    self.log_test(
                        "Settings API - GET", 
                        True, 
                        f"Retrieved settings with all required fields", 
                        settings
                    )
                    
                    # Test PUT settings
                    update_data = {"immediate_insertion": False}
                    put_response = self.session.put(
                        f"{self.base_url}/settings",
                        json=update_data
                    )
                    
                    if put_response.status_code == 200:
                        updated_settings = put_response.json()
                        if updated_settings.get("immediate_insertion") == False:
                            self.log_test(
                                "Settings API - PUT", 
                                True, 
                                "Successfully updated immediate_insertion to False", 
                                updated_settings
                            )
                        else:
                            self.log_test(
                                "Settings API - PUT", 
                                False, 
                                "Setting not updated correctly", 
                                updated_settings
                            )
                    else:
                        self.log_test(
                            "Settings API - PUT", 
                            False, 
                            f"HTTP {put_response.status_code}", 
                            put_response.text
                        )
                else:
                    self.log_test(
                        "Settings API - GET", 
                        False, 
                        f"Missing required fields. Got: {list(settings.keys())}", 
                        settings
                    )
            else:
                self.log_test(
                    "Settings API - GET", 
                    False, 
                    f"HTTP {response.status_code}", 
                    response.text
                )
                
        except Exception as e:
            self.log_test("Settings API", False, f"Exception: {str(e)}")
    
    def test_voice_commands_api(self):
        """Test Voice Commands CRUD API"""
        try:
            # Test GET voice commands
            response = self.session.get(f"{self.base_url}/voice-commands")
            
            if response.status_code == 200:
                commands = response.json()
                self.log_test(
                    "Voice Commands API - GET", 
                    True, 
                    f"Retrieved {len(commands)} voice commands", 
                    {"count": len(commands)}
                )
                
                # Test POST - Create new command
                new_command = {
                    "trigger": "test trigger",
                    "action": "TEST_ACTION",
                    "action_type": "key",
                    "enabled": True
                }
                
                post_response = self.session.post(
                    f"{self.base_url}/voice-commands",
                    json=new_command
                )
                
                if post_response.status_code == 200:
                    created_command = post_response.json()
                    command_id = created_command.get("id")
                    
                    if command_id and created_command.get("trigger") == "test trigger":
                        self.log_test(
                            "Voice Commands API - POST", 
                            True, 
                            f"Created command with ID: {command_id}", 
                            created_command
                        )
                        
                        # Test DELETE - Remove the created command
                        delete_response = self.session.delete(
                            f"{self.base_url}/voice-commands/{command_id}"
                        )
                        
                        if delete_response.status_code == 200:
                            self.log_test(
                                "Voice Commands API - DELETE", 
                                True, 
                                f"Successfully deleted command {command_id}", 
                                delete_response.json()
                            )
                        else:
                            self.log_test(
                                "Voice Commands API - DELETE", 
                                False, 
                                f"HTTP {delete_response.status_code}", 
                                delete_response.text
                            )
                    else:
                        self.log_test(
                            "Voice Commands API - POST", 
                            False, 
                            "Created command missing ID or incorrect data", 
                            created_command
                        )
                else:
                    self.log_test(
                        "Voice Commands API - POST", 
                        False, 
                        f"HTTP {post_response.status_code}", 
                        post_response.text
                    )
            else:
                self.log_test(
                    "Voice Commands API - GET", 
                    False, 
                    f"HTTP {response.status_code}", 
                    response.text
                )
                
        except Exception as e:
            self.log_test("Voice Commands API", False, f"Exception: {str(e)}")
    
    def create_test_audio_file(self) -> str:
        """Create a small test audio file for transcription testing"""
        # Create a simple 1-second sine wave audio file
        sample_rate = 16000
        duration = 1.0  # 1 second
        frequency = 440  # A4 note
        
        # Generate sine wave
        samples = int(sample_rate * duration)
        audio_data = []
        for i in range(samples):
            value = int(32767 * 0.3 * (i % (sample_rate // frequency)) / (sample_rate // frequency))
            audio_data.append(struct.pack('<h', value))
        
        # Create temporary WAV file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        
        with wave.open(temp_file.name, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b''.join(audio_data))
        
        return temp_file.name
    
    def test_transcription_api(self):
        """Test POST /api/transcribe endpoint with audio file"""
        try:
            # Create test audio file
            audio_file_path = self.create_test_audio_file()
            
            try:
                with open(audio_file_path, 'rb') as audio_file:
                    files = {'audio': ('test_audio.wav', audio_file, 'audio/wav')}
                    response = self.session.post(f"{self.base_url}/transcribe", files=files)
                
                if response.status_code == 200:
                    result = response.json()
                    required_fields = ["text", "success"]
                    
                    if all(field in result for field in required_fields):
                        if result.get("success"):
                            self.log_test(
                                "Transcription API", 
                                True, 
                                f"Transcription successful. Text: '{result.get('text', '')[:50]}...'", 
                                result
                            )
                        else:
                            error_msg = result.get("error", "Unknown error")
                            self.log_test(
                                "Transcription API", 
                                False, 
                                f"Transcription failed: {error_msg}", 
                                result
                            )
                    else:
                        self.log_test(
                            "Transcription API", 
                            False, 
                            f"Missing required fields. Got: {list(result.keys())}", 
                            result
                        )
                else:
                    self.log_test(
                        "Transcription API", 
                        False, 
                        f"HTTP {response.status_code}", 
                        response.text
                    )
            finally:
                # Clean up temp file
                if os.path.exists(audio_file_path):
                    os.unlink(audio_file_path)
                    
        except Exception as e:
            self.log_test("Transcription API", False, f"Exception: {str(e)}")
    
    def test_connected_pcs_api(self):
        """Test GET /api/connected-pcs endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/connected-pcs")
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["count", "client_ids"]
                
                if all(field in data for field in required_fields):
                    self.log_test(
                        "Connected PCs API", 
                        True, 
                        f"Count: {data['count']}, Client IDs: {data['client_ids']}", 
                        data
                    )
                else:
                    self.log_test(
                        "Connected PCs API", 
                        False, 
                        f"Missing required fields. Got: {list(data.keys())}", 
                        data
                    )
            else:
                self.log_test(
                    "Connected PCs API", 
                    False, 
                    f"HTTP {response.status_code}", 
                    response.text
                )
                
        except Exception as e:
            self.log_test("Connected PCs API", False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        """Run all backend API tests"""
        print(f"🚀 Starting VoiceKey AI Backend API Tests")
        print(f"📍 Backend URL: {self.base_url}")
        print("=" * 60)
        
        # Run all tests
        self.test_health_check()
        self.test_settings_api()
        self.test_voice_commands_api()
        self.test_transcription_api()
        self.test_connected_pcs_api()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {total - passed}/{total}")
        
        if total - passed > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['test']}: {result['details']}")
        
        return passed == total

def main():
    """Main test execution"""
    tester = VoiceKeyAPITester(BACKEND_URL)
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed!")
        return 1

if __name__ == "__main__":
    exit(main())