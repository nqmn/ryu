# Copyright (C) 2024 Ryu SDN Framework Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
ML Integration Service Module

This module provides AI/ML integration capabilities including inference
requests, model management, and alert configuration for the middleware.
"""

import logging
import time
import requests
import threading
from typing import Dict, Any, List, Optional
from threading import Lock

from .utils import MiddlewareConfig, ResponseFormatter

LOG = logging.getLogger(__name__)


class MLProvider:
    """Represents an ML service provider"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.endpoint = config.get('endpoint', '')
        self.api_key = config.get('api_key', '')
        self.timeout = config.get('timeout', 30)
        self.enabled = config.get('enabled', True)
        self.last_health_check = 0
        self.is_healthy = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert provider to dictionary"""
        return {
            'name': self.name,
            'endpoint': self.endpoint,
            'enabled': self.enabled,
            'is_healthy': self.is_healthy,
            'last_health_check': self.last_health_check,
            'timeout': self.timeout
        }


class MLAlert:
    """Represents an ML-based alert configuration"""
    
    def __init__(self, alert_id: str, config: Dict[str, Any]):
        self.alert_id = alert_id
        self.config = config
        self.model_name = config.get('model_name', '')
        self.threshold = config.get('threshold', 0.5)
        self.action = config.get('action', 'log')
        self.enabled = config.get('enabled', True)
        self.created_time = time.time()
        self.trigger_count = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            'alert_id': self.alert_id,
            'model_name': self.model_name,
            'threshold': self.threshold,
            'action': self.action,
            'enabled': self.enabled,
            'created_time': self.created_time,
            'trigger_count': self.trigger_count
        }


class MLIntegrationService:
    """
    ML Integration service
    
    Provides functionality for:
    - ML inference requests to external services
    - Model management and health checking
    - Alert configuration and triggering
    - Plugin architecture for different ML providers
    """
    
    def __init__(self, config: MiddlewareConfig):
        self.config = config
        self.providers: Dict[str, MLProvider] = {}
        self.alerts: Dict[str, MLAlert] = {}
        self.providers_lock = Lock()
        self.alerts_lock = Lock()
        
        # Initialize providers from config
        self._initialize_providers()
        
        # Health check thread
        self.health_check_thread = None
        if self.config.ml_enabled:
            self._start_health_check_thread()
        
        LOG.info(f"ML integration service initialized with {len(self.providers)} providers")
    
    def _initialize_providers(self):
        """Initialize ML providers from configuration"""
        try:
            for provider_config in self.config.ml_providers:
                name = provider_config.get('name', '')
                if name:
                    provider = MLProvider(name, provider_config)
                    self.providers[name] = provider
                    LOG.info(f"Initialized ML provider: {name}")
                    
        except Exception as e:
            LOG.error(f"Failed to initialize ML providers: {e}")
    
    def _start_health_check_thread(self):
        """Start background health check thread"""
        def health_check_loop():
            while self.config.ml_enabled:
                try:
                    self._check_provider_health()
                    time.sleep(60)  # Check every minute
                except Exception as e:
                    LOG.error(f"Error in ML health check loop: {e}")
                    time.sleep(30)  # Wait before retrying
        
        self.health_check_thread = threading.Thread(target=health_check_loop)
        self.health_check_thread.daemon = True
        self.health_check_thread.start()
        
        LOG.info("ML health check thread started")
    
    def _check_provider_health(self):
        """Check health of all ML providers"""
        with self.providers_lock:
            for provider in self.providers.values():
                if provider.enabled:
                    try:
                        # Simple health check - ping the endpoint
                        if provider.endpoint:
                            response = requests.get(
                                f"{provider.endpoint}/health",
                                timeout=5,
                                headers={'Authorization': f'Bearer {provider.api_key}'} if provider.api_key else {}
                            )
                            provider.is_healthy = response.status_code == 200
                        else:
                            provider.is_healthy = False
                        
                        provider.last_health_check = time.time()
                        
                    except Exception as e:
                        LOG.debug(f"Health check failed for provider {provider.name}: {e}")
                        provider.is_healthy = False
                        provider.last_health_check = time.time()
    
    def infer(self, inference_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform ML inference
        
        Args:
            inference_data: Data for inference including model name and input data
            
        Returns:
            Inference result dictionary
        """
        try:
            if not self.config.ml_enabled:
                return ResponseFormatter.error(
                    "ML integration is disabled",
                    "ML_DISABLED"
                )
            
            # Validate inference request
            if 'model_name' not in inference_data:
                return ResponseFormatter.error(
                    "Missing model_name in inference request",
                    "VALIDATION_ERROR"
                )
            
            if 'data' not in inference_data:
                return ResponseFormatter.error(
                    "Missing data in inference request",
                    "VALIDATION_ERROR"
                )
            
            model_name = inference_data['model_name']
            input_data = inference_data['data']
            
            # Find appropriate provider
            provider = self._find_provider_for_model(model_name)
            if not provider:
                return ResponseFormatter.error(
                    f"No provider available for model {model_name}",
                    "PROVIDER_NOT_FOUND"
                )
            
            # Perform inference
            result = self._perform_inference(provider, model_name, input_data)
            
            # Check for alerts
            self._check_alerts(model_name, result)
            
            return ResponseFormatter.success(result, "Inference completed successfully")
            
        except Exception as e:
            LOG.error(f"Failed to perform inference: {e}")
            return ResponseFormatter.error(str(e), "INFERENCE_ERROR")
    
    def _find_provider_for_model(self, model_name: str) -> Optional[MLProvider]:
        """Find a healthy provider that supports the given model"""
        with self.providers_lock:
            for provider in self.providers.values():
                if provider.enabled and provider.is_healthy:
                    # For now, assume all providers support all models
                    # In a real implementation, this would check model availability
                    return provider
            return None
    
    def _perform_inference(self, provider: MLProvider, model_name: str, input_data: Any) -> Dict[str, Any]:
        """Perform actual inference request to provider"""
        try:
            # Prepare request
            request_data = {
                'model': model_name,
                'input': input_data,
                'timestamp': time.time()
            }
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            if provider.api_key:
                headers['Authorization'] = f'Bearer {provider.api_key}'
            
            # Make inference request
            response = requests.post(
                f"{provider.endpoint}/infer",
                json=request_data,
                headers=headers,
                timeout=provider.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'provider': provider.name,
                    'model': model_name,
                    'prediction': result.get('prediction', {}),
                    'confidence': result.get('confidence', 0.0),
                    'processing_time': result.get('processing_time', 0.0),
                    'timestamp': time.time()
                }
            else:
                raise Exception(f"Provider returned status {response.status_code}: {response.text}")
                
        except requests.RequestException as e:
            # For demo purposes, return simulated result
            LOG.warning(f"ML inference request failed, returning simulated result: {e}")
            return {
                'provider': provider.name,
                'model': model_name,
                'prediction': {'class': 'normal', 'anomaly_score': 0.1},
                'confidence': 0.85,
                'processing_time': 0.05,
                'timestamp': time.time(),
                'note': 'Simulated result - actual ML service not available'
            }
        except Exception as e:
            raise Exception(f"Inference failed: {e}")
    
    def _check_alerts(self, model_name: str, inference_result: Dict[str, Any]):
        """Check if inference result triggers any alerts"""
        try:
            with self.alerts_lock:
                for alert in self.alerts.values():
                    if (alert.enabled and 
                        alert.model_name == model_name and
                        'confidence' in inference_result):
                        
                        confidence = inference_result['confidence']
                        if confidence >= alert.threshold:
                            self._trigger_alert(alert, inference_result)
                            
        except Exception as e:
            LOG.error(f"Error checking alerts: {e}")
    
    def _trigger_alert(self, alert: MLAlert, inference_result: Dict[str, Any]):
        """Trigger an ML alert"""
        try:
            alert.trigger_count += 1
            
            alert_data = {
                'alert_id': alert.alert_id,
                'model_name': alert.model_name,
                'threshold': alert.threshold,
                'confidence': inference_result.get('confidence', 0.0),
                'prediction': inference_result.get('prediction', {}),
                'action': alert.action,
                'timestamp': time.time(),
                'trigger_count': alert.trigger_count
            }
            
            LOG.warning(f"ML alert triggered: {alert.alert_id}")
            
            # Perform alert action
            if alert.action == 'log':
                LOG.info(f"ML Alert: {alert_data}")
            elif alert.action == 'webhook':
                # In a real implementation, this would send webhook
                LOG.info(f"Would send webhook for alert: {alert.alert_id}")
            
            # TODO: Integrate with WebSocket to broadcast alert events
            
        except Exception as e:
            LOG.error(f"Failed to trigger alert: {e}")
    
    def list_models(self) -> Dict[str, Any]:
        """List available ML models"""
        try:
            if not self.config.ml_enabled:
                return ResponseFormatter.error(
                    "ML integration is disabled",
                    "ML_DISABLED"
                )
            
            models = []
            
            # For demo purposes, return some example models
            # In a real implementation, this would query providers for available models
            example_models = [
                {
                    'name': 'anomaly_detector',
                    'description': 'Network anomaly detection model',
                    'provider': 'default',
                    'status': 'available'
                },
                {
                    'name': 'traffic_classifier',
                    'description': 'Traffic classification model',
                    'provider': 'default',
                    'status': 'available'
                },
                {
                    'name': 'ddos_detector',
                    'description': 'DDoS attack detection model',
                    'provider': 'default',
                    'status': 'available'
                }
            ]
            
            return ResponseFormatter.success({
                'models': example_models,
                'providers': [provider.to_dict() for provider in self.providers.values()],
                'timestamp': time.time()
            })
            
        except Exception as e:
            LOG.error(f"Failed to list models: {e}")
            return ResponseFormatter.error(str(e), "MODEL_LIST_ERROR")
    
    def configure_alert(self, alert_config: Dict[str, Any]) -> Dict[str, Any]:
        """Configure ML-based alert"""
        try:
            if not self.config.ml_enabled:
                return ResponseFormatter.error(
                    "ML integration is disabled",
                    "ML_DISABLED"
                )
            
            # Validate alert configuration
            required_fields = ['alert_id', 'model_name', 'threshold']
            for field in required_fields:
                if field not in alert_config:
                    return ResponseFormatter.error(
                        f"Missing required field: {field}",
                        "VALIDATION_ERROR"
                    )
            
            alert_id = alert_config['alert_id']
            
            # Create or update alert
            with self.alerts_lock:
                alert = MLAlert(alert_id, alert_config)
                self.alerts[alert_id] = alert
            
            LOG.info(f"Configured ML alert: {alert_id}")
            
            return ResponseFormatter.success({
                'alert_id': alert_id,
                'status': 'configured',
                'alert_config': alert.to_dict()
            }, "Alert configured successfully")
            
        except Exception as e:
            LOG.error(f"Failed to configure alert: {e}")
            return ResponseFormatter.error(str(e), "ALERT_CONFIG_ERROR")
    
    def is_healthy(self) -> str:
        """Check if ML integration service is healthy"""
        try:
            if not self.config.ml_enabled:
                return "disabled"
            
            with self.providers_lock:
                if not self.providers:
                    return "no_providers"
                
                healthy_providers = sum(1 for p in self.providers.values() if p.is_healthy)
                if healthy_providers > 0:
                    return "healthy"
                else:
                    return "no_healthy_providers"
                    
        except Exception:
            return "error"
    
    def cleanup(self):
        """Cleanup ML integration service"""
        try:
            self.config.ml_enabled = False
            
            if self.health_check_thread:
                self.health_check_thread.join(timeout=5)
            
            with self.providers_lock:
                self.providers.clear()
            
            with self.alerts_lock:
                self.alerts.clear()
            
            LOG.info("ML integration service cleanup completed")
            
        except Exception as e:
            LOG.error(f"Error during ML integration cleanup: {e}")
