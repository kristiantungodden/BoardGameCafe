"""Vipps payment provider integration."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from decimal import Decimal
import requests
from config import settings


class PaymentProvider(ABC):
    """Abstract payment provider interface."""
    
    @abstractmethod
    def charge(self, amount: Decimal, customer_id: int, reference: str, description: str) -> Dict[str, Any]:
        """Charge a customer."""
        pass
    
    @abstractmethod
    def refund(self, transaction_id: str, amount: Optional[Decimal] = None) -> Dict[str, Any]:
        """Refund a payment."""
        pass
    
    @abstractmethod
    def check_status(self, transaction_id: str) -> Dict[str, Any]:
        """Check payment status."""
        pass


class VippsPaymentProvider(PaymentProvider):
    """Vipps payment provider implementation."""
    
    def __init__(self):
        """Initialize Vipps provider with API credentials."""
        self.api_key = getattr(settings, 'vipps_api_key', '')
        self.merchant_id = getattr(settings, 'vipps_merchant_id', '')
        self.base_url = getattr(settings, 'vipps_api_url', 'https://api.vipps.no')
        self.timeout = 30
    
    def charge(self, amount: Decimal, customer_id: int, reference: str, description: str) -> Dict[str, Any]:
        """
        Charge a customer using Vipps.
        
        Args:
            amount: Amount to charge in NOK
            customer_id: Customer ID for reference
            reference: Unique transaction reference
            description: Payment description
            
        Returns:
            Dict with transaction details including transaction_id and status
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            }
            
            payload = {
                'merchantInfo': {
                    'merchantSerialNumber': self.merchant_id,
                },
                'transaction': {
                    'amount': int(amount * 100),  # Convert to øre
                    'transactionText': description,
                    'transactionId': reference,
                },
                'customerInfo': {
                    'mobileNumber': '',  # Phone number integration TBD
                },
                'redirectUrl': getattr(settings, 'vipps_callback_url', 'http://localhost:8000/payment/callback'),
            }
            
            response = requests.post(
                f'{self.base_url}/ecomm/v2/payments',
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            
            if response.status_code == 201:
                data = response.json()
                return {
                    'success': True,
                    'transaction_id': data.get('orderId'),
                    'status': 'initiated',
                    'provider_response': data,
                }
            else:
                return {
                    'success': False,
                    'error': f'Vipps API error: {response.status_code}',
                    'provider_response': response.text,
                }
        except requests.RequestException as e:
            return {
                'success': False,
                'error': f'Vipps connection error: {str(e)}',
            }
    
    def refund(self, transaction_id: str, amount: Optional[Decimal] = None) -> Dict[str, Any]:
        """
        Refund a Vipps payment.
        
        Args:
            transaction_id: Vipps transaction ID to refund
            amount: Optional partial refund amount
            
        Returns:
            Dict with refund status
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            }
            
            endpoint = f'{self.base_url}/ecomm/v2/payments/{transaction_id}/refund'
            
            payload = {}
            if amount:
                payload['refundAmount'] = int(amount * 100)  # Convert to øre
            
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            
            if response.status_code in [200, 201]:
                return {
                    'success': True,
                    'status': 'refunded',
                    'provider_response': response.json(),
                }
            else:
                return {
                    'success': False,
                    'error': f'Vipps refund error: {response.status_code}',
                    'provider_response': response.text,
                }
        except requests.RequestException as e:
            return {
                'success': False,
                'error': f'Vipps connection error: {str(e)}',
            }
    
    def check_status(self, transaction_id: str) -> Dict[str, Any]:
        """
        Check payment status with Vipps.
        
        Args:
            transaction_id: Vipps transaction ID
            
        Returns:
            Dict with payment status
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
            }
            
            response = requests.get(
                f'{self.base_url}/ecomm/v2/payments/{transaction_id}/details',
                headers=headers,
                timeout=self.timeout,
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'status': data.get('transactionInfo', {}).get('status', 'unknown'),
                    'provider_response': data,
                }
            else:
                return {
                    'success': False,
                    'error': f'Vipps query error: {response.status_code}',
                }
        except requests.RequestException as e:
            return {
                'success': False,
                'error': f'Vipps connection error: {str(e)}',
            }


class MockPaymentProvider(PaymentProvider):
    """Mock payment provider for testing."""
    
    def __init__(self):
        """Initialize mock provider."""
        self.transactions = {}
    
    def charge(self, amount: Decimal, customer_id: int, reference: str, description: str) -> Dict[str, Any]:
        """Mock charge operation."""
        transaction_id = f'MOCK-{reference}'
        self.transactions[transaction_id] = {
            'amount': amount,
            'customer_id': customer_id,
            'status': 'completed',
            'description': description,
        }
        return {
            'success': True,
            'transaction_id': transaction_id,
            'status': 'completed',
        }
    
    def refund(self, transaction_id: str, amount: Optional[Decimal] = None) -> Dict[str, Any]:
        """Mock refund operation."""
        if transaction_id in self.transactions:
            self.transactions[transaction_id]['status'] = 'refunded'
            return {'success': True, 'status': 'refunded'}
        return {'success': False, 'error': 'Transaction not found'}
    
    def check_status(self, transaction_id: str) -> Dict[str, Any]:
        """Mock check status operation."""
        if transaction_id in self.transactions:
            return {
                'success': True,
                'status': self.transactions[transaction_id]['status'],
            }
        return {'success': False, 'error': 'Transaction not found'}


def get_payment_provider() -> PaymentProvider:
    """Get payment provider instance based on configuration."""
    if getattr(settings, 'debug', False):
        return MockPaymentProvider()
    return VippsPaymentProvider()
