from app.core.interfaces import ExecutionProvider
from typing import Dict, Any

class MockBrokerAdapter(ExecutionProvider):
    def submit_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        print(f"MockBrokerAdapter submitting order: {order}")
        return {"status": "SUBMITTED", "order_id": "mock_123"}

    def cancel_order(self, order_id: str) -> bool:
        print(f"MockBrokerAdapter cancelling order: {order_id}")
        return True
